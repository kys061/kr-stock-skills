# Phase 9: 한국 시장 전용 신규 스킬 설계

> **Feature**: kr-stock-skills-phase9
> **Phase**: Design
> **Created**: 2026-03-04
> **Based on**: kr-stock-skills.plan.md (Section 3.9)
> **Depends on**: Phase 1 (KRClient), Phase 5 (kr-institutional-flow, kr-earnings-calendar), Phase 6 (kr-options-advisor), Phase 8 (kr-weekly-strategy)

---

## 1. 범위 요약

Phase 9는 **미국에 없는 한국 시장 고유 스킬 5개**를 신규 개발한다.

| # | KR 스킬명 | 복잡도 | US 원본 | 핵심 |
|:-:|-----------|:------:|:-------:|------|
| 40 | **kr-supply-demand-analyzer** | High | 없음 | 시장/섹터 레벨 수급 종합 + 유동성 |
| 41 | **kr-short-sale-tracker** | Medium | 없음 | 공매도 추적 + 숏커버 시그널 |
| 42 | **kr-credit-monitor** | Medium | 없음 | 신용잔고 + 반대매매 리스크 |
| 43 | **kr-program-trade-analyzer** | High | 없음 | 차익/비차익 + 베이시스 + 만기일 |
| 44 | **kr-dart-disclosure-monitor** | High | 없음 | 10유형 공시 분류 + 영향도 스코어 |

**총계**: High 3 + Medium 2 = 5개 스킬 (전부 100% 한국 고유)

---

## 2. 스킬 간 관계 아키텍처

```
Phase 9 (한국 고유 신규)
──────────────────────────
│
├─→ kr-supply-demand-analyzer (시장/섹터 수급)
│     ├── 시장 레벨 수급 (KOSPI/KOSDAQ 전체)
│     ├── 섹터별 자금 흐름 (14 섹터)
│     ├── 유동성 지표 (거래대금/회전율)
│     └── 수급 종합 스코어 (4 컴포넌트)
│
├─→ kr-short-sale-tracker (공매도 추적)
│     ├── 공매도 비율 분석 (잔고/거래)
│     ├── 숏커버 시그널 탐지
│     └── 공매도 리스크 스코어 (4 컴포넌트)
│
├─→ kr-credit-monitor (신용잔고)
│     ├── 신용잔고 분석 (시총 대비)
│     ├── 반대매매 리스크 시나리오
│     └── 신용 리스크 스코어 (4 컴포넌트)
│
├─→ kr-program-trade-analyzer (프로그램 매매)
│     ├── 차익/비차익 프로그램 분석
│     ├── 선물 베이시스 분석
│     ├── 만기일 효과 분석
│     └── 프로그램 영향 스코어 (4 컴포넌트)
│
└─→ kr-dart-disclosure-monitor (공시 모니터)
      ├── 10유형 공시 분류
      ├── 이벤트 영향도 (5단계)
      ├── 지분 변동 추적
      └── 공시 리스크 스코어 (4 컴포넌트)
```

**업스트림 참조**:
```
kr-institutional-flow → kr-supply-demand-analyzer (투자자 분류, 수급 패턴)
_kr-common            → 전체 (INDEX_CODES, INVESTOR_TYPES, ticker_utils)
kr-options-advisor    → kr-program-trade-analyzer (KOSPI200 상수)
kr-earnings-calendar  → kr-dart-disclosure-monitor (DART_REPORT_CODES)
kr-weekly-strategy    → kr-supply-demand-analyzer (KR_SECTORS 14개)
kr-bubble-detector    → kr-credit-monitor (credit_balance 스코어링 참조)
```

---

## 3. 스킬별 상세 설계

---

### 3.1 Skill 40: kr-supply-demand-analyzer (High)

**핵심**: 시장 전체 수급 동학 + 섹터별 자금 흐름 + 유동성 지표 종합 분석
**차별화**: kr-institutional-flow(종목 레벨 4팩터) → 시장/섹터 레벨 + 유동성

#### 3.1.1 시장 레벨 수급 상수

```python
# ─── 시장 수급 분석 ───

MARKET_FLOW_CONFIG = {
    'markets': ['KOSPI', 'KOSDAQ'],
    'investor_groups': ['foreign', 'institution', 'individual'],
    'consecutive_thresholds': {
        'strong': 10,   # 10일 연속 → 강력
        'moderate': 5,  # 5일 연속 → 보통
        'mild': 3,      # 3일 연속 → 약한
    },
    'amount_thresholds': {
        'foreign': {
            'strong': 500_000_000_000,   # 5000억/일
            'moderate': 100_000_000_000, # 1000억/일
            'mild': 50_000_000_000,      # 500억/일
        },
        'institution': {
            'strong': 300_000_000_000,   # 3000억/일
            'moderate': 100_000_000_000, # 1000억/일
            'mild': 30_000_000_000,      # 300억/일
        },
    },
}

# ─── 시장 수급 시그널 (7단계) ───

MARKET_FLOW_SIGNALS = {
    'STRONG_BUY': {'min_score': 85, 'label': '강력 유입'},
    'BUY': {'min_score': 70, 'label': '유입'},
    'MILD_BUY': {'min_score': 55, 'label': '약한 유입'},
    'NEUTRAL': {'min_score': 45, 'label': '중립'},
    'MILD_SELL': {'min_score': 30, 'label': '약한 유출'},
    'SELL': {'min_score': 15, 'label': '유출'},
    'STRONG_SELL': {'min_score': 0, 'label': '강력 유출'},
}

# ─── 투자자 심리 지수 ───

SENTIMENT_WEIGHTS = {
    'foreign': 0.45,      # 외국인 (코스피 방향 결정)
    'institution': 0.35,  # 기관
    'individual_inverse': 0.20,  # 개인 역지표
}
```

#### 3.1.2 섹터 자금 흐름 상수

```python
# ─── 섹터 자금 흐름 ───

# Phase 6/8과 동일한 14 섹터 (kr-weekly-strategy)
KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학',
    '바이오/제약', '금융/은행', '유통/소비', '건설/부동산',
    'IT/소프트웨어', '통신', '에너지/유틸리티', '엔터테인먼트',
    '방산', '2차전지',
]

SECTOR_FLOW_CONFIG = {
    'rotation_lookback': 5,   # 로테이션 비교: 전주 대비
    'hhi_warning': 0.25,      # HHI 집중도 경고: 0.25 이상
    'hhi_critical': 0.40,     # HHI 집중도 위험: 0.40 이상
    'divergence_threshold': 0.30,  # 외국인-기관 괴리 경고: 30% 이상
}
```

#### 3.1.3 유동성 지표 상수

```python
# ─── 유동성 지표 ───

LIQUIDITY_CONFIG = {
    'volume_ma_periods': [5, 20, 60],   # 거래대금 이동평균
    'turnover_warning': 0.5,            # 회전율 경고: 0.5% 이하 (저유동성)
    'turnover_high': 2.0,               # 회전율 과열: 2.0% 이상
    'concentration_warning': 0.30,      # 상위 10종목 비중 30% 이상
    'concentration_critical': 0.50,     # 상위 10종목 비중 50% 이상
}

LIQUIDITY_GRADES = {
    'ABUNDANT': {'min_score': 80, 'label': '풍부'},
    'NORMAL': {'min_score': 60, 'label': '보통'},
    'TIGHT': {'min_score': 40, 'label': '위축'},
    'DRIED': {'min_score': 0, 'label': '고갈'},
}
```

#### 3.1.4 수급 종합 스코어 (0-100)

```python
# ─── 수급 종합 스코어 ───

SUPPLY_DEMAND_COMPOSITE_WEIGHTS = {
    'market_flow': {'weight': 0.30, 'label': '시장 순매수 강도'},
    'sector_rotation': {'weight': 0.25, 'label': '섹터 로테이션 건전성'},
    'liquidity': {'weight': 0.25, 'label': '유동성 충분도'},
    'investor_sentiment': {'weight': 0.20, 'label': '투자자 심리'},
}
# 가중치 합계: 0.30 + 0.25 + 0.25 + 0.20 = 1.00

SUPPLY_DEMAND_GRADES = {
    'STRONG_INFLOW': {'min_score': 80, 'label': '강력 자금 유입'},
    'INFLOW': {'min_score': 65, 'label': '자금 유입'},
    'BALANCED': {'min_score': 45, 'label': '균형'},
    'OUTFLOW': {'min_score': 30, 'label': '자금 유출'},
    'STRONG_OUTFLOW': {'min_score': 0, 'label': '강력 자금 유출'},
}
```

#### 3.1.5 파일 구조

```
skills/kr-supply-demand-analyzer/
├── SKILL.md
├── references/
│   └── kr_supply_demand_guide.md
├── scripts/
│   ├── market_flow_analyzer.py       # 시장 레벨 수급
│   ├── sector_flow_mapper.py         # 섹터별 자금 흐름
│   ├── liquidity_tracker.py          # 유동성 지표
│   ├── report_generator.py           # 리포트 생성
│   └── tests/
│       ├── __init__.py
│       └── test_supply_demand.py
```

#### 3.1.6 함수 시그니처

```python
# market_flow_analyzer.py
def analyze_market_flow(investor_data, market='KOSPI') -> dict
    # Args: investor_data = {date: {foreign: net, institution: net, individual: net}}
    # Returns: {foreign_score, institution_score, individual_score,
    #           consecutive_days, signal, sentiment_score}

def calc_consecutive_days(daily_flows, investor_type) -> dict
    # Returns: {buy_days, sell_days, direction, strength}

def calc_investor_sentiment(foreign_score, inst_score, individual_score) -> float
    # Returns: 0-100 sentiment score

# sector_flow_mapper.py
def map_sector_flows(sector_data) -> dict
    # Args: sector_data = {sector: {foreign: net, institution: net, individual: net}}
    # Returns: {flows, heatmap, rotation_speed, hhi, divergence}

def calc_sector_hhi(sector_flows) -> float
    # Returns: HHI index (0-1)

def calc_sector_divergence(sector_flows) -> dict
    # Returns: {sector: divergence_score} (foreign vs institution)

# liquidity_tracker.py
def analyze_liquidity(volume_data, market_cap_data) -> dict
    # Returns: {volume_ratio, turnover, concentration, grade, score}

def calc_volume_ratio(daily_volumes, ma_periods) -> dict
    # Returns: {5d_ratio, 20d_ratio, 60d_ratio}

def calc_turnover_rate(volume, market_cap) -> float
    # Returns: turnover rate (%)

# report_generator.py
def generate_supply_demand_report(market_flow, sector_flow, liquidity) -> str
```

---

### 3.2 Skill 41: kr-short-sale-tracker (Medium)

**핵심**: 공매도 비율 추이 + 숏커버 시그널 탐지 + 리스크 스코어
**차별화**: KRClient 공매도 메서드만 → 분석 엔진 + 시그널 탐지

#### 3.2.1 공매도 비율 상수

```python
# ─── 공매도 비율 분석 ───

SHORT_RATIO_CONFIG = {
    'ma_periods': [5, 20, 60],  # 이동평균 기간
    'percentile_lookback': 252,  # 퍼센타일 계산: 1년 (영업일)
}

# 잔고비율 수준 (공매도 잔고 / 상장주식수)
SHORT_BALANCE_LEVELS = {
    'extreme': 0.10,     # 10% 이상: 극단적
    'high': 0.05,        # 5% 이상: 높음
    'moderate': 0.02,    # 2% 이상: 보통
    'low': 0.01,         # 1% 이상: 낮음
    'minimal': 0.0,      # 1% 미만: 미미
}

# 거래비율 수준 (공매도 거래량 / 총 거래량)
SHORT_TRADE_LEVELS = {
    'extreme': 0.20,     # 20% 이상: 극단적
    'high': 0.10,        # 10% 이상: 높음
    'moderate': 0.05,    # 5% 이상: 보통
    'low': 0.0,          # 5% 미만: 낮음
}
```

#### 3.2.2 숏커버 시그널 상수

```python
# ─── 숏커버 시그널 ───

SHORT_COVER_CONFIG = {
    'consecutive_decrease': {
        'strong': 7,     # 7일 연속 잔고 감소 → 강한 숏커버
        'moderate': 5,   # 5일 연속
        'mild': 3,       # 3일 연속
    },
    'sharp_decrease_pct': 0.10,  # 전일 대비 -10% 이상 급감
    'days_to_cover': {
        'critical': 10,  # 10일 이상: 위험 (숏스퀴즈 가능)
        'high': 5,       # 5일 이상: 높음
        'moderate': 3,   # 3일 이상: 보통
        'low': 0,        # 3일 미만: 낮음
    },
}

# 숏스퀴즈 확률 조건
SQUEEZE_CONDITIONS = {
    'high_balance': 0.05,           # 잔고비율 5% 이상
    'decreasing_balance': True,     # 잔고 감소 추세
    'price_rising': True,           # 주가 상승 중
    'high_days_to_cover': 5,        # DTC 5일 이상
}

SHORT_COVER_SIGNALS = {
    'STRONG_COVER': {'min_score': 80, 'label': '강한 숏커버'},
    'COVER': {'min_score': 60, 'label': '숏커버 진행'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'BUILDING': {'min_score': 20, 'label': '공매도 축적'},
    'HEAVY_SHORT': {'min_score': 0, 'label': '과도한 공매도'},
}
```

#### 3.2.3 공매도 리스크 스코어 (0-100)

```python
# ─── 공매도 리스크 스코어 ───

SHORT_RISK_WEIGHTS = {
    'short_ratio': {'weight': 0.30, 'label': '잔고비율 수준'},
    'trend': {'weight': 0.30, 'label': '증가/감소 추세'},
    'concentration': {'weight': 0.20, 'label': '집중도'},
    'days_to_cover': {'weight': 0.20, 'label': '커버 소요일'},
}
# 가중치 합계: 0.30 + 0.30 + 0.20 + 0.20 = 1.00

SHORT_RISK_GRADES = {
    'LOW': {'min_score': 0, 'max_score': 25, 'label': '낮음'},
    'MODERATE': {'min_score': 25, 'max_score': 50, 'label': '보통'},
    'HIGH': {'min_score': 50, 'max_score': 75, 'label': '높음'},
    'EXTREME': {'min_score': 75, 'max_score': 100, 'label': '극단적'},
}
```

#### 3.2.4 파일 구조

```
skills/kr-short-sale-tracker/
├── SKILL.md
├── references/
│   └── kr_short_sale_guide.md
├── scripts/
│   ├── short_ratio_analyzer.py       # 공매도 비율 분석
│   ├── short_cover_detector.py       # 숏커버 시그널 탐지
│   ├── report_generator.py           # 리포트 생성
│   └── tests/
│       ├── __init__.py
│       └── test_short_sale.py
```

#### 3.2.5 함수 시그니처

```python
# short_ratio_analyzer.py
def analyze_short_ratio(short_data, shares_outstanding) -> dict
    # Args: short_data = [{date, short_balance, short_volume, total_volume}]
    # Returns: {balance_ratio, trade_ratio, ma_ratios, percentile, level}

def calc_short_percentile(current_ratio, historical_ratios) -> float
    # Returns: 0-100 percentile

def analyze_sector_concentration(sector_short_data) -> dict
    # Returns: {sector_ratios, anomalies, hhi}

# short_cover_detector.py
def detect_short_cover(short_data, price_data) -> dict
    # Returns: {signal, consecutive_decrease, sharp_decrease,
    #           days_to_cover, squeeze_probability}

def calc_days_to_cover(short_balance, avg_volume) -> float
    # Returns: days to cover

def calc_squeeze_probability(balance_ratio, dtc, trend, price_trend) -> float
    # Returns: 0-1 probability

def calc_short_risk_score(ratio_data, cover_data) -> dict
    # Returns: {score, grade, components}

# report_generator.py
def generate_short_sale_report(ratio_analysis, cover_signals) -> str
```

---

### 3.3 Skill 42: kr-credit-monitor (Medium)

**핵심**: 신용잔고 전문 분석 + 반대매매 리스크 시나리오 + 레버리지 사이클
**차별화**: kr-bubble-detector(YoY 1개만) → 전문 신용 분석 4컴포넌트

#### 3.3.1 신용잔고 분석 상수

```python
# ─── 신용잔고 분석 ───

CREDIT_BALANCE_CONFIG = {
    'lookback_years': 3,        # 퍼센타일 계산: 3년
    'yoy_warning': 0.15,        # YoY +15% 이상: 경고
    'yoy_critical': 0.30,       # YoY +30% 이상: 위험
    'mom_warning': 0.05,        # MoM +5% 이상: 경고
    'mom_critical': 0.10,       # MoM +10% 이상: 위험
}

# 시총 대비 신용잔고 비율 기준
CREDIT_MARKET_RATIO_LEVELS = {
    'critical': 0.030,   # 3.0% 이상: 위험 (역사적 고점 수준)
    'high': 0.025,       # 2.5% 이상: 높음
    'elevated': 0.020,   # 2.0% 이상: 상승
    'normal': 0.015,     # 1.5% 이상: 보통
    'safe': 0.0,         # 1.5% 미만: 안전
}
```

#### 3.3.2 반대매매 리스크 상수

```python
# ─── 반대매매 리스크 ───

MARGIN_CALL_CONFIG = {
    'maintenance_ratio': 1.40,      # 담보유지비율: 140%
    'initial_ratio': 2.00,          # 최초 담보비율: 200% (신용융자 시)
    'liquidation_delay_days': 2,    # D+2 반대매매 (담보부족 통보 후 2영업일)
}

# 시장 하락 시나리오 (-10%, -20%, -30%)
FORCED_LIQUIDATION_SCENARIOS = [
    {'drop_pct': 0.10, 'label': '10% 하락', 'severity': 'mild'},
    {'drop_pct': 0.20, 'label': '20% 하락', 'severity': 'moderate'},
    {'drop_pct': 0.30, 'label': '30% 하락 (가격제한폭)', 'severity': 'severe'},
]

# 반대매매 영향도 기준
LIQUIDATION_IMPACT_LEVELS = {
    'negligible': 0.01,  # 시장 거래대금 대비 1% 미만
    'minor': 0.03,       # 3% 미만
    'significant': 0.05, # 5% 미만
    'major': 0.10,       # 10% 미만
    'critical': 0.10,    # 10% 이상 (연쇄 하락 가능)
}
```

#### 3.3.3 레버리지 사이클 상수

```python
# ─── 레버리지 사이클 ───

LEVERAGE_CYCLE_PHASES = {
    'EXPANSION': {
        'label': '확장기',
        'condition': 'credit_mom > 0 AND credit_yoy > 0',
        'risk': 'increasing',
    },
    'PEAK': {
        'label': '정점',
        'condition': 'credit_percentile >= 90',
        'risk': 'high',
    },
    'CONTRACTION': {
        'label': '수축기',
        'condition': 'credit_mom < 0 AND credit_yoy > 0',
        'risk': 'decreasing',
    },
    'TROUGH': {
        'label': '저점',
        'condition': 'credit_percentile <= 20',
        'risk': 'low',
    },
}

# 예탁금 대비 신용잔고 비율
DEPOSIT_CREDIT_RATIO = {
    'overheated': 0.80,   # 80% 이상: 과열 (대기자금 대비 레버리지 과다)
    'high': 0.60,         # 60% 이상
    'normal': 0.40,       # 40% 이상
    'healthy': 0.0,       # 40% 미만: 건전
}
```

#### 3.3.4 신용 리스크 스코어 (0-100)

```python
# ─── 신용 리스크 스코어 ───

CREDIT_RISK_WEIGHTS = {
    'credit_level': {'weight': 0.30, 'label': '시총 대비 신용잔고 수준'},
    'growth_rate': {'weight': 0.25, 'label': '신용잔고 증가 속도'},
    'forced_liquidation': {'weight': 0.25, 'label': '반대매매 근접도'},
    'leverage_cycle': {'weight': 0.20, 'label': '사이클 위치'},
}
# 가중치 합계: 0.30 + 0.25 + 0.25 + 0.20 = 1.00

CREDIT_RISK_GRADES = {
    'SAFE': {'min_score': 0, 'max_score': 20, 'label': '안전'},
    'NORMAL': {'min_score': 20, 'max_score': 40, 'label': '보통'},
    'ELEVATED': {'min_score': 40, 'max_score': 60, 'label': '상승'},
    'HIGH': {'min_score': 60, 'max_score': 80, 'label': '높음'},
    'CRITICAL': {'min_score': 80, 'max_score': 100, 'label': '위험'},
}
```

#### 3.3.5 파일 구조

```
skills/kr-credit-monitor/
├── SKILL.md
├── references/
│   └── kr_credit_guide.md
├── scripts/
│   ├── credit_balance_analyzer.py    # 신용잔고 분석
│   ├── forced_liquidation_risk.py    # 반대매매 리스크
│   ├── report_generator.py           # 리포트 생성
│   └── tests/
│       ├── __init__.py
│       └── test_credit_monitor.py
```

#### 3.3.6 함수 시그니처

```python
# credit_balance_analyzer.py
def analyze_credit_balance(credit_data, market_cap) -> dict
    # Args: credit_data = [{date, margin_loan, margin_short, total}]
    # Returns: {total, market_ratio, yoy, mom, percentile, level, cycle_phase}

def calc_credit_percentile(current, historical) -> float
    # Returns: 0-100 percentile

def classify_leverage_cycle(credit_data) -> str
    # Returns: 'EXPANSION' / 'PEAK' / 'CONTRACTION' / 'TROUGH'

def calc_deposit_credit_ratio(credit_balance, deposit_balance) -> dict
    # Returns: {ratio, level, label}

# forced_liquidation_risk.py
def estimate_forced_liquidation(credit_data, scenarios=None) -> dict
    # Returns: {scenarios: [{drop_pct, affected_amount, market_impact, severity}]}

def calc_margin_call_threshold(credit_amount, initial_ratio, maintenance_ratio) -> dict
    # Returns: {trigger_price_drop, buffer_pct}

def calc_credit_risk_score(balance_analysis, liquidation_risk) -> dict
    # Returns: {score, grade, components}

# report_generator.py
def generate_credit_report(balance_analysis, liquidation_risk) -> str
```

---

### 3.4 Skill 43: kr-program-trade-analyzer (High)

**핵심**: 차익/비차익 프로그램 매매 + 선물 베이시스 + 만기일 효과
**차별화**: 100% 한국 고유 (미국에 없는 시장 메커니즘)

#### 3.4.1 프로그램 매매 상수

```python
# ─── 프로그램 매매 ───

PROGRAM_TRADE_CONFIG = {
    'trade_types': ['arbitrage', 'non_arbitrage'],
    'flow_periods': [1, 5, 20],  # 일, 주, 월
}

# 차익거래 기준 (KOSPI200 선물-현물)
ARBITRAGE_CONFIG = {
    'significant_amount': 500_000_000_000,   # 5000억: 유의미한 차익거래
    'large_amount': 1_000_000_000_000,       # 1조: 대규모
    'direction_signals': {
        'buy_arb': '선물 매도 + 현물 매수 (콘탱고 해소)',
        'sell_arb': '선물 매수 + 현물 매도 (백워데이션 해소)',
    },
}

# 비차익거래 기준
NON_ARBITRAGE_CONFIG = {
    'significant_amount': 300_000_000_000,   # 3000억: 유의미한 바스켓 매매
    'large_amount': 500_000_000_000,         # 5000억: 대규모
    'warning_consecutive': 5,                # 5일 연속 매도 → 경고
}

PROGRAM_FLOW_SIGNALS = {
    'STRONG_BUY': {'min_score': 80, 'label': '강한 프로그램 매수'},
    'BUY': {'min_score': 60, 'label': '프로그램 매수'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'SELL': {'min_score': 20, 'label': '프로그램 매도'},
    'STRONG_SELL': {'min_score': 0, 'label': '강한 프로그램 매도'},
}
```

#### 3.4.2 선물 베이시스 상수

```python
# ─── 선물 베이시스 ───

# kr-options-advisor 참조: KOSPI200_MULTIPLIER = 250_000
KOSPI200_MULTIPLIER = 250_000

BASIS_CONFIG = {
    'normal_range_pct': 0.003,       # 정상 베이시스: ±0.3%
    'warning_range_pct': 0.007,      # 경고 베이시스: ±0.7%
    'critical_range_pct': 0.015,     # 위험 베이시스: ±1.5%
    'risk_free_rate': 0.035,         # 무위험이자율: 3.5% (BOK 기준금리)
}

BASIS_STATES = {
    'DEEP_CONTANGO': {'label': '강한 콘탱고', 'implication': '차익 매도 가능'},
    'CONTANGO': {'label': '콘탱고', 'implication': '선물 프리미엄'},
    'FAIR': {'label': '적정', 'implication': '이론가 근접'},
    'BACKWARDATION': {'label': '백워데이션', 'implication': '선물 할인'},
    'DEEP_BACKWARDATION': {'label': '강한 백워데이션', 'implication': '차익 매수 가능'},
}

# 미결제약정 (Open Interest) 분석
OI_CONFIG = {
    'change_significant': 0.05,   # OI 5% 이상 변화: 유의미
    'change_large': 0.10,         # OI 10% 이상 변화: 대규모
}
```

#### 3.4.3 만기일 효과 상수

```python
# ─── 만기일 효과 ───

EXPIRY_CONFIG = {
    'monthly_expiry_weekday': 3,   # 목요일 (0=월, 3=목)
    'monthly_expiry_week': 2,      # 둘째 주
    'quarterly_months': [3, 6, 9, 12],  # 분기 만기월
}

# 만기 유형
EXPIRY_TYPES = {
    'MONTHLY': {
        'label': '월간 만기 (옵션)',
        'impact': 'moderate',
        'volatility_premium': 1.05,  # 변동성 5% 프리미엄
    },
    'QUARTERLY': {
        'label': '분기 만기 (선물+옵션)',
        'impact': 'high',
        'volatility_premium': 1.15,  # 변동성 15% 프리미엄
    },
}

# 만기일 근접도
EXPIRY_PROXIMITY = {
    'expiry_day': 0,    # D-day
    'near': 1,          # D-1
    'approaching': 3,   # D-3
    'week': 5,          # D-5 (만기 주간)
    'far': 999,         # 만기 주간 아님
}

# 만기 효과 패턴
EXPIRY_PATTERNS = {
    'pin_risk': '최대고통가격 근접 시 가격 고정 경향',
    'gamma_squeeze': '옵션 감마 급증으로 변동성 확대',
    'rollover_pressure': '선물 롤오버 매매 압력',
    'expiry_volatility': '만기일 거래량 급증 + 변동성',
}
```

#### 3.4.4 프로그램 영향 스코어 (0-100)

```python
# ─── 프로그램 영향 스코어 ───

PROGRAM_IMPACT_WEIGHTS = {
    'arbitrage_flow': {'weight': 0.25, 'label': '차익거래 방향/규모'},
    'non_arb_flow': {'weight': 0.30, 'label': '비차익 방향/규모'},
    'basis_signal': {'weight': 0.25, 'label': '베이시스 이상 신호'},
    'expiry_effect': {'weight': 0.20, 'label': '만기일 근접도'},
}
# 가중치 합계: 0.25 + 0.30 + 0.25 + 0.20 = 1.00

PROGRAM_IMPACT_GRADES = {
    'POSITIVE': {'min_score': 65, 'label': '긍정적 (프로그램 매수 우위)'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'NEGATIVE': {'min_score': 20, 'label': '부정적 (프로그램 매도 우위)'},
    'WARNING': {'min_score': 0, 'label': '경고 (만기일/베이시스 이상)'},
}
```

#### 3.4.5 파일 구조

```
skills/kr-program-trade-analyzer/
├── SKILL.md
├── references/
│   ├── kr_program_trade_guide.md
│   └── kr_expiry_calendar.md
├── scripts/
│   ├── program_trade_analyzer.py    # 프로그램 매매 분석
│   ├── basis_analyzer.py            # 선물 베이시스
│   ├── expiry_effect_analyzer.py    # 만기일 효과
│   ├── report_generator.py          # 리포트 생성
│   └── tests/
│       ├── __init__.py
│       └── test_program_trade.py
```

#### 3.4.6 함수 시그니처

```python
# program_trade_analyzer.py
def analyze_program_trades(program_data) -> dict
    # Args: program_data = [{date, arb_buy, arb_sell, non_arb_buy, non_arb_sell}]
    # Returns: {arbitrage, non_arbitrage, total, signal, consecutive}

def classify_program_signal(arb_net, non_arb_net) -> str
    # Returns: 'STRONG_BUY' / ... / 'STRONG_SELL'

# basis_analyzer.py
def analyze_basis(futures_price, spot_price, days_to_expiry, risk_free_rate=0.035) -> dict
    # Returns: {basis, basis_pct, theoretical_basis, state, deviation}

def calc_theoretical_basis(spot, rate, days) -> float
    # Returns: theoretical futures price

def analyze_open_interest(oi_data) -> dict
    # Returns: {current, change_pct, trend, significance}

# expiry_effect_analyzer.py
def get_next_expiry(from_date=None) -> dict
    # Returns: {date, type, days_until, proximity}

def analyze_expiry_effect(expiry_info, historical_data=None) -> dict
    # Returns: {type, proximity, volatility_premium, patterns, impact_score}

def calc_max_pain(option_data) -> dict
    # Returns: {max_pain_price, current_distance_pct}

def calc_program_impact_score(program_analysis, basis_analysis, expiry_analysis) -> dict
    # Returns: {score, grade, components}

# report_generator.py
def generate_program_trade_report(program, basis, expiry) -> str
```

---

### 3.5 Skill 44: kr-dart-disclosure-monitor (High)

**핵심**: 10유형 공시 분류 + 영향도 5단계 + 지분 변동 추적 + 리스크 스코어
**차별화**: kr-earnings-calendar(실적 5유형만) → 전체 공시 10유형 + 이벤트 영향도

#### 3.5.1 공시 유형 분류 상수

```python
# ─── DART 공시 유형 ───

DISCLOSURE_TYPES = {
    'EARNINGS': {
        'label': '실적 공시',
        'subtypes': ['preliminary', 'confirmed', 'guidance'],
        'dart_kinds': ['A001', 'A002', 'A003', 'D001', 'D002'],
        'keywords': ['사업보고서', '분기보고서', '반기보고서', '잠정실적', '영업실적'],
    },
    'DIVIDEND': {
        'label': '배당 관련',
        'subtypes': ['increase', 'decrease', 'omission', 'record_date'],
        'keywords': ['배당', '현금배당', '주식배당', '기준일'],
    },
    'CAPITAL': {
        'label': '자본 변동',
        'subtypes': ['rights_offering', 'bonus_issue', 'reduction', 'convertible'],
        'keywords': ['유상증자', '무상증자', '감자', '전환사채', 'CB', 'BW'],
    },
    'MA': {
        'label': 'M&A',
        'subtypes': ['merger', 'acquisition', 'spin_off', 'business_transfer'],
        'keywords': ['합병', '인수', '분할', '영업양수도', '주식교환'],
    },
    'GOVERNANCE': {
        'label': '지배구조',
        'subtypes': ['ceo_change', 'board', 'articles'],
        'keywords': ['대표이사', '이사선임', '정관변경', '감사', '이사회'],
    },
    'STAKE': {
        'label': '지분 변동',
        'subtypes': ['major_holder', 'officer_trade', 'treasury_stock'],
        'keywords': ['대량보유', '임원', '자사주', '주요주주', '특정증권'],
    },
    'LEGAL': {
        'label': '법적 이벤트',
        'subtypes': ['lawsuit', 'sanction', 'penalty'],
        'keywords': ['소송', '제재', '과징금', '조치', '위반'],
    },
    'IPO': {
        'label': '상장 관련',
        'subtypes': ['listing', 'delisting', 'spac'],
        'keywords': ['상장', '상장폐지', '스팩', '신규상장'],
    },
    'REGULATION': {
        'label': '규제',
        'subtypes': ['management_issue', 'investment_warning', 'trading_halt'],
        'keywords': ['관리종목', '투자주의', '매매정지', '투자위험'],
    },
    'OTHER': {
        'label': '기타',
        'subtypes': ['contract', 'patent', 'facility'],
        'keywords': ['수주', '특허', '공장', '설립', '계약'],
    },
}
```

#### 3.5.2 이벤트 영향도 상수

```python
# ─── 이벤트 영향도 (1-5) ───

EVENT_IMPACT_LEVELS = {
    5: {
        'label': 'Critical',
        'korean': '매우 심각',
        'events': [
            'delisting', 'reduction', 'management_issue', 'trading_halt',
        ],
        'action': '즉시 확인 필요',
    },
    4: {
        'label': 'High',
        'korean': '높음',
        'events': [
            'merger', 'acquisition', 'rights_offering', 'ceo_change',
            'decrease',  # 감배
            'spin_off',
        ],
        'action': '당일 내 확인',
    },
    3: {
        'label': 'Medium',
        'korean': '보통',
        'events': [
            'preliminary', 'confirmed',  # 실적
            'major_holder',  # 5% 보유변동
            'increase',  # 증배
            'convertible',  # CB/BW
        ],
        'action': '주간 리뷰 시 확인',
    },
    2: {
        'label': 'Low',
        'korean': '낮음',
        'events': [
            'treasury_stock', 'articles', 'bonus_issue',
            'contract', 'patent',
        ],
        'action': '참고',
    },
    1: {
        'label': 'Info',
        'korean': '정보',
        'events': [
            'guidance', 'board', 'facility',
            'record_date',
        ],
        'action': '기록',
    },
}

# 영향도 보정 요인
IMPACT_ADJUSTMENTS = {
    'market_cap_large': 1.0,        # 시총 10조+ → 가중치 유지
    'market_cap_mid': 0.8,          # 시총 1-10조 → 0.8배
    'market_cap_small': 0.6,        # 시총 1조 미만 → 0.6배
    'after_hours': 1.2,             # 장후 공시 → 1.2배 (다음날 반영)
    'consecutive_disclosure': 1.5,  # 연속 공시 → 1.5배 (이상 탐지)
}
```

#### 3.5.3 지분 변동 추적 상수

```python
# ─── 지분 변동 추적 ───

STAKE_CHANGE_CONFIG = {
    'major_threshold': 0.05,        # 5% 대량보유 보고 기준
    'significant_change': 0.01,     # 1%p 이상 변동: 유의미
    'accumulation_days': 5,         # 5건 이상 매수: 축적 패턴
    'disposal_days': 5,             # 5건 이상 매도: 매각 패턴
}

STAKE_SIGNALS = {
    'ACCUMULATION': {'label': '지분 축적', 'direction': 'buy', 'sentiment': 'positive'},
    'DISPOSAL': {'label': '지분 매각', 'direction': 'sell', 'sentiment': 'negative'},
    'TREASURY_BUY': {'label': '자사주 매입', 'direction': 'buy', 'sentiment': 'positive'},
    'TREASURY_SELL': {'label': '자사주 매각', 'direction': 'sell', 'sentiment': 'negative'},
    'NEUTRAL': {'label': '변동 없음', 'direction': 'none', 'sentiment': 'neutral'},
}

INSIDER_TYPES = [
    'ceo',               # 대표이사
    'executive',         # 임원
    'major_shareholder', # 최대주주/특수관계인
    'related_party',     # 특수관계법인
]
```

#### 3.5.4 공시 리스크 스코어 (0-100)

```python
# ─── 공시 리스크 스코어 ───

DISCLOSURE_RISK_WEIGHTS = {
    'event_severity': {'weight': 0.35, 'label': '이벤트 심각도'},
    'frequency': {'weight': 0.20, 'label': '공시 빈도 이상'},
    'stake_change': {'weight': 0.25, 'label': '지분 변동 방향'},
    'governance': {'weight': 0.20, 'label': '지배구조 안정성'},
}
# 가중치 합계: 0.35 + 0.20 + 0.25 + 0.20 = 1.00

DISCLOSURE_RISK_GRADES = {
    'NORMAL': {'min_score': 0, 'max_score': 25, 'label': '정상'},
    'ATTENTION': {'min_score': 25, 'max_score': 50, 'label': '주의'},
    'WARNING': {'min_score': 50, 'max_score': 75, 'label': '경고'},
    'CRITICAL': {'min_score': 75, 'max_score': 100, 'label': '위험'},
}

# 공시 빈도 이상 탐지
FREQUENCY_ANOMALY = {
    'normal_daily': 2,     # 일 2건 이하: 정상
    'elevated_daily': 5,   # 일 5건 이상: 상승
    'anomaly_daily': 10,   # 일 10건 이상: 이상 (구조조정 의심)
}
```

#### 3.5.5 파일 구조

```
skills/kr-dart-disclosure-monitor/
├── SKILL.md
├── references/
│   ├── kr_disclosure_types.md
│   └── kr_dart_api_guide.md
├── scripts/
│   ├── disclosure_classifier.py     # 공시 유형 분류
│   ├── event_impact_scorer.py       # 이벤트 영향도
│   ├── stake_change_tracker.py      # 지분 변동 추적
│   ├── report_generator.py          # 리포트 생성
│   └── tests/
│       ├── __init__.py
│       └── test_dart_disclosure.py
```

#### 3.5.6 함수 시그니처

```python
# disclosure_classifier.py
def classify_disclosure(title, report_code=None) -> dict
    # Args: title = DART 공시 제목 문자열
    # Returns: {type, subtype, keywords_matched}

def classify_batch(disclosures) -> list
    # Args: disclosures = [{title, report_code, date, corp_name}]
    # Returns: [{...original, type, subtype, impact_level}]

# event_impact_scorer.py
def score_event_impact(disclosure_type, subtype, market_cap=None, timing=None) -> dict
    # Returns: {level, label, action, adjusted_level}

def detect_frequency_anomaly(disclosures, corp_code, lookback_days=30) -> dict
    # Returns: {daily_avg, is_anomaly, anomaly_score}

def calc_disclosure_risk_score(events, stake_data, governance_data) -> dict
    # Returns: {score, grade, components}

# stake_change_tracker.py
def track_stake_changes(major_holders_data) -> dict
    # Returns: {changes: [{holder, before_pct, after_pct, change_pct, date}],
    #           signal, pattern}

def track_insider_trades(officer_data) -> dict
    # Returns: {trades: [{name, position, type, shares, amount, date}],
    #           net_direction, signal}

def track_treasury_stock(treasury_data) -> dict
    # Returns: {actions: [{type, shares, amount, date}], signal}

# report_generator.py
def generate_disclosure_report(classifications, impacts, stake_changes) -> str
```

---

## 4. 설계 상수 요약

### 4.1 스코어링 가중치 검증 (합계 = 1.00)

| 스킬 | 스코어 | 컴포넌트 | 가중치 합계 |
|------|--------|---------|:----------:|
| supply-demand | SUPPLY_DEMAND_COMPOSITE_WEIGHTS | market_flow 0.30 + sector_rotation 0.25 + liquidity 0.25 + investor_sentiment 0.20 | **1.00** |
| short-sale | SHORT_RISK_WEIGHTS | short_ratio 0.30 + trend 0.30 + concentration 0.20 + days_to_cover 0.20 | **1.00** |
| credit | CREDIT_RISK_WEIGHTS | credit_level 0.30 + growth_rate 0.25 + forced_liquidation 0.25 + leverage_cycle 0.20 | **1.00** |
| program-trade | PROGRAM_IMPACT_WEIGHTS | arbitrage_flow 0.25 + non_arb_flow 0.30 + basis_signal 0.25 + expiry_effect 0.20 | **1.00** |
| dart-disclosure | DISCLOSURE_RISK_WEIGHTS | event_severity 0.35 + frequency 0.20 + stake_change 0.25 + governance 0.20 | **1.00** |

### 4.2 총 상수 수량

| 스킬 | 상수 dict/list 수 |
|------|:-----------------:|
| supply-demand | 26 |
| short-sale | 20 |
| credit | 24 |
| program-trade | 30 |
| dart-disclosure | 32 |
| **합계** | **132** |

### 4.3 총 파일 수량

| 카테고리 | 수량 |
|---------|:----:|
| SKILL.md | 5 |
| references | 7 |
| scripts | 18 |
| tests/__init__.py | 5 |
| tests/test_*.py | 5 |
| **합계** | **40** |

---

## 5. 구현 순서 (6-Step)

```
Step 1: kr-supply-demand-analyzer
  ├── market_flow_analyzer.py (MARKET_FLOW_CONFIG, 7단계 시그널)
  ├── sector_flow_mapper.py (KR_SECTORS 14개, HHI)
  ├── liquidity_tracker.py (LIQUIDITY_CONFIG)
  ├── report_generator.py
  └── tests: ~50개

Step 2: kr-short-sale-tracker
  ├── short_ratio_analyzer.py (SHORT_BALANCE_LEVELS, 섹터 집중도)
  ├── short_cover_detector.py (숏커버 시그널, 스퀴즈 확률)
  ├── report_generator.py
  └── tests: ~40개

Step 3: kr-credit-monitor
  ├── credit_balance_analyzer.py (CREDIT_MARKET_RATIO, 레버리지 사이클)
  ├── forced_liquidation_risk.py (MARGIN_CALL_CONFIG, 시나리오)
  ├── report_generator.py
  └── tests: ~40개

Step 4: kr-program-trade-analyzer
  ├── program_trade_analyzer.py (차익/비차익)
  ├── basis_analyzer.py (KOSPI200 선물 베이시스)
  ├── expiry_effect_analyzer.py (EXPIRY_CONFIG, max_pain)
  ├── report_generator.py
  └── tests: ~50개

Step 5: kr-dart-disclosure-monitor
  ├── disclosure_classifier.py (10유형, 키워드 매칭)
  ├── event_impact_scorer.py (5단계 영향도)
  ├── stake_change_tracker.py (지분 변동 추적)
  ├── report_generator.py
  └── tests: ~50개

Step 6: 통합 테스트
  └── Phase 1-9 전체 44 모듈, ~1,632 테스트
```

---

## 6. 14 한국 섹터 일관성 확인

Phase 6 (kr-scenario-analyzer), Phase 8 (kr-weekly-strategy), Phase 9 (kr-supply-demand-analyzer)에서 동일하게 사용:

```python
KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학',
    '바이오/제약', '금융/은행', '유통/소비', '건설/부동산',
    'IT/소프트웨어', '통신', '에너지/유틸리티', '엔터테인먼트',
    '방산', '2차전지',
]  # 14개 - 변경 없음
```

---

## Version History

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2026-03-04 | Phase 9 상세 설계 작성 | Claude Code + User |
