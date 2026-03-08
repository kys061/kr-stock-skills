# Design: kr-stock-analysis 매수구간/매도타점 기능 추가

> Feature: buy-sell-target
> Created: 2026-03-08
> Status: Design
> Plan Reference: `docs/01-plan/features/buy-sell-target.plan.md`

## 1. 아키텍처 개요

기존 kr-stock-analysis 파이프라인 끝에 **매수/매도 산출 레이어**를 추가한다.
기존 5-컴포넌트 스코어링과 US 오버레이 로직은 일절 수정하지 않는다.

```
[기존 파이프라인]
  Fundamental → Technical → Supply/Demand → Valuation → Growth Quick
       ↓              ↓
  calc_comprehensive_score()  →  apply_monetary_overlay()
                                         ↓
                              [신규] calc_buy_sell_targets()
                                         ↓
                              리포트 섹션 13. 매수/매도 전략
```

## 2. 수정 파일 목록

| # | 파일 | 변경 내용 | LOC 예상 |
|:-:|------|----------|:--------:|
| F-1 | `scripts/technical_analyzer.py` | `calc_support_resistance()` 함수 추가 | +60 |
| F-2 | `scripts/comprehensive_scorer.py` | `calc_buy_sell_targets()`, `calc_rr_ratio()` 함수 추가 | +120 |
| F-3 | `scripts/tests/test_stock_analysis.py` | 테스트 클래스 3개 추가 (~28 테스트) | +250 |
| F-4 | `SKILL.md` (skills/kr-stock-analysis/) | 매수구간/매도타점 섹션 추가 | +60 |
| F-5 | `~/.claude/skills/kr-stock-analysis/SKILL.md` | F-4 동기화 | 동일 |

### 비수정 파일 (명시적 확인)

| 파일 | 이유 |
|------|------|
| `fundamental_analyzer.py` | 변경 없음 |
| `supply_demand_analyzer.py` | 변경 없음 |
| `growth_quick_scorer.py` | 변경 없음 |
| `report_generator.py` | 변경 없음 |
| `_kr_common/templates/` | 변경 없음 |
| `install.sh` | 스킬 수 변경 없음 |
| `README.md` | 스킬 수 변경 없음 |

---

## 3. F-1: technical_analyzer.py — `calc_support_resistance()`

### 3-1. 함수 시그니처

```python
def calc_support_resistance(
    current_price: float,
    ma_data: dict,              # calc_moving_averages() 결과
    bb_data: dict | None,       # calc_bollinger_bands() 결과
    week52_high: float | None,
    week52_low: float | None,
) -> dict:
    """지지선/저항선 산출.

    Args:
        current_price: 현재가
        ma_data: {'ma20': float, 'ma60': float, 'ma120': float}
        bb_data: {'upper': float, 'lower': float, ...} or None
        week52_high: 52주 최고가 (None 허용)
        week52_low: 52주 최저가 (None 허용)

    Returns:
        {
            'supports': [float, ...],    # 현재가 아래 지지선 (내림차순)
            'resistances': [float, ...], # 현재가 위 저항선 (오름차순)
        }
    """
```

### 3-2. 산출 로직

```python
def calc_support_resistance(current_price, ma_data, bb_data, week52_high, week52_low):
    levels = []

    # 이동평균선
    for key in ('ma20', 'ma60', 'ma120'):
        val = ma_data.get(key)
        if val is not None and val > 0:
            levels.append(val)

    # 볼린저 밴드
    if bb_data:
        if bb_data.get('lower'):
            levels.append(bb_data['lower'])
        if bb_data.get('upper'):
            levels.append(bb_data['upper'])

    # 52주 고/저
    if week52_high and week52_high > 0:
        levels.append(week52_high)
    if week52_low and week52_low > 0:
        levels.append(week52_low)

    # 분류
    supports = sorted(
        [lv for lv in levels if lv < current_price],
        reverse=True  # 현재가에 가까운 순
    )
    resistances = sorted(
        [lv for lv in levels if lv > current_price]
    )

    return {
        'supports': supports,
        'resistances': resistances,
    }
```

### 3-3. 설계 상수

없음 (순수 데이터 정렬 함수)

---

## 4. F-2: comprehensive_scorer.py — 매수/매도 산출

### 4-1. 상수 정의

```python
# ─── 매수/매도 타점 상수 ───

BUY_ZONE_CONFIG = {
    'buy1_range': (-0.03, -0.10),   # 1차 매수: 현재가 대비 -3% ~ -10%
    'buy2_range': (-0.05, -0.15),   # 2차 매수: 1차 매수 대비 -5% ~ -15%
    'stop_loss_ma_margin': 0.03,    # MA120 대비 -3% 하회
    'stop_loss_buy2_margin': 0.05,  # 2차 매수가 대비 -5%
    'buy2_fallback_ratio': 0.93,    # 1차 매수 × 0.93
    'week52_low_buffer': 1.05,      # 52주 저점 × 1.05
}

SELL_TARGET_CONFIG = {
    'sell1_range': (0.05, 0.20),    # 1차 목표: 현재가 대비 +5% ~ +20%
    'sell2_multiplier': 1.10,       # 2차 목표: 1차 목표 × 1.10
    'trailing_stop_default': 0.10,  # 기본 10%
    'trailing_stop_high_beta': 0.15,  # Beta > 1.5 → 15%
    'trailing_stop_low_beta': 0.07,   # Beta < 0.8 → 7%
    'beta_high_threshold': 1.5,
    'beta_low_threshold': 0.8,
}

RR_RATIO_LABELS = {
    3.0: '매우 유리',
    2.0: '유리',
    1.0: '보통',
    0.0: '불리 — 진입 재고 필요',
}

# 등급별 매수/매도 표시 규칙
GRADE_DISPLAY_RULES = {
    'STRONG_BUY': {'show_buy': True,  'show_sell': True,  'buy_label': '적극 매수구간'},
    'BUY':        {'show_buy': True,  'show_sell': True,  'buy_label': '매수구간'},
    'HOLD':       {'show_buy': False, 'show_sell': True,  'buy_label': '추가 매수 비추, 보유 유지'},
    'SELL':       {'show_buy': False, 'show_sell': True,  'buy_label': None},
    'STRONG_SELL':{'show_buy': False, 'show_sell': True,  'buy_label': None},
}
```

**상수 총 개수: 19개**

### 4-2. `calc_buy_sell_targets()` 함수

```python
def calc_buy_sell_targets(
    current_price: float,
    grade: str,
    supports: list[float],
    resistances: list[float],
    target_mean: float | None = None,
    target_high: float | None = None,
    target_low: float | None = None,
    week52_high: float | None = None,
    week52_low: float | None = None,
    beta: float | None = None,
) -> dict:
    """매수구간/매도타점 산출.

    Args:
        current_price: 현재가
        grade: 투자 등급 ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL')
        supports: 지지선 목록 (현재가 아래, 내림차순)
        resistances: 저항선 목록 (현재가 위, 오름차순)
        target_mean: 컨센서스 목표가 평균 (None 허용)
        target_high: 컨센서스 목표가 상단 (None 허용)
        target_low: 컨센서스 목표가 하단 (None 허용)
        week52_high: 52주 고가 (None 허용)
        week52_low: 52주 저가 (None 허용)
        beta: 베타 (None 허용)

    Returns:
        {
            'buy_zone': {
                'show': bool,
                'label': str,
                'buy_1': {'price': float, 'pct': float, 'reason': str},
                'buy_2': {'price': float, 'pct': float, 'reason': str},
                'stop_loss': {'price': float, 'pct': float, 'reason': str},
            } | None,
            'sell_target': {
                'show': bool,
                'sell_1': {'price': float, 'pct': float, 'reason': str, 'portion': '50%'},
                'sell_2': {'price': float, 'pct': float, 'reason': str, 'portion': '잔량'},
                'trailing_stop': {'pct': float, 'reason': str},
            } | None,
            'rr_ratio': {
                'ratio': float,
                'label': str,
                'expected_profit_pct': float,
                'expected_loss_pct': float,
            } | None,
            'disclaimer': str,
        }
    """
```

### 4-3. 핵심 산출 로직

#### 1차 매수가 산출
```python
cfg = BUY_ZONE_CONFIG
lo, hi = cfg['buy1_range']  # (-0.03, -0.10)

# 후보: supports 중 현재가 대비 -3% ~ -10% 범위 내
candidates = []
for s in supports:
    pct = (s - current_price) / current_price
    if lo >= pct >= hi:  # -3% ~ -10%
        candidates.append(s)

if candidates:
    buy_1 = max(candidates)  # 가장 가까운 지지선
    reason = _identify_level_name(buy_1, ma_data, bb_data, week52_low)
else:
    # 폴백: 현재가 × 0.95 (5% 하방)
    buy_1 = round(current_price * 0.95)
    reason = '현재가 대비 -5% (기본값)'
```

#### 2차 매수가 산출
```python
candidates_2 = []
lo2, hi2 = cfg['buy2_range']  # (-0.05, -0.15)

for s in supports:
    pct = (s - buy_1) / buy_1
    if lo2 >= pct >= hi2:
        candidates_2.append(s)

if candidates_2:
    buy_2 = max(candidates_2)
    reason_2 = _identify_level_name(buy_2, ...)
else:
    # 폴백 우선순위: week52_low × 1.05 > buy_1 × 0.93
    if week52_low and week52_low * cfg['week52_low_buffer'] < buy_1:
        buy_2 = round(week52_low * cfg['week52_low_buffer'])
        reason_2 = '52주 저점 × 1.05'
    else:
        buy_2 = round(buy_1 * cfg['buy2_fallback_ratio'])
        reason_2 = '1차 매수 × 0.93'
```

#### 손절가 산출
```python
ma120 = ma_data.get('ma120')
stop_candidates = []
if ma120:
    stop_candidates.append(round(ma120 * (1 - cfg['stop_loss_ma_margin'])))
stop_candidates.append(round(buy_2 * (1 - cfg['stop_loss_buy2_margin'])))

stop_loss = min(stop_candidates)
stop_reason = 'MA120 이탈' if (ma120 and stop_loss == round(ma120 * 0.97)) else '2차 매수 -5%'
```

#### 1차 목표가 산출
```python
scfg = SELL_TARGET_CONFIG
lo_s, hi_s = scfg['sell1_range']  # (0.05, 0.20)

sell_candidates = []
# 컨센서스 목표가
if target_mean and target_mean > current_price:
    pct = (target_mean - current_price) / current_price
    if lo_s <= pct <= hi_s:
        sell_candidates.append((target_mean, '컨센서스 목표가 평균'))

# 저항선
for r in resistances:
    pct = (r - current_price) / current_price
    if lo_s <= pct <= hi_s:
        sell_candidates.append((r, _identify_level_name(r, ...)))

if sell_candidates:
    sell_candidates.sort(key=lambda x: x[0])
    sell_1, sell_1_reason = sell_candidates[0]  # 가장 가까운 저항
else:
    # 폴백: 현재가 × 1.10
    sell_1 = round(current_price * 1.10)
    sell_1_reason = '현재가 대비 +10% (기본값)'
```

#### 2차 목표가 산출
```python
sell_2_candidates = []
if target_high and target_high > sell_1:
    sell_2_candidates.append((target_high, '컨센서스 목표가 상단'))
if week52_high and week52_high > sell_1:
    sell_2_candidates.append((week52_high, '52주 고가'))
sell_2_candidates.append((round(sell_1 * scfg['sell2_multiplier']), '1차 목표 × 1.10'))

sell_2_candidates.sort(key=lambda x: x[0])
sell_2, sell_2_reason = sell_2_candidates[0]  # 가장 가까운 상위 저항
```

#### 트레일링 스탑
```python
if beta and beta > scfg['beta_high_threshold']:
    trailing_pct = scfg['trailing_stop_high_beta']
    trailing_reason = f'고변동성(Beta {beta:.1f}) → 15%'
elif beta and beta < scfg['beta_low_threshold']:
    trailing_pct = scfg['trailing_stop_low_beta']
    trailing_reason = f'저변동성(Beta {beta:.1f}) → 7%'
else:
    trailing_pct = scfg['trailing_stop_default']
    trailing_reason = '기본 10%'
```

### 4-4. `calc_rr_ratio()` 함수

```python
def calc_rr_ratio(
    current_price: float,
    sell_1_price: float,
    stop_loss_price: float,
) -> dict:
    """Risk/Reward Ratio 계산.

    Args:
        current_price: 현재가
        sell_1_price: 1차 목표가
        stop_loss_price: 손절가

    Returns:
        {
            'ratio': float,           # R/R 비율
            'label': str,             # '매우 유리' / '유리' / '보통' / '불리'
            'expected_profit_pct': float,  # 예상 수익률 (%)
            'expected_loss_pct': float,    # 예상 손실률 (%)
        }
    """
    expected_profit = sell_1_price - current_price
    expected_loss = current_price - stop_loss_price

    if expected_loss <= 0:
        return {
            'ratio': 99.9,
            'label': '매우 유리',
            'expected_profit_pct': round(expected_profit / current_price * 100, 1),
            'expected_loss_pct': 0.0,
        }

    ratio = round(expected_profit / expected_loss, 2)

    label = '불리 — 진입 재고 필요'
    for threshold in sorted(RR_RATIO_LABELS.keys(), reverse=True):
        if ratio >= threshold:
            label = RR_RATIO_LABELS[threshold]
            break

    return {
        'ratio': ratio,
        'label': label,
        'expected_profit_pct': round(expected_profit / current_price * 100, 1),
        'expected_loss_pct': round(expected_loss / current_price * 100, 1),
    }
```

### 4-5. 헬퍼: `_identify_level_name()`

```python
def _identify_level_name(price, ma_data, bb_data=None, week52_low=None, week52_high=None):
    """가격이 어떤 기술적 레벨에 해당하는지 문자열 반환."""
    tolerance = 0.02  # 2% 오차 허용

    if ma_data:
        for key, label in [('ma20', 'MA20'), ('ma60', 'MA60'), ('ma120', 'MA120')]:
            val = ma_data.get(key)
            if val and abs(price - val) / val <= tolerance:
                return f'{label} 지지/저항'

    if bb_data:
        if bb_data.get('lower') and abs(price - bb_data['lower']) / bb_data['lower'] <= tolerance:
            return '볼린저 하단'
        if bb_data.get('upper') and abs(price - bb_data['upper']) / bb_data['upper'] <= tolerance:
            return '볼린저 상단'

    if week52_low and abs(price - week52_low) / week52_low <= tolerance:
        return '52주 저점 근접'
    if week52_high and abs(price - week52_high) / week52_high <= tolerance:
        return '52주 고점 근접'

    return '기술적 레벨'
```

상수: `_LEVEL_TOLERANCE = 0.02` (2%)

---

## 5. F-3: 테스트 설계

### 5-1. TestCalcSupportResistance (8 테스트)

| # | 테스트명 | 입력 | 기대 출력 |
|:-:|---------|------|----------|
| T-01 | `test_basic_support_resistance` | 현재가 100, MA20=95, MA60=90, MA120=85, BB상단=110, BB하단=88 | supports=[95,90,88,85], resistances=[110] |
| T-02 | `test_with_52week` | 현재가 100, 52주고=120, 52주저=70 | 70 in supports, 120 in resistances |
| T-03 | `test_no_ma_data` | 현재가 100, ma_data={} | supports=[], resistances=[] |
| T-04 | `test_no_bb_data` | bb_data=None | BB 관련 레벨 미포함 |
| T-05 | `test_all_above` | 모든 레벨 > 현재가 | supports=[], resistances 에 전부 |
| T-06 | `test_all_below` | 모든 레벨 < 현재가 | supports에 전부, resistances=[] |
| T-07 | `test_sort_order` | 여러 supports | 내림차순 정렬 확인 |
| T-08 | `test_none_values` | MA에 None 값 | None 무시, 정상 동작 |

### 5-2. TestCalcBuySellTargets (12 테스트)

| # | 테스트명 | 시나리오 | 핵심 검증 |
|:-:|---------|---------|----------|
| T-09 | `test_buy_strong_buy_grade` | STRONG_BUY, supports=[95,90,85] | show_buy=True, buy_1 산출 |
| T-10 | `test_buy_buy_grade` | BUY, 정상 지지선 | show_buy=True |
| T-11 | `test_buy_hold_grade` | HOLD | show_buy=False |
| T-12 | `test_buy_sell_grade` | SELL | show_buy=False, show_sell=True |
| T-13 | `test_buy_strong_sell_grade` | STRONG_SELL | show_buy=False |
| T-14 | `test_sell_with_consensus` | target_mean=110 | sell_1=110 근처 |
| T-15 | `test_sell_without_consensus` | target_mean=None | 폴백 사용 |
| T-16 | `test_trailing_stop_high_beta` | beta=2.0 | trailing_pct=0.15 |
| T-17 | `test_trailing_stop_low_beta` | beta=0.5 | trailing_pct=0.07 |
| T-18 | `test_trailing_stop_default_beta` | beta=1.0 | trailing_pct=0.10 |
| T-19 | `test_trailing_stop_no_beta` | beta=None | trailing_pct=0.10 |
| T-20 | `test_disclaimer_always_present` | 아무 등급 | disclaimer 문자열 존재 |

### 5-3. TestCalcRrRatio (5 테스트)

| # | 테스트명 | 입력 | 기대 출력 |
|:-:|---------|------|----------|
| T-21 | `test_rr_favorable` | 수익 30, 손실 10 | ratio=3.0, '매우 유리' |
| T-22 | `test_rr_moderate` | 수익 20, 손실 10 | ratio=2.0, '유리' |
| T-23 | `test_rr_neutral` | 수익 10, 손실 10 | ratio=1.0, '보통' |
| T-24 | `test_rr_unfavorable` | 수익 5, 손실 10 | ratio=0.5, '불리' |
| T-25 | `test_rr_zero_loss` | 손절가 >= 현재가 | ratio=99.9, '매우 유리' |

### 5-4. TestEdgeCases (3 테스트)

| # | 테스트명 | 시나리오 | 핵심 검증 |
|:-:|---------|---------|----------|
| T-26 | `test_no_supports` | supports=[] | 폴백 buy_1 = 현재가 × 0.95 |
| T-27 | `test_no_resistances` | resistances=[] | 폴백 sell_1 = 현재가 × 1.10 |
| T-28 | `test_all_none` | 모든 optional=None | 폴백 동작, 에러 없음 |

**총 테스트: 28개**

---

## 6. F-4: SKILL.md 추가 섹션

SKILL.md의 `## 투자 등급` 섹션 뒤에 추가:

```markdown
## 매수구간/매도타점 (Buy Zone & Sell Target)

종합 분석 완료 후 투자 등급에 따라 **구체적인 매수 가격대와 매도 가격대**를 산출한다.

### 매수구간 산출

| 항목 | 산출 기준 | 비중 |
|------|----------|:----:|
| 1차 매수 | 지지선 중 현재가 대비 -3%~-10% 범위 최고가 | 50% |
| 2차 매수 | 지지선 중 1차 대비 -5%~-15% 범위, 52주저×1.05 폴백 | 50% |
| 손절가 | MA120×0.97, 2차매수×0.95 중 최저 | 전량 |

### 매도타점 산출

| 항목 | 산출 기준 | 비중 |
|------|----------|:----:|
| 1차 목표 | 저항선/컨센서스 중 현재가 +5%~+20% 범위 최저가 | 50% |
| 2차 목표 | 컨센서스 상단, 52주 고가, 1차×1.10 중 최저 | 잔량 |
| 트레일링 스탑 | Beta>1.5→15%, Beta<0.8→7%, 기본 10% | 전량 |

### 등급별 표시 규칙

| 등급 | 매수구간 | 매도타점 |
|------|:-------:|:-------:|
| STRONG_BUY | ✅ 적극 매수구간 | ✅ 목표가 |
| BUY | ✅ 매수구간 | ✅ 목표가 |
| HOLD | ❌ (보유 유지) | ✅ 매도타점 |
| SELL | ❌ | ✅ 청산 기준 |
| STRONG_SELL | ❌ | ✅ 즉시 청산 |

### R/R Ratio 판단

| R/R | 판단 |
|:---:|------|
| ≥ 3.0 | 매우 유리 |
| ≥ 2.0 | 유리 |
| ≥ 1.0 | 보통 |
| < 1.0 | 불리 — 진입 재고 필요 |
```

---

## 7. 구현 순서

| Step | 작업 | 의존성 |
|:----:|------|--------|
| 1 | `technical_analyzer.py`에 `calc_support_resistance()` 추가 | 없음 |
| 2 | `comprehensive_scorer.py`에 상수 + `_identify_level_name()` 추가 | 없음 |
| 3 | `comprehensive_scorer.py`에 `calc_buy_sell_targets()` 추가 | Step 1, 2 |
| 4 | `comprehensive_scorer.py`에 `calc_rr_ratio()` 추가 | 없음 |
| 5 | `test_stock_analysis.py`에 28 테스트 추가 | Step 1-4 |
| 6 | 테스트 실행 (`python -m pytest tests/ -v`) | Step 5 |
| 7 | `SKILL.md` 업데이트 + `~/.claude/skills/` 동기화 | Step 6 통과 후 |

---

## 8. 검증 기준 (Gap Analysis 체크리스트)

| # | 항목 | 기준 | 가중치 |
|:-:|------|------|:------:|
| V-01 | `calc_support_resistance()` 존재 및 시그니처 일치 | F-1 설계대로 | 10% |
| V-02 | `BUY_ZONE_CONFIG` 상수 7개 | 값 정확 일치 | 5% |
| V-03 | `SELL_TARGET_CONFIG` 상수 7개 | 값 정확 일치 | 5% |
| V-04 | `RR_RATIO_LABELS` 상수 4개 | 값 정확 일치 | 3% |
| V-05 | `GRADE_DISPLAY_RULES` 상수 5개 | 값 정확 일치 | 5% |
| V-06 | `_LEVEL_TOLERANCE` 상수 | 0.02 | 2% |
| V-07 | `calc_buy_sell_targets()` 존재 및 시그니처 일치 | F-2 설계대로 | 15% |
| V-08 | `calc_rr_ratio()` 존재 및 시그니처 일치 | F-2 설계대로 | 10% |
| V-09 | `_identify_level_name()` 존재 | 헬퍼 함수 | 5% |
| V-10 | 기존 테스트 0 failures | 하위호환 100% | 15% |
| V-11 | 신규 테스트 28개 전원 Pass | T-01 ~ T-28 | 15% |
| V-12 | SKILL.md 매수/매도 섹션 존재 | F-4 설계대로 | 5% |
| V-13 | `~/.claude/skills/` 동기화 완료 | diff 0 | 5% |

**상수 합계: 19 + 1(_LEVEL_TOLERANCE) = 20개**
**함수 합계: 4개** (`calc_support_resistance`, `calc_buy_sell_targets`, `calc_rr_ratio`, `_identify_level_name`)

---

## 9. 하위호환성

| 항목 | 영향 |
|------|------|
| `calc_comprehensive_score()` | **수정 없음** — 기존 시그니처 유지 |
| `apply_monetary_overlay()` | **수정 없음** |
| `analyze_technicals()` | **수정 없음** — `calc_support_resistance`는 별도 함수 |
| 기존 73 테스트 | **0 failures 보장** |
| 리포트 출력 | 섹션 13 추가만 — 기존 섹션 1-12 변경 없음 |

---

## 10. 면책 조항 상수

```python
DISCLAIMER = (
    "본 매수/매도 가격은 기술적 분석과 컨센서스 기반 참고 정보이며, "
    "투자 판단의 최종 책임은 투자자 본인에게 있습니다."
)
```

**총 상수: 21개 (BUY_ZONE_CONFIG 7 + SELL_TARGET_CONFIG 7 + RR_RATIO_LABELS 4 + GRADE_DISPLAY_RULES 5엔트리 + _LEVEL_TOLERANCE 1 + DISCLAIMER 1 = 21)**
