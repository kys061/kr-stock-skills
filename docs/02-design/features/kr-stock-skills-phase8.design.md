# Phase 8: 메타 & 유틸리티 스킬 설계

> **Feature**: kr-stock-skills-phase8
> **Phase**: Design
> **Created**: 2026-03-04
> **Based on**: kr-stock-skills.plan.md (Section 3.8)
> **Depends on**: Phase 1 (KRClient), Phase 2-7 (모든 업스트림 스킬)

---

## 1. 범위 요약

Phase 8은 **개별 종목 종합 분석, 전략 통합/합성, 스킬 품질 리뷰, 주간 전략 워크플로우**를 다루는 4개 스킬을 구현한다.

| # | US 원본 | KR 스킬명 | 복잡도 | 핵심 변경 |
|:-:|---------|-----------|:------:|-----------|
| 36 | us-stock-analysis | **kr-stock-analysis** | High | PyKRX+DART 기반 종합 분석, 수급 분석 추가 |
| 37 | stanley-druckenmiller-investment | **kr-strategy-synthesizer** | High | KR 스킬 8개 JSON 통합, 한국 시장 확신도 |
| 38 | dual-axis-skill-reviewer | **kr-skill-reviewer** | Medium | 메타 스킬 (방법론 동일, KR 스킬 대상) |
| 39 | weekly-trade-strategy | **kr-weekly-strategy** | Medium | 한국 시장 주간 전략 워크플로우 |

**총계**: High 2 + Medium 2 = 4개 스킬

---

## 2. 스킬 간 관계 아키텍처

```
Phase 2-7 (모든 업스트림 스킬)
──────────────────────────
│
├─→ kr-stock-analysis (개별 종목 종합 분석)
│     ├── 펀더멘털 (DART 재무제표)
│     ├── 기술적 (PyKRX OHLCV + RSI/MACD/BB)
│     ├── 수급 (외국인/기관/개인)
│     └── 밸류에이션 (PER/PBR/PSR)
│
├─→ kr-strategy-synthesizer (전략 통합)
│     ├── 8개 업스트림 스킬 JSON 통합
│     ├── 7-컴포넌트 확신도 (0-100)
│     ├── 4 패턴 분류
│     └── 자산 배분 추천
│
├─→ kr-skill-reviewer (품질 리뷰)
│     ├── Auto Axis (5 체크)
│     ├── LLM Axis (딥 리뷰)
│     └── 합산 점수 (0-100)
│
└─→ kr-weekly-strategy (주간 전략)
      ├── 시장 환경 분석
      ├── 섹터 전략
      ├── 리스크 관리
      └── 액션 플랜
```

---

## 3. 스킬별 상세 설계

---

### 3.1 Skill 36: kr-stock-analysis (High)

**US 원본**: us-stock-analysis
**핵심**: PyKRX+DART 기반 한국 종목 종합 분석 + 수급 분석

#### 3.1.1 분석 유형

```python
# ─── 분석 유형 ───

ANALYSIS_TYPES = [
    'BASIC',          # 기본 정보 (시가총액, PER, PBR, 배당, 52주 고저)
    'FUNDAMENTAL',    # 펀더멘털 (매출, 영업이익, ROE, 부채비율, 현금흐름)
    'TECHNICAL',      # 기술적 분석 (MA, RSI, MACD, Bollinger Bands)
    'SUPPLY_DEMAND',  # 수급 분석 (외국인, 기관, 개인 - KR 고유)
    'COMPREHENSIVE',  # 종합 리포트 (위 4개 통합)
]
```

#### 3.1.2 펀더멘털 분석 지표

```python
# ─── 펀더멘털 지표 ───

FUNDAMENTAL_METRICS = {
    'valuation': {
        'per': {'label': 'PER', 'source': 'PyKRX'},
        'pbr': {'label': 'PBR', 'source': 'PyKRX'},
        'psr': {'label': 'PSR', 'source': 'calculated'},
        'ev_ebitda': {'label': 'EV/EBITDA', 'source': 'DART'},
    },
    'profitability': {
        'roe': {'label': 'ROE', 'source': 'DART'},
        'roa': {'label': 'ROA', 'source': 'DART'},
        'operating_margin': {'label': '영업이익률', 'source': 'DART'},
        'net_margin': {'label': '순이익률', 'source': 'DART'},
    },
    'growth': {
        'revenue_growth_3y': {'label': '매출 3년 CAGR', 'source': 'DART'},
        'earnings_growth_3y': {'label': '순이익 3년 CAGR', 'source': 'DART'},
        'dividend_growth_3y': {'label': '배당 3년 CAGR', 'source': 'DART'},
    },
    'financial_health': {
        'debt_ratio': {'label': '부채비율', 'source': 'DART'},
        'current_ratio': {'label': '유동비율', 'source': 'DART'},
        'interest_coverage': {'label': '이자보상비율', 'source': 'DART'},
    },
}
```

#### 3.1.3 기술적 분석 지표

```python
# ─── 기술적 지표 ───

TECHNICAL_INDICATORS = {
    'trend': {
        'ma20': {'period': 20, 'label': '20일 이동평균'},
        'ma60': {'period': 60, 'label': '60일 이동평균'},
        'ma120': {'period': 120, 'label': '120일 이동평균'},
    },
    'momentum': {
        'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},
    },
    'volatility': {
        'bollinger': {'period': 20, 'std': 2},
    },
    'volume': {
        'avg_volume_20': {'period': 20, 'label': '20일 평균 거래량'},
        'volume_ratio': {'label': '거래량 비율 (당일/20일평균)'},
    },
}
```

#### 3.1.4 수급 분석 (KR 고유)

```python
# ─── 수급 분석 ───

SUPPLY_DEMAND_ANALYSIS = {
    'investor_types': [
        'foreign',          # 외국인
        'institution',      # 기관 합계
        'individual',       # 개인
    ],
    'periods': [1, 5, 20, 60],  # 일, 주, 월, 분기
    'signals': {
        'strong_buy': {'foreign': 'buy', 'institution': 'buy'},
        'buy': {'foreign': 'buy', 'institution': 'neutral'},
        'neutral': {},
        'sell': {'foreign': 'sell', 'institution': 'sell'},
        'strong_sell': {'foreign': 'sell', 'institution': 'sell', 'individual': 'buy'},
    },
}
```

#### 3.1.5 종합 점수 (0-100)

```python
# ─── 종합 분석 스코어링 ───

COMPREHENSIVE_SCORING = {
    'fundamental': {'weight': 0.35, 'label': '펀더멘털'},
    'technical': {'weight': 0.25, 'label': '기술적'},
    'supply_demand': {'weight': 0.25, 'label': '수급'},
    'valuation': {'weight': 0.15, 'label': '밸류에이션'},
}

ANALYSIS_GRADES = {
    'STRONG_BUY': 80,
    'BUY': 65,
    'HOLD': 50,
    'SELL': 35,
    'STRONG_SELL': 0,
}
```

#### 3.1.6 파일 구조

```
skills/kr-stock-analysis/
├── SKILL.md
├── references/
│   └── kr_stock_analysis_guide.md
├── scripts/
│   ├── fundamental_analyzer.py       # 펀더멘털 분석
│   ├── technical_analyzer.py         # 기술적 분석
│   ├── supply_demand_analyzer.py     # 수급 분석 (KR 고유)
│   ├── comprehensive_scorer.py       # 종합 스코어링
│   ├── report_generator.py           # 리포트 생성
│   └── tests/
│       └── test_stock_analysis.py
```

#### 3.1.7 함수 시그니처

```python
# fundamental_analyzer.py
def analyze_fundamentals(stock_data) -> dict
    # Returns: {valuation, profitability, growth, health, score}

# technical_analyzer.py
def calc_moving_averages(prices, periods) -> dict
def calc_rsi(prices, period=14) -> float
def calc_macd(prices) -> dict
def calc_bollinger_bands(prices, period=20, std=2) -> dict
def analyze_technicals(ohlcv_data) -> dict
    # Returns: {trend, momentum, volatility, volume, score}

# supply_demand_analyzer.py
def analyze_supply_demand(investor_data, periods) -> dict
    # Returns: {foreign, institution, individual, signal, score}
def classify_supply_signal(foreign_net, inst_net) -> str

# comprehensive_scorer.py
def calc_comprehensive_score(fundamental, technical, supply_demand) -> dict
    # Returns: {score, grade, components, recommendation}
```

**예상 테스트**: ~55개

---

### 3.2 Skill 37: kr-strategy-synthesizer (High)

**US 원본**: stanley-druckenmiller-investment
**핵심**: 8개 KR 스킬 JSON 결과를 통합하여 확신도 (0-100) 및 자산 배분 추천

#### 3.2.1 7-컴포넌트 스코어링

```python
# ─── 확신도 스코어링 ───

CONVICTION_COMPONENTS = {
    'market_structure': {
        'weight': 0.18,
        'sources': ['kr-market-breadth', 'kr-uptrend-analyzer'],
        'description': '시장 참여도 건강성',
    },
    'distribution_risk': {
        'weight': 0.18,
        'sources': ['kr-market-top-detector'],
        'description': '기관 매도 리스크 (역수)',
    },
    'bottom_confirmation': {
        'weight': 0.12,
        'sources': ['kr-ftd-detector'],
        'description': '바닥 확인 시그널',
    },
    'macro_alignment': {
        'weight': 0.18,
        'sources': ['kr-macro-regime'],
        'description': '거시 레짐 유리도',
    },
    'theme_quality': {
        'weight': 0.12,
        'sources': ['kr-theme-detector'],
        'description': '섹터 모멘텀 품질',
    },
    'setup_availability': {
        'weight': 0.10,
        'sources': ['kr-vcp-screener', 'kr-canslim-screener'],
        'description': '품질 셋업 가용성',
    },
    'signal_convergence': {
        'weight': 0.12,
        'sources': ['all_required'],
        'description': '스킬 간 시그널 수렴도',
    },
}
# weights sum = 0.18+0.18+0.12+0.18+0.12+0.10+0.12 = 1.00
```

#### 3.2.2 확신도 존

```python
# ─── 확신도 존 ───

CONVICTION_ZONES = {
    'MAXIMUM': {
        'min_score': 80,
        'equity_range': (90, 100),
        'daily_vol': 0.004,
        'max_single_position': 0.25,
    },
    'HIGH': {
        'min_score': 60,
        'equity_range': (70, 90),
        'daily_vol': 0.003,
        'max_single_position': 0.15,
    },
    'MODERATE': {
        'min_score': 40,
        'equity_range': (50, 70),
        'daily_vol': 0.0025,
        'max_single_position': 0.10,
    },
    'LOW': {
        'min_score': 20,
        'equity_range': (20, 50),
        'daily_vol': 0.0015,
        'max_single_position': 0.05,
    },
    'PRESERVATION': {
        'min_score': 0,
        'equity_range': (0, 20),
        'daily_vol': 0.001,
        'max_single_position': 0.03,
    },
}
```

#### 3.2.3 4 패턴 분류

```python
# ─── 시장 패턴 분류 ───

MARKET_PATTERNS = {
    'POLICY_PIVOT': {
        'name': '정책 전환 예측',
        'trigger': 'transitional_regime + high_transition_prob',
        'principle': '중앙은행과 유동성에 집중하라',
        'equity_range': (70, 90),
    },
    'UNSUSTAINABLE_DISTORTION': {
        'name': '지속불가 왜곡',
        'trigger': 'top_risk >= 60 + contraction_or_inflationary',
        'principle': '틀렸을 때 얼마나 잃느냐가 가장 중요하다',
        'equity_range': (30, 50),
    },
    'EXTREME_CONTRARIAN': {
        'name': '극단 역발상',
        'trigger': 'ftd_confirmed + high_top_risk + bearish_breadth',
        'principle': '가장 큰 수익은 약세장에서 나온다',
        'equity_range': (25, 40),
    },
    'WAIT_OBSERVE': {
        'name': '관망',
        'trigger': 'low_conviction + mixed_signals',
        'principle': '보이지 않으면 스윙하지 마라',
        'equity_range': (0, 20),
    },
}
```

#### 3.2.4 한국 적응 포인트

```python
# ─── 한국 시장 적응 ───

KR_ADAPTATION = {
    'foreign_flow_weight': 0.15,        # 외국인 수급 가중치 (US에 없음)
    'bok_rate_sensitivity': True,        # BOK 기준금리 반응
    'kospi_kosdaq_dual': True,           # KOSPI/KOSDAQ 이중 추적
    'geopolitical_premium': 0.05,        # 지정학적 리스크 프리미엄
    'report_max_age_hours': 72,          # 리포트 유효 시간
}
```

#### 3.2.5 파일 구조

```
skills/kr-strategy-synthesizer/
├── SKILL.md
├── references/
│   ├── kr_conviction_guide.md
│   └── kr_pattern_matrix.md
├── scripts/
│   ├── report_loader.py            # 업스트림 스킬 JSON 로드
│   ├── conviction_scorer.py        # 7-컴포넌트 확신도 계산
│   ├── pattern_classifier.py       # 4 패턴 분류
│   ├── allocation_engine.py        # 자산 배분 엔진
│   ├── report_generator.py         # 리포트 생성
│   └── tests/
│       └── test_strategy_synthesizer.py
```

#### 3.2.6 함수 시그니처

```python
# report_loader.py
def load_skill_reports(report_dir, max_age_hours=72) -> dict
def validate_report(report, required_fields) -> bool

# conviction_scorer.py
def normalize_signal(raw_value, source_skill) -> float
def calc_component_scores(reports) -> dict
def calc_conviction_score(components) -> dict
    # Returns: {score, zone, components}

# pattern_classifier.py
def classify_pattern(components, reports) -> dict
    # Returns: {pattern, confidence, principle, equity_range}

# allocation_engine.py
def generate_allocation(conviction_score, pattern) -> dict
    # Returns: {equity, bonds, alternatives, cash, max_single}
def apply_kr_adjustment(allocation, kr_signals) -> dict
```

**예상 테스트**: ~50개

---

### 3.3 Skill 38: kr-skill-reviewer (Medium)

**US 원본**: dual-axis-skill-reviewer
**핵심**: Dual-Axis (Auto + LLM) 스킬 품질 리뷰, 메타 스킬

#### 3.3.1 Auto Axis (결정적 체크)

```python
# ─── Auto Axis 가중치 ───

AUTO_AXIS_WEIGHTS = {
    'metadata_use_case': {
        'weight': 0.20,
        'checks': ['skill_md_exists', 'use_case_defined', 'triggers_listed'],
    },
    'workflow_coverage': {
        'weight': 0.25,
        'checks': ['execution_steps', 'input_output_defined', 'error_handling'],
    },
    'execution_safety': {
        'weight': 0.25,
        'checks': ['command_examples', 'path_hygiene', 'reproducibility'],
    },
    'supporting_artifacts': {
        'weight': 0.10,
        'checks': ['scripts_exist', 'references_exist', 'constants_defined'],
    },
    'test_health': {
        'weight': 0.20,
        'checks': ['tests_exist', 'tests_pass', 'coverage_adequate'],
    },
}
# weights sum = 0.20+0.25+0.25+0.10+0.20 = 1.00
```

#### 3.3.2 점수 기준

```python
# ─── 점수 등급 ───

REVIEW_GRADES = {
    'PRODUCTION_READY': 90,    # ≥90: 프로덕션 가능
    'USABLE': 80,              # 80-89: 개선 필요하나 사용 가능
    'NOTABLE_GAPS': 70,        # 70-79: 주목할 갭
    'HIGH_RISK': 0,            # <70: 고위험, 드래프트 취급
}

MERGE_WEIGHTS = {
    'auto': 0.50,
    'llm': 0.50,
}
```

#### 3.3.3 파일 구조

```
skills/kr-skill-reviewer/
├── SKILL.md
├── references/
│   └── kr_review_rubric.md
├── scripts/
│   ├── auto_reviewer.py            # Auto Axis 엔진
│   ├── review_merger.py            # Auto + LLM 합산
│   ├── report_generator.py         # 리뷰 리포트 생성
│   └── tests/
│       └── test_skill_reviewer.py
```

#### 3.3.4 함수 시그니처

```python
# auto_reviewer.py
def check_metadata(skill_path) -> dict
def check_workflow_coverage(skill_path) -> dict
def check_execution_safety(skill_path) -> dict
def check_artifacts(skill_path) -> dict
def check_test_health(skill_path) -> dict
def run_auto_review(skill_path) -> dict
    # Returns: {score, components, findings}

# review_merger.py
def merge_reviews(auto_result, llm_result, weights) -> dict
    # Returns: {final_score, grade, auto_score, llm_score, improvements}

# report_generator.py
def generate_review_report(merged_result) -> str
```

**예상 테스트**: ~35개

---

### 3.4 Skill 39: kr-weekly-strategy (Medium)

**US 원본**: weekly-trade-strategy
**핵심**: 한국 시장 주간 전략 워크플로우 (에이전트 오케스트레이션 → 단순화)

#### 3.4.1 주간 전략 구조

```python
# ─── 주간 전략 섹션 ───

WEEKLY_SECTIONS = [
    'market_summary',        # 시장 환경 요약 (3줄)
    'this_week_action',      # 이번 주 액션 플랜
    'scenario_plans',        # 시나리오별 계획 (Base/Bull/Bear)
    'sector_strategy',       # 섹터 전략
    'risk_management',       # 리스크 관리
    'operation_guide',       # 운용 가이드 (겸업 투자자용)
]
```

#### 3.4.2 시장 환경 분류

```python
# ─── 시장 상태 ───

MARKET_PHASES = {
    'RISK_ON': {
        'description': '위험 선호 (강세장)',
        'equity_target': (80, 100),
        'cash_target': (0, 10),
    },
    'BASE': {
        'description': '보통 (횡보장)',
        'equity_target': (60, 80),
        'cash_target': (10, 20),
    },
    'CAUTION': {
        'description': '주의 (약세 전환 가능)',
        'equity_target': (40, 60),
        'cash_target': (20, 35),
    },
    'STRESS': {
        'description': '스트레스 (약세장)',
        'equity_target': (10, 40),
        'cash_target': (35, 60),
    },
}
```

#### 3.4.3 주간 전략 파라미터

```python
# ─── 전략 제약 ───

WEEKLY_CONSTRAINTS = {
    'max_sector_change_pct': 0.15,     # 섹터 비중 변경 ±15%
    'max_cash_change_pct': 0.15,       # 현금 비중 변경 ±15%
    'blog_length_lines': (150, 250),   # 블로그 길이 150-250줄
    'continuity_required': True,        # 전주 전략 연속성
}

# ─── 한국 시장 주간 체크리스트 ───

KR_WEEKLY_CHECKLIST = [
    'kospi_kosdaq_trend',       # KOSPI/KOSDAQ 주간 추세
    'foreign_net_flow',         # 외국인 순매수/매도
    'institutional_net_flow',   # 기관 순매수/매도
    'bok_rate_decision',        # BOK 금리 결정 (있을 경우)
    'major_earnings',           # 주요 실적 발표
    'dart_disclosures',         # DART 주요 공시
    'geopolitical_events',      # 지정학적 이벤트
    'usd_krw_trend',            # 환율 추세
]

# ─── 한국 14개 섹터 ───

KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학',
    '바이오/제약', '금융/은행', '유통/소비', '건설/부동산',
    'IT/소프트웨어', '통신', '에너지/유틸리티', '엔터테인먼트',
    '방산', '2차전지',
]
```

#### 3.4.4 파일 구조

```
skills/kr-weekly-strategy/
├── SKILL.md
├── references/
│   ├── kr_weekly_workflow_guide.md
│   └── kr_sector_list.md
├── scripts/
│   ├── market_environment.py       # 시장 환경 분석
│   ├── sector_strategy.py          # 섹터 전략 생성
│   ├── weekly_planner.py           # 주간 전략 통합
│   ├── report_generator.py         # 주간 리포트 생성
│   └── tests/
│       └── test_weekly_strategy.py
```

#### 3.4.5 함수 시그니처

```python
# market_environment.py
def classify_market_phase(indicators) -> dict
    # Returns: {phase, description, equity_target, cash_target}
def generate_weekly_checklist(market_data) -> list

# sector_strategy.py
def calc_sector_scores(sector_data) -> dict
def recommend_sector_allocation(scores, prev_allocation) -> dict
    # Returns: {allocations, changes, constrained}
def apply_rotation_constraints(new_alloc, prev_alloc, max_change) -> dict

# weekly_planner.py
def generate_scenarios(market_phase, macro_data) -> dict
    # Returns: {base, bull, bear} with probability and actions
def generate_weekly_plan(environment, sectors, scenarios) -> dict
    # Returns: {summary, action, scenarios, sectors, risks, guide}

# report_generator.py
def generate_weekly_report(plan) -> str
```

**예상 테스트**: ~40개

---

## 4. 상수 총정리

### 4.1 전체 상수 카운트

| 스킬 | 상수 그룹 | 개수 |
|------|-----------|:----:|
| kr-stock-analysis | TYPES(5) + FUND(14) + TECH(8) + SUPPLY(7) + SCORING(4+5) | 43 |
| kr-strategy-synthesizer | COMPONENTS(7) + ZONES(5) + PATTERNS(4) + KR_ADAPT(5) | 21 |
| kr-skill-reviewer | AUTO(5) + GRADES(4) + MERGE(2) | 11 |
| kr-weekly-strategy | SECTIONS(6) + PHASES(4) + CONSTRAINTS(4) + CHECKLIST(8) + SECTORS(14) | 36 |
| **합계** | | **111** |

---

## 5. 파일 인벤토리

### 5.1 전체 파일 목록

| # | 경로 | 유형 |
|:-:|------|:----:|
| 1 | kr-stock-analysis/SKILL.md | doc |
| 2 | kr-stock-analysis/references/kr_stock_analysis_guide.md | ref |
| 3 | kr-stock-analysis/scripts/fundamental_analyzer.py | code |
| 4 | kr-stock-analysis/scripts/technical_analyzer.py | code |
| 5 | kr-stock-analysis/scripts/supply_demand_analyzer.py | code |
| 6 | kr-stock-analysis/scripts/comprehensive_scorer.py | code |
| 7 | kr-stock-analysis/scripts/report_generator.py | code |
| 8 | kr-stock-analysis/scripts/tests/test_stock_analysis.py | test |
| 9 | kr-strategy-synthesizer/SKILL.md | doc |
| 10 | kr-strategy-synthesizer/references/kr_conviction_guide.md | ref |
| 11 | kr-strategy-synthesizer/references/kr_pattern_matrix.md | ref |
| 12 | kr-strategy-synthesizer/scripts/report_loader.py | code |
| 13 | kr-strategy-synthesizer/scripts/conviction_scorer.py | code |
| 14 | kr-strategy-synthesizer/scripts/pattern_classifier.py | code |
| 15 | kr-strategy-synthesizer/scripts/allocation_engine.py | code |
| 16 | kr-strategy-synthesizer/scripts/report_generator.py | code |
| 17 | kr-strategy-synthesizer/scripts/tests/test_strategy_synthesizer.py | test |
| 18 | kr-skill-reviewer/SKILL.md | doc |
| 19 | kr-skill-reviewer/references/kr_review_rubric.md | ref |
| 20 | kr-skill-reviewer/scripts/auto_reviewer.py | code |
| 21 | kr-skill-reviewer/scripts/review_merger.py | code |
| 22 | kr-skill-reviewer/scripts/report_generator.py | code |
| 23 | kr-skill-reviewer/scripts/tests/test_skill_reviewer.py | test |
| 24 | kr-weekly-strategy/SKILL.md | doc |
| 25 | kr-weekly-strategy/references/kr_weekly_workflow_guide.md | ref |
| 26 | kr-weekly-strategy/references/kr_sector_list.md | ref |
| 27 | kr-weekly-strategy/scripts/market_environment.py | code |
| 28 | kr-weekly-strategy/scripts/sector_strategy.py | code |
| 29 | kr-weekly-strategy/scripts/weekly_planner.py | code |
| 30 | kr-weekly-strategy/scripts/report_generator.py | code |
| 31 | kr-weekly-strategy/scripts/tests/test_weekly_strategy.py | test |

**총계**: 4 SKILL.md + 6 references + 17 scripts + 4 test files = **31 파일**

---

## 6. 구현 순서

```
Step 1 (High): kr-stock-analysis
├── fundamental_analyzer.py
├── technical_analyzer.py
├── supply_demand_analyzer.py (KR 고유)
├── comprehensive_scorer.py
├── report_generator.py
└── ~55 tests

Step 2 (High): kr-strategy-synthesizer
├── report_loader.py
├── conviction_scorer.py (7-컴포넌트)
├── pattern_classifier.py (4 패턴)
├── allocation_engine.py
├── report_generator.py
└── ~50 tests

Step 3 (Medium): kr-skill-reviewer
├── auto_reviewer.py (5 체크)
├── review_merger.py (Auto + LLM)
├── report_generator.py
└── ~35 tests

Step 4 (Medium): kr-weekly-strategy
├── market_environment.py
├── sector_strategy.py
├── weekly_planner.py
├── report_generator.py
└── ~40 tests

Step 5: 통합 테스트
└── 전체 스킬 테스트 실행 (Phase 1-8 누적)
```

**예상 테스트 합계**: ~180개

---

## 7. Phase 1-7 연동 포인트

### 7.1 kr-stock-analysis 입력 소스

| 데이터 | 소스 스킬/모듈 | Phase |
|--------|---------------|:-----:|
| OHLCV | _kr-common (KRClient → PyKRX) | 1 |
| 재무제표 | _kr-common (DARTProvider) | 1 |
| PER/PBR | PyKRX | 1 |
| 수급 데이터 | kr-institutional-flow | 5 |

### 7.2 kr-strategy-synthesizer 입력 스킬

| 컴포넌트 | 입력 스킬 | Phase |
|----------|-----------|:-----:|
| market_structure | kr-market-breadth, kr-uptrend-analyzer | 2, 2 |
| distribution_risk | kr-market-top-detector | 3 |
| bottom_confirmation | kr-ftd-detector | 3 |
| macro_alignment | kr-macro-regime | 3 |
| theme_quality | kr-theme-detector | 2 |
| setup_availability | kr-vcp-screener, kr-canslim-screener | 4 |

### 7.3 한국 시장 적응 요약

| US 원본 | KR 핵심 변경 |
|---------|-------------|
| us-stock-analysis | +수급 분석 (외국인/기관/개인), DART 재무제표, PyKRX |
| stanley-druckenmiller | +외국인 수급 가중치, BOK 금리, 지정학 프리미엄 |
| dual-axis-reviewer | 방법론 동일 (KR 스킬 대상) |
| weekly-trade-strategy | 에이전트 → 함수 단순화, 한국 14개 섹터, 8개 체크리스트 |
