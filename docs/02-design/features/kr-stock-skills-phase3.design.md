# 한국 주식 스킬 - Phase 3 마켓 타이밍 스킬 상세 설계

> **Feature**: kr-stock-skills (Phase 3)
> **Created**: 2026-02-28
> **Status**: Design Phase
> **Plan Reference**: `docs/01-plan/features/kr-stock-skills.plan.md` (섹션 3.3)
> **Phase 1 Reference**: `docs/02-design/features/kr-stock-skills-phase1.design.md`
> **Phase 2 Reference**: `docs/02-design/features/kr-stock-skills-phase2.design.md`

---

## 1. 설계 개요

### 1.1 Phase 3 목표
**5개 마켓 타이밍 스킬**을 한국 시장에 맞게 포팅한다.
US 스킬의 분석 방법론(스코어링, 상태 머신, 레짐 분류)은 보존하되,
데이터 소스를 Phase 1 `KRClient`로 교체하고 한국 시장 특화 지표를 추가한다.

Phase 3 스킬은 **시장 방향성 판단**에 집중한다:
- 천장 감지 (방어적): 하락 시작 전에 위험 인식
- 바닥 확인 (공격적): 상승 전환 시그널 포착
- 버블 평가 (구조적): 장기 과열 여부 판단
- 레짐 전환 (전략적): 1-2년 거시 환경 변화 감지
- 시장폭 차트 (시각적): 브레드스 데이터 차트 해석

### 1.2 설계 원칙
- **방법론 보존**: US 스킬의 스코어링 공식/상태 머신/레짐 분류 프레임워크 유지
- **KRClient 활용**: Phase 1 공통 모듈을 데이터 계층으로 일관 사용
- **FMP → KRClient**: US 스킬이 FMP API로 수집하던 데이터를 PyKRX/FDR로 대체
- **한국 특화 지표 추가**: 외국인 수급, 신용잔고, VKOSPI, PER 밴드 등
- **Phase 2 크로스레퍼런스**: kr-market-breadth, kr-uptrend-analyzer 결과 활용
- **점진적 구현**: Low → Medium → High 복잡도 순서

### 1.3 Phase 3 스킬 목록

| # | KR 스킬명 | US 원본 | 복잡도 | 스크립트 | 데이터 소스 | 시간 지평 |
|---|-----------|---------|:------:|:--------:|-------------|-----------|
| 8 | kr-market-top-detector | market-top-detector | **High** | 7개 | KRClient (PyKRX) | 2-8주 (전술) |
| 9 | kr-ftd-detector | ftd-detector | **High** | 5개 | KRClient (PyKRX) | 수일~수주 (이벤트) |
| 10 | kr-bubble-detector | us-market-bubble-detector | **Medium** | 3개 | KRClient + WebSearch | 수개월~수년 (구조) |
| 11 | kr-macro-regime | macro-regime-detector | **High** | 9개 | KRClient (PyKRX+FDR) | 1-2년 (전략) |
| 12 | kr-breadth-chart | breadth-chart-analyst | Low | 0 | 차트 이미지 | - |

### 1.4 스킬 간 관계

```
┌─────────────────────────────────────────────────────────┐
│                  시간 지평별 배치                          │
│                                                         │
│  단기 (일~주)        중기 (주~월)         장기 (월~년)     │
│  ┌──────────┐      ┌──────────────┐    ┌─────────────┐  │
│  │kr-ftd    │      │kr-market-top │    │kr-bubble    │  │
│  │(바닥 확인)│      │(천장 감지)     │    │(버블 평가)   │  │
│  └─────┬────┘      └──────┬───────┘    └──────┬──────┘  │
│        │                  │                    │         │
│        └──────────┬───────┘                    │         │
│                   │                            │         │
│              ┌────▼─────┐              ┌───────▼──────┐  │
│              │Phase 2   │              │kr-macro-regime│  │
│              │breadth/  │              │(레짐 전환)    │  │
│              │uptrend   │              └──────────────┘  │
│              └──────────┘                               │
│                                                         │
│  ※ Phase 8에서 kr-strategy-synthesizer가               │
│    모든 스킬 결과를 통합 (드러켄밀러 전략)               │
└─────────────────────────────────────────────────────────┘
```

### 1.5 디렉토리 구조 (전체)

```
~/stock/skills/
├── _kr-common/                        # Phase 1 (구현 완료)
├── kr-market-environment/             # Phase 2 (구현 완료)
├── kr-market-news-analyst/            # Phase 2 (구현 완료)
├── kr-sector-analyst/                 # Phase 2 (구현 완료)
├── kr-technical-analyst/              # Phase 2 (구현 완료)
├── kr-market-breadth/                 # Phase 2 (구현 완료)
├── kr-uptrend-analyzer/               # Phase 2 (구현 완료)
├── kr-theme-detector/                 # Phase 2 (구현 완료)
│
├── kr-market-top-detector/            # Skill 8 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── distribution_day_kr.md         # 한국 분배일 가이드
│   │   └── historical_kr_tops.md          # 한국 시장 역사적 천장 사례
│   └── scripts/
│       ├── kr_market_top_detector.py      # 메인 오케스트레이터
│       ├── distribution_calculator.py     # 분배일 카운터
│       ├── leading_stock_calculator.py    # 선도주 건전성 계산
│       ├── defensive_rotation_calculator.py # 방어 섹터 로테이션
│       ├── foreign_flow_calculator.py     # 외국인 이탈 계산 (한국 특화)
│       ├── scorer.py                      # 7-컴포넌트 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_market_top.py
│
├── kr-ftd-detector/                   # Skill 9 (High)
│   ├── SKILL.md
│   ├── references/
│   │   └── ftd_methodology_kr.md          # FTD 방법론 한국 적용
│   └── scripts/
│       ├── kr_ftd_detector.py             # 메인 오케스트레이터
│       ├── rally_tracker.py               # 랠리 시도 추적 + 상태 머신
│       ├── ftd_qualifier.py               # FTD 자격 판정 + 품질 점수
│       ├── post_ftd_monitor.py            # FTD 이후 건전성 모니터링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_ftd.py
│
├── kr-bubble-detector/                # Skill 10 (Medium)
│   ├── SKILL.md
│   ├── references/
│   │   ├── bubble_framework_kr.md         # 한국 버블 프레임워크
│   │   └── historical_kr_bubbles.md       # 한국 역사적 버블 사례
│   └── scripts/
│       ├── kr_bubble_detector.py          # 메인 오케스트레이터
│       ├── bubble_scorer.py               # 6 정량 + 3 정성 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_bubble.py
│
├── kr-macro-regime/                   # Skill 11 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── regime_methodology_kr.md       # 한국 레짐 탐지 방법론
│   │   └── historical_kr_regimes.md       # 한국 역사적 레짐 전환 사례
│   └── scripts/
│       ├── kr_macro_regime_detector.py    # 메인 오케스트레이터
│       ├── calculators/
│       │   ├── concentration_calculator.py    # 시장 집중도
│       │   ├── yield_curve_calculator.py      # 금리 곡선
│       │   ├── credit_calculator.py           # 신용 환경
│       │   ├── size_factor_calculator.py      # 사이즈 팩터
│       │   ├── equity_bond_calculator.py      # 주식-채권 관계
│       │   └── sector_rotation_calculator.py  # 섹터 로테이션
│       ├── scorer.py                      # 레짐 분류 스코어러
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_macro_regime.py
│
└── kr-breadth-chart/                  # Skill 12 (Low)
    ├── SKILL.md
    └── references/
        └── kr_breadth_chart_guide.md      # 한국 시장폭 차트 해석 가이드
```

---

## 2. 공통 의존성

### 2.1 KRClient 메서드 매핑 (Phase 3 스킬별 사용)

| KRClient 메서드 | Skill 8 | 9 | 10 | 11 | 12 | 용도 |
|-----------------|:-------:|:-:|:--:|:--:|:--:|------|
| `get_index()` | ● | ● | ● | ● | | KOSPI/KOSDAQ 지수 OHLCV |
| `get_ohlcv()` | ● | | | | | 개별 종목 OHLCV (선도주) |
| `get_ohlcv_multi()` | ● | | | | | 복수 종목 일괄 조회 |
| `get_index_fundamentals()` | | | ● | | | KOSPI PER 밴드 |
| `get_sector_performance()` | ● | | | ● | | 업종별 수익률 |
| `get_investor_trading_market()` | ● | ● | | | | 기관/외국인 매매동향 |
| `get_bond_yields()` | | | | ● | | 국고채 수익률 |
| `get_global_index()` | | | | ● | | USD/KRW, 글로벌 지수 |
| `get_fred()` | | | | ● | | FRED 경제지표 |
| `get_ticker_list()` | ● | | ● | | | 전종목 목록 (시장폭) |
| `get_market_cap()` | ● | | | ● | | 시가총액 (집중도) |

### 2.2 ta_utils 메서드 매핑

| ta_utils 메서드 | Skill 8 | 9 | 10 | 11 | 용도 |
|----------------|:-------:|:-:|:--:|:--:|------|
| `sma()` | ● | ● | ● | ● | 이동평균 (50/200일) |
| `ema()` | ● | | | | 지수이동평균 |
| `rate_of_change()` | | | ● | ● | 가격 변화율 |
| `volume_ratio()` | ● | ● | | | 거래량 비율 |

### 2.3 Phase 2 스킬 크로스레퍼런스

Phase 3 스킬은 Phase 2 결과를 참조하여 정확도를 높인다:

| Phase 3 스킬 | 참조 Phase 2 스킬 | 참조 데이터 |
|-------------|-----------------|-----------|
| kr-market-top-detector | kr-market-breadth | breadth_ratio (200MA 위 종목 비율) |
| kr-market-top-detector | kr-uptrend-analyzer | uptrend_ratio (업트렌드 비율) |
| kr-ftd-detector | kr-market-breadth | breadth 개선 여부 |
| kr-bubble-detector | kr-market-breadth | breadth_ratio (시장폭 이상) |
| kr-breadth-chart | kr-market-breadth | 전체 JSON 출력 |

크로스레퍼런스는 **선택적**: 해당 Phase 2 JSON이 없으면 자체 계산으로 대체.

### 2.4 한국 시장 핵심 지표 매핑 (US → KR)

#### 2.4.1 지수 매핑

| US 지수/ETF | Korean 대체 | 코드 | 데이터 소스 |
|------------|-----------|------|-----------|
| S&P 500 | KOSPI | 0001 (KRX) / KS11 (FDR) | PyKRX / FDR |
| NASDAQ | KOSDAQ | 1001 (KRX) / KQ11 (FDR) | PyKRX / FDR |
| VIX | VKOSPI | 0060 (KRX) | PyKRX |
| Russell 2000 (IWM) | KOSDAQ / KOSPI 중소형주 | 1001 / 업종지수 | PyKRX |

#### 2.4.2 선도주/성장 ETF 매핑

| US ETF | 역할 | Korean 대체 (종목/ETF) | Ticker |
|--------|------|----------------------|--------|
| SOXX/SMH | 반도체 | 삼성전자 / SK하이닉스 | 005930 / 000660 |
| XBI | 바이오 | 삼성바이오 / 셀트리온 | 207940 / 068270 |
| TAN | 신재생 | LG에너지솔루션 / 삼성SDI | 373220 / 006400 |
| ARKK | 혁신성장 | NAVER / 카카오 | 035420 / 035720 |
| WCLD | 클라우드/IT | NAVER / 카카오 | 035420 / 035720 |
| IGV | 소프트웨어 | (NAVER에 포함) | - |
| KWEB | 중국테크 | (제외 - 한국 무관) | - |

**한국 선도주 바스켓 (8종목)**:

| 종목 | Ticker | 테마 | 시총 순위 |
|------|--------|------|:---------:|
| 삼성전자 | 005930 | AI/반도체 | 1 |
| SK하이닉스 | 000660 | 반도체 | 2 |
| LG에너지솔루션 | 373220 | 2차전지 | 3 |
| 삼성바이오로직스 | 207940 | 바이오 | 4 |
| 현대차 | 005380 | 자동차 | 5 |
| 셀트리온 | 068270 | 바이오시밀러 | ~7 |
| NAVER | 035420 | 플랫폼 | ~8 |
| 한화에어로스페이스 | 012450 | 방산 | ~10 |

#### 2.4.3 방어 vs 성장 섹터 매핑

| 분류 | US ETF | Korean KRX 업종 | 업종코드 |
|------|--------|----------------|---------|
| 방어 | XLU (유틸리티) | 전기가스업 | 1013 |
| 방어 | XLP (필수소비) | 음식료 | 1001 |
| 방어 | XLV (헬스케어) | 의약품 | 1005 |
| 성장 | XLK (기술) | 전기전자 | 1009 |
| 성장 | XLC (통신서비스) | 서비스업 | 1021 |
| 성장 | XLY (임의소비) | 유통업 | 1012 |

#### 2.4.4 채권/크레딧 매핑

| US 지표 | Korean 대체 | 데이터 소스 |
|---------|-----------|-----------|
| US 10Y Treasury | 국고채 10년 | PyKRX `bond.get_otc_treasury_yields()` |
| US 2Y Treasury | 국고채 3년 | PyKRX |
| HYG (High Yield) | 회사채 BBB- 수익률 | PyKRX |
| LQD (Inv. Grade) | 회사채 AA- 수익률 | PyKRX |
| TLT (Long Bond) | 국고채 10년 가격 | FDR (역산) |

#### 2.4.5 한국 전용 지표 (US에 없음)

| 지표 | 설명 | 활용 스킬 | 데이터 소스 |
|------|------|----------|-----------|
| 외국인 순매수 연속일수 | 외국인 매매 추세 | Skill 8, 9 | PyKRX |
| 신용잔고 비율 | 레버리지 과열 | Skill 10 | WebSearch / Tier 2 |
| 투자자 예탁금 | 대기 자금 규모 | Skill 10 | WebSearch |
| KOSPI PER 밴드 | 역사적 밸류에이션 위치 | Skill 10 | PyKRX |
| 프로그램 순매수 | 차익/비차익 프로그램 | Skill 8 | WebSearch / Tier 2 |
| VKOSPI | 한국판 VIX | Skill 8, 10 | PyKRX |

### 2.5 추가 의존성

```
# Phase 3 추가 (requirements.txt)
# Phase 1/2와 동일 — 추가 라이브러리 없음
# scipy, numpy, pandas, pyyaml 은 Phase 2에서 이미 설치
```

---

## 3. Skill 8: kr-market-top-detector (시장 천장 탐지기)

### 3.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | market-top-detector |
| 복잡도 | **High** |
| 시간 지평 | 2-8주 (전술적 타이밍) |
| 탐지 대상 | 10-20% 조정 직전의 천장 형성 |
| 방법론 | O'Neil 분배일 + Minervini 선도주 악화 + 방어 섹터 로테이션 |
| 주요 변경 | KOSPI 기반 + 외국인 이탈 지표 추가 (7번째 컴포넌트) |
| 데이터 소스 | KRClient (PyKRX) |

### 3.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| S&P 500 + QQQ 분배일 | **KOSPI + KOSDAQ** 분배일 | KRClient `get_index()` |
| 8개 성장 ETF 바스켓 | **한국 선도주 8종목** 바스켓 | 2.4.2절 참조 |
| XLU/XLP/XLV vs XLK/XLC/XLY | **KRX 업종지수** 방어 vs 성장 | 2.4.3절 참조 |
| 200DMA breadth (CSV/WebSearch) | **kr-market-breadth JSON** 또는 자체 계산 | Phase 2 크로스레퍼런스 |
| S&P 500 MA structure | **KOSPI MA structure** | 동일 로직 |
| VIX + Put/Call | **VKOSPI** + 신용잔고 변화 | PyKRX `get_index('0060')` |
| - (없음) | **외국인 순매수 이탈 지표** (신규) | PyKRX 투자자별 매매동향 |
| FMP API | **KRClient** | 전체 교체 |

### 3.3 7-컴포넌트 스코어링 시스템

US 원본은 6-컴포넌트이나, 한국 시장에서 외국인 수급의 중요성을 반영하여 7번째 컴포넌트를 추가.

| # | 컴포넌트 | 가중치 | US 가중치 | 데이터 소스 | 핵심 시그널 |
|---|---------|:------:|:---------:|-------------|-----------|
| 1 | Distribution Day Count | **20%** | 25% | KRClient `get_index()` | 25 거래일 내 기관 매도 분배일 누적 |
| 2 | Leading Stock Health | **15%** | 20% | KRClient `get_ohlcv_multi()` | 선도주 8종목 건전성 악화 |
| 3 | Defensive Sector Rotation | **12%** | 15% | KRClient `get_sector_performance()` | 방어→성장 상대 성과 역전 |
| 4 | Market Breadth Divergence | **13%** | 15% | kr-market-breadth JSON / 자체 | 지수 고점 vs 시장폭 하락 다이버전스 |
| 5 | Index Technical Condition | **13%** | 15% | KRClient `get_index()` | MA 구조 악화, 실패 랠리, 저점 하향 |
| 6 | Sentiment & Speculation | **12%** | 10% | KRClient `get_index('0060')` + WebSearch | VKOSPI 수준, 신용잔고 변화 |
| 7 | **Foreign Investor Flow** | **15%** | - (신규) | KRClient `get_investor_trading_market()` | 외국인 연속 순매도, 이탈 강도 |

**가중치 조정 근거**:
- 외국인이 KOSPI 시가총액의 ~30%를 보유, 수급 영향력이 매우 큼
- US 원본에서는 기관 매도를 분배일로만 간접 측정하지만, 한국은 일별 외국인 데이터 직접 활용 가능
- 센티먼트에 VKOSPI(한국 VIX) + 신용잔고를 반영하여 12%로 소폭 상향

#### 3.3.1 Component 1: Distribution Day Count (20%)

**정의**: 25 거래일 윈도우 내 분배일(Distribution Day) 누적 횟수.

**분배일 조건** (O'Neil 방법론):
- 지수 종가가 전일 대비 **-0.2% 이상** 하락
- 거래량이 **전일 거래량 이상**
- 25 거래일 이내 발생

**스코어링**:

| 분배일 수 | 점수 (0-100) | 해석 |
|:---------:|:----------:|------|
| 0-2 | 0-20 | 정상 — 기관 매도 압력 없음 |
| 3 | 30 | 초기 경고 |
| 4 | 50 | 주의 구간 |
| 5 | 70 | 위험 상승 |
| 6+ | 80-100 | 높은 천장 확률 |

**KOSPI + KOSDAQ 이중 추적**:
- 두 지수의 분배일을 독립 계산
- 최종 점수 = max(KOSPI 점수, KOSDAQ 점수) × 0.7 + min(KOSPI 점수, KOSDAQ 점수) × 0.3
- 두 지수 동시 분배일 누적 → 신호 강화

```python
def count_distribution_days(index_data: pd.DataFrame, window: int = 25) -> int:
    """
    Args:
        index_data: columns=['close', 'volume'], 최근 window+5 거래일
    Returns:
        분배일 횟수
    """
```

#### 3.3.2 Component 2: Leading Stock Health (15%)

**정의**: 한국 선도주 8종목의 건전성을 측정.

**선도주 바스켓** (2.4.2절 참조):
삼성전자, SK하이닉스, LG에솔, 삼성바이오, 현대차, 셀트리온, NAVER, 한화에어로

**건전성 지표**:

| 지표 | 설명 | 점수 기여 |
|------|------|----------|
| `pct_below_50ma` | 50MA 아래 종목 비율 | 높을수록 위험 |
| `avg_drawdown` | 52주 고점 대비 평균 하락률 | 깊을수록 위험 |
| `declining_count` | 주간 수익률 음수 종목 수 | 많을수록 위험 |

**스코어링**:

| 조건 | 점수 (0-100) |
|------|:----------:|
| 50MA 아래 0-12% + 평균 하락 < 5% | 0-20 |
| 50MA 아래 13-37% + 평균 하락 5-10% | 21-40 |
| 50MA 아래 38-62% + 평균 하락 10-15% | 41-60 |
| 50MA 아래 63-87% + 평균 하락 15-25% | 61-80 |
| 50MA 아래 88%+ + 평균 하락 > 25% | 81-100 |

```python
KR_LEADING_STOCKS = [
    {'ticker': '005930', 'name': '삼성전자', 'theme': 'AI/반도체'},
    {'ticker': '000660', 'name': 'SK하이닉스', 'theme': '반도체'},
    {'ticker': '373220', 'name': 'LG에너지솔루션', 'theme': '2차전지'},
    {'ticker': '207940', 'name': '삼성바이오로직스', 'theme': '바이오'},
    {'ticker': '005380', 'name': '현대차', 'theme': '자동차'},
    {'ticker': '068270', 'name': '셀트리온', 'theme': '바이오시밀러'},
    {'ticker': '035420', 'name': 'NAVER', 'theme': '플랫폼'},
    {'ticker': '012450', 'name': '한화에어로스페이스', 'theme': '방산'},
]
```

#### 3.3.3 Component 3: Defensive Sector Rotation (12%)

**정의**: 방어 섹터가 성장 섹터를 outperform하는 정도 측정.

**KRX 업종 그룹**:

| 그룹 | 업종 (KRX 코드) |
|------|----------------|
| 방어 | 전기가스업(1013), 음식료(1001), 의약품(1005) |
| 성장 | 전기전자(1009), 서비스업(1021), 유통업(1012) |

**스코어링**:
- 1주/1개월 상대 성과 비율 계산: 방어 섹터 수익률 - 성장 섹터 수익률
- 양(+) = 방어 outperform → 위험 시그널

| 상대 성과 (방어 - 성장) | 점수 |
|:---------------------:|:----:|
| < -3% | 0-10 | 성장 강세, 정상 |
| -3% ~ 0% | 10-30 |
| 0% ~ +2% | 30-50 | 전환 시작 |
| +2% ~ +5% | 50-75 | 방어 선호 뚜렷 |
| > +5% | 75-100 | 강한 위험 회피 |

#### 3.3.4 Component 4: Market Breadth Divergence (13%)

**정의**: 지수가 고점을 만들지만 시장폭이 축소되는 다이버전스.

**데이터 소스**:
1. (우선) Phase 2 kr-market-breadth JSON 출력의 `breadth_ratio`
2. (대체) KRClient로 KOSPI 전종목 200MA 돌파 비율 자체 계산

**스코어링**:

| KOSPI 위치 | 200MA 위 종목 비율 | 점수 |
|-----------|:-----------------:|:----:|
| 신고가 | > 60% | 0-15 | 건전한 참여 |
| 신고가 | 45-60% | 30-50 | 경미한 다이버전스 |
| 신고가 | < 45% | 60-85 | 심각한 다이버전스 |
| 고점 근접 (5% 이내) | < 40% | 70-100 | 극단적 다이버전스 |
| 고점 대비 5%+ 하락 | - | N/A | 이미 조정 중 |

#### 3.3.5 Component 5: Index Technical Condition (13%)

**정의**: KOSPI 지수의 이동평균 구조와 가격 패턴 분석.

**기술적 신호**:

| 신호 | 점수 기여 | 설명 |
|------|:--------:|------|
| 10MA < 21MA | +15 | 단기 약세 전환 |
| 21MA < 50MA | +15 | 중기 약세 전환 |
| 50MA < 200MA (데드크로스) | +25 | 장기 약세 |
| 실패 랠리 (저항선 돌파 실패 후 하락) | +20 | 매수세 소진 |
| 저점 하향 (Lower Low) | +15 | 하락 추세 확인 |
| 거래량 감소 속 상승 | +10 | 매수 동력 약화 |

최종 점수 = min(합계, 100)

#### 3.3.6 Component 6: Sentiment & Speculation (12%)

**정의**: VKOSPI(한국 VIX) + 신용잔고 변화로 시장 심리 측정.

**VKOSPI 스코어링**:

| VKOSPI 수준 | 점수 기여 | 해석 |
|:-----------:|:--------:|------|
| < 13 | +40 | 극단적 안일 (complacency) → 위험 |
| 13-18 | +20 | 정상적 낙관 |
| 18-25 | 0 | 건전한 경계 |
| > 25 | -10 | 공포 → 천장보다 바닥 근접 |

**신용잔고 스코어링** (WebSearch로 데이터 수집):

| 신용잔고 변화 | 점수 기여 | 해석 |
|:----------:|:--------:|------|
| YoY +15% 이상 | +30 | 레버리지 과열 |
| YoY +5~15% | +15 | 보통 |
| YoY -5~+5% | 0 | 정상 |
| YoY -5% 이하 | -10 | 디레버리징 (바닥 근접) |

최종 점수 = max(0, min(VKOSPI 점수 + 신용잔고 점수, 100))

#### 3.3.7 Component 7: Foreign Investor Flow (15%) — 한국 특화

**정의**: 외국인 투자자의 순매수/순매도 패턴으로 이탈 강도 측정.

**지표**:

| 지표 | 설명 | 데이터 |
|------|------|--------|
| `consecutive_sell_days` | 외국인 연속 순매도 일수 | PyKRX 투자자별 매매동향 |
| `sell_intensity` | 최근 5일 순매도 금액 / 20일 평균 | PyKRX |
| `foreign_ratio_change` | 외국인 보유비율 20일 변화 | PyKRX |

**스코어링**:

| 조건 | 점수 (0-100) |
|------|:----------:|
| 연속 순매수 5일+ | 0-10 |
| 중립 (순매수/순매도 혼재) | 10-30 |
| 연속 순매도 3-5일 | 30-50 |
| 연속 순매도 5-10일 + 강도 1.5x+ | 50-75 |
| 연속 순매도 10일+ + 강도 2x+ | 75-100 |

```python
class ForeignFlowCalculator:
    """외국인 이탈 강도 계산기 (한국 시장 특화)."""

    def calculate(self, investor_data: pd.DataFrame) -> dict:
        """
        Args:
            investor_data: 최근 30 거래일 투자자별 매매동향
                columns: ['date', 'foreign_net', 'institution_net', 'retail_net']
        Returns:
            {
                'score': float (0-100),
                'consecutive_sell_days': int,
                'sell_intensity': float,
                'foreign_ratio_change': float,
                'signal': str  # 'strong_outflow' | 'moderate_outflow' | 'neutral' | 'inflow'
            }
        """
```

### 3.4 리스크 존 매핑

US 원본과 동일한 5-존 체계:

| 점수 | 존 | 리스크 예산 | 행동 지침 |
|:----:|-----|:---------:|----------|
| 0-20 | Green (정상) | 100% | 정상 운영, 신규 진입 가능 |
| 21-40 | Yellow (초기 경고) | 80-90% | 손절 강화, 신규 진입 축소 |
| 41-60 | Orange (위험 상승) | 60-75% | 약한 포지션 이익실현 |
| 61-80 | Red (고확률 천장) | 40-55% | 적극적 이익실현 |
| 81-100 | Critical (천장 형성) | 20-35% | 최대 방어, 헤지 |

### 3.5 스크립트 상세

#### 3.5.1 distribution_calculator.py

```python
class DistributionDayCalculator:
    """KOSPI/KOSDAQ 분배일 계산기."""

    DISTRIBUTION_THRESHOLD = -0.002  # -0.2%
    WINDOW = 25  # 25 거래일

    def count(self, index_data: pd.DataFrame) -> dict:
        """분배일 카운팅."""

    def score(self, kospi_count: int, kosdaq_count: int) -> float:
        """이중 지수 분배일 → 점수(0-100)."""

    @staticmethod
    def is_distribution_day(close: float, prev_close: float,
                           volume: int, prev_volume: int) -> bool:
        """개별 일자가 분배일인지 판정."""
```

#### 3.5.2 leading_stock_calculator.py

```python
KR_LEADING_STOCKS = [...]  # 8종목 정의 (3.3.2절)

class LeadingStockCalculator:
    """한국 선도주 건전성 계산기."""

    def calculate(self, ohlcv_dict: dict[str, pd.DataFrame]) -> dict:
        """8종목 OHLCV → 건전성 지표."""

    def score(self, health: dict) -> float:
        """건전성 지표 → 점수(0-100)."""
```

#### 3.5.3 defensive_rotation_calculator.py

```python
KR_DEFENSIVE_SECTORS = ['1013', '1001', '1005']  # 전기가스, 음식료, 의약
KR_GROWTH_SECTORS = ['1009', '1021', '1012']      # 전기전자, 서비스, 유통

class DefensiveRotationCalculator:
    """방어 vs 성장 섹터 로테이션 계산기."""

    def calculate(self, sector_data: dict) -> dict:
        """업종별 수익률 → 상대 성과."""

    def score(self, rotation: dict) -> float:
        """상대 성과 → 점수(0-100)."""
```

#### 3.5.4 foreign_flow_calculator.py (한국 특화)

```python
class ForeignFlowCalculator:
    """외국인 이탈 강도 계산기."""

    def calculate(self, investor_data: pd.DataFrame) -> dict:
        """투자자별 매매동향 → 이탈 지표."""

    def score(self, flow: dict) -> float:
        """이탈 지표 → 점수(0-100)."""
```

#### 3.5.5 scorer.py

```python
COMPONENT_WEIGHTS = {
    'distribution': 0.20,
    'leading_stock': 0.15,
    'defensive_rotation': 0.12,
    'breadth_divergence': 0.13,
    'index_technical': 0.13,
    'sentiment': 0.12,
    'foreign_flow': 0.15,
}

RISK_ZONES = {
    'Green':    (0, 20, '정상'),
    'Yellow':   (21, 40, '초기 경고'),
    'Orange':   (41, 60, '위험 상승'),
    'Red':      (61, 80, '고확률 천장'),
    'Critical': (81, 100, '천장 형성'),
}

class MarketTopScorer:
    """7-컴포넌트 천장 리스크 스코어러."""

    def score(self, components: dict) -> dict:
        """
        Returns:
            {
                'composite_score': float (0-100),
                'risk_zone': str,
                'risk_budget': str,
                'components': dict,
                'action': str,
            }
        """
```

#### 3.5.6 report_generator.py

```python
class ReportGenerator:
    """JSON + Markdown 천장 탐지 리포트."""

    def __init__(self, output_dir: str):
        ...

    def generate(self, scored: dict, components: dict) -> dict:
        """리포트 생성. Returns {'json_path': ..., 'md_path': ...}"""
```

#### 3.5.7 kr_market_top_detector.py (메인 오케스트레이터)

```python
def analyze(output_dir: str, breadth_json: str = None) -> dict:
    """
    1. KRClient로 데이터 수집 (KOSPI/KOSDAQ, 선도주, 업종, 투자자)
    2. 7개 컴포넌트 계산
    3. 스코어링
    4. 리포트 생성
    """
```

### 3.6 테스트 계획

**test_market_top.py** (예상 25-30 테스트):

| 테스트 클래스 | 테스트 수 | 범위 |
|-------------|:--------:|------|
| TestDistributionCalculator | 5 | 분배일 카운팅, 이중 지수 점수 |
| TestLeadingStockCalculator | 4 | 선도주 건전성 지표, 점수 |
| TestDefensiveRotation | 3 | 방어 vs 성장 상대 성과 |
| TestForeignFlowCalculator | 5 | 연속 순매도, 이탈 강도 |
| TestSentimentScorer | 3 | VKOSPI + 신용잔고 |
| TestMarketTopScorer | 5 | 가중치 합계, 존 매핑, 통합 스코어 |
| TestReportGenerator | 2 | JSON/MD 파일 생성 |

### 3.7 참조 문서 목록

| 파일 | 내용 |
|------|------|
| `references/distribution_day_kr.md` | 분배일 방법론 한국 적용, KOSPI/KOSDAQ 이중 추적 |
| `references/historical_kr_tops.md` | 한국 역사적 천장 사례: 2007 (6,124pt), 2011 (2,228pt), 2018 (2,607pt), 2021 (3,316pt) |

---

## 4. Skill 9: kr-ftd-detector (FTD 탐지기)

### 4.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | ftd-detector |
| 복잡도 | **High** |
| 시간 지평 | 수일~수주 (이벤트 기반) |
| 탐지 대상 | 조정 후 바닥 확인 시그널 (Follow-Through Day) |
| 방법론 | William O'Neil FTD 방법론 |
| 주요 변경 | KOSPI + KOSDAQ 이중 추적, 외국인 순매수 전환 연동 |
| 데이터 소스 | KRClient (PyKRX) |
| 관계 | kr-market-top-detector와 공격/방어 쌍 |

### 4.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| S&P 500 + NASDAQ 이중 추적 | **KOSPI + KOSDAQ** 이중 추적 | 동일 구조 |
| FMP API 일봉 | KRClient `get_index()` | PyKRX |
| 3%+ 하락 = 조정 | **3%+ 하락** (동일, 한국 변동성 반영 검토) | KOSPI 변동성은 S&P 500과 유사 |
| Day 4-10, 1.5%+ 상승 | **Day 4-10, 1.5%+ 상승** (동일) | 가격제한폭 ±30%이므로 충분 |
| - (없음) | **외국인 순매수 전환** 품질 점수 반영 | 한국 특화 |
| - (없음) | **기관 순매수 동시 확인** | 한국 특화 |

### 4.3 상태 머신 (State Machine)

US 원본과 동일한 7-상태 머신:

```
                   ┌──────────────┐
                   │  NO_SIGNAL   │ ← 상승 추세, 조정 없음
                   └──────┬───────┘
                     KOSPI/KOSDAQ 3%+ 하락
                   ┌──────▼───────┐
                   │  CORRECTION  │◄──── 랠리 실패 ───┐
                   └──────┬───────┘                   │
                     스윙 로우 확인 (전일 대비 상승)     │
                   ┌──────▼───────┐                   │
                   │RALLY_ATTEMPT │                   │
                   │  (Day 1-3)   │───── 스윙 로우 이탈 ┘
                   └──────┬───────┘
                     Day 4 진입
                   ┌──────▼───────┐
                   │  FTD_WINDOW  │───── 스윙 로우 이탈 ──► RALLY_FAILED
                   │  (Day 4-10)  │───── Day 11+ 미충족 ──► RALLY_FAILED
                   └──────┬───────┘
                     FTD 자격 조건 충족
                   ┌──────▼───────┐
                   │FTD_CONFIRMED │───── FTD 일 종가 하회 ──► FTD_INVALIDATED
                   └──────────────┘
```

**KOSPI + KOSDAQ 이중 추적 규칙**:
- 각 지수에 독립적 상태 머신 운영
- 둘 중 하나라도 FTD_CONFIRMED → 시그널 발생
- 두 지수 모두 FTD_CONFIRMED → 강화 시그널 (품질 점수 +15)

### 4.4 FTD 자격 조건

| 조건 | 값 | 비고 |
|------|-----|------|
| 최소 랠리 일수 | 4일째부터 | Day 1 = 스윙 로우 반등일 |
| 최대 FTD 윈도우 | 10일째까지 | Day 11+ → 유효하지만 품질 감점 |
| 최소 상승률 | **+1.5%** | US 동일 (가격제한폭 감안 충분) |
| 거래량 조건 | 전일 대비 증가 | 확인 거래량 |
| 교정 하한 | 3%+ 하락 | 의미 있는 조정 |
| 조정 일수 | 최소 3 거래일 | 의미 있는 기간 |

### 4.5 FTD 품질 점수 (0-100)

US 원본의 4-컴포넌트에 한국 특화 컴포넌트 추가:

| # | 컴포넌트 | 가중치 | US 가중치 | 설명 |
|---|---------|:------:|:---------:|------|
| 1 | Volume Surge | **25%** | 30% | 거래량 급증 정도 (volume_ratio) |
| 2 | Day Number | **15%** | 20% | FTD 발생일 (Day 4-6 선호) |
| 3 | Gain Size | **20%** | 20% | 상승 폭 (클수록 강한 시그널) |
| 4 | Breadth Confirmation | **20%** | 30% | 시장폭 개선 (kr-market-breadth 연동) |
| 5 | **Foreign Flow Confirmation** | **20%** | - (신규) | 외국인 순매수 전환 여부 |

#### 4.5.1 Component 1: Volume Surge (25%)

| Volume Ratio (FTD일 / 전일) | 점수 |
|:--------------------------:|:----:|
| < 1.0 | 0 (비자격) |
| 1.0 - 1.2 | 30 |
| 1.2 - 1.5 | 50 |
| 1.5 - 2.0 | 70 |
| > 2.0 | 90-100 |

#### 4.5.2 Component 2: Day Number (15%)

| FTD 발생일 | 점수 |
|:---------:|:----:|
| Day 4 | 100 |
| Day 5 | 90 |
| Day 6 | 80 |
| Day 7 | 65 |
| Day 8 | 50 |
| Day 9 | 35 |
| Day 10 | 20 |

#### 4.5.3 Component 3: Gain Size (20%)

| 상승률 | 점수 |
|:-----:|:----:|
| 1.5-2.0% | 40 |
| 2.0-2.5% | 60 |
| 2.5-3.5% | 80 |
| > 3.5% | 100 |

#### 4.5.4 Component 4: Breadth Confirmation (20%)

| 시장폭 변화 | 점수 |
|:---------:|:----:|
| 200MA 위 종목 비율 +5%p 이상 개선 | 80-100 |
| +2~5%p 개선 | 50-70 |
| 변화 없음 (±2%p) | 20-40 |
| 악화 | 0-15 |

#### 4.5.5 Component 5: Foreign Flow Confirmation (20%) — 한국 특화

| 외국인 순매수 전환 | 점수 |
|:--------------:|:----:|
| FTD 당일 + 전일 순매수 | 90-100 |
| FTD 당일만 순매수 | 60-80 |
| 순매수 전환 없음 (중립) | 30-40 |
| 여전히 순매도 | 0-20 |

### 4.6 노출 가이드

| 품질 점수 | 시그널 강도 | 노출 비율 |
|:--------:|----------|:--------:|
| 80-100 | Strong FTD | 75-100% |
| 60-79 | Moderate FTD | 50-75% |
| 40-59 | Weak FTD | 25-50% |
| < 40 | No FTD / Failed | 0-25% |

### 4.7 스크립트 상세

#### 4.7.1 rally_tracker.py

```python
class RallyState(Enum):
    NO_SIGNAL = 'no_signal'
    CORRECTION = 'correction'
    RALLY_ATTEMPT = 'rally_attempt'
    FTD_WINDOW = 'ftd_window'
    FTD_CONFIRMED = 'ftd_confirmed'
    RALLY_FAILED = 'rally_failed'
    FTD_INVALIDATED = 'ftd_invalidated'

class RallyTracker:
    """KOSPI/KOSDAQ 랠리 시도 추적기."""

    CORRECTION_THRESHOLD = -0.03  # -3%
    MIN_CORRECTION_DAYS = 3

    def __init__(self, index_name: str = 'KOSPI'):
        self.state = RallyState.NO_SIGNAL
        self.swing_low = None
        self.rally_day = 0

    def update(self, date: str, close: float, volume: int) -> RallyState:
        """일별 데이터로 상태 머신 업데이트."""

    def get_state(self) -> dict:
        """현재 상태 + 메타데이터."""
```

#### 4.7.2 ftd_qualifier.py

```python
QUALITY_WEIGHTS = {
    'volume_surge': 0.25,
    'day_number': 0.15,
    'gain_size': 0.20,
    'breadth_confirmation': 0.20,
    'foreign_flow': 0.20,
}

class FTDQualifier:
    """FTD 자격 판정 + 품질 점수 계산."""

    FTD_MIN_GAIN = 0.015      # +1.5%
    FTD_WINDOW_START = 4
    FTD_WINDOW_END = 10

    def qualify(self, rally_state: dict, index_data: pd.DataFrame,
                breadth_data: dict = None, foreign_data: pd.DataFrame = None) -> dict:
        """
        Returns:
            {
                'is_ftd': bool,
                'quality_score': float (0-100),
                'components': dict,
                'exposure_guidance': str,
                'signal_strength': str,
            }
        """
```

#### 4.7.3 post_ftd_monitor.py

```python
class PostFTDMonitor:
    """FTD 이후 건전성 모니터링."""

    def check_health(self, ftd_data: dict, current_data: pd.DataFrame) -> dict:
        """
        FTD 무효화 조건 체크:
        - FTD 일 종가 하회
        - 추가 분배일 3일 이상
        - 스윙 로우 이탈
        """
```

#### 4.7.4 report_generator.py

```python
class ReportGenerator:
    """FTD 탐지 JSON + Markdown 리포트."""

    def generate(self, result: dict) -> dict:
        """리포트 생성. Returns {'json_path': ..., 'md_path': ...}"""
```

#### 4.7.5 kr_ftd_detector.py (메인 오케스트레이터)

```python
def analyze(output_dir: str, breadth_json: str = None) -> dict:
    """
    1. KOSPI + KOSDAQ 일봉 데이터 수집 (60+ 거래일)
    2. 각 지수에 RallyTracker 독립 운영
    3. FTD 자격 판정 + 품질 점수 계산
    4. 외국인 매매동향 크로스체크
    5. 리포트 생성
    """
```

### 4.8 테스트 계획

**test_ftd.py** (예상 25-30 테스트):

| 테스트 클래스 | 테스트 수 | 범위 |
|-------------|:--------:|------|
| TestRallyState | 3 | 상태 Enum, 초기 상태 |
| TestRallyTracker | 8 | 상태 전이, 조정 감지, 랠리 시도, 스윙 로우 |
| TestFTDQualifier | 6 | FTD 자격, 비자격, 품질 점수, 노출 가이드 |
| TestPostFTDMonitor | 4 | 무효화 조건, 건전성 유지 |
| TestQualityWeights | 2 | 가중치 합계, 컴포넌트 범위 |
| TestForeignFlowConfirmation | 3 | 순매수 전환, 중립, 순매도 |
| TestDualIndexTracking | 3 | KOSPI만, KOSDAQ만, 양쪽 동시 |
| TestReportGenerator | 2 | JSON/MD 파일 생성 |

### 4.9 참조 문서 목록

| 파일 | 내용 |
|------|------|
| `references/ftd_methodology_kr.md` | FTD 방법론 한국 적용, 이중 추적, 외국인 전환 시그널 |

---

## 5. Skill 10: kr-bubble-detector (버블 탐지기)

### 5.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | us-market-bubble-detector (v2.1) |
| 복잡도 | **Medium** |
| 시간 지평 | 수개월~수년 (구조적/장기) |
| 탐지 대상 | 30%+ 폭락 가능성이 있는 버블 과열 |
| 방법론 | Minsky/Kindleberger 프레임워크 v2.1 |
| 주요 변경 | 한국 지표로 교체 (VKOSPI, 신용잔고, PER 밴드) |
| 특징 | 정량(max 12점) + 정성(max 3점) 2단계 평가 |

### 5.2 US → KR 변경점

| US 지표 | KR 대체 | 비고 |
|---------|---------|------|
| CBOE Put/Call Ratio | **VKOSPI + 시장 위치** | VKOSPI로 대체 (Put/Call 데이터 접근 제한) |
| VIX + 52주 고점 | **VKOSPI + KOSPI 위치** | 통합 (US는 분리) |
| FINRA Margin Debt | **신용잔고 변화율** | WebSearch / Tier 2 |
| Renaissance Capital IPO | **한국 IPO 통계** | DART + WebSearch |
| 50DMA breadth | **200MA 위 종목 비율** | kr-market-breadth 연동 |
| 3개월 수익률 percentile | **KOSPI 3개월 수익률** percentile | 동일 로직 |
| - (없음) | **KOSPI PER 밴드** (한국 특화) | PyKRX 지수 PER |

### 5.3 6개 정량 지표 (Phase 2: 최대 12점)

각 지표 0/1/2 점, 합계 최대 12점.

#### 지표 1: VKOSPI + 시장 위치 (자만+과열 복합)

US의 Put/Call Ratio와 VIX+New Highs를 통합.

| 조건 | 점수 |
|------|:----:|
| VKOSPI < 13 AND KOSPI 52주 고점 대비 5% 이내 | **2** |
| VKOSPI 13-18 AND KOSPI 고점 근접 | **1** |
| VKOSPI > 18 OR 고점 대비 10%+ 하락 | **0** |

```python
def score_vkospi_market(vkospi: float, kospi_pct_from_high: float) -> int:
```

#### 지표 2: 신용잔고 변화 (레버리지)

| 조건 | 점수 |
|------|:----:|
| 신용잔고 YoY +20% 이상 AND 역대 최고 | **2** |
| 신용잔고 YoY +10~20% | **1** |
| YoY +10% 이하 또는 감소 | **0** |

```python
def score_credit_balance(credit_yoy: float, is_ath: bool) -> int:
```

#### 지표 3: IPO 과열도

| 조건 | 점수 |
|------|:----:|
| 분기 IPO 건수 > 5년 평균 2배 AND 평균 청약경쟁률 > 500:1 | **2** |
| IPO 건수 > 5년 평균 1.5배 | **1** |
| 정상 수준 | **0** |

```python
def score_ipo_heat(quarterly_ipo_count: int, avg_5y: float,
                   avg_competition: float) -> int:
```

#### 지표 4: 시장폭 이상 (Breadth Anomaly)

| 조건 | 점수 |
|------|:----:|
| KOSPI 신고가 AND 200MA 위 종목 비율 < 45% | **2** |
| 200MA 위 종목 비율 45-60% | **1** |
| 200MA 위 종목 비율 > 60% | **0** |

```python
def score_breadth_anomaly(is_new_high: bool, breadth_200ma: float) -> int:
```

#### 지표 5: 가격 가속화 (Price Acceleration)

| 조건 | 점수 |
|------|:----:|
| KOSPI 3개월 수익률 > 10년 95th percentile | **2** |
| 85-95th percentile | **1** |
| 85th percentile 미만 | **0** |

```python
def score_price_acceleration(return_3m: float, hist_percentile: float) -> int:
```

#### 지표 6: KOSPI PER 밴드 (한국 특화)

US에 없는 지표. 한국 시장에서 PER 밴드는 역사적 과열/침체 판단의 핵심 도구.

| 조건 | 점수 |
|------|:----:|
| KOSPI PER > 역사적 상위 10% (PER ≥ 14) | **2** |
| 상위 10-25% (PER 12-14) | **1** |
| 중위 이하 (PER < 12) | **0** |

```python
def score_per_band(kospi_per: float) -> int:
```

**참고**: KOSPI 역사적 PER 범위
- 저점: ~8 (2008 금융위기, 2020 코로나)
- 중위: ~10-11
- 고점: ~14-16 (2007, 2021)
- 극단: ~20+ (2000 IT버블 시기)

### 5.4 3개 정성 조정 (Phase 3: 최대 +3점)

US v2.1의 엄격한 정성 기준 유지. 각 +0 또는 +1점.

#### 조정 A: 사회적 침투도 (0-1점)

**+1점 충족 요건** (3가지 모두 필요):
- 직접 사용자 보고 (지인의 주식 투자 언급)
- 구체적 사례 (택시기사, 학생 등 비전문가 투자)
- 복수 출처 (3개 이상 독립 소스)

#### 조정 B: 미디어/검색 트렌드 (0-1점)

**+1점 충족 요건** (2가지 모두 필요):
- 네이버 트렌드 "주식투자" 검색량 YoY 5배+
- 지상파 방송 (KBS/MBC/SBS) 투자 관련 보도 확인

#### 조정 C: 밸류에이션 괴리 (0-1점)

**+1점 충족 요건** (3가지 모두 필요):
- KOSPI PER > 14 (or KOSDAQ PER > 30)
- 실적 무시 상승 (적자 기업 급등)
- "이번엔 다르다" 내러티브 확인

### 5.5 리스크 존 매핑 (US v2.1 동일)

| 점수 | 존 | 리스크 예산 | 행동 지침 |
|:----:|-----|:---------:|----------|
| 0-4 | Normal (정상) | 100% | 정상 투자 전략 |
| 5-7 | Caution (주의) | 70-80% | 부분 이익실현 시작 |
| 8-9 | Elevated Risk (위험 상승) | 50-70% | 이익실현 강화, 선별 진입 |
| 10-12 | Euphoria (유포리아) | 40-50% | 적극 이익실현 |
| 13-15 | Critical (위기) | 20-30% | 최대 방어, 헤지 |

### 5.6 스크립트 상세

#### 5.6.1 bubble_scorer.py

```python
INDICATOR_NAMES = [
    'vkospi_market',      # VKOSPI + 시장 위치
    'credit_balance',     # 신용잔고
    'ipo_heat',          # IPO 과열도
    'breadth_anomaly',   # 시장폭 이상
    'price_acceleration', # 가격 가속화
    'per_band',          # KOSPI PER 밴드
]

RISK_ZONES = {
    'Normal':        (0, 4, '정상'),
    'Caution':       (5, 7, '주의'),
    'Elevated_Risk': (8, 9, '위험 상승'),
    'Euphoria':      (10, 12, '유포리아'),
    'Critical':      (13, 15, '위기'),
}

class BubbleScorer:
    """6 정량 + 3 정성 버블 스코어러."""

    def score_quantitative(self, indicators: dict) -> dict:
        """정량 6개 지표 스코어링. Returns {'scores': dict, 'total': int}"""

    def score_qualitative(self, adjustments: dict) -> dict:
        """정성 3개 조정. Returns {'adjustments': dict, 'total': int}"""

    def calculate_final(self, quant: dict, qual: dict) -> dict:
        """최종 점수 = 정량 + 정성. Returns {'final_score': int, 'risk_zone': str, ...}"""
```

#### 5.6.2 kr_bubble_detector.py (메인 오케스트레이터)

```python
def analyze(output_dir: str, breadth_json: str = None,
            qualitative: dict = None) -> dict:
    """
    1. KRClient로 데이터 수집 (KOSPI, VKOSPI, PER)
    2. WebSearch로 보충 (신용잔고, IPO)
    3. 6개 정량 지표 자동 스코어링
    4. 3개 정성 조정 (사용자 입력 또는 기본값)
    5. 리포트 생성
    """
```

#### 5.6.3 report_generator.py

```python
class ReportGenerator:
    """버블 탐지 JSON + Markdown 리포트."""

    def generate(self, result: dict) -> dict:
        """Phase 2 (정량) + Phase 3 (정성) 분리 표시 리포트."""
```

### 5.7 테스트 계획

**test_bubble.py** (예상 20-25 테스트):

| 테스트 클래스 | 테스트 수 | 범위 |
|-------------|:--------:|------|
| TestScoreVkospiMarket | 3 | 3가지 점수 케이스 |
| TestScoreCreditBalance | 3 | 3가지 점수 케이스 |
| TestScoreIPOHeat | 3 | 3가지 점수 케이스 |
| TestScoreBreadthAnomaly | 3 | 3가지 점수 케이스 |
| TestScorePriceAcceleration | 3 | 3가지 점수 케이스 |
| TestScorePerBand | 3 | 3가지 점수 케이스 |
| TestBubbleScorerQuantitative | 2 | 합산, 범위 |
| TestBubbleScorerQualitative | 2 | 정성 조정, 최대 3점 |
| TestRiskZoneMapping | 3 | 존 매핑 정확성 |
| TestReportGenerator | 2 | JSON/MD 파일 생성 |

### 5.8 참조 문서 목록

| 파일 | 내용 |
|------|------|
| `references/bubble_framework_kr.md` | Minsky/Kindleberger v2.1 한국 적용, 6지표 상세 |
| `references/historical_kr_bubbles.md` | 1999 IT버블, 2007 KOSPI 6124, 2021 KOSPI 3316 사례 |

---

## 6. Skill 11: kr-macro-regime (매크로 레짐 탐지기)

### 6.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | macro-regime-detector |
| 복잡도 | **High** |
| 시간 지평 | 1-2년 (구조적 전환) |
| 탐지 대상 | 거시 레짐 변화 (인플레이션/긴축/확산 등) |
| 방법론 | 월간 크로스에셋 비율 분석 (6M/12M SMA) |
| 주요 변경 | 한국 ETF/지수/채권으로 교체 |
| 데이터 소스 | KRClient (PyKRX + FDR) |

### 6.2 US → KR 변경점

| US 지표 | 한국 대체 | 데이터 소스 |
|---------|---------|-----------|
| RSP/SPY (Equal/Cap Weight) | **KOSPI 대형주 / KOSPI 전체** 비율 | PyKRX 업종지수 |
| 10Y-2Y Treasury spread | **국고채 10년 - 국고채 3년** spread | PyKRX 채권 |
| HYG/LQD (High Yield/IG) | **회사채 BBB- - AA-** 스프레드 | PyKRX 채권 |
| IWM/SPY (Small/Large) | **KOSDAQ / KOSPI** 비율 | PyKRX 지수 |
| SPY/TLT (Equity/Bond) | **KOSPI / 국고채10년 가격** | PyKRX + FDR |
| XLY/XLP (Cyclical/Defensive) | **경기민감 / 방어 업종** 비율 | PyKRX 업종지수 |
| FMP API (600일) | KRClient (동일 기간) | 전체 교체 |

### 6.3 6-컴포넌트 크로스에셋 비율 분석

| # | 컴포넌트 | 가중치 | US 가중치 | 비율/데이터 | 탐지 대상 |
|---|---------|:------:|:---------:|-----------|----------|
| 1 | 시장 집중도 | **25%** | 25% | 대형주 / 전체 비율 | 대형주 쏠림 vs 시장 확산 |
| 2 | 금리 곡선 | **20%** | 20% | 국고채 10Y - 3Y | 금리 사이클 전환 |
| 3 | 신용 환경 | **15%** | 15% | BBB- vs AA- 스프레드 | 신용 리스크 선호도 |
| 4 | 사이즈 팩터 | **15%** | 15% | KOSDAQ / KOSPI | 소형 vs 대형 로테이션 |
| 5 | 주식-채권 관계 | **15%** | 15% | KOSPI / 국고채 + 상관관계 | 자산 간 관계 레짐 |
| 6 | 섹터 로테이션 | **10%** | 10% | 경기민감 / 방어 | 경기 사이클 |

#### 6.3.1 Component 1: 시장 집중도 (25%)

**비율**: KOSPI 대형주 시총 비중 (상위 10종목 / 전체)

**방법**:
1. KOSPI 시가총액 상위 10종목 비중 계산 (`get_market_cap()`)
2. 6M SMA와 12M SMA의 크로스오버 감지
3. 상위 10종목 비중 추세로 집중/확산 판단

**시그널**:

| 비중 추세 | 해석 | 레짐 기여 |
|----------|------|----------|
| 비중 상승 (6M > 12M) | 대형주 집중 심화 | → Concentration |
| 비중 하락 (6M < 12M) | 시장 확산 | → Broadening |
| 비중 안정 | 중립 | → Transitional |

```python
class ConcentrationCalculator:
    """시장 집중도 계산기."""

    def calculate(self, market_caps: pd.DataFrame,
                  lookback_6m: int = 130, lookback_12m: int = 260) -> dict:
        """
        Returns:
            {
                'top10_ratio': float,         # 상위 10종목 비중 (현재)
                'top10_ratio_6m_sma': float,  # 6M SMA
                'top10_ratio_12m_sma': float, # 12M SMA
                'trend': str,                 # 'concentrating' | 'broadening' | 'stable'
                'regime_signal': str,
            }
        """
```

#### 6.3.2 Component 2: 금리 곡선 (20%)

**비율**: 국고채 10년 - 국고채 3년 스프레드

| 스프레드 상태 | 해석 | 레짐 기여 |
|-------------|------|----------|
| 역전 (< 0bp) | 긴축 / 경기침체 선행 | → Contraction |
| 평탄화 (0-30bp) | 경계 구간 | → Transitional |
| 정상 (30-100bp) | 정상적 금리 구조 | → 중립 |
| 스티프닝 (> 100bp) | 완화적 환경 | → Broadening |

```python
class YieldCurveCalculator:
    """한국 국채 금리 곡선 분석."""

    def calculate(self, yields_10y: pd.Series, yields_3y: pd.Series) -> dict:
        """국고채 10Y-3Y 스프레드 분석."""
```

#### 6.3.3 Component 3: 신용 환경 (15%)

**비율**: 회사채 BBB- 수익률 - AA- 수익률 (신용 스프레드)

| 스프레드 변화 | 해석 | 레짐 기여 |
|-------------|------|----------|
| 확대 (6M > 12M) | 신용 위험 증가, 리스크 회피 | → Contraction |
| 축소 (6M < 12M) | 신용 위험 감소, 리스크 선호 | → Broadening |
| 안정 | 중립 | → 중립 |

```python
class CreditCalculator:
    """한국 신용 환경 분석."""

    def calculate(self, bbb_yields: pd.Series, aa_yields: pd.Series) -> dict:
        """BBB- vs AA- 스프레드 분석."""
```

#### 6.3.4 Component 4: 사이즈 팩터 (15%)

**비율**: KOSDAQ 지수 / KOSPI 지수

| KOSDAQ/KOSPI 비율 추세 | 해석 | 레짐 기여 |
|:--------------------:|------|----------|
| 상승 (6M > 12M) | 소형주 선호 → 리스크 온 | → Broadening |
| 하락 (6M < 12M) | 대형주 선호 → 안전 자산 | → Concentration |
| 안정 | 중립 | → Transitional |

```python
class SizeFactorCalculator:
    """KOSDAQ/KOSPI 사이즈 팩터 분석."""

    def calculate(self, kospi: pd.Series, kosdaq: pd.Series) -> dict:
        """KOSDAQ/KOSPI 비율 추세 분석."""
```

#### 6.3.5 Component 5: 주식-채권 관계 (15%)

**이중 분석**:
1. **비율**: KOSPI / 국고채 10년 가격 추세
2. **상관관계**: 60일 롤링 상관계수

| 조건 | 해석 | 레짐 기여 |
|------|------|----------|
| 양(+) 상관 (> 0.3) | 주식-채권 동행 → 유동성/인플레이션 주도 | → Inflationary |
| 음(-) 상관 (< -0.3) | 전통적 역상관 → 정상적 헤지 작동 | → 중립 |
| 약한 상관 (-0.3 ~ 0.3) | 관계 붕괴 → 전환기 | → Transitional |

```python
class EquityBondCalculator:
    """주식-채권 관계 분석."""

    def calculate(self, kospi: pd.Series, bond_price: pd.Series) -> dict:
        """KOSPI-국고채 비율 + 상관관계 분석."""
```

#### 6.3.6 Component 6: 섹터 로테이션 (10%)

**비율**: 경기민감 업종 수익률 / 방어 업종 수익률

경기민감: 자동차(운수장비), 철강금속, 건설업
방어: 통신업, 음식료, 의약품

| 비율 추세 | 해석 | 레짐 기여 |
|----------|------|----------|
| 경기민감 강세 (6M > 12M) | 경기 확장 기대 | → Broadening |
| 방어 강세 (6M < 12M) | 경기 수축 우려 | → Contraction |
| 혼재 | 전환기 | → Transitional |

```python
KR_CYCLICAL_SECTORS = ['1011', '1007', '1014']  # 운수장비, 철강금속, 건설
KR_DEFENSIVE_SECTORS = ['1016', '1001', '1005'] # 통신, 음식료, 의약품

class SectorRotationCalculator:
    """섹터 로테이션 분석."""

    def calculate(self, sector_data: dict) -> dict:
        """경기민감/방어 상대 성과 분석."""
```

### 6.4 5개 레짐 분류

| 레짐 | 정의 | 주요 시그널 | 전략적 함의 |
|------|------|----------|-----------|
| **Concentration** (집중) | 대형주/반도체 쏠림, 좁은 시장 | 집중도↑, 사이즈↓ | 대형 성장주 유지, 소형주 회피 |
| **Broadening** (확산) | 참여 확대, 소형/가치 로테이션 | 집중도↓, 사이즈↑, 신용↓ | 소형/가치주 비중 확대 |
| **Contraction** (긴축) | 신용 악화, 방어적 로테이션 | 금리역전, 신용↑, 방어강세 | 현금 비중 확대, 방어 섹터 |
| **Inflationary** (인플레) | 주식-채권 양(+) 상관 | 상관>0.3, 원자재↑ | 실물자산, 에너지/원자재 |
| **Transitional** (전환기) | 복합 시그널, 불확실 | 다수 컴포넌트 혼재 | 포지션 축소, 관망 |

**레짐 판정 로직**:
```python
def classify_regime(components: dict) -> str:
    """
    6개 컴포넌트의 regime_signal을 집계하여 최다 레짐 선택.
    가중 투표 방식:
    - 각 컴포넌트가 투표 (가중치 반영)
    - 최고 득표 레짐 = 현재 레짐
    - 최고 득표가 40% 미만이면 'Transitional'
    """
```

### 6.5 전환 확률

US 원본과 동일한 방식으로 레짐 전환 확률 계산:

```python
def calculate_transition_probability(current_regime: str,
                                      components: dict) -> dict:
    """
    현재 레짐에서 다른 레짐으로의 전환 확률.
    컴포넌트 추세 방향 + 속도 기반.
    Returns: {'broadening': 0.35, 'contraction': 0.25, ...}
    """
```

### 6.6 스크립트 상세

#### 6.6.1 calculators/ (6개 파일)

```
calculators/
├── concentration_calculator.py    # 시장 집중도 (6.3.1)
├── yield_curve_calculator.py      # 금리 곡선 (6.3.2)
├── credit_calculator.py           # 신용 환경 (6.3.3)
├── size_factor_calculator.py      # 사이즈 팩터 (6.3.4)
├── equity_bond_calculator.py      # 주식-채권 (6.3.5)
└── sector_rotation_calculator.py  # 섹터 로테이션 (6.3.6)
```

각 calculator 클래스의 공통 인터페이스:

```python
class BaseCalculator:
    """모든 calculator의 베이스 클래스."""

    def calculate(self, **kwargs) -> dict:
        """비율 + 추세 계산. Returns {'value': ..., 'trend': ..., 'regime_signal': ...}"""

    def sma(self, data: pd.Series, window: int) -> pd.Series:
        """단순이동평균."""
```

#### 6.6.2 scorer.py

```python
COMPONENT_WEIGHTS = {
    'concentration': 0.25,
    'yield_curve': 0.20,
    'credit': 0.15,
    'size_factor': 0.15,
    'equity_bond': 0.15,
    'sector_rotation': 0.10,
}

REGIME_TYPES = ['Concentration', 'Broadening', 'Contraction',
                'Inflationary', 'Transitional']

class MacroRegimeScorer:
    """레짐 분류 스코어러."""

    def classify(self, components: dict) -> dict:
        """
        Returns:
            {
                'regime': str,
                'confidence': float (0-1),
                'transition_probs': dict,
                'components': dict,
                'strategic_implication': str,
            }
        """
```

#### 6.6.3 report_generator.py

```python
class ReportGenerator:
    """매크로 레짐 JSON + Markdown 리포트."""

    def generate(self, result: dict) -> dict:
        """리포트 생성. 레짐 대시보드 + 컴포넌트 상세 + 전환 확률."""
```

#### 6.6.4 kr_macro_regime_detector.py (메인 오케스트레이터)

```python
def analyze(output_dir: str) -> dict:
    """
    1. KRClient로 데이터 수집:
       - KOSPI/KOSDAQ 지수 (600+ 거래일)
       - 국고채 수익률 (3Y, 10Y)
       - 회사채 수익률 (AA-, BBB-)
       - 시가총액 상위 종목
       - KRX 업종별 지수
    2. 6개 calculator 실행
    3. 레짐 분류 + 전환 확률
    4. 리포트 생성
    """
```

### 6.7 테스트 계획

**test_macro_regime.py** (예상 30-35 테스트):

| 테스트 클래스 | 테스트 수 | 범위 |
|-------------|:--------:|------|
| TestConcentrationCalculator | 4 | 집중/확산/안정 시그널, SMA |
| TestYieldCurveCalculator | 4 | 역전/평탄/정상/스티프 |
| TestCreditCalculator | 3 | 확대/축소/안정 |
| TestSizeFactorCalculator | 3 | KOSDAQ/KOSPI 비율 추세 |
| TestEquityBondCalculator | 4 | 상관관계 +/- /약, 비율 추세 |
| TestSectorRotationCalculator | 3 | 경기민감/방어/혼재 |
| TestMacroRegimeScorer | 5 | 5개 레짐 분류, 가중치, 전환 확률 |
| TestRegimeClassification | 3 | 가중 투표, 40% 임계값 |
| TestReportGenerator | 2 | JSON/MD 파일 생성 |

### 6.8 참조 문서 목록

| 파일 | 내용 |
|------|------|
| `references/regime_methodology_kr.md` | 크로스에셋 비율 분석 한국 적용, 6M/12M SMA |
| `references/historical_kr_regimes.md` | 한국 역사적 레짐 전환: 2008(긴축→확산), 2011(집중→긴축), 2017(확산), 2022(인플레→긴축) |

---

## 7. Skill 12: kr-breadth-chart (시장폭 차트 분석)

### 7.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | breadth-chart-analyst |
| 복잡도 | **Low** |
| 스크립트 | 없음 (SKILL.md + 참조 문서만) |
| 역할 | kr-market-breadth 출력 차트의 시각적 해석 가이드 |

### 7.2 US → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| S&P 500 Breadth Index (200DMA) | **KOSPI Breadth (200MA 위 종목 비율)** | kr-market-breadth 데이터 |
| US Uptrend Stock Ratio | **한국 업종별 업트렌드 비율** | kr-uptrend-analyzer 데이터 |
| Barchart/TraderMonty 차트 | **kr-market-breadth JSON 시각화** | 자체 생성 |

### 7.3 SKILL.md 핵심 구조

```markdown
# kr-breadth-chart (한국 시장폭 차트 분석)

## 개요
kr-market-breadth 및 kr-uptrend-analyzer가 생성한 데이터를
차트 이미지로 시각화한 결과를 해석하는 가이드.

## 분석 대상
1. KOSPI Breadth (200MA 위 종목 비율) 차트
2. KOSDAQ Breadth (200MA 위 종목 비율) 차트
3. 업종별 업트렌드 비율 히트맵

## 해석 프레임워크
### 시장폭 존 (Breadth Zones)
- Strong (70%+): 건전한 강세장
- Normal (50-70%): 정상 참여
- Weak (30-50%): 참여 약화, 주의
- Critical (<30%): 약세장 가능

### 다이버전스 패턴
- 강세 다이버전스: 지수 하락 + breadth 개선
- 약세 다이버전스: 지수 상승 + breadth 악화

### kr-market-breadth JSON 연동
- latest breadth_ratio 확인
- 6-component score 해석
- warning 시그널 체크
```

### 7.4 참조 문서

| 파일 | 내용 |
|------|------|
| `references/kr_breadth_chart_guide.md` | 시장폭 차트 해석 패턴, 존 정의, 다이버전스, Phase 2 연동 |

---

## 8. 구현 순서

### 8.1 5-Step 순차 구현

복잡도가 낮은 것부터 시작하여 점진적으로 High 스킬 구현.

| Step | 스킬 | 복잡도 | 산출물 | 예상 기간 |
|:----:|------|:------:|--------|:---------:|
| 1 | kr-breadth-chart | Low | SKILL.md + 1 reference | 0.5일 |
| 2 | kr-bubble-detector | Medium | SKILL.md + 2 references + 3 scripts + 1 test | 2일 |
| 3 | kr-ftd-detector | High | SKILL.md + 1 reference + 5 scripts + 1 test | 3일 |
| 4 | kr-market-top-detector | High | SKILL.md + 2 references + 7 scripts + 1 test | 4일 |
| 5 | kr-macro-regime | High | SKILL.md + 2 references + 9 scripts + 1 test | 4일 |

**총 예상 기간**: ~14일 (2주)

### 8.2 단계별 산출물 요약

| 산출물 유형 | 수량 |
|-----------|:----:|
| SKILL.md | 5 |
| References (.md) | 8 |
| Python Scripts | 24 |
| Test Files | 4 |
| **총 파일 수** | **41** |

### 8.3 테스트 목표

| 스킬 | 예상 테스트 수 |
|------|:----------:|
| kr-market-top-detector | 27 |
| kr-ftd-detector | 31 |
| kr-bubble-detector | 27 |
| kr-macro-regime | 31 |
| **Phase 3 총계** | **~116** |

Phase 1 (25) + Phase 2 (76) + Phase 3 (116) = **총 ~217 테스트**

---

## 9. 품질 기준

### 9.1 테스트 요구사항

- 모든 테스트는 **네트워크 불필요** (mock 데이터)
- 각 스킬별 최소 20개 단위 테스트
- 스코어링 로직 100% 커버리지 (가중치, 임계값, 존 매핑)
- 상태 머신 전이 100% 커버리지 (kr-ftd-detector)
- 엣지 케이스: 빈 데이터, 경계값, 극단값

### 9.2 Gap Analysis 기준

- **Match Rate 목표**: ≥ 90%
- Phase 2 기준과 동일:
  - 디렉토리 구조 일치
  - 스크립트 클래스/메서드 시그니처 일치
  - 스코어링 가중치/임계값 일치
  - 참조 문서 존재
  - 테스트 파일 존재 및 통과

### 9.3 Phase 2 → Phase 3 일관성

- KRClient import 패턴 동일: `from _kr_common.kr_client import KRClient`
- ta_utils import 패턴 동일: `from _kr_common.utils.ta_utils import sma, ema`
- 리포트 포맷 동일: JSON + Markdown, 동일 파일명 패턴
- 테스트 패턴 동일: unittest, mock 데이터, 헬퍼 함수

---

## 10. Phase 2 크로스레퍼런스 상세

### 10.1 kr-market-breadth JSON 출력 형식

Phase 3 스킬이 참조하는 Phase 2 출력:

```json
{
  "analysis_date": "2026-02-28",
  "market": "KOSPI",
  "breadth_ratio": 52.3,
  "composite_score": 65.0,
  "zone": "Normal",
  "components": {
    "breadth_level": {"score": 60, "raw": 52.3},
    "crossover": {"score": 70, "raw": "golden_cross"},
    "cycle": {"score": 55, "raw": "rising"},
    "bearish": {"score": 80, "raw": 0},
    "percentile": {"score": 45, "raw": 45.0},
    "divergence": {"score": 65, "raw": "none"}
  },
  "warnings": []
}
```

### 10.2 kr-uptrend-analyzer JSON 출력 형식

```json
{
  "analysis_date": "2026-02-28",
  "overall_uptrend_ratio": 48.5,
  "composite_score": 55.0,
  "zone": "Neutral",
  "group_averages": {
    "cyclical": 42.0,
    "defensive": 58.0,
    "growth": 45.0,
    "financial": 55.0
  },
  "warnings": ["high_spread"]
}
```

Phase 3 스킬은 이 JSON 파일을 `--breadth-json` 또는 `--uptrend-json` 인수로 받아
내부 계산 대신 기존 분석 결과를 활용할 수 있다.

---

## 부록 A: 한국 역사적 시장 천장 사례

Phase 3 스킬의 백테스트 및 검증에 활용할 한국 역사적 이벤트:

| 시기 | 이벤트 | KOSPI 고점 | 하락폭 | 주요 특징 |
|------|--------|:---------:|:------:|---------|
| 2007.10 | 글로벌 금융위기 직전 | 2,085 | -54% | 외국인 대규모 이탈, 원화 급락 |
| 2011.05 | 유럽 재정위기 | 2,228 | -26% | 외국인 연속 순매도, 원자재 급락 |
| 2018.01 | 글로벌 긴축 우려 | 2,607 | -20% | 미중 무역분쟁, 신용잔고 급증 후 |
| 2021.06 | 코로나 유동성 천장 | 3,316 | -25% | 개인 투자자 급증, 신용잔고 사상최고 |

---

## 부록 B: VKOSPI 역사적 수준

| VKOSPI 범위 | 해석 | 빈도 |
|:-----------:|------|:----:|
| < 13 | 극단적 안일 → 위험 경고 | ~5% |
| 13-18 | 정상적 낙관 | ~45% |
| 18-25 | 건전한 경계심 | ~35% |
| 25-35 | 불안 / 공포 초입 | ~10% |
| > 35 | 극단적 공포 | ~5% |

---

## 부록 C: 한국 국고채 스프레드 역사적 범위

| 스프레드 (10Y - 3Y) | 해석 | 역사적 사례 |
|:------------------:|------|-----------|
| < -20bp | 강한 역전 → 침체 경고 | 2019.8, 2022.10 |
| -20bp ~ 0bp | 약한 역전 → 주의 | 2018.12 |
| 0bp ~ 30bp | 평탄 → 경계 | 2023 |
| 30bp ~ 80bp | 정상 → 건전 | 대부분 기간 |
| > 80bp | 스티프 → 완화적 | 2020.Q3 (대규모 유동성) |
