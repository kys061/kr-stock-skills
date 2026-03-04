# 한국 주식 스킬 - Phase 4 종목 스크리닝 스킬 상세 설계

> **Feature**: kr-stock-skills (Phase 4)
> **Created**: 2026-03-03
> **Status**: Design Phase
> **Plan Reference**: `docs/01-plan/features/kr-stock-skills.plan.md` (섹션 3.4)
> **Phase 1 Reference**: `docs/02-design/features/kr-stock-skills-phase1.design.md`
> **Phase 2 Reference**: `docs/02-design/features/kr-stock-skills-phase2.design.md`
> **Phase 3 Reference**: `docs/02-design/features/kr-stock-skills-phase3.design.md`

---

## 1. 설계 개요

### 1.1 Phase 4 목표
**7개 종목 스크리닝 스킬**을 한국 시장에 맞게 포팅한다.
US 스킬의 분석 방법론(CANSLIM, VCP, PEAD, 배당 스크리닝, 페어 트레이딩)은 보존하되,
데이터 소스를 Phase 1 `KRClient`로 교체하고 한국 시장 특화 스크리닝 기준을 추가한다.

Phase 4 스킬은 **개별 종목 발굴**에 집중한다:
- 성장주 스크리닝 (CANSLIM): 펀더멘털 + 모멘텀 복합 평가
- 기술적 패턴 (VCP): 변동성 축소 패턴으로 브레이크아웃 대기
- 배당 가치주 (Value-Dividend): 배당 + 밸류에이션 결합
- 배당 성장 풀백 (Dividend-Pullback): 고성장 배당주 + RSI 타이밍
- 실적 드리프트 (PEAD): 실적 발표 후 갭업 연속 패턴
- 페어 트레이딩 (Pair-Trade): 공적분 기반 통계적 차익거래
- 종합 스크리너 (Stock-Screener): 다조건 필터 조합 도구

### 1.2 설계 원칙
- **방법론 보존**: US 스킬의 스코어링 공식/가중치/임계값 프레임워크 유지
- **KRClient 활용**: Phase 1 공통 모듈(48개 메서드)을 데이터 계층으로 일관 사용
- **FMP/FINVIZ → KRClient**: US 스킬이 FMP/FINVIZ API로 수집하던 데이터를 PyKRX/FDR/DART로 대체
- **한국 특화 스크리닝 기준 추가**: 외국인 지분율 변화, 신용비율, 공매도 잔고, 대주주 지분 변동
- **Phase 2/3 크로스레퍼런스**: 시장 건강도(M 컴포넌트), 레짐 분류 결과 활용
- **점진적 구현**: Low → Medium → High 복잡도 순서

### 1.3 Phase 4 스킬 목록

| # | KR 스킬명 | US 원본 | 복잡도 | 스크립트 | 데이터 소스 | 용도 |
|---|-----------|---------|:------:|:--------:|-------------|------|
| 13 | kr-canslim-screener | canslim-screener | **High** | 9개 | KRClient + DART | 성장주 발굴 |
| 14 | kr-vcp-screener | vcp-screener | **High** | 7개 | KRClient (PyKRX) | 패턴 브레이크아웃 |
| 15 | kr-value-dividend | value-dividend-screener | **Medium** | 5개 | KRClient + DART | 배당 가치주 |
| 16 | kr-dividend-pullback | dividend-growth-pullback | **Medium** | 5개 | KRClient + DART | 배당 성장 + 타이밍 |
| 17 | kr-pair-trade | pair-trade-screener | **High** | 6개 | KRClient (PyKRX) | 통계적 차익거래 |
| 18 | kr-pead-screener | pead-screener | **Medium** | 6개 | KRClient + DART | 실적 드리프트 |
| 19 | kr-stock-screener | finviz-screener | **Low** | 0개 | KRClient | 다조건 필터 도구 |

### 1.4 스킬 간 관계

```
┌─────────────────────────────────────────────────────────┐
│                  종목 발굴 파이프라인                      │
│                                                         │
│  Phase 2/3 시그널               Phase 4 스크리닝          │
│  ┌──────────────┐             ┌───────────────┐         │
│  │M 컴포넌트     │──Gate──→   │kr-canslim     │         │
│  │(시장 방향)    │             │kr-vcp         │         │
│  └──────────────┘             │kr-pead        │         │
│                               └───────┬───────┘         │
│  ┌──────────────┐                     │                 │
│  │kr-macro-regime│──Context──→ ┌──────▼───────┐         │
│  │(레짐 분류)    │             │kr-pair-trade  │         │
│  └──────────────┘             └──────────────┘         │
│                                                         │
│  독립 스크리닝 (시장 방향 무관)                            │
│  ┌──────────────────────────────────────────┐           │
│  │kr-value-dividend  kr-dividend-pullback    │           │
│  │kr-stock-screener (다조건 필터)             │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  ※ Phase 8에서 kr-strategy-synthesizer가               │
│    스크리닝 결과를 통합 (드러켄밀러 전략)               │
└─────────────────────────────────────────────────────────┘
```

### 1.5 디렉토리 구조 (전체)

```
~/stock/skills/
├── _kr-common/                        # Phase 1 (구현 완료)
├── kr-market-environment/ ~ kr-theme-detector/  # Phase 2 (구현 완료, 7개)
├── kr-market-top-detector/ ~ kr-breadth-chart/  # Phase 3 (구현 완료, 5개)
│
├── kr-stock-screener/                 # Skill 19 (Low)
│   ├── SKILL.md
│   └── references/
│       └── kr_screening_guide.md          # 한국 스크리닝 기준 가이드
│
├── kr-value-dividend/                 # Skill 15 (Medium)
│   ├── SKILL.md
│   ├── references/
│   │   ├── dividend_methodology_kr.md     # 한국 배당 투자 방법론
│   │   └── kr_dividend_tax.md             # 한국 배당 세제 요약
│   └── scripts/
│       ├── kr_value_dividend_screener.py   # 메인 오케스트레이터
│       ├── fundamental_filter.py          # 3-Phase 펀더멘털 필터
│       ├── scorer.py                      # 4-컴포넌트 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_value_dividend.py
│
├── kr-dividend-pullback/              # Skill 16 (Medium)
│   ├── SKILL.md
│   ├── references/
│   │   └── dividend_growth_kr.md          # 한국 배당 성장주 가이드
│   └── scripts/
│       ├── kr_dividend_pullback_screener.py  # 메인 오케스트레이터
│       ├── growth_filter.py               # 배당 성장 필터
│       ├── scorer.py                      # 4-컴포넌트 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_dividend_pullback.py
│
├── kr-pead-screener/                  # Skill 18 (Medium)
│   ├── SKILL.md
│   ├── references/
│   │   └── pead_methodology_kr.md         # 한국 PEAD 방법론
│   └── scripts/
│       ├── kr_pead_screener.py            # 메인 오케스트레이터
│       ├── weekly_candle_calculator.py    # 주봉 캔들 분석
│       ├── breakout_calculator.py         # 브레이크아웃 판정
│       ├── scorer.py                      # 스테이지 분류 + 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_pead.py
│
├── kr-canslim-screener/               # Skill 13 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── canslim_methodology_kr.md      # 한국 CANSLIM 적용 가이드
│   │   └── kr_growth_stock_guide.md       # 한국 성장주 투자 기준
│   └── scripts/
│       ├── kr_canslim_screener.py         # 메인 오케스트레이터
│       ├── calculators/
│       │   ├── earnings_calculator.py     # C: 분기 실적 성장
│       │   ├── growth_calculator.py       # A: 연간 성장 안정성
│       │   ├── new_highs_calculator.py    # N: 신고가 근접도
│       │   ├── supply_demand_calculator.py # S: 수급
│       │   ├── leadership_calculator.py   # L: 상대강도
│       │   └── market_calculator.py       # M: 시장 방향
│       ├── scorer.py                      # 7-컴포넌트 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_canslim.py
│
├── kr-vcp-screener/                   # Skill 14 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── vcp_methodology_kr.md          # 한국 VCP 패턴 가이드
│   │   └── stage2_template_kr.md          # Stage 2 트렌드 템플릿
│   └── scripts/
│       ├── kr_vcp_screener.py             # 메인 오케스트레이터
│       ├── trend_template_calculator.py   # 7점 Stage 2 필터
│       ├── vcp_pattern_calculator.py      # VCP 패턴 탐지
│       ├── volume_pattern_calculator.py   # 거래량 축소 분석
│       ├── scorer.py                      # 5-컴포넌트 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_vcp.py
│
└── kr-pair-trade/                     # Skill 17 (High)
    ├── SKILL.md
    ├── references/
    │   ├── pair_trade_methodology_kr.md   # 한국 페어 트레이딩 방법론
    │   └── kr_sector_pairs.md             # 한국 섹터별 유력 페어 목록
    └── scripts/
        ├── kr_pair_trade_screener.py      # 메인 오케스트레이터
        ├── correlation_analyzer.py        # 상관/베타 분석
        ├── cointegration_tester.py        # ADF 공적분 테스트
        ├── spread_analyzer.py             # 스프레드 Z-Score 분석
        ├── report_generator.py            # JSON/Markdown 리포트
        └── tests/
            └── test_pair_trade.py
```

---

## 2. 공통 의존성

### 2.1 KRClient 메서드 매핑 (Phase 4 스킬별 사용)

| KRClient 메서드 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 용도 |
|-----------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|------|
| `get_ohlcv()` | ● | ● | ● | ● | ● | ● | ● | 일봉/주봉 OHLCV |
| `get_fundamentals()` | ● | | ● | ● | | | ● | PER/PBR/EPS/DIV |
| `get_financial_statements()` | ● | | ● | ● | | ● | | DART 재무제표 |
| `get_financial_ratios()` | ● | | ● | ● | | | ● | ROE/부채비율 |
| `get_market_cap()` | ● | ● | ● | ● | ● | ● | ● | 시가총액 필터 |
| `get_dividend_info()` | | | ● | ● | | | ● | 배당 정보 |
| `get_investor_trading()` | ● | | | | | | | 수급 (I 컴포넌트) |
| `get_foreign_exhaustion()` | ● | | | | | | | 외국인 지분율 |
| `get_short_selling()` | | | | | | | ● | 공매도 잔고 |
| `get_index()` | ● | ● | | | | | | KOSPI/KOSDAQ 지수 |
| `get_index_constituents()` | ● | ● | | | ● | | | 지수 구성종목 |
| `get_ticker_list()` | ● | ● | ● | ● | | ● | ● | 전종목 목록 |
| `get_sector_performance()` | | | | | ● | | ● | 섹터 수익률 |
| `get_disclosures()` | | | | | | ● | | DART 공시 |

### 2.2 ta_utils 메서드 매핑

| ta_utils 메서드 | 13 | 14 | 15 | 16 | 17 | 18 | 용도 |
|----------------|:--:|:--:|:--:|:--:|:--:|:--:|------|
| `sma()` | ● | ● | | | | | 이동평균 (50/150/200일) |
| `ema()` | ● | ● | | | | | 지수이동평균 |
| `rsi()` | | | | ● | | | RSI 오버솔드 판정 |
| `volume_ratio()` | ● | ● | | | | | 거래량 비율 |
| `rate_of_change()` | ● | ● | | | | | 가격 모멘텀 |
| `atr()` | | ● | | | | | VCP 변동성 측정 |

### 2.3 추가 라이브러리 의존성

```
# Phase 4 추가 (requirements.txt)
scipy>=1.10          # 통계 분석 (ADF 테스트, 상관 분석) — Phase 1에서 이미 설치
statsmodels>=0.14    # 공적분 테스트 (kr-pair-trade) — 신규 설치 필요
```

### 2.4 Phase 2/3 크로스레퍼런스

| Phase 4 스킬 | 참조 Phase 2/3 스킬 | 참조 데이터 | 용도 |
|-------------|-------------------|-----------|------|
| kr-canslim-screener | kr-market-breadth | breadth_score | M 컴포넌트 (시장 건강도) |
| kr-canslim-screener | kr-macro-regime | regime | M 컴포넌트 (레짐 확인) |
| kr-canslim-screener | kr-market-top-detector | risk_zone | M 컴포넌트 (천장 위험) |
| kr-vcp-screener | kr-uptrend-analyzer | uptrend_ratio | Stage 2 사전 필터 |
| kr-pead-screener | kr-market-breadth | breadth_score | 시장 환경 필터 |

크로스레퍼런스는 **선택적**: Phase 2/3 JSON이 없으면 자체 계산 또는 생략.

### 2.5 한국 시장 핵심 차이 (스크리닝 관련)

| 항목 | US | KR 적응 | 영향 스킬 |
|------|-----|---------|----------|
| 재무제표 | SEC/FMP (분기별 신속) | DART (분기보고서 45일 후) | 13, 15, 16, 18 |
| 배당 패턴 | 분기 배당 일반 | **연 1회 12월 집중** | 15, 16 |
| 배당세 | 적격 0-20% | **15.4%** 균일 | 15, 16 |
| 가격제한폭 | 없음 | **±30%** | 14 (VCP 깊이) |
| 수급 데이터 | 13F 분기 지연 | **일별 12분류 실시간** | 13 (I 컴포넌트) |
| 공매도 | 자유 | 개인 제한적 | 17 (페어 트레이딩) |
| 실적 발표 | 각사 자율 | DART 공시 (정기보고서) | 18 (PEAD) |
| RS 벤치마크 | S&P 500 | KOSPI | 13, 14 |
| 스크리닝 도구 | FinViz | 없음 (자체 구축) | 19 |

---

## 3. Skill 13: kr-canslim-screener (CANSLIM 성장주 스크리닝)

### 3.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | canslim-screener |
| 복잡도 | **High** |
| 방법론 | William O'Neil CANSLIM (7 컴포넌트) |
| 스크리닝 대상 | KOSPI 200 + KOSDAQ 150 (350종목) |
| 주요 변경 | FMP → KRClient/DART, S&P500 → KOSPI, 외국인 수급 강화 |
| 데이터 소스 | KRClient (PyKRX + DART) |

### 3.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| FMP income-statement | **DART `get_financial_statements()`** | IFRS 재무제표 |
| FMP quote | **PyKRX `get_ohlcv()`** | 일봉 OHLCV |
| FMP institutional-holder | **PyKRX `get_investor_trading(detail=True)`** | 12분류 일별 수급 |
| FINVIZ institutional % | **PyKRX `get_foreign_exhaustion()`** | 외국인 지분율 |
| S&P 500 RS benchmark | **KOSPI (0001)** RS benchmark | get_index() |
| S&P 500 + 50 EMA (M) | **KOSPI + 50 EMA + Phase 3 시그널** | 크로스레퍼런스 |
| VIX (M) | **VKOSPI (0060)** | PyKRX get_index() |
| 40 stocks (FMP budget) | **350 stocks** (KOSPI200 + KOSDAQ150) | API 제한 없음 |

### 3.3 7-컴포넌트 스코어링 시스템

US 원본의 가중치와 임계값을 보존하되, 한국 데이터 소스로 교체.

| # | 컴포넌트 | 약자 | 가중치 | 데이터 소스 |
|---|---------|------|:------:|-----------|
| 1 | Current Earnings (분기 실적) | C | 15% | DART 분기보고서 |
| 2 | Annual Growth (연간 성장) | A | 20% | DART 사업보고서 |
| 3 | New (신고가 근접) | N | 15% | PyKRX OHLCV |
| 4 | Supply/Demand (수급) | S | 15% | PyKRX OHLCV (거래량) |
| 5 | Leadership (상대강도) | L | 20% | PyKRX OHLCV + 지수 |
| 6 | Institutional (기관/외국인) | I | 10% | PyKRX 투자자별 매매동향 |
| 7 | Market Direction (시장 방향) | M | 5% | Phase 3 크로스레퍼런스 |
| | **합계** | | **100%** | |

#### C (Current Earnings) — 15%

분기 EPS 성장률 (전년 동기 대비 YoY):

| 조건 | 점수 |
|------|:----:|
| EPS 성장률 ≥ 50% + 매출 성장률 ≥ 25% | 100 |
| EPS 성장률 30-49% | 80 |
| EPS 성장률 18-29% | 60 |
| EPS 성장률 10-17% | 40 |
| EPS 성장률 < 10% | 20 |

**한국 적응**: DART `get_financial_statements(ticker, year, 'q1'|'q3')` → 분기 영업이익/순이익 추출.
한국은 반기(q2)/사업보고서(annual) 기준이므로, 분기별 데이터는 `report_type` 매핑 필요:
- Q1: '11013' (1분기), Q2: '11012' (반기), Q3: '11014' (3분기), Q4: '11011' (사업보고서)

#### A (Annual Growth) — 20%

3년 연간 EPS CAGR + 안정성:

| 조건 | 점수 |
|------|:----:|
| CAGR ≥ 40% | 90 |
| CAGR 30-39% | 70 |
| CAGR 25-29% | 50 |
| CAGR 15-24% | 35 |
| CAGR < 15% | 20 |

- **안정성 보너스**: 3년 모두 EPS 증가 → +10
- **하락 페널티**: 1년이라도 EPS 감소 → -10

**한국 적응**: DART 사업보고서 3개년 → EPS 추출 → CAGR 계산.

#### N (New Highs) — 15%

52주 신고가 근접도 + 브레이크아웃:

| 조건 | 점수 |
|------|:----:|
| 52주 고가 5% 이내 + 거래량 브레이크아웃 | 100 |
| 52주 고가 10% 이내 + 브레이크아웃 | 80 |
| 52주 고가 15% 이내 | 60 |
| 52주 고가 25% 이내 | 40 |
| 52주 고가 25% 이상 하락 | 20 |

- **브레이크아웃 조건**: 당일 거래량 > 50일 평균 × 1.5
- **한국 적응**: PyKRX `get_ohlcv(ticker, 260일)` → 52주 고가 계산

#### S (Supply/Demand) — 15%

상승일 거래량 / 하락일 거래량 비율 (60일 윈도우):

| 조건 | 점수 |
|------|:----:|
| Up/Down Volume ≥ 2.0 | 100 |
| Up/Down Volume 1.5-2.0 | 80 |
| Up/Down Volume 1.0-1.5 | 60 |
| Up/Down Volume 0.7-1.0 | 40 |
| Up/Down Volume < 0.7 | 20 |

- **상승일**: Close > Close[-1]
- **하락일**: Close < Close[-1]
- **한국 적응**: PyKRX `get_ohlcv(ticker, 60일)` → 상승/하락일 분류

#### L (Leadership / RS Rank) — 20%

52주 상대강도 (vs KOSPI):

| 조건 | 점수 |
|------|:----:|
| RS Rank ≥ 90 | 100 |
| RS Rank 80-89 | 80 |
| RS Rank 70-79 | 60 |
| RS Rank 50-69 | 40 |
| RS Rank < 50 | 20 |

**RS Rank 계산**:
1. 종목 52주 수익률 계산
2. KOSPI(또는 KOSDAQ) 52주 수익률 계산
3. 상대 수익률 = 종목 수익률 - 지수 수익률
4. 전체 종목 중 백분위 순위 (0-100)

**Minervini 가중치 적용**:
- RS = 40% × (최근 3개월) + 20% × (6개월) + 20% × (9개월) + 20% × (12개월)

#### I (Institutional / 기관·외국인) — 10%

**US 원본**: 기관 보유 비율 + 홀더 수
**한국 적응**: 외국인 지분율 + 최근 20일 기관/외국인 순매수

| 조건 | 점수 |
|------|:----:|
| 외국인 지분율 20-50% + 최근 순매수 | 100 |
| 외국인 지분율 10-20% + 최근 순매수 | 80 |
| 외국인 지분율 5-10% | 60 |
| 외국인 지분율 < 5% | 40 |
| 외국인 순매도 10일+ | 20 |

- **순매수 보너스**: 최근 20일 기관+외국인 순매수 → +10
- **연기금 보너스**: 연기금 순매수 → +5 (한국 특화)

**데이터**: `get_foreign_exhaustion()` + `get_investor_trading(detail=True)`

#### M (Market Direction) — 5%

**Phase 3 크로스레퍼런스 우선 사용**:

| 조건 | 점수 | 의미 |
|------|:----:|------|
| KOSPI > 50 EMA + breadth ≥ 60 + regime != Contraction | 100 | 강한 상승장 |
| KOSPI > 50 EMA + risk_zone ≤ Yellow | 80 | 상승장 |
| KOSPI < 50 EMA but breadth ≥ 40 | 40 | 약세 |
| KOSPI < 50 EMA + VKOSPI > 25 | 0 | 약세장 (매수 금지) |

- **M = 0 (CRITICAL GATE)**: M 점수가 0이면 다른 컴포넌트 점수와 무관하게 매수하지 않음
- **크로스레퍼런스 미존재 시**: KOSPI 50 EMA + VKOSPI로 자체 계산

### 3.4 종합 평가 등급

| 등급 | 점수 범위 | 권고 |
|------|:--------:|------|
| Exceptional+ | 90-100 | 즉시 매수 (15-20% 포지션) |
| Exceptional | 80-89 | 강한 매수 (10-15%) |
| Strong | 70-79 | 매수 (8-12%) |
| Above Average | 60-69 | 관찰 리스트 |
| Below Average | < 60 | 패스 |

**최소 기준선**: C≥60, A≥50, N≥40, S≥40, L≥70, I≥40, M≥40
→ 어느 하나라도 미달이면 등급 하락

### 3.5 파일 구조

```
kr-canslim-screener/
├── SKILL.md
├── references/
│   ├── canslim_methodology_kr.md
│   └── kr_growth_stock_guide.md
└── scripts/
    ├── kr_canslim_screener.py          # 메인 오케스트레이터
    ├── calculators/
    │   ├── earnings_calculator.py      # C: calc_quarterly_growth()
    │   ├── growth_calculator.py        # A: calc_annual_cagr()
    │   ├── new_highs_calculator.py     # N: calc_52w_proximity()
    │   ├── supply_demand_calculator.py # S: calc_volume_ratio()
    │   ├── leadership_calculator.py    # L: calc_rs_rank()
    │   └── market_calculator.py        # M: calc_market_direction()
    ├── scorer.py                       # 7-컴포넌트 가중합
    ├── report_generator.py             # JSON/Markdown 리포트
    └── tests/
        └── test_canslim.py
```

### 3.6 테스트 추정

| 테스트 클래스 | 추정 수 | 범위 |
|-------------|:------:|------|
| TestEarningsCalculator | 5 | C 컴포넌트 경계값 |
| TestGrowthCalculator | 5 | A 컴포넌트 + 안정성 보너스 |
| TestNewHighsCalculator | 4 | N 근접도 + 브레이크아웃 |
| TestSupplyDemandCalculator | 4 | S 거래량 비율 |
| TestLeadershipCalculator | 5 | L RS Rank + Minervini 가중치 |
| TestMarketCalculator | 4 | M 시장 방향 + 크로스레퍼런스 |
| TestCANSLIMScorer | 6 | 종합 스코어 + 최소 기준선 + M=0 게이트 |
| TestReportGenerator | 2 | JSON/Markdown 출력 |
| TestConstants | 3 | 가중치 합 검증 |
| **합계** | **~38** | |

---

## 4. Skill 14: kr-vcp-screener (VCP 패턴 스크리닝)

### 4.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | vcp-screener |
| 복잡도 | **High** |
| 방법론 | Mark Minervini Stage 2 + Volatility Contraction Pattern |
| 스크리닝 대상 | KOSPI 200 + KOSDAQ 150 (350종목) |
| 주요 변경 | 가격제한폭 ±30% 반영 VCP 깊이 조정, KOSPI RS 벤치마크 |
| 데이터 소스 | KRClient (PyKRX) |

### 4.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| S&P 500 RS benchmark | **KOSPI** RS benchmark | |
| T1 depth 8-35% (large), ~50% (small) | **T1 depth 10-30%** (가격제한폭 반영) | ±30% 제한 |
| FMP 260일 히스토리 | **PyKRX `get_ohlcv()`** 260일 | |
| 3-Phase pipeline | **동일** 3-Phase 파이프라인 | |

### 4.3 Stage 2 트렌드 템플릿 (7점)

Minervini Stage 2 필터 (동일 로직):

| # | 조건 | 검증 방법 |
|---|------|----------|
| 1 | 현재가 > 150일 SMA AND 현재가 > 200일 SMA | `close > sma(150) and close > sma(200)` |
| 2 | 150일 SMA > 200일 SMA | `sma(150) > sma(200)` |
| 3 | 200일 SMA가 22거래일 이상 상승 추세 | `sma(200)[-1] > sma(200)[-23]` |
| 4 | 현재가 > 50일 SMA | `close > sma(50)` |
| 5 | 현재가 ≥ 52주 저가 대비 +25% | `close >= low_52w * 1.25` |
| 6 | 현재가 ≤ 52주 고가 대비 -25% (25% 이내) | `close >= high_52w * 0.75` |
| 7 | RS Rank > 70 (KOSPI 대비) | `rs_rank > 70` |

- **통과 기준**: 7점 중 6점 이상 (score ≥ 85)
- **한국 적응**: RS Rank는 KOSPI 대비 계산 (Skill 13 L 컴포넌트와 공유 가능)

### 4.4 VCP 패턴 파라미터

**수축 (Contraction) 규칙**:

| 파라미터 | US 값 | KR 값 | 조정 이유 |
|---------|:-----:|:-----:|---------|
| T1 최소 깊이 | 8% | **10%** | 한국 ±30% 가격제한폭으로 변동성 높음 |
| T1 최대 깊이 (대형주) | 35% | **30%** | ±30% 제한 반영 |
| T1 최대 깊이 (소형주) | 50% | **40%** | |
| 수축 비율 (T2/T1) | ≤ 0.75 | **≤ 0.75** | 동일 |
| 최소 수축 횟수 | 2 | **2** | 동일 |
| 이상적 수축 횟수 | 3-4 | **3-4** | 동일 |
| 패턴 기간 | 15-325 거래일 | **15-325** | 동일 |
| 피봇 포인트 | 마지막 수축 고가 | **동일** | |
| 스탑로스 | 마지막 수축 저가 -1~2% | **동일** | |

### 4.5 5-컴포넌트 스코어링

| # | 컴포넌트 | 가중치 | 설명 |
|---|---------|:------:|------|
| 1 | Trend Template (Stage 2) | 25% | 7점 중 통과 점수 |
| 2 | Contraction Quality | 25% | 수축 횟수 + 깊이 진행 |
| 3 | Volume Pattern | 20% | 거래량 축소 비율 (dry-up) |
| 4 | Pivot Proximity | 15% | 피봇 포인트 근접도 |
| 5 | Relative Strength | 15% | KOSPI 대비 RS |

#### Contraction Quality 세부 스코어

| 조건 | 점수 |
|------|:----:|
| 수축 4회 + 각 ≥25% 축소 | 90 |
| 수축 3회 + 각 ≥25% 축소 | 80 |
| 수축 2회 + 각 ≥25% 축소 | 60 |
| 수축 2회 + 축소 불충분 | 40 |
| 수축 1회 또는 미검출 | 20 |

- **타이트 패턴 보너스**: 마지막 수축 깊이 < 10% → +10
- **딥 패턴 페널티**: 마지막 수축 깊이 > 20% → -10

#### Volume Pattern (Dry-Up Ratio)

Dry-Up Ratio = 수축 기간 평균 거래량 / 이전 상승 기간 평균 거래량

| 조건 | 점수 |
|------|:----:|
| Dry-Up < 0.30 | 90 |
| Dry-Up 0.30-0.50 | 75 |
| Dry-Up 0.50-0.70 | 60 |
| Dry-Up 0.70-1.00 | 40 |
| Dry-Up > 1.00 | 20 |

#### Pivot Proximity

| 조건 | 점수 | 의미 |
|------|:----:|------|
| 피봇 0-3% 위 | 100 | 브레이크아웃 확인 |
| 피봇 0-3% 아래 | 85 | 피봇 근접 대기 |
| 피봇 3-5% 아래 | 75 | 관찰 |
| 피봇 5-10% 아래 | 50 | 패턴 형성 중 |
| 피봇 10-20% 아래 | 30 | 초기 단계 |
| 피봇 20%+ 아래 | 20 | 추격 금지 |

### 4.6 등급 및 액션

| 등급 | 점수 | 액션 |
|------|:----:|------|
| Textbook VCP | 90-100 | 피봇에서 매수 (1.5-2x 사이징) |
| Strong VCP | 80-89 | 피봇에서 매수 (표준 사이징) |
| Good VCP | 70-79 | 거래량 확인 후 매수 |
| Developing | 60-69 | 관찰 리스트 |
| No VCP | < 60 | 패스 |

### 4.7 테스트 추정

| 테스트 클래스 | 추정 수 | 범위 |
|-------------|:------:|------|
| TestTrendTemplate | 6 | 7점 템플릿 + 경계값 |
| TestVCPPattern | 6 | 수축 탐지 + 깊이 진행 |
| TestVolumePattern | 4 | Dry-Up Ratio 구간 |
| TestPivotProximity | 5 | 근접도 + 브레이크아웃 |
| TestRelativeStrength | 3 | RS Rank 계산 |
| TestVCPScorer | 5 | 종합 스코어 + 등급 |
| TestReportGenerator | 2 | JSON/Markdown 출력 |
| TestConstants | 3 | 가중치/파라미터 검증 |
| **합계** | **~34** | |

---

## 5. Skill 15: kr-value-dividend (배당 가치주 스크리닝)

### 5.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | value-dividend-screener |
| 복잡도 | **Medium** |
| 방법론 | 3-Phase 펀더멘털 필터 + 4-컴포넌트 스코어링 |
| 스크리닝 대상 | KOSPI 전종목 + KOSDAQ 150 |
| 주요 변경 | FINVIZ 제거, 한국 배당 패턴(연 1회) 반영, 배당세 15.4% |
| 데이터 소스 | KRClient (PyKRX + DART) |

### 5.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| FINVIZ + FMP 2-Stage | **KRClient only** (API 제한 없음) | FINVIZ 한국 미지원 |
| Dividend Yield ≥ 3.5% | **Dividend Yield ≥ 2.5%** | 한국 배당수익률 평균 낮음 |
| P/E ≤ 20 | **PER ≤ 15** | 한국 시장 PER 평균 낮음 |
| P/B ≤ 2.0 | **PBR ≤ 1.5** | 한국 시장 PBR 할인 |
| Market Cap ≥ $2B | **시가총액 ≥ 5,000억원** | |
| 분기 배당 | **연 1회 배당** (12월 집중) | 한국 배당 패턴 |
| 배당세 적격/비적격 | **15.4% 균일** (금융소득종합과세 2천만원) | |
| 3-year CAGR | **3-year 연속 배당 유지** | 한국 배당 안정성 기준 |

### 5.3 3-Phase 스크리닝 필터

**Phase 1: 정량 필터**

| 기준 | 임계값 | 비고 |
|------|:------:|------|
| 배당수익률 | ≥ 2.5% | 한국 평균 ~1.8% 대비 상회 |
| PER | ≤ 15 | 한국 KOSPI 평균 ~12 |
| PBR | ≤ 1.5 | 한국 할인 반영 |
| 시가총액 | ≥ 5,000억원 | 유동성 확보 |

**Phase 2: 성장 품질 필터**

| 기준 | 임계값 | 비고 |
|------|:------:|------|
| 3년 배당 연속 유지 | 무삭감 | 1년이라도 삭감 시 제외 |
| 매출 성장 | 3년 양의 추세 | DART 사업보고서 |
| EPS 성장 | 3년 양의 추세 | DART 사업보고서 |

**Phase 3: 지속가능성 필터**

| 기준 | 임계값 | 비고 |
|------|:------:|------|
| 배당성향 (Payout Ratio) | < 80% | 한국 기준 (US 100%보다 엄격) |
| 부채비율 (D/E) | < 150% | 한국 기업 부채 특성 반영 |
| 유동비율 | > 1.0 | |

### 5.4 4-컴포넌트 스코어링 (0-100)

| # | 컴포넌트 | 가중치 | 설명 |
|---|---------|:------:|------|
| 1 | Value Score | 40% | PER + PBR 복합 |
| 2 | Growth Score | 35% | 3년 배당/매출/EPS 성장률 |
| 3 | Sustainability Score | 20% | 배당성향 + 부채비율 |
| 4 | Quality Score | 5% | ROE + 영업이익률 |

#### Value Score (40%)

| PER | 점수 | PBR | 점수 |
|-----|:----:|-----|:----:|
| ≤ 8 | 100 | ≤ 0.5 | 100 |
| 8-10 | 80 | 0.5-0.8 | 80 |
| 10-12 | 60 | 0.8-1.0 | 60 |
| 12-15 | 40 | 1.0-1.5 | 40 |

Value Score = PER점수 × 0.6 + PBR점수 × 0.4

#### Growth Score (35%)

| 배당 성장률 (3Y CAGR) | 점수 |
|----------------------|:----:|
| ≥ 15% | 100 |
| 10-14% | 80 |
| 5-9% | 60 |
| 1-4% | 40 |
| 0% (유지) | 20 |

- **매출 성장 보너스**: 3년 양의 추세 → +10
- **EPS 성장 보너스**: 3년 양의 추세 → +10
- **최대 100 캡**

#### Sustainability Score (20%)

| 배당성향 | 점수 | 부채비율 | 점수 |
|---------|:----:|---------|:----:|
| < 30% | 100 | < 50% | 100 |
| 30-50% | 80 | 50-100% | 80 |
| 50-70% | 60 | 100-150% | 60 |
| 70-80% | 40 | > 150% | 20 |

Sustainability Score = 배당성향점수 × 0.6 + 부채비율점수 × 0.4

### 5.5 테스트 추정

| 테스트 클래스 | 추정 수 |
|-------------|:------:|
| TestPhase1Filter | 5 |
| TestPhase2Filter | 4 |
| TestPhase3Filter | 4 |
| TestValueScore | 4 |
| TestGrowthScore | 4 |
| TestSustainabilityScore | 4 |
| TestDividendScorer | 5 |
| TestReportGenerator | 2 |
| TestConstants | 3 |
| **합계** | **~35** |

---

## 6. Skill 16: kr-dividend-pullback (배당 성장 풀백 스크리닝)

### 6.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | dividend-growth-pullback-screener |
| 복잡도 | **Medium** |
| 방법론 | 고성장 배당주 (12%+ CAGR) + RSI ≤ 40 타이밍 |
| 스크리닝 대상 | KOSPI 전종목 + KOSDAQ 150 |
| 주요 변경 | RSI 임계값 조정, 한국 배당 성장률 기준 조정 |
| 데이터 소스 | KRClient (PyKRX + DART) |

### 6.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| 3Y Dividend CAGR ≥ 12% | **3Y 배당 CAGR ≥ 8%** | 한국 배당 성장률 낮음 |
| Dividend Yield ≥ 1.5% | **배당수익률 ≥ 2.0%** | |
| RSI ≤ 40 (14-period) | **RSI ≤ 40** (동일) | |
| Market Cap ≥ $2B | **시가총액 ≥ 3,000억원** | |

### 6.3 2-Phase 스크리닝

**Phase 1: 배당 성장 필터**

| 기준 | 임계값 |
|------|:------:|
| 배당수익률 | ≥ 2.0% |
| 3년 배당 CAGR | ≥ 8% |
| 4년 연속 무삭감 | 필수 |
| 시가총액 | ≥ 3,000억원 |
| 매출 성장 (3Y) | 양의 추세 |
| EPS 성장 (3Y) | 양의 추세 |
| 부채비율 | < 150% |
| 유동비율 | > 1.0 |
| 배당성향 | < 80% |

**Phase 2: RSI 타이밍 필터**

| RSI 구간 | 의미 | 점수 |
|---------|------|:----:|
| < 30 | 극단적 과매도 | 90 |
| 30-35 | 강한 과매도 | 80 |
| 35-40 | 초기 풀백 | 70 |
| > 40 | 제외 | 0 |

### 6.4 4-컴포넌트 스코어링 (0-100)

| # | 컴포넌트 | 가중치 | 설명 |
|---|---------|:------:|------|
| 1 | Dividend Growth | 40% | 3Y CAGR + 연속성 |
| 2 | Financial Quality | 30% | ROE + 영업이익률 + 부채비율 |
| 3 | Technical Setup | 20% | RSI 수준 (낮을수록 높은 점수) |
| 4 | Valuation | 10% | PER + PBR 맥락 |

### 6.5 테스트 추정

| 테스트 클래스 | 추정 수 |
|-------------|:------:|
| TestGrowthFilter | 5 |
| TestRSIFilter | 4 |
| TestDividendGrowthScore | 4 |
| TestFinancialQualityScore | 4 |
| TestTechnicalSetupScore | 3 |
| TestPullbackScorer | 4 |
| TestReportGenerator | 2 |
| TestConstants | 3 |
| **합계** | **~29** |

---

## 7. Skill 17: kr-pair-trade (페어 트레이딩 스크리닝)

### 7.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | pair-trade-screener |
| 복잡도 | **High** |
| 방법론 | 상관분석 + ADF 공적분 테스트 + Z-Score 스프레드 |
| 스크리닝 대상 | KOSPI 200 (동일 업종 내 페어) |
| 주요 변경 | KRX 업종 분류 기반, 한국 거래비용 반영 |
| 데이터 소스 | KRClient (PyKRX) |
| 추가 라이브러리 | `statsmodels` (ADF 테스트) |

### 7.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| GICS 섹터 기반 | **KRX 업종 분류** 기반 | |
| Market Cap ≥ $2B | **시가총액 ≥ 5,000억원** | |
| 거래비용 0.1% round-trip/leg | **0.25% round-trip** (수수료+세금) | 한국 거래세 포함 |
| 공매도 자유 | **공매도 제한** (기관/외국인만) | Pair Short leg 대안 필요 |

### 7.3 분석 워크플로우 (8-Step)

**Step 1: 페어 유니버스 정의**
- KRX 업종 내 동일 업종 종목 조합
- 시가총액 ≥ 5,000억원 필터
- 일 거래량 ≥ 10억원 필터

**Step 2: 히스토리컬 데이터**
- 2년(500거래일) 일봉 종가
- `get_ohlcv(ticker, start, end)` 사용

**Step 3: 상관 분석**

| 상관계수(ρ) | 등급 | 액션 |
|:----------:|------|------|
| ≥ 0.90 | 매우 강함 | 최우선 후보 |
| 0.70-0.90 | 강함 | 후보 |
| 0.50-0.70 | 보통 | 관찰 |
| < 0.50 | 약함 | 제외 |

- **롤링 상관**: 90일 윈도우로 안정성 확인
- **안정성 경고**: 최근 상관 < 과거 - 0.15 → 플래그

**Step 4: 공적분 테스트 (ADF)**

Spread = Price_A - (Beta × Price_B)

| p-value | 등급 | 공적분 |
|:-------:|------|:------:|
| < 0.01 | ★★★ 매우 강함 | 확인 |
| 0.01-0.05 | ★★ 보통 | 확인 |
| > 0.05 | 없음 | **제외** |

**Step 5: Z-Score 분석**

Z-Score = (현재_Spread - 평균_Spread) / 표준편차_Spread

| Z-Score | 의미 | 액션 |
|:-------:|------|------|
| |Z| > 3.0 | 극단 | 스탑로스/퇴출 |
| |Z| > 2.0 | 진입 시그널 | 포지션 구축 |
| |Z| 1.5-2.0 | 관찰 | 대기 |
| |Z| < 1.5 | 정상 범위 | 보유/관망 |
| Z = 0 | 평균 회귀 | 청산 (이익 실현) |

**Step 6: 진입/청산 규칙**

- **LONG**: Z < -2.0 → A 매수, B 매도 (헤지비율 = β)
- **SHORT**: Z > +2.0 → A 매도, B 매수
- **청산**: Z = 0 (평균 회귀)
- **부분 청산**: |Z| = 1.0에서 50% 청산
- **스탑**: |Z| > 3.0
- **시간 기반**: 90일 미회귀 시 청산

**Step 7: 포지션 사이징**
- 균등 금액 노출: Long A = Short B × β
- 페어당 포트폴리오 10-20%
- 최대 동시 페어: 5-8개

**Step 8: Half-Life 계산**
- < 30일: 빠른 회귀 (최적)
- 30-60일: 보통
- > 60일: 느림 (장기 보유)

### 7.4 한국 시장 특화 고려사항

**공매도 제한 대안**:
- 한국에서 개인 공매도 제한 → Short leg 대안:
  1. 인버스 ETF 활용 (KODEX 인버스)
  2. 롱 Only 페어: 강한 종목 롱, 약한 종목 미보유
  3. 기관/외국인 계좌에서만 진정한 페어 트레이딩 가능
- **설계 대응**: `short_method` 파라미터 (direct/inverse_etf/long_only)

**한국 유력 페어 업종**:
- 반도체: 삼성전자 vs SK하이닉스
- 자동차: 현대차 vs 기아
- 금융: KB금융 vs 신한금융
- 통신: SK텔레콤 vs KT
- 철강: POSCO홀딩스 vs 현대제철
- 화학: LG화학 vs 롯데케미칼

### 7.5 테스트 추정

| 테스트 클래스 | 추정 수 |
|-------------|:------:|
| TestCorrelationAnalyzer | 5 |
| TestCointegrationTester | 5 |
| TestSpreadAnalyzer | 6 |
| TestZScore | 4 |
| TestHalfLife | 3 |
| TestPairTradeScorer | 4 |
| TestReportGenerator | 2 |
| TestConstants | 3 |
| **합계** | **~32** |

---

## 8. Skill 18: kr-pead-screener (실적 드리프트 스크리닝)

### 8.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | pead-screener |
| 복잡도 | **Medium** |
| 방법론 | Post-Earnings Announcement Drift (주봉 캔들 패턴) |
| 스크리닝 대상 | DART 정기보고서 공시 종목 |
| 주요 변경 | FMP 실적캘린더 → DART 공시, 한국 실적 시즌 반영 |
| 데이터 소스 | KRClient (DART + PyKRX) |

### 8.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| FMP earnings calendar | **DART `get_disclosures(kind='A')`** | 정기보고서 공시 |
| Gap ≥ 3% | **Gap ≥ 3%** (동일) | |
| Weekly candle analysis | **주봉 분석** (동일) | PyKRX `get_ohlcv(freq='w')` |
| 5주 모니터링 | **5주** (동일) | |
| S&P 500 stocks | **KOSPI + KOSDAQ** | DART 공시 기반 |

### 8.3 한국 실적 시즌

| 시기 | 보고서 | DART 공시 |
|------|--------|----------|
| 1월 말~2월 | 4Q 잠정실적 | 주요사항보고서 |
| 3월 | 4Q 확정실적 | 사업보고서 |
| 5월 | 1Q | 분기보고서 |
| 8월 | 2Q | 반기보고서 |
| 11월 | 3Q | 분기보고서 |

- **한국 특성**: 잠정실적(속보) → 확정실적(공식) 2단계
- **갭 발생 시점**: 잠정실적 공시일이 주요 갭 발생 (실적 서프라이즈)

### 8.4 스테이지 기반 분류 (4단계)

| Stage | 정의 | 액션 |
|-------|------|------|
| MONITORING | 실적 갭업, 아직 적색 캔들 없음 | 관찰, 주간 체크 |
| SIGNAL_READY | 적색 주봉 캔들 형성 | 적색 캔들 고가에 알림 설정 |
| BREAKOUT | 녹색 캔들 + 적색 캔들 고가 돌파 | 진입 (스탑: 적색 캔들 저가) |
| EXPIRED | 실적 발표 후 5주 초과 | 리스트에서 제거 |

### 8.5 스코어링 (0-100)

| # | 컴포넌트 | 가중치 | 설명 |
|---|---------|:------:|------|
| 1 | Gap Size | 30% | 갭 크기 (클수록 높은 점수) |
| 2 | Pattern Quality | 25% | 적색 캔들 형성 + 거래량 감소 |
| 3 | Earnings Surprise | 25% | 실적 서프라이즈 크기 |
| 4 | Risk/Reward | 20% | 진입가 vs 스탑 vs 목표가 비율 |

#### Gap Size Score

| 갭 크기 | 점수 |
|---------|:----:|
| ≥ 15% | 100 |
| 10-14% | 85 |
| 7-9% | 70 |
| 5-6% | 55 |
| 3-4% | 40 |

#### Pattern Quality Score

| 조건 | 점수 |
|------|:----:|
| 적색 캔들 + 거래량 감소 + 갭 유지 | 100 |
| 적색 캔들 + 거래량 감소 | 80 |
| 적색 캔들만 | 60 |
| 아직 적색 캔들 없음 (MONITORING) | 40 |

### 8.6 테스트 추정

| 테스트 클래스 | 추정 수 |
|-------------|:------:|
| TestWeeklyCandleCalculator | 5 |
| TestBreakoutCalculator | 4 |
| TestGapSizeScore | 4 |
| TestPatternQualityScore | 4 |
| TestStageClassification | 5 |
| TestPEADScorer | 4 |
| TestReportGenerator | 2 |
| TestConstants | 3 |
| **합계** | **~31** |

---

## 9. Skill 19: kr-stock-screener (종합 스크리닝 도구)

### 9.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | finviz-screener |
| 복잡도 | **Low** |
| 방법론 | 다조건 필터 조합 (자연어 → 스크리닝 조건) |
| 스크리닝 대상 | KOSPI + KOSDAQ 전종목 |
| 주요 변경 | FinViz URL 빌더 → KRClient 기반 프로그래매틱 스크리너 |
| 데이터 소스 | KRClient |
| 스크립트 | **0개** (SKILL.md 중심, AI 실행) |

### 9.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| FinViz 142개 필터코드 | **KRClient 기반 조건 조합** | FinViz 한국 미지원 |
| URL 빌더 + 브라우저 열기 | **Python 코드 생성 + 결과 반환** | |
| NLP → 필터코드 매핑 | **NLP → KRClient 메서드 조합** | AI가 코드 생성 |

### 9.3 지원 스크리닝 조건

| 카테고리 | 조건 예시 | KRClient 메서드 |
|---------|----------|----------------|
| 밸류에이션 | PER < 10, PBR < 1.0 | `get_fundamentals()` |
| 배당 | 배당수익률 > 3% | `get_dividend_info()` |
| 시가총액 | 시총 > 1조원 | `get_market_cap()` |
| 수급 | 외국인 순매수 5일+ | `get_investor_trading()` |
| 공매도 | 공매도 비율 < 5% | `get_short_selling()` |
| 기술적 | RSI < 30, 현재가 > 200SMA | `get_ohlcv()` + `ta_utils` |
| 섹터 | 반도체 업종 | `get_ticker_list()` 섹터 필터 |
| 재무 | ROE > 15%, 부채비율 < 100% | `get_financial_ratios()` |

### 9.4 SKILL.md 구현 방식

AI가 자연어 요청을 받아 KRClient 메서드 조합 코드를 생성하고 실행.
별도 스크립트 파일 불필요 — SKILL.md에 스크리닝 패턴과 예시 코드 포함.

### 9.5 Reference 문서

`kr_screening_guide.md`:
- KRClient 스크리닝 메서드 요약
- 자주 사용하는 스크리닝 조합 15개
- 한국 시장 스크리닝 팁 (외국인 지분율, 신용비율 등)

---

## 10. 구현 순서 (5-Step)

| Step | 스킬 | 복잡도 | 의존성 | 예상 테스트 |
|:----:|------|:------:|--------|:----------:|
| 1 | kr-stock-screener | Low | 없음 | 0 |
| 2 | kr-value-dividend | Medium | DART | ~35 |
| 3 | kr-dividend-pullback | Medium | DART + ta_utils | ~29 |
| 4 | kr-pead-screener | Medium | DART | ~31 |
| 5 | kr-canslim-screener | High | DART + Phase 3 | ~38 |
| 6 | kr-vcp-screener | High | ta_utils | ~34 |
| 7 | kr-pair-trade | High | statsmodels | ~32 |
| | **합계** | | | **~199** |

### 10.1 구현 순서 근거

1. **kr-stock-screener** (Low): SKILL.md만 작성, 코드 없음 → 빠른 완료
2. **배당 스크리너 2개** (Medium): DART 재무제표 패턴 학습 → 이후 CANSLIM에 활용
3. **kr-pead-screener** (Medium): DART 공시 패턴 학습 → 독립적
4. **kr-canslim-screener** (High): DART + Phase 3 크로스레퍼런스 → 가장 복잡
5. **kr-vcp-screener** (High): 순수 기술적 분석 → DART 불필요
6. **kr-pair-trade** (High): statsmodels 추가 필요 → 마지막

---

## 11. 전체 파일 목록

### 11.1 요약

| 항목 | 개수 |
|------|:----:|
| SKILL.md | 7개 |
| References | 10개 |
| Scripts (Python) | 38개 |
| Test files | 6개 |
| **Total** | **61개 파일** |

### 11.2 스킬별 파일 수

| 스킬 | SKILL.md | References | Scripts | Tests | Total |
|------|:--------:|:----------:|:-------:|:-----:|:-----:|
| kr-stock-screener | 1 | 1 | 0 | 0 | 2 |
| kr-value-dividend | 1 | 2 | 4 | 1 | 8 |
| kr-dividend-pullback | 1 | 1 | 4 | 1 | 7 |
| kr-pead-screener | 1 | 1 | 5 | 1 | 8 |
| kr-canslim-screener | 1 | 2 | 8 | 1 | 12 |
| kr-vcp-screener | 1 | 2 | 6 | 1 | 10 |
| kr-pair-trade | 1 | 2 | 5 | 1 | 9 |
| **합계** | **7** | **11** | **32** | **6** | **56** |

---

## 12. 테스트 전략

### 12.1 테스트 목표

| 항목 | 목표 |
|------|------|
| 설계 추정 테스트 수 | ~199개 |
| Phase 3 기준 초과율 | 최소 150% 목표 |
| 스코어링 로직 검증 | 모든 가중치/임계값 경계값 테스트 |
| 설계값 자동 검증 | TestConstants 클래스 (Phase 3 베스트 프랙티스) |

### 12.2 Phase 4 고유 테스트 패턴

1. **DART 데이터 모킹**: 재무제표 응답을 모킹하여 테스트
2. **기간 조건 검증**: 3년 연속 성장/무삭감 등 시계열 조건
3. **통계 라이브러리 검증**: ADF 테스트, 상관계수 계산 정확성 (kr-pair-trade)
4. **크로스레퍼런스 Fallback**: Phase 3 JSON 미존재 시 자체 계산 경로

---

## 변경 이력

| 날짜 | 버전 | 작업 내용 | 관련 섹션 |
|------|------|----------|----------|
| 2026-03-03 | 1.0 | Phase 4 종목 스크리닝 스킬 설계 초안 작성 | 전체 |
