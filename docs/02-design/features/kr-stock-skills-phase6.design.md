# Phase 6: 전략 & 리스크 관리 스킬 설계

> **Feature**: kr-stock-skills-phase6
> **Phase**: Design
> **Created**: 2026-03-03
> **Based on**: kr-stock-skills.plan.md (Section 3.6)
> **Depends on**: Phase 1 (KRClient), Phase 2-5 (분석 스킬)

---

## 1. 범위 요약

Phase 6은 전략 수립, 백테스트, 포트폴리오 관리, 엣지 발굴 파이프라인을 포함하는 **9개 스킬**을 구현한다.

| # | US 원본 | KR 스킬명 | 복잡도 | 핵심 변경 |
|:-:|---------|-----------|:------:|-----------|
| 24 | backtest-expert | **kr-backtest-expert** | High | 한국 거래비용/세금/±30% 가격제한 |
| 25 | options-strategy-advisor | **kr-options-advisor** | High | KOSPI200 옵션, 승수 25만원, VKOSPI |
| 26 | portfolio-manager | **kr-portfolio-manager** | High | KRClient 기반, 한국 섹터/세제 |
| 27 | scenario-analyzer | **kr-scenario-analyzer** | Medium | 한국 뉴스/이벤트, 한국어 출력 |
| 28 | edge-hint-extractor | **kr-edge-hint** | Low | 한국 시장 관찰, 수급 데이터 |
| 29 | edge-concept-synthesizer | **kr-edge-concept** | Low | 방법론 동일, 데이터 형식 변환 |
| 30 | edge-strategy-designer | **kr-edge-strategy** | Low | 한국 거래 비용 모델 |
| 31 | edge-candidate-agent | **kr-edge-candidate** | Medium | KR 데이터 파이프라인 |
| 32 | strategy-pivot-designer | **kr-strategy-pivot** | Low | 방법론 동일 |

**총계**: High 3 + Medium 2 + Low 4 = 9개 스킬

---

## 2. 엣지 파이프라인 아키텍처

9개 스킬은 하나의 파이프라인을 구성한다:

```
kr-edge-hint → kr-edge-concept → kr-edge-strategy → kr-edge-candidate
      ↓                                                     ↓
  hints.yaml                                          strategy.yaml
                                                           ↓
kr-scenario-analyzer ←→ kr-backtest-expert ←→ kr-strategy-pivot
                              ↓
                     backtest_eval.json
                              ↓
                    kr-portfolio-manager
                              ↓
                    kr-options-advisor (포지션 리스크)
```

---

## 3. 스킬별 상세 설계

---

### 3.1 Skill 24: kr-backtest-expert (High)

**US 원본**: backtest-expert
**핵심**: 5차원 스코어링으로 백테스트 결과를 평가하고 DEPLOY/REFINE/ABANDON 판정

#### 3.1.1 5차원 스코어링 시스템 (US 동일, 총 100점)

```python
# ─── Dimension 1: Sample Size (20점) ───
SAMPLE_SIZE_SCORING = [
    # (trades, points)
    (200, 20),   # ≥200: 만점
    (100, 15),   # 100-199: 15점
    (30, 8),     # 30-99: 8점
    (0, 0),      # <30: 0점
]

# ─── Dimension 2: Expectancy (20점) ───
# expectancy = win_rate * avg_win - loss_rate * avg_loss
EXPECTANCY_THRESHOLDS = [
    (1.5, 20),   # ≥1.5%: 만점
    (0.5, 10),   # 0.5-1.5%: 10-18 (선형)
    (0.0, 5),    # 0-0.5%: 5-10 (선형)
    (-999, 0),   # <0%: 0점
]

# ─── Dimension 3: Risk Management (20점) ───
# Drawdown Component (0-12) + Profit Factor Component (0-8)
MAX_DRAWDOWN_CATASTROPHIC = 50   # ≥50%: 0점 강제
DRAWDOWN_SAFE = 20               # <20%: 12점 만점
PROFIT_FACTOR_MAX = 3.0          # ≥3.0: 8점 만점
PROFIT_FACTOR_MIN = 1.0          # <1.0: 0점

# ─── Dimension 4: Robustness (20점) ───
# Years Component (0-15) + Parameter Component (0-5)
MIN_YEARS_TESTED = 5             # <5년: 0점
MAX_YEARS_FULL = 10              # ≥10년: 15점
MAX_PARAMS_NO_PENALTY = 4        # ≤4개: 5점
PARAMS_MEDIUM_PENALTY = 6        # 5-6개: 3점
PARAMS_HEAVY_PENALTY = 7         # 7개: 1점
PARAMS_SEVERE_PENALTY = 8        # ≥8개: 0점

# ─── Dimension 5: Execution Realism (20점) ───
# 슬리피지 테스트 완료 → 20점, 미완료 → 0점
```

#### 3.1.2 판정 기준 (US 동일)

```python
VERDICT_THRESHOLDS = {
    'DEPLOY': 70,    # ≥70점: 배포
    'REFINE': 40,    # 40-69점: 개선
    'ABANDON': 0,    # <40점: 포기
}
```

#### 3.1.3 Red Flags (US 동일 + 한국 추가)

```python
RED_FLAGS = [
    # US 동일
    {'id': 'small_sample', 'severity': 'HIGH', 'trigger': 'total_trades < 30'},
    {'id': 'no_slippage_test', 'severity': 'HIGH', 'trigger': 'slippage_tested = False'},
    {'id': 'excessive_drawdown', 'severity': 'HIGH', 'trigger': 'max_drawdown_pct > 50'},
    {'id': 'negative_expectancy', 'severity': 'HIGH', 'trigger': 'expectancy < 0'},
    {'id': 'over_optimized', 'severity': 'MEDIUM', 'trigger': 'num_parameters >= 7'},
    {'id': 'short_test_period', 'severity': 'MEDIUM', 'trigger': 'years_tested < 5'},
    {'id': 'too_good', 'severity': 'MEDIUM', 'trigger': 'win_rate > 90 AND max_dd < 5'},
    # 한국 추가
    {'id': 'price_limit_untested', 'severity': 'MEDIUM',
     'trigger': '±30% 가격제한폭 시나리오 미테스트'},
    {'id': 'tax_unaccounted', 'severity': 'MEDIUM',
     'trigger': '거래세/배당세 미반영'},
]
```

#### 3.1.4 한국 거래 비용 모델

```python
KR_COST_MODEL = {
    'brokerage_fee': 0.00015,      # 0.015% (증권사 온라인 수수료)
    'sell_tax': 0.0023,            # 0.23% (증권거래세, 매도 시)
    'dividend_tax': 0.154,         # 15.4% (배당소득세)
    'capital_gains_tax': 0.22,     # 22% (대주주 양도소득세, 해당 시)
    'slippage_default': 0.001,     # 0.1% (기본 슬리피지)
    'slippage_stress': 0.002,      # 0.2% (스트레스 슬리피지)
}

# 가격제한폭
KR_PRICE_LIMIT = 0.30             # ±30%
```

#### 3.1.5 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_backtest_methodology.md` | 한국 시장 백테스트 방법론 |
| `references/kr_cost_model.md` | 한국 거래 비용 가이드 |
| `scripts/evaluate_backtest.py` | 5차원 스코어링 엔진 |
| `scripts/kr_cost_calculator.py` | 한국 거래 비용 계산기 |
| `scripts/report_generator.py` | JSON/Markdown 리포트 |
| `scripts/tests/test_backtest_expert.py` | 테스트 (~30) |

---

### 3.2 Skill 25: kr-options-advisor (High)

**US 원본**: options-strategy-advisor
**핵심**: KOSPI200 옵션 기반 Black-Scholes 가격결정, 그릭스, 18개 전략

#### 3.2.1 한국 옵션 시장 상수

```python
# ─── KOSPI200 옵션 기본 상수 ───
KOSPI200_MULTIPLIER = 250_000      # 1포인트 = 25만원
KOSPI200_TICK_SIZE = 0.01          # 프리미엄 <3: 0.01pt, ≥3: 0.05pt
KOSPI200_TICK_VALUE = 2_500        # 0.01pt × 25만원

# ─── 금리 ───
KR_RISK_FREE_RATE = 0.035         # BOK 기준금리 3.5% (변동)

# ─── 변동성 ───
VKOSPI_DEFAULT = 0.20             # VKOSPI 기본값
HV_LOOKBACK = 90                  # 역사적 변동성 데이터 수집 기간
HV_WINDOW = 30                    # 역사적 변동성 계산 윈도우

# ─── ATM 판정 ───
ATM_TOLERANCE = 0.02              # ±2% 이내: ATM

# ─── 거래 단위 ───
TRADING_HOURS = (9, 0, 15, 45)    # 09:00-15:45 (KST)
SETTLEMENT = 'T+1'                # T+1 결제 (현금결제)
LAST_TRADING_DAY = '매월 2번째 목요일'  # 옵션 만기일
```

#### 3.2.2 18개 전략 (US 동일 구조)

```python
STRATEGIES = {
    # 인컴 전략 (3)
    'covered_call': {'legs': 2, 'category': 'income'},
    'cash_secured_put': {'legs': 1, 'category': 'income'},
    'poor_mans_covered_call': {'legs': 2, 'category': 'income'},
    # 보호 전략 (2)
    'protective_put': {'legs': 2, 'category': 'protection'},
    'collar': {'legs': 3, 'category': 'protection'},
    # 방향성 전략 (6)
    'bull_call_spread': {'legs': 2, 'category': 'directional'},
    'bull_put_spread': {'legs': 2, 'category': 'directional'},
    'bear_call_spread': {'legs': 2, 'category': 'directional'},
    'bear_put_spread': {'legs': 2, 'category': 'directional'},
    'long_straddle': {'legs': 2, 'category': 'directional'},
    'long_strangle': {'legs': 2, 'category': 'directional'},
    # 변동성 전략 (4)
    'short_straddle': {'legs': 2, 'category': 'volatility'},
    'short_strangle': {'legs': 2, 'category': 'volatility'},
    'iron_condor': {'legs': 4, 'category': 'volatility'},
    'iron_butterfly': {'legs': 4, 'category': 'volatility'},
    # 고급 전략 (3)
    'calendar_spread': {'legs': 2, 'category': 'advanced'},
    'diagonal_spread': {'legs': 2, 'category': 'advanced'},
    'ratio_spread': {'legs': 3, 'category': 'advanced'},
}
```

#### 3.2.3 포트폴리오 그릭스 타겟 (US 동일)

```python
GREEKS_TARGETS = {
    'delta': (-10, 10),       # 델타 중립 목표
    'theta': 'positive',      # 양의 세타 선호
    'vega_warning': 500,      # $500 → KRW 환산 필요 없음 (포인트 기준)
}

# 포지션 사이징
POSITION_SIZING = {
    'risk_tolerance': 0.02,    # 계좌의 2%
}
```

#### 3.2.4 IV Crush 모델

```python
IV_CRUSH_MODEL = {
    'pre_earnings_iv_premium': 1.5,   # 실적 전 IV 1.5배
    'post_earnings_iv_drop': 0.625,   # 실적 후 IV 62.5%로 하락
}
```

#### 3.2.5 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kospi200_options_guide.md` | KOSPI200 옵션 가이드 |
| `references/strategy_playbook_kr.md` | 18개 전략 한국어 설명 |
| `scripts/black_scholes.py` | BS 가격결정 + 그릭스 엔진 |
| `scripts/strategy_simulator.py` | P/L 시뮬레이션 |
| `scripts/report_generator.py` | 리포트 생성 |
| `scripts/tests/test_options_advisor.py` | 테스트 (~25) |

---

### 3.3 Skill 26: kr-portfolio-manager (High)

**US 원본**: portfolio-manager
**핵심**: KRClient 기반 포트폴리오 분석, 한국 섹터/세제 반영

#### 3.3.1 분석 차원

```python
# ─── 자산 배분 분석 차원 ───
ALLOCATION_DIMENSIONS = [
    'asset_class',       # 주식/채권/현금/대안
    'sector',            # KRX 업종 분류
    'market_cap',        # 대형/중형/소형
    'market',            # KOSPI/KOSDAQ/ETF
]

# ─── 분산 투자 지표 ───
DIVERSIFICATION = {
    'optimal_positions': (15, 30),    # 최적 종목 수
    'under_diversified': 10,          # 미만: 과집중
    'over_diversified': 50,           # 초과: 과분산
    'max_single_position': 0.15,      # 단일 종목 15%
    'max_sector': 0.35,               # 단일 섹터 35%
    'correlation_redundancy': 0.8,    # 상관계수 >0.8: 중복
}

# ─── 리밸런싱 기준 ───
REBALANCING = {
    'major_drift': 0.10,     # 10% 이상 편차: 즉시
    'moderate_drift': 0.05,  # 5-10% 편차: 높음
    'excess_cash': 0.10,     # 현금 10% 초과: 배분 필요
}
```

#### 3.3.2 한국 세제 모델

```python
KR_TAX_MODEL = {
    'dividend_tax': 0.154,           # 15.4% (소득세 14% + 지방세 1.4%)
    'financial_income_threshold': 20_000_000,  # 2,000만원 (금융소득종합과세)
    'capital_gains_tax': 0.22,       # 22% (대주주 양도세)
    'capital_gains_threshold': 1_000_000_000,  # 10억원 (대주주 기준)
    'transaction_tax': 0.0023,       # 0.23% (증권거래세)
    'isa_tax_free': 2_000_000,       # ISA 비과세 한도 200만원
}
```

#### 3.3.3 액션 추천 기준

```python
POSITION_ACTIONS = ['HOLD', 'ADD', 'TRIM', 'SELL']

REBALANCING_PRIORITY = [
    'IMMEDIATE',  # 리스크 축소 (과집중 해소)
    'HIGH',       # 주요 편차 (>10%)
    'MEDIUM',     # 중간 편차 (5-10%)
    'LOW',        # 미세 조정
]
```

#### 3.3.4 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_portfolio_guidelines.md` | 한국 포트폴리오 관리 가이드 |
| `references/kr_tax_guide.md` | 한국 투자 세제 가이드 |
| `scripts/portfolio_analyzer.py` | 포트폴리오 분석 엔진 |
| `scripts/risk_calculator.py` | 리스크 메트릭스 계산 |
| `scripts/rebalancing_engine.py` | 리밸런싱 추천 엔진 |
| `scripts/report_generator.py` | 리포트 생성 |
| `scripts/tests/test_portfolio_manager.py` | 테스트 (~25) |

---

### 3.4 Skill 27: kr-scenario-analyzer (Medium)

**US 원본**: scenario-analyzer (일본어 출력)
**핵심**: 한국 뉴스/이벤트 → 18개월 시나리오 분석, 한국어 출력

#### 3.4.1 시나리오 구조

```python
SCENARIO_STRUCTURE = {
    'base': {'name': '기본 시나리오', 'probability': None},  # 합계 100%
    'bull': {'name': '강세 시나리오', 'probability': None},
    'bear': {'name': '약세 시나리오', 'probability': None},
}

TIME_HORIZON_MONTHS = 18

# 영향 분석 단계
IMPACT_ORDERS = ['1차 영향', '2차 영향', '3차 영향']

# 종목 추천
RECOMMENDATION_COUNT = {
    'positive': (3, 5),   # 3-5개 수혜 종목
    'negative': (3, 5),   # 3-5개 피해 종목
}
```

#### 3.4.2 한국 섹터 민감도

```python
KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학', '바이오/제약',
    '금융/은행', '유통/소비재', '건설/부동산', 'IT/소프트웨어',
    '통신', '에너지/유틸리티', '엔터테인먼트', '방산', '2차전지',
]

# 한국 특화 이벤트 유형
KR_EVENT_TYPES = [
    'bok_rate_decision',      # BOK 금통위 금리결정
    'north_korea_geopolitical', # 북한 지정학 리스크
    'china_trade_policy',     # 중국 통상 정책
    'semiconductor_cycle',    # 반도체 사이클
    'exchange_rate_shock',    # 환율 급변
    'government_policy',      # 정부 정책 (부동산, 규제)
    'earnings_surprise',      # 대형주 실적 서프라이즈
]
```

#### 3.4.3 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_sector_sensitivity.md` | 한국 섹터 민감도 매트릭스 |
| `references/kr_event_patterns.md` | 한국 이벤트 패턴 |
| `references/scenario_playbooks_kr.md` | 시나리오 플레이북 |
| `scripts/kr_scenario_analyzer.py` | 시나리오 분석 엔진 |
| `scripts/report_generator.py` | 리포트 생성 |
| `scripts/tests/test_scenario_analyzer.py` | 테스트 (~15) |

---

### 3.5 Skill 28: kr-edge-hint (Low)

**US 원본**: edge-hint-extractor
**핵심**: 한국 시장 관찰 → 구조화된 엣지 힌트, 수급 데이터 활용

#### 3.5.1 상수

```python
# Risk On/Off 판정
RISK_ON_OFF_THRESHOLD = 10  # risk_on - risk_off ≥ 10: RiskOn

# 지원 진입 패밀리
SUPPORTED_ENTRY_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}

# 한국 추가 힌트 소스
KR_HINT_SOURCES = [
    'foreign_flow',           # 외국인 수급 전환
    'institutional_flow',     # 기관 수급
    'program_trading',        # 프로그램 매매
    'short_interest',         # 공매도 잔고
    'credit_balance',         # 신용잔고
]
```

#### 3.5.2 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_hints_schema.md` | 힌트 스키마 |
| `scripts/build_hints.py` | 힌트 생성기 |
| `scripts/tests/test_edge_hint.py` | 테스트 (~10) |

---

### 3.6 Skill 29: kr-edge-concept (Low)

**US 원본**: edge-concept-synthesizer
**핵심**: 8개 가설 유형 기반 엣지 컨셉 합성 (방법론 US 동일)

#### 3.6.1 8개 가설 유형

```python
HYPOTHESIS_TYPES = {
    'breakout': '참여 확대 기반 추세 돌파',
    'earnings_drift': '이벤트 기반 지속 드리프트',
    'news_reaction': '뉴스 과반응 드리프트',
    'futures_trigger': '교차 자산 전파',
    'calendar_anomaly': '계절성 수요 불균형',
    'panic_reversal': '충격 과도 반전',
    'regime_shift': '레짐 전환 기회',
    'sector_x_stock': '리더-래거드 섹터 릴레이',
}

# 컨셉 합성 최소 지지
MIN_TICKET_SUPPORT = 2

# 내보내기 가능 패밀리
EXPORTABLE_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}
```

#### 3.6.2 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/concept_schema_kr.md` | 컨셉 스키마 |
| `scripts/synthesize_concepts.py` | 컨셉 합성 엔진 |
| `scripts/tests/test_edge_concept.py` | 테스트 (~10) |

---

### 3.7 Skill 30: kr-edge-strategy (Low)

**US 원본**: edge-strategy-designer
**핵심**: 엣지 컨셉 → 전략 드래프트 변환, 한국 거래 비용 반영

#### 3.7.1 리스크 프로파일

```python
RISK_PROFILES = {
    'conservative': {
        'risk_per_trade': 0.005,   # 0.5%
        'max_positions': 3,
        'stop_loss_pct': 0.05,     # 5%
        'take_profit_rr': 2.2,
    },
    'balanced': {
        'risk_per_trade': 0.01,    # 1.0%
        'max_positions': 5,
        'stop_loss_pct': 0.07,     # 7%
        'take_profit_rr': 3.0,
    },
    'aggressive': {
        'risk_per_trade': 0.015,   # 1.5%
        'max_positions': 7,
        'stop_loss_pct': 0.09,     # 9%
        'take_profit_rr': 3.5,
    },
}

# 변형 오버라이드
VARIANT_OVERRIDES = {
    'core': {'risk_multiplier': 1.0},
    'conservative': {'risk_multiplier': 0.75},
    'research_probe': {'risk_multiplier': 0.5},
}

# 전략 공통
MAX_SECTOR_EXPOSURE = 0.30         # 섹터 집중 30%
TIME_STOP_BREAKOUT = 20            # 돌파 전략: 20일
TIME_STOP_DEFAULT = 10             # 기본: 10일
```

#### 3.7.2 한국 비용 모델 (전략 수준)

```python
KR_STRATEGY_COSTS = {
    'round_trip_cost': 0.0053,     # 0.015%×2(매수매도) + 0.23%(거래세) + 0.2%(슬리피지)
    'holding_cost_daily': 0.0,     # 현물 보유비용 없음
    'margin_rate': 0.0,            # 현물 거래 기준 (신용 미사용)
}
```

#### 3.7.3 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/strategy_draft_schema_kr.md` | 전략 드래프트 스키마 |
| `scripts/design_strategy_drafts.py` | 전략 드래프트 생성기 |
| `scripts/tests/test_edge_strategy.py` | 테스트 (~12) |

---

### 3.8 Skill 31: kr-edge-candidate (Medium)

**US 원본**: edge-candidate-agent
**핵심**: 한국 시장 데이터 기반 후보 자동탐지 및 파이프라인 내보내기

#### 3.8.1 인터페이스 스펙 (US 동일)

```python
# edge-finder-candidate/v1 인터페이스
CANDIDATE_REQUIRED_KEYS = [
    'id', 'name', 'universe', 'signals',
    'risk', 'cost_model', 'validation', 'promotion_gates',
]

# 검증 규칙
VALIDATION_RULES = {
    'risk_per_trade_max': 0.10,       # ≤10%
    'max_positions_min': 1,            # ≥1
    'max_sector_exposure_max': 1.0,    # ≤100%
    'validation_method': 'full_sample', # Phase I
}
```

#### 3.8.2 한국 유니버스

```python
KR_UNIVERSES = {
    'kospi200': 'KOSPI200 구성종목',
    'kosdaq150': 'KOSDAQ150 구성종목',
    'all_kospi': 'KOSPI 전체',
    'all_kosdaq': 'KOSDAQ 전체',
}
```

#### 3.8.3 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_pipeline_spec.md` | 한국 파이프라인 스펙 |
| `references/kr_signal_mapping.md` | 한국 시장 시그널 매핑 |
| `scripts/auto_detect_candidates.py` | 자동 후보 탐지 |
| `scripts/candidate_contract.py` | 인터페이스 검증 |
| `scripts/export_candidate.py` | 후보 내보내기 |
| `scripts/tests/test_edge_candidate.py` | 테스트 (~15) |

---

### 3.9 Skill 32: kr-strategy-pivot (Low)

**US 원본**: strategy-pivot-designer
**핵심**: 백테스트 반복 정체 감지 및 구조적 피벗 제안 (방법론 US 동일)

#### 3.9.1 4개 정체 트리거

```python
STAGNATION_TRIGGERS = {
    'improvement_plateau': {
        'window': 3,           # 최근 3회 반복
        'threshold': 3,        # 점수 범위 < 3점
        'severity': 'HIGH',
    },
    'overfitting_proxy': {
        'expectancy_min': 15,
        'risk_mgmt_min': 15,
        'robustness_max': 10,
        'severity': 'MEDIUM',
    },
    'cost_defeat': {
        'description': '거래 비용이 얇은 엣지를 초과',
        'severity': 'HIGH',
    },
    'tail_risk_elevation': {
        'description': '꼬리 리스크/드로다운 초과',
        'severity': 'HIGH',
    },
}

# 판정
DIAGNOSIS_OUTCOMES = ['continue', 'pivot', 'abandon']
```

#### 3.9.2 파일 인벤토리

| 파일 | 용도 |
|------|------|
| `SKILL.md` | 스킬 매뉴얼 |
| `references/kr_pivot_techniques.md` | 피벗 기법 가이드 |
| `scripts/detect_stagnation.py` | 정체 감지 |
| `scripts/generate_pivots.py` | 피벗 제안 생성 |
| `scripts/tests/test_strategy_pivot.py` | 테스트 (~12) |

---

## 4. 파일 인벤토리 총괄

### 4.1 스킬별 파일 수

| 스킬 | SKILL.md | refs | scripts | tests | 합계 |
|------|:--------:|:----:|:-------:|:-----:|:----:|
| kr-backtest-expert | 1 | 2 | 3 | 1 | 7 |
| kr-options-advisor | 1 | 2 | 3 | 1 | 7 |
| kr-portfolio-manager | 1 | 2 | 4 | 1 | 8 |
| kr-scenario-analyzer | 1 | 3 | 2 | 1 | 7 |
| kr-edge-hint | 1 | 1 | 1 | 1 | 4 |
| kr-edge-concept | 1 | 1 | 1 | 1 | 4 |
| kr-edge-strategy | 1 | 1 | 1 | 1 | 4 |
| kr-edge-candidate | 1 | 2 | 3 | 1 | 7 |
| kr-strategy-pivot | 1 | 1 | 2 | 1 | 5 |
| **합계** | **9** | **15** | **20** | **9** | **53** |

### 4.2 테스트 예상 수

| 스킬 | 테스트 수 | 주요 테스트 항목 |
|------|:--------:|----------------|
| kr-backtest-expert | ~30 | 5차원 스코어링, 판정, Red Flags, 비용 계산 |
| kr-options-advisor | ~25 | BS 가격, 그릭스, 전략 시뮬레이션, KOSPI200 |
| kr-portfolio-manager | ~25 | 배분 분석, 리스크, 리밸런싱, 세제 |
| kr-scenario-analyzer | ~15 | 시나리오 구조, 섹터 분석, 확률 합산 |
| kr-edge-hint | ~10 | 힌트 생성, Risk On/Off, 수급 데이터 |
| kr-edge-concept | ~10 | 가설 유형, 컨셉 합성, 내보내기 |
| kr-edge-strategy | ~12 | 리스크 프로파일, 드래프트, 비용 모델 |
| kr-edge-candidate | ~15 | 인터페이스 검증, 유니버스, 자동탐지 |
| kr-strategy-pivot | ~12 | 정체 감지 4트리거, 피벗 제안, 판정 |
| **합계** | **~154** | |

---

## 5. 한국 특화 사항 요약

| 항목 | 내용 | 적용 스킬 |
|------|------|----------|
| 거래 비용 | 수수료 0.015% + 거래세 0.23% + 슬리피지 | backtest, edge-strategy |
| 배당/양도세 | 15.4% 배당세, 22% 양도세, 금융소득종합과세 | portfolio, backtest |
| ISA/연금 | 비과세 한도 200만원, 세액공제 | portfolio |
| KOSPI200 옵션 | 승수 25만원, T+1 결제, 매월 2째주 목요일 만기 | options |
| VKOSPI | VIX 대체 변동성 지수 | options |
| ±30% 가격제한 | 변동성 분석, 갭 분석 영향 | backtest |
| 한국 섹터 | 14개 한국 섹터 분류 | scenario, portfolio |
| 한국 이벤트 | BOK 금통위, 북한 리스크, 중국 통상 | scenario |
| 수급 데이터 | 외국인/기관/개인 일별 수급 힌트 | edge-hint |
| KR 유니버스 | KOSPI200, KOSDAQ150 | edge-candidate |

---

## 6. 구현 순서

### 6-Step 구현 계획

```
Step 1 (Low × 4): kr-edge-hint → kr-edge-concept → kr-edge-strategy → kr-strategy-pivot
Step 2 (Medium × 2): kr-scenario-analyzer → kr-edge-candidate
Step 3 (High): kr-backtest-expert
Step 4 (High): kr-options-advisor
Step 5 (High): kr-portfolio-manager
Step 6: 전체 테스트 실행 (9개 스킬 × 개별 테스트)
```

### 예상 기간: ~14일

| Step | 스킬 수 | 예상 시간 |
|:----:|:-------:|:---------:|
| 1 | 4 Low | 2일 |
| 2 | 2 Medium | 3일 |
| 3 | 1 High | 3일 |
| 4 | 1 High | 3일 |
| 5 | 1 High | 3일 |
| 6 | 통합 테스트 | - |

---

## 7. 의존성 & 선행 조건

### Phase 1-5 의존성

| 의존 대상 | 용도 | 사용 스킬 |
|----------|------|----------|
| KRClient (Phase 1) | 주가/재무/수급 데이터 | 전체 |
| kr-institutional-flow (Phase 5) | 수급 시그널 | edge-hint |
| kr-earnings-trade (Phase 5) | 실적 분석 | scenario, backtest |
| kr-market-top-detector (Phase 3) | 시장 상태 | scenario, edge-hint |
| kr-macro-regime (Phase 3) | 레짐 판단 | edge-concept, edge-strategy |

### 외부 의존성

- **scipy**: Black-Scholes norm.cdf (옵션 가격결정)
- **numpy**: 행렬 연산 (포트폴리오 상관계수)
- **yaml**: 엣지 파이프라인 데이터 형식

> 모든 의존성은 `pip install` 가능한 표준 패키지.
