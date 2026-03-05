# us-monetary-regime Design Document

> **Summary**: US 통화정책 분석 독립 스킬 + B방식 오버레이 통합 상세 설계
>
> **Plan Reference**: `docs/01-plan/features/us-monetary-regime.plan.md`
> **Date**: 2026-03-05
> **Status**: Draft

---

## 1. File Structure

```
skills/us-monetary-regime/
  SKILL.md                                    # 스킬 사용법
  references/
    fed_policy_database.md                    # FOMC 일정, FFR 이력, 정책 키워드
    sector_sensitivity_map.md                 # 14섹터 US 정책 민감도
  scripts/
    __init__.py
    fed_stance_analyzer.py                    # Fed 기조 분석 (-100~+100)
    rate_trend_classifier.py                  # 금리 5단계 분류
    liquidity_tracker.py                      # 유동성 스코어 (0~100)
    kr_transmission_scorer.py                 # 한국 전이 5채널
    regime_synthesizer.py                     # 종합 레짐 + 오버레이
    tests/
      __init__.py
      test_us_monetary_regime.py              # 전체 테스트
```

### Patch Files (기존 스킬 수정)

```
skills/kr-stock-analysis/scripts/
  comprehensive_scorer.py                     # apply_monetary_overlay() 추가

skills/kr-strategy-synthesizer/scripts/
  conviction_scorer.py                        # global_monetary_context 9번째 컴포넌트

skills/kr-market-environment/scripts/
  market_utils.py                             # foreign_flow_forecast() 추가
```

---

## 2. Constants Registry

### 2.1 fed_stance_analyzer.py Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-01 | `STANCE_WEIGHTS['fomc_tone']` | 0.40 | FOMC 성명서 톤 가중치 |
| C-02 | `STANCE_WEIGHTS['dot_plot']` | 0.25 | 점도표 방향 가중치 |
| C-03 | `STANCE_WEIGHTS['qt_qe']` | 0.20 | QT/QE 상태 가중치 |
| C-04 | `STANCE_WEIGHTS['speakers']` | 0.15 | Fed 위원 발언 톤 가중치 |
| C-05 | **SUM** | **1.00** | **검증 필수** |
| C-06 | `STANCE_LABELS['very_hawkish']` | (-100, -60) | 극단적 긴축 범위 |
| C-07 | `STANCE_LABELS['hawkish']` | (-60, -20) | 긴축 기조 범위 |
| C-08 | `STANCE_LABELS['neutral']` | (-20, +20) | 중립 범위 |
| C-09 | `STANCE_LABELS['dovish']` | (+20, +60) | 완화 기조 범위 |
| C-10 | `STANCE_LABELS['very_dovish']` | (+60, +100) | 극단적 완화 범위 |
| C-11 | `FOMC_TONE_MAP['hawkish']` | -80 | Hawkish 톤 매핑 값 |
| C-12 | `FOMC_TONE_MAP['slightly_hawkish']` | -40 | 약간 Hawkish |
| C-13 | `FOMC_TONE_MAP['neutral']` | 0 | 중립 |
| C-14 | `FOMC_TONE_MAP['slightly_dovish']` | +40 | 약간 Dovish |
| C-15 | `FOMC_TONE_MAP['dovish']` | +80 | Dovish 톤 매핑 값 |
| C-16 | `DOT_PLOT_MAP['higher']` | -70 | 점도표 상향 |
| C-17 | `DOT_PLOT_MAP['stable']` | 0 | 점도표 안정 |
| C-18 | `DOT_PLOT_MAP['lower']` | +70 | 점도표 하향 |
| C-19 | `QT_QE_MAP['active_qt']` | -80 | 적극 QT |
| C-20 | `QT_QE_MAP['tapering_qt']` | -40 | QT 감속 |
| C-21 | `QT_QE_MAP['neutral']` | 0 | 중립 |
| C-22 | `QT_QE_MAP['tapering_qe']` | +40 | QE 개시/준비 |
| C-23 | `QT_QE_MAP['active_qe']` | +80 | 적극 QE |

### 2.2 rate_trend_classifier.py Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-24 | `RATE_REGIMES['aggressive_hike']` | (0, 20) | 급격 인상기 점수 범위 |
| C-25 | `RATE_REGIMES['gradual_hike']` | (20, 40) | 점진 인상기 |
| C-26 | `RATE_REGIMES['hold']` | (40, 60) | 동결기 |
| C-27 | `RATE_REGIMES['gradual_cut']` | (60, 80) | 점진 인하기 |
| C-28 | `RATE_REGIMES['aggressive_cut']` | (80, 100) | 급격 인하기 |
| C-29 | `CHANGE_THRESHOLDS['aggressive']` | 50 | bp, 50bp 이상 = aggressive |
| C-30 | `CHANGE_THRESHOLDS['gradual']` | 25 | bp, 25bp = gradual |
| C-31 | `YIELD_CURVE_WEIGHTS['level']` | 0.50 | 금리 수준 가중치 |
| C-32 | `YIELD_CURVE_WEIGHTS['direction']` | 0.30 | 방향성 가중치 |
| C-33 | `YIELD_CURVE_WEIGHTS['market_expectation']` | 0.20 | 시장 기대 가중치 |
| C-34 | **SUM** | **1.00** | **검증 필수** |
| C-35 | `INVERSION_THRESHOLD` | 0 | bp, 2y-10y 역전 기준 |

### 2.3 liquidity_tracker.py Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-36 | `LIQUIDITY_WEIGHTS['fed_bs']` | 0.30 | Fed B/S 변화 가중치 |
| C-37 | `LIQUIDITY_WEIGHTS['m2']` | 0.30 | M2 증가율 가중치 |
| C-38 | `LIQUIDITY_WEIGHTS['dxy']` | 0.25 | 달러 인덱스 가중치 |
| C-39 | `LIQUIDITY_WEIGHTS['rrp']` | 0.15 | 역레포 변화 가중치 |
| C-40 | **SUM** | **1.00** | **검증 필수** |
| C-41 | `LIQUIDITY_LEVELS['severe_contraction']` | (0, 20) | 급격 축소 |
| C-42 | `LIQUIDITY_LEVELS['contraction']` | (20, 40) | 축소 |
| C-43 | `LIQUIDITY_LEVELS['stable']` | (40, 60) | 안정 |
| C-44 | `LIQUIDITY_LEVELS['expansion']` | (60, 80) | 확대 |
| C-45 | `LIQUIDITY_LEVELS['severe_expansion']` | (80, 100) | 급격 확대 |
| C-46 | `FED_BS_SCORING['shrinking_fast']` | 15 | MoM -1%+ 축소 |
| C-47 | `FED_BS_SCORING['shrinking']` | 30 | MoM -0.5~-1% |
| C-48 | `FED_BS_SCORING['stable']` | 50 | MoM +-0.5% |
| C-49 | `FED_BS_SCORING['growing']` | 70 | MoM +0.5~1% |
| C-50 | `FED_BS_SCORING['growing_fast']` | 85 | MoM +1%+ 확대 |
| C-51 | `M2_SCORING['contracting']` | 20 | YoY < -2% |
| C-52 | `M2_SCORING['flat']` | 40 | YoY -2% ~ +2% |
| C-53 | `M2_SCORING['moderate_growth']` | 60 | YoY +2% ~ +6% |
| C-54 | `M2_SCORING['strong_growth']` | 80 | YoY > +6% |
| C-55 | `DXY_SCORING['strong_rise']` | 20 | DXY 3M > +5% |
| C-56 | `DXY_SCORING['mild_rise']` | 35 | DXY 3M +1~5% |
| C-57 | `DXY_SCORING['stable']` | 50 | DXY 3M +-1% |
| C-58 | `DXY_SCORING['mild_fall']` | 65 | DXY 3M -1~-5% |
| C-59 | `DXY_SCORING['strong_fall']` | 80 | DXY 3M < -5% |

### 2.4 kr_transmission_scorer.py Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-60 | `TRANSMISSION_WEIGHTS['interest_rate_diff']` | 0.30 | 한미 금리차 가중치 |
| C-61 | `TRANSMISSION_WEIGHTS['fx_impact']` | 0.25 | 환율 영향 가중치 |
| C-62 | `TRANSMISSION_WEIGHTS['risk_appetite']` | 0.20 | 글로벌 위험선호 가중치 |
| C-63 | `TRANSMISSION_WEIGHTS['sector_rotation']` | 0.15 | 섹터 회전 효과 가중치 |
| C-64 | `TRANSMISSION_WEIGHTS['bok_policy_lag']` | 0.10 | BOK 정책 후행 가중치 |
| C-65 | **SUM** | **1.00** | **검증 필수** |
| C-66 | `RATE_DIFF_SCORING` | dict | 금리차 → 점수 매핑 (아래) |
| C-67 | `RATE_DIFF_SCORING['kr_much_higher']` | 80 | KR > US +1.5%p+ |
| C-68 | `RATE_DIFF_SCORING['kr_higher']` | 65 | KR > US +0.5~1.5%p |
| C-69 | `RATE_DIFF_SCORING['similar']` | 50 | 차이 +-0.5%p |
| C-70 | `RATE_DIFF_SCORING['us_higher']` | 35 | US > KR +0.5~1.5%p |
| C-71 | `RATE_DIFF_SCORING['us_much_higher']` | 20 | US > KR +1.5%p+ |
| C-72 | `FX_SCORING['won_strong_appreciation']` | 80 | 원화 3M > +5% 강세 |
| C-73 | `FX_SCORING['won_appreciation']` | 65 | 원화 3M +1~5% |
| C-74 | `FX_SCORING['stable']` | 50 | +-1% |
| C-75 | `FX_SCORING['won_depreciation']` | 35 | 원화 3M -1~-5% |
| C-76 | `FX_SCORING['won_strong_depreciation']` | 20 | 원화 3M < -5% 약세 |
| C-77 | `BOK_LAG_MONTHS` | (6, 12) | BOK 정책 후행 범위 (개월) |

### 2.5 regime_synthesizer.py Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-78 | `REGIME_WEIGHTS['stance']` | 0.35 | Fed 기조 가중치 |
| C-79 | `REGIME_WEIGHTS['rate']` | 0.30 | 금리 트렌드 가중치 |
| C-80 | `REGIME_WEIGHTS['liquidity']` | 0.35 | 유동성 가중치 |
| C-81 | **SUM** | **1.00** | **검증 필수** |
| C-82 | `REGIME_LABELS['tightening']` | (0, 35) | 긴축 레짐 범위 |
| C-83 | `REGIME_LABELS['hold']` | (35, 65) | 동결 레짐 범위 |
| C-84 | `REGIME_LABELS['easing']` | (65, 100) | 완화 레짐 범위 |
| C-85 | `OVERLAY_MULTIPLIER` | 0.30 | (score-50)*0.30 = +-15 |
| C-86 | `OVERLAY_MAX` | 15 | 오버레이 최대 절대값 |
| C-87 | `OVERLAY_MIN` | -15 | 오버레이 최소 절대값 |

### 2.6 sector_sensitivity_map.md Constants

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-88 | `SECTOR_SENSITIVITY['semiconductor']` | 1.3 | 반도체 민감도 |
| C-89 | `SECTOR_SENSITIVITY['secondary_battery']` | 1.3 | 2차전지 민감도 |
| C-90 | `SECTOR_SENSITIVITY['bio']` | 1.2 | 바이오 민감도 |
| C-91 | `SECTOR_SENSITIVITY['it']` | 1.2 | IT 민감도 |
| C-92 | `SECTOR_SENSITIVITY['auto']` | 1.1 | 자동차 민감도 |
| C-93 | `SECTOR_SENSITIVITY['shipbuilding']` | 1.0 | 조선 민감도 |
| C-94 | `SECTOR_SENSITIVITY['steel']` | 0.9 | 철강 민감도 |
| C-95 | `SECTOR_SENSITIVITY['chemical']` | 0.9 | 화학 민감도 |
| C-96 | `SECTOR_SENSITIVITY['construction']` | 0.8 | 건설 민감도 |
| C-97 | `SECTOR_SENSITIVITY['finance']` | 0.7 | 금융 민감도 |
| C-98 | `SECTOR_SENSITIVITY['insurance']` | 0.6 | 보험 민감도 |
| C-99 | `SECTOR_SENSITIVITY['retail']` | 0.5 | 유통 민감도 |
| C-100 | `SECTOR_SENSITIVITY['defense']` | 0.4 | 방산 민감도 |
| C-101 | `SECTOR_SENSITIVITY['food']` | 0.3 | 음식료 민감도 |
| C-102 | `DEFAULT_SENSITIVITY` | 0.7 | 기본 민감도 |

### 2.7 Patch Constants (기존 스킬)

| # | Constant | Value | Description |
|---|----------|-------|-------------|
| C-103 | `CONVICTION_COMPONENTS['global_monetary']['weight']` | 0.10 | 9번째 컴포넌트 (conviction_scorer) |
| C-104 | 기존 8컴포넌트 가중치 재조정 | (아래 상세) | 합계 = 1.00 유지 |

### 2.8 Conviction Scorer Weight Rebalance (Patch)

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| market_structure | 0.16 | 0.15 | -0.01 |
| distribution_risk | 0.16 | 0.14 | -0.02 |
| bottom_confirmation | 0.10 | 0.09 | -0.01 |
| macro_alignment | 0.16 | 0.14 | -0.02 |
| theme_quality | 0.10 | 0.09 | -0.01 |
| setup_availability | 0.09 | 0.08 | -0.01 |
| signal_convergence | 0.11 | 0.11 | 0 |
| growth_outlook | 0.12 | 0.10 | -0.02 |
| **global_monetary** | **-** | **0.10** | **NEW** |
| **SUM** | **1.00** | **1.00** | **검증 필수** |

---

## 3. Function Signatures

### 3.1 fed_stance_analyzer.py

```python
# ─── Constants ───
STANCE_WEIGHTS = {
    'fomc_tone': 0.40,
    'dot_plot': 0.25,
    'qt_qe': 0.20,
    'speakers': 0.15,
}  # sum = 1.00

FOMC_TONE_MAP = {
    'hawkish': -80, 'slightly_hawkish': -40,
    'neutral': 0,
    'slightly_dovish': 40, 'dovish': 80,
}

DOT_PLOT_MAP = {'higher': -70, 'stable': 0, 'lower': 70}

QT_QE_MAP = {
    'active_qt': -80, 'tapering_qt': -40,
    'neutral': 0,
    'tapering_qe': 40, 'active_qe': 80,
}

STANCE_LABELS = {
    'very_hawkish': (-100, -60),
    'hawkish': (-60, -20),
    'neutral': (-20, 20),
    'dovish': (20, 60),
    'very_dovish': (60, 100),
}


def analyze_fed_stance(fomc_tone='neutral', dot_plot='stable',
                       qt_qe='neutral', speaker_tone=0.0):
    """Fed 통화정책 기조 분석.

    Args:
        fomc_tone: str, FOMC 성명서 톤.
            Options: 'hawkish', 'slightly_hawkish', 'neutral',
                     'slightly_dovish', 'dovish'
        dot_plot: str, 점도표 방향.
            Options: 'higher', 'stable', 'lower'
        qt_qe: str, QT/QE 상태.
            Options: 'active_qt', 'tapering_qt', 'neutral',
                     'tapering_qe', 'active_qe'
        speaker_tone: float, Fed 위원 평균 발언 톤 (-1.0 ~ +1.0).
            -1.0 = very hawkish, +1.0 = very dovish

    Returns:
        dict: {
            'stance_score': float (-100 ~ +100),
            'stance_label': str,
            'components': {
                'fomc_tone': {'raw': str, 'score': float, 'weight': float},
                'dot_plot': {'raw': str, 'score': float, 'weight': float},
                'qt_qe': {'raw': str, 'score': float, 'weight': float},
                'speakers': {'raw': float, 'score': float, 'weight': float},
            },
            'description': str,
        }
    """
```

### 3.2 rate_trend_classifier.py

```python
# ─── Constants ───
RATE_REGIMES = {
    'aggressive_hike': {'range': (0, 20), 'label': '급격한 인상기'},
    'gradual_hike': {'range': (20, 40), 'label': '점진적 인상기'},
    'hold': {'range': (40, 60), 'label': '동결기'},
    'gradual_cut': {'range': (60, 80), 'label': '점진적 인하기'},
    'aggressive_cut': {'range': (80, 100), 'label': '급격한 인하기'},
}

CHANGE_THRESHOLDS = {'aggressive': 50, 'gradual': 25}  # bp

YIELD_CURVE_WEIGHTS = {
    'level': 0.50,
    'direction': 0.30,
    'market_expectation': 0.20,
}  # sum = 1.00


def classify_rate_trend(current_ffr=5.50, ffr_6m_ago=5.50,
                        ffr_12m_ago=5.50, last_change_bp=0,
                        next_meeting_cut_prob=0.0,
                        next_meeting_hike_prob=0.0,
                        yield_curve_2y10y=0.0):
    """금리 트렌드 분류.

    Args:
        current_ffr: float, 현재 FFR (%).
        ffr_6m_ago: float, 6개월 전 FFR (%).
        ffr_12m_ago: float, 12개월 전 FFR (%).
        last_change_bp: int, 마지막 변경 폭 (bp). 양수=인상, 음수=인하.
        next_meeting_cut_prob: float, 다음 회의 인하 확률 (0~1).
        next_meeting_hike_prob: float, 다음 회의 인상 확률 (0~1).
        yield_curve_2y10y: float, 2y-10y 스프레드 (bp).

    Returns:
        dict: {
            'rate_regime': str,
            'rate_score': float (0~100),
            'regime_label': str,
            'direction': str ('rising'/'stable'/'falling'),
            'direction_confidence': float (0~1),
            'yield_curve_signal': str ('inverted'/'flat'/'normal'/'steep'),
            'components': {
                'level': {'score': float, 'weight': float},
                'direction': {'score': float, 'weight': float},
                'market_expectation': {'score': float, 'weight': float},
            },
        }
    """
```

### 3.3 liquidity_tracker.py

```python
# ─── Constants ───
LIQUIDITY_WEIGHTS = {
    'fed_bs': 0.30,
    'm2': 0.30,
    'dxy': 0.25,
    'rrp': 0.15,
}  # sum = 1.00

LIQUIDITY_LEVELS = {
    'severe_contraction': (0, 20),
    'contraction': (20, 40),
    'stable': (40, 60),
    'expansion': (60, 80),
    'severe_expansion': (80, 100),
}

FED_BS_SCORING = {
    'shrinking_fast': 15,   # MoM < -1%
    'shrinking': 30,        # MoM -0.5% ~ -1%
    'stable': 50,           # MoM +-0.5%
    'growing': 70,          # MoM +0.5% ~ +1%
    'growing_fast': 85,     # MoM > +1%
}

M2_SCORING = {
    'contracting': 20,      # YoY < -2%
    'flat': 40,             # YoY -2% ~ +2%
    'moderate_growth': 60,  # YoY +2% ~ +6%
    'strong_growth': 80,    # YoY > +6%
}

DXY_SCORING = {
    'strong_rise': 20,      # 3M > +5%
    'mild_rise': 35,        # 3M +1% ~ +5%
    'stable': 50,           # 3M +-1%
    'mild_fall': 65,        # 3M -1% ~ -5%
    'strong_fall': 80,      # 3M < -5%
}


def track_liquidity(fed_bs_change_pct=0.0, m2_growth_yoy=0.0,
                    dxy_change_3m=0.0, rrp_change_pct=0.0):
    """글로벌 유동성 추적.

    Args:
        fed_bs_change_pct: float, Fed 대차대조표 MoM 변화율 (%).
        m2_growth_yoy: float, M2 통화량 YoY 증가율 (%).
        dxy_change_3m: float, 달러 인덱스 3개월 변화율 (%).
        rrp_change_pct: float, 역레포(RRP) 잔고 MoM 변화율 (%).

    Returns:
        dict: {
            'liquidity_score': float (0~100),
            'liquidity_level': str,
            'liquidity_trend': str ('contracting'/'stable'/'expanding'),
            'components': {
                'fed_bs': {'raw': float, 'score': float, 'weight': float},
                'm2': {'raw': float, 'score': float, 'weight': float},
                'dxy': {'raw': float, 'score': float, 'weight': float},
                'rrp': {'raw': float, 'score': float, 'weight': float},
            },
        }
    """
```

### 3.4 kr_transmission_scorer.py

```python
# ─── Constants ───
TRANSMISSION_WEIGHTS = {
    'interest_rate_diff': 0.30,
    'fx_impact': 0.25,
    'risk_appetite': 0.20,
    'sector_rotation': 0.15,
    'bok_policy_lag': 0.10,
}  # sum = 1.00

RATE_DIFF_SCORING = {
    'kr_much_higher': 80,     # KR > US +1.5%p+
    'kr_higher': 65,          # KR > US +0.5~1.5%p
    'similar': 50,            # +-0.5%p
    'us_higher': 35,          # US > KR +0.5~1.5%p
    'us_much_higher': 20,     # US > KR +1.5%p+
}

FX_SCORING = {
    'won_strong_appreciation': 80,  # 원화 3M > +5%
    'won_appreciation': 65,         # 3M +1~5%
    'stable': 50,                   # +-1%
    'won_depreciation': 35,         # 3M -1~-5%
    'won_strong_depreciation': 20,  # 3M < -5%
}

BOK_LAG_MONTHS = (6, 12)

SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,
    'secondary_battery': 1.3,
    'bio': 1.2,
    'it': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'construction': 0.8,
    'finance': 0.7,
    'insurance': 0.6,
    'retail': 0.5,
    'defense': 0.4,
    'food': 0.3,
}

DEFAULT_SENSITIVITY = 0.7


def score_kr_transmission(us_regime_score=50, kr_rate=3.50,
                          us_rate=4.50, usdkrw_change_3m=0.0,
                          foreign_flow_5d=0, bok_direction='hold'):
    """한국 전이 스코어 계산.

    Args:
        us_regime_score: float (0~100), US 통화정책 레짐 점수.
        kr_rate: float, 한국 기준금리 (%).
        us_rate: float, US FFR 상단 (%).
        usdkrw_change_3m: float, 원달러 3개월 변화율 (%).
            양수 = 원화 약세, 음수 = 원화 강세.
        foreign_flow_5d: float, 외국인 5일 순매수 (억원).
        bok_direction: str, BOK 정책 방향.
            Options: 'hiking', 'hold', 'cutting'

    Returns:
        dict: {
            'kr_impact_score': float (0~100),
            'impact_label': str ('negative'/'neutral'/'positive'),
            'overlay': float (-15 ~ +15),
            'channels': {
                'interest_rate_diff': {'score': float, 'weight': float, 'detail': str},
                'fx_impact': {'score': float, 'weight': float, 'detail': str},
                'risk_appetite': {'score': float, 'weight': float, 'detail': str},
                'sector_rotation': {'score': float, 'weight': float, 'detail': str},
                'bok_policy_lag': {'score': float, 'weight': float, 'detail': str},
            },
            'sector_overlays': dict,  # {sector: float overlay per sector}
            'favored_sectors': list,
            'unfavored_sectors': list,
        }
    """


def get_sector_overlay(overlay, sector='default'):
    """섹터별 오버레이 계산.

    Args:
        overlay: float, base overlay (-15~+15).
        sector: str, 한국 섹터명.

    Returns:
        float: sector-adjusted overlay.
    """
```

### 3.5 regime_synthesizer.py

```python
# ─── Constants ───
REGIME_WEIGHTS = {
    'stance': 0.35,
    'rate': 0.30,
    'liquidity': 0.35,
}  # sum = 1.00

REGIME_LABELS = {
    'tightening': (0, 35),
    'hold': (35, 65),
    'easing': (65, 100),
}

OVERLAY_MULTIPLIER = 0.30
OVERLAY_MAX = 15
OVERLAY_MIN = -15


def synthesize_regime(fomc_tone='neutral', dot_plot='stable',
                      qt_qe='neutral', speaker_tone=0.0,
                      current_ffr=5.50, ffr_6m_ago=5.50,
                      ffr_12m_ago=5.50, last_change_bp=0,
                      next_meeting_cut_prob=0.0,
                      next_meeting_hike_prob=0.0,
                      yield_curve_2y10y=0.0,
                      fed_bs_change_pct=0.0, m2_growth_yoy=0.0,
                      dxy_change_3m=0.0, rrp_change_pct=0.0,
                      kr_rate=3.50, usdkrw_change_3m=0.0,
                      foreign_flow_5d=0, bok_direction='hold'):
    """US 통화정책 레짐 종합 분석 + 한국 오버레이.

    All parameters are passed through to sub-modules.

    Returns:
        dict: {
            'us_regime': {
                'regime_score': float (0~100),
                'regime_label': str,
                'stance': dict (from analyze_fed_stance),
                'rate': dict (from classify_rate_trend),
                'liquidity': dict (from track_liquidity),
            },
            'kr_impact': dict (from score_kr_transmission),
            'overlay': float (-15 ~ +15),
            'sector_overlays': dict,
            'summary': str,
            'data_inputs': dict,  # 입력 파라미터 기록
        }
    """
```

### 3.6 Patch: comprehensive_scorer.py (kr-stock-analysis)

```python
# 추가할 함수 (기존 코드 변경 없음)

def apply_monetary_overlay(base_score, overlay=None, sector='default'):
    """통화정책 오버레이 적용.

    기존 calc_comprehensive_score()의 결과에 us-monetary-regime
    오버레이를 섹터 민감도에 따라 적용한다.
    overlay=None이면 base_score를 그대로 반환 (기존 호환).

    Args:
        base_score: float (0~100), calc_comprehensive_score() 결과 score.
        overlay: float or None, us-monetary-regime 오버레이 (-15~+15).
        sector: str, 한국 섹터명 (kr_transmission_scorer.SECTOR_SENSITIVITY 키).

    Returns:
        dict: {
            'original_score': float,
            'overlay_applied': float or None,
            'sector': str,
            'sector_sensitivity': float,
            'adjusted_overlay': float,
            'final_score': float (0~100),
            'final_grade': str,
            'overlay_impact': str ('positive'/'neutral'/'negative'),
        }
    """
```

### 3.7 Patch: conviction_scorer.py (kr-strategy-synthesizer)

```python
# CONVICTION_COMPONENTS에 9번째 추가:
# 'global_monetary': {
#     'weight': 0.10,
#     'sources': ['us-monetary-regime'],
#     'description': '글로벌 통화정책 환경',
# }

# normalize_signal()에 케이스 추가:
# elif source_skill == 'us-monetary-regime':
#     # regime_score: 0-100
#     return max(0, min(100, float(raw_value)))

# calc_component_scores()에 9번째 컴포넌트 추가:
# 9. global_monetary
# monetary = reports.get('us-monetary-regime', {})
# gm_score = normalize_signal(monetary.get('regime_score'), 'us-monetary-regime')
```

### 3.8 Patch: market_utils.py (kr-market-environment)

```python
# 추가할 함수

def estimate_foreign_flow_outlook(us_regime_score=None, kr_us_rate_diff=None,
                                  usdkrw_trend=None):
    """US 통화정책 기반 외국인 수급 전망 추정.

    Optional 함수. us-monetary-regime 결과가 있을 때만 활용.
    None이면 빈 dict 반환 (기존 호환).

    Args:
        us_regime_score: float or None, US 레짐 점수 (0~100).
        kr_us_rate_diff: float or None, 한미 금리차 (%p).
        usdkrw_trend: str or None, 원달러 추세.

    Returns:
        dict: {
            'outlook': str ('net_inflow'/'neutral'/'net_outflow'),
            'confidence': float (0~1),
            'reasoning': str,
        } or {} if no input
    """
```

---

## 4. Weight Sum Verification

| # | Location | Weights | Sum | Status |
|---|----------|---------|-----|--------|
| W-01 | `STANCE_WEIGHTS` | 0.40+0.25+0.20+0.15 | 1.00 | Verify |
| W-02 | `YIELD_CURVE_WEIGHTS` | 0.50+0.30+0.20 | 1.00 | Verify |
| W-03 | `LIQUIDITY_WEIGHTS` | 0.30+0.30+0.25+0.15 | 1.00 | Verify |
| W-04 | `TRANSMISSION_WEIGHTS` | 0.30+0.25+0.20+0.15+0.10 | 1.00 | Verify |
| W-05 | `REGIME_WEIGHTS` | 0.35+0.30+0.35 | 1.00 | Verify |
| W-06 | `CONVICTION_COMPONENTS` (patched) | 0.15+0.14+0.09+0.14+0.09+0.08+0.11+0.10+0.10 | 1.00 | Verify |

---

## 5. Test Design

### 5.1 test_us_monetary_regime.py Structure

```python
class TestFedStanceAnalyzer:
    """Fed 기조 분석 테스트 (~20 tests)."""

    def test_very_hawkish_scenario(self):
        # fomc_tone='hawkish', dot_plot='higher', qt_qe='active_qt', speaker_tone=-0.8
        # → stance_score < -60, label = 'very_hawkish'

    def test_very_dovish_scenario(self):
        # fomc_tone='dovish', dot_plot='lower', qt_qe='active_qe', speaker_tone=0.8
        # → stance_score > 60, label = 'very_dovish'

    def test_neutral_scenario(self):
        # all defaults → stance_score ≈ 0, label = 'neutral'

    def test_mixed_signals(self):
        # hawkish tone + lower dot_plot → moderate hawkish

    def test_stance_weights_sum(self):
        # sum(STANCE_WEIGHTS.values()) == 1.00

    def test_all_fomc_tones(self):
        # iterate all FOMC_TONE_MAP keys → valid score

    def test_all_dot_plot_values(self):
        # iterate all DOT_PLOT_MAP keys

    def test_all_qt_qe_values(self):
        # iterate all QT_QE_MAP keys

    def test_speaker_tone_range(self):
        # -1.0, -0.5, 0, 0.5, 1.0 → valid scores

    def test_score_bounds(self):
        # extreme inputs → score within [-100, 100]

    def test_label_classification(self):
        # each label range boundary → correct label


class TestRateTrendClassifier:
    """금리 트렌드 분류 테스트 (~15 tests)."""

    def test_aggressive_hike(self):
        # last_change_bp=75, 12m rise → aggressive_hike, score 0~20

    def test_gradual_hike(self):
        # last_change_bp=25, 12m rise → gradual_hike, score 20~40

    def test_hold(self):
        # last_change_bp=0, 3m+ → hold, score 40~60

    def test_gradual_cut(self):
        # last_change_bp=-25, 12m fall → gradual_cut, score 60~80

    def test_aggressive_cut(self):
        # last_change_bp=-50, 12m fall → aggressive_cut, score 80~100

    def test_yield_curve_weights_sum(self):
        # sum == 1.00

    def test_inverted_curve(self):
        # 2y10y < 0 → inverted signal

    def test_steep_curve(self):
        # 2y10y > 100bp → steep signal

    def test_market_expectation_high_cut(self):
        # cut_prob=0.9 → pushes score toward cut

    def test_score_bounds(self):
        # 0 <= score <= 100

    def test_direction_consistency(self):
        # falling FFR → direction = 'falling'

    def test_all_regimes_reachable(self):
        # each regime can be triggered


class TestLiquidityTracker:
    """유동성 추적 테스트 (~15 tests)."""

    def test_severe_contraction(self):
        # fed_bs shrinking fast + m2 contracting + dxy rising + rrp growing

    def test_severe_expansion(self):
        # all expanding → score > 80

    def test_stable(self):
        # all zero → score ≈ 50

    def test_liquidity_weights_sum(self):
        # sum == 1.00

    def test_fed_bs_scoring_all_levels(self):
        # each FED_BS_SCORING level

    def test_m2_scoring_all_levels(self):

    def test_dxy_scoring_all_levels(self):

    def test_dxy_inverse_relationship(self):
        # dxy rise → lower score (inverse)

    def test_score_bounds(self):

    def test_level_classification(self):
        # each LIQUIDITY_LEVELS boundary

    def test_trend_classification(self):
        # score < 40 → contracting, 40-60 → stable, > 60 → expanding


class TestKRTransmissionScorer:
    """한국 전이 스코어 테스트 (~20 tests)."""

    def test_positive_transmission(self):
        # US easing + KR>US rate + won strengthening → positive

    def test_negative_transmission(self):
        # US tightening + US>KR rate + won weakening → negative

    def test_neutral_transmission(self):
        # all neutral → impact ≈ neutral

    def test_transmission_weights_sum(self):
        # sum == 1.00

    def test_rate_diff_all_levels(self):
        # each RATE_DIFF_SCORING level

    def test_fx_all_levels(self):
        # each FX_SCORING level

    def test_overlay_range(self):
        # -15 <= overlay <= +15

    def test_sector_overlay_semiconductor(self):
        # overlay * 1.3

    def test_sector_overlay_food(self):
        # overlay * 0.3

    def test_sector_overlay_default(self):
        # overlay * 0.7

    def test_all_14_sectors(self):
        # each SECTOR_SENSITIVITY key → valid overlay

    def test_favored_unfavored_sectors(self):
        # easing → favored includes growth sectors

    def test_bok_direction_all(self):
        # 'hiking', 'hold', 'cutting' → valid score

    def test_get_sector_overlay(self):
        # standalone function test

    def test_foreign_flow_positive(self):
        # large positive → higher score

    def test_foreign_flow_negative(self):


class TestRegimeSynthesizer:
    """종합 레짐 테스트 (~15 tests)."""

    def test_full_easing_scenario(self):
        # all dovish/cutting/expanding → regime='easing', score > 65

    def test_full_tightening_scenario(self):
        # all hawkish/hiking/contracting → regime='tightening', score < 35

    def test_hold_scenario(self):
        # mixed → regime='hold', score 35~65

    def test_regime_weights_sum(self):
        # sum == 1.00

    def test_overlay_calculation(self):
        # (score - 50) * 0.30, clamped to +-15

    def test_overlay_max_clamp(self):
        # score=100 → overlay = min(15, 50*0.30) = 15

    def test_overlay_min_clamp(self):
        # score=0 → overlay = max(-15, -50*0.30) = -15

    def test_overlay_zero_at_50(self):
        # score=50 → overlay = 0

    def test_sector_overlays_generated(self):
        # 14 sectors in sector_overlays

    def test_summary_generation(self):
        # summary string not empty

    def test_data_inputs_recorded(self):
        # data_inputs contains all params

    def test_sub_module_integration(self):
        # all sub-modules called and results included


class TestPatchComprehensiveScorer:
    """오버레이 패치 테스트 (~10 tests)."""

    def test_overlay_none_returns_original(self):
        # apply_monetary_overlay(60.0, None) → final_score = 60.0

    def test_positive_overlay(self):
        # apply_monetary_overlay(50.0, 10.0, 'semiconductor')
        # → 50 + 10 * 1.3 = 63.0

    def test_negative_overlay(self):
        # apply_monetary_overlay(50.0, -10.0, 'semiconductor')
        # → 50 + (-10) * 1.3 = 37.0

    def test_clamp_upper(self):
        # apply_monetary_overlay(95.0, 15.0) → 100 (clamped)

    def test_clamp_lower(self):
        # apply_monetary_overlay(5.0, -15.0) → 0 (clamped)

    def test_default_sector(self):
        # sector='default' → sensitivity = 0.7

    def test_grade_update(self):
        # overlay changes grade from HOLD to BUY

    def test_existing_comprehensive_unaffected(self):
        # calc_comprehensive_score() 기존 동작 불변 확인

    def test_overlay_impact_label(self):
        # positive/neutral/negative correctly assigned


class TestPatchConvictionScorer:
    """conviction_scorer 패치 테스트 (~8 tests)."""

    def test_9_components_sum_1(self):
        # sum(all weights) == 1.00

    def test_global_monetary_component(self):
        # reports with us-monetary-regime → global_monetary score

    def test_global_monetary_missing(self):
        # no us-monetary-regime report → default 50

    def test_normalize_us_monetary(self):
        # normalize_signal(65, 'us-monetary-regime') == 65

    def test_existing_8_components_work(self):
        # 기존 8 컴포넌트 로직 불변

    def test_weight_rebalance(self):
        # 각 컴포넌트 새 가중치 확인


class TestPatchMarketUtils:
    """market_utils 패치 테스트 (~5 tests)."""

    def test_estimate_foreign_flow_no_input(self):
        # all None → {} empty dict

    def test_easing_regime_inflow(self):
        # regime_score=80 → outlook='net_inflow'

    def test_tightening_regime_outflow(self):
        # regime_score=20 → outlook='net_outflow'

    def test_existing_functions_unaffected(self):
        # get_kr_market_snapshot signature unchanged
```

### 5.2 Test Summary

| Test Class | Count | Module |
|-----------|-------|--------|
| TestFedStanceAnalyzer | ~20 | fed_stance_analyzer.py |
| TestRateTrendClassifier | ~15 | rate_trend_classifier.py |
| TestLiquidityTracker | ~15 | liquidity_tracker.py |
| TestKRTransmissionScorer | ~20 | kr_transmission_scorer.py |
| TestRegimeSynthesizer | ~15 | regime_synthesizer.py |
| TestPatchComprehensiveScorer | ~10 | comprehensive_scorer.py (patch) |
| TestPatchConvictionScorer | ~8 | conviction_scorer.py (patch) |
| TestPatchMarketUtils | ~5 | market_utils.py (patch) |
| **Total** | **~108** | |

---

## 6. Implementation Order

| Step | Task | Files | Dependencies | Est. Tests |
|------|------|-------|-------------|-----------|
| 1 | Reference 데이터 작성 | `fed_policy_database.md`, `sector_sensitivity_map.md` | None | 0 |
| 2 | SKILL.md 작성 | `SKILL.md` | None | 0 |
| 3 | fed_stance_analyzer 구현 | `fed_stance_analyzer.py` | Step 1 | ~20 |
| 4 | rate_trend_classifier 구현 | `rate_trend_classifier.py` | Step 1 | ~15 |
| 5 | liquidity_tracker 구현 | `liquidity_tracker.py` | Step 1 | ~15 |
| 6 | kr_transmission_scorer 구현 | `kr_transmission_scorer.py` | Step 1 | ~20 |
| 7 | regime_synthesizer 구현 | `regime_synthesizer.py` | Step 3,4,5,6 | ~15 |
| 8 | comprehensive_scorer 패치 | `comprehensive_scorer.py` | Step 6 | ~10 |
| 9 | conviction_scorer 패치 | `conviction_scorer.py` | Step 7 | ~8 |
| 10 | market_utils 패치 | `market_utils.py` | Step 7 | ~5 |
| 11 | 테스트 작성 및 실행 | `test_us_monetary_regime.py` | Step 3-10 | All |

---

## 7. Data Flow Diagram

```
 ┌─────────────────────────────────────────────────────────────────┐
 │ INPUT (WebSearch / 수동입력)                                      │
 │ fomc_tone, dot_plot, qt_qe, speaker_tone,                       │
 │ FFR(current/6m/12m), last_change_bp, FedWatch probs,            │
 │ yield_curve, fed_bs_change, m2_growth, dxy_change, rrp_change,  │
 │ kr_rate, usdkrw_change, foreign_flow, bok_direction             │
 └─────────────────┬───────────────────────────────────────────────┘
                   │
       ┌───────────┼───────────────┐
       ▼           ▼               ▼
 ┌──────────┐ ┌──────────┐ ┌──────────────┐
 │fed_stance│ │rate_trend│ │liquidity     │
 │_analyzer │ │_classifr │ │_tracker      │
 │          │ │          │ │              │
 │score     │ │score     │ │score         │
 │-100~+100 │ │0~100     │ │0~100         │
 └────┬─────┘ └────┬─────┘ └──────┬───────┘
      │            │               │
      │  normalize │               │
      │  to 0-100  │               │
      ▼            ▼               ▼
 ┌─────────────────────────────────────┐
 │ regime_synthesizer                   │
 │ stance*0.35 + rate*0.30 + liq*0.35  │
 │ → regime_score (0~100)              │
 │ → regime_label (tight/hold/ease)    │
 └──────────────┬──────────────────────┘
                │
                ▼
 ┌─────────────────────────────────────┐
 │ kr_transmission_scorer              │
 │ 5채널 가중 → kr_impact_score        │
 │ (regime_score-50)*0.30 → overlay   │
 │ overlay * sector_sensitivity        │
 │ → sector_overlays{14}              │
 └──────────────┬──────────────────────┘
                │
       ┌────────┼────────────────┐
       ▼        ▼                ▼
 ┌──────────┐ ┌────────────┐ ┌────────────┐
 │kr-stock- │ │kr-strategy │ │kr-market-  │
 │analysis  │ │-synthesizer│ │environment │
 │          │ │            │ │            │
 │base_score│ │9th comp    │ │foreign flow│
 │+overlay  │ │global_     │ │outlook     │
 │*sector   │ │monetary    │ │            │
 │=final    │ │            │ │            │
 └──────────┘ └────────────┘ └────────────┘
```

---

## 8. Reference Data Design

### 8.1 fed_policy_database.md

```markdown
# Fed Policy Database

## FOMC Schedule 2026
| # | Date | Type | Notes |
|---|------|------|-------|
| 1 | 2026-01-28~29 | Regular | |
| 2 | 2026-03-17~18 | Regular + SEP/Dot Plot | |
| 3 | 2026-05-05~06 | Regular | |
| 4 | 2026-06-16~17 | Regular + SEP/Dot Plot | |
| 5 | 2026-07-28~29 | Regular | |
| 6 | 2026-09-15~16 | Regular + SEP/Dot Plot | |
| 7 | 2026-11-03~04 | Regular | |
| 8 | 2026-12-15~16 | Regular + SEP/Dot Plot | |

## Federal Funds Rate History (Recent 2Y)
| Date | FFR Upper | Change (bp) | Cumulative |
|------|-----------|-------------|------------|
| 2024-07 | 5.50 | 0 | 0 |
| 2024-09 | 5.00 | -50 | -50 |
| 2024-11 | 4.75 | -25 | -75 |
| 2024-12 | 4.50 | -25 | -100 |
| 2025-03 | 4.25 | -25 | -125 |
| 2025-06 | 4.00 | -25 | -150 |
| 2025-09 | 3.75 | -25 | -175 |
| 2025-12 | 3.50 | -25 | -200 |
| 2026-01 | 3.50 | 0 | -200 |

## Policy Keywords Reference
### Hawkish Keywords
inflation, elevated, restrictive, vigilant, tighten, upside risks,
data-dependent (when used with caution), remains high, ...

### Dovish Keywords
support, accommodate, easing, downside risk, labor market softening,
progress toward target, balance of risks, sufficient progress, ...
```

### 8.2 sector_sensitivity_map.md

```markdown
# Sector Sensitivity to US Monetary Policy

## Sensitivity Map (14 Korean Sectors)

| Sector | Key | Sensitivity | Rationale |
|--------|-----|:-----------:|-----------|
| 반도체 | semiconductor | 1.3 | 수출 비중 높음, 글로벌 수요 민감, 성장주 특성 |
| 2차전지 | secondary_battery | 1.3 | 글로벌 EV 수요, 자본집약, 성장주 |
| 바이오 | bio | 1.2 | 장기 듀레이션 자산, 금리 민감 |
| IT | it | 1.2 | 수출 비중, 성장주 밸류에이션 |
| 자동차 | auto | 1.1 | 글로벌 수요, 환율 영향 |
| 조선 | shipbuilding | 1.0 | 수출 100%, 달러 결제 |
| 철강 | steel | 0.9 | 글로벌 수요 일부, 내수 비중 |
| 화학 | chemical | 0.9 | 원자재 가격 연동 |
| 건설 | construction | 0.8 | 국내 금리 민감, 간접 영향 |
| 금융 | finance | 0.7 | NIM 영향 있지만 BOK 기준 |
| 보험 | insurance | 0.6 | 장기 투자수익률 영향 |
| 유통 | retail | 0.5 | 내수 소비, 간접적 |
| 방산 | defense | 0.4 | 정부 예산 기반, 금리 둔감 |
| 음식료 | food | 0.3 | 필수 소비재, 통화정책 거의 무관 |

## Default Sensitivity
- 미분류 섹터: 0.7
```

---

## 9. Edge Cases & Validation Rules

| # | Rule | Validation |
|---|------|-----------|
| V-01 | stance_score 범위 | -100 <= score <= 100 |
| V-02 | rate_score 범위 | 0 <= score <= 100 |
| V-03 | liquidity_score 범위 | 0 <= score <= 100 |
| V-04 | regime_score 범위 | 0 <= score <= 100 |
| V-05 | overlay 범위 | -15 <= overlay <= 15 |
| V-06 | sector_sensitivity 범위 | 0.0 < sensitivity <= 2.0 |
| V-07 | final_score 범위 | 0 <= final <= 100 (clamp) |
| V-08 | speaker_tone 범위 | -1.0 <= tone <= 1.0 |
| V-09 | 확률 범위 | 0 <= prob <= 1.0 |
| V-10 | 가중치 합계 | 모든 weight dict sum == 1.00 |

---

## 10. Backward Compatibility Guarantees

| Guarantee | How |
|-----------|-----|
| `calc_comprehensive_score()` 기존 동작 불변 | 새 함수 `apply_monetary_overlay()` 별도 추가 |
| `calc_conviction_score()` 기존 8컴포넌트 동작 | 9번째 컴포넌트 없으면 기존 가중치로 정규화 |
| `get_kr_market_snapshot()` 기존 동작 불변 | 새 함수 `estimate_foreign_flow_outlook()` 별도 추가 |
| 기존 1,814 테스트 전체 통과 | overlay=Optional, 기본 None |
| 기존 ANALYSIS_GRADES 불변 | apply_monetary_overlay에서 동일 등급 체계 재사용 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-05 | Initial design - 104 constants, ~108 tests, 11 step impl order | Claude |
