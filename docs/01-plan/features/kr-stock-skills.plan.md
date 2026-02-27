# 한국 주식 시장용 커스텀 스킬 개발 계획

> **Feature**: kr-stock-skills
> **Created**: 2026-02-27
> **Status**: Plan Phase
> **Author**: Claude Code + User

---

## 1. 프로젝트 개요

### 1.1 목적
미국 주식 전용으로 설계된 39개 Claude Trading Skills를 한국 주식 시장(KOSPI/KOSDAQ)에서 활용 가능하도록 포팅한다.

### 1.2 범위
- US 스킬 39개 → KR 스킬로 전량 포팅
- 한국 시장 특화 기능 추가 (기관/외국인 매매동향, 프로그램 매매, 신용/공매도 등)
- 한국 세제(배당소득세 15.4%, 양도소득세 등) 반영

### 1.3 핵심 원칙
- **방법론은 보존**: CANSLIM, VCP, 드러켄밀러 등의 투자 방법론은 그대로 유지
- **데이터 소스만 교체**: FMP/FINVIZ/Alpaca → PyKRX/FinanceDataReader/DART (+ 선택적으로 한투 API)
- **계좌 없이 시작 가능**: 오픈소스 라이브러리만으로 80% 분석 가능
- **한국 시장 특성 반영**: 기관/외국인 수급, T+2 결제, 가격제한폭 ±30% 등

---

## 2. 데이터 소스 아키텍처

### 2.1 2-Tier 데이터 소스 구조

**계좌 없이도 바로 시작** 가능한 Tier 1과, 계좌 개설 후 확장하는 Tier 2로 구분:

```
═══════════════════════════════════════════════════════════
  Tier 1: 계좌 불필요 - 즉시 시작 (커버리지 ~80%)
═══════════════════════════════════════════════════════════
┌─────────────────────────────────────────────────────────┐
│  Layer A: PyKRX (pip install pykrx)                     │
│  - OHLCV 일봉/주봉/월봉 (전 종목)                       │
│  - PER/PBR/EPS/DIV/BPS (밸류에이션)                     │
│  - 투자자별 매매동향 (기관/외국인/개인, 상세 12분류)      │
│  - 외국인 지분율 및 한도소진율                           │
│  - 공매도 잔고/거래량 (Top 50 포함)                      │
│  - 시가총액 이력                                        │
│  - KRX 지수 OHLCV + 지수 PER/PBR                       │
│  - ETF NAV/괴리율/추적오차/구성종목                      │
│  - 국채/회사채 수익률 (1Y~30Y, AA-/BBB-)                │
├─────────────────────────────────────────────────────────┤
│  Layer B: FinanceDataReader (pip install finance-datareader)│
│  - 한국 주식 OHLCV + 시가총액 (전 종목)                  │
│  - 글로벌 주가지수 (S&P500, NASDAQ, 니케이 등)           │
│  - 환율 (USD/KRW, EUR/KRW 등)                          │
│  - 원자재 (유가, 금 등)                                  │
│  - 암호화폐 (BTC/KRW 등)                               │
│  - 미국 국채 수익률 (US10YT 등)                          │
│  - FRED 경제지표 (M2, 실업률 등)                         │
│  - 업종/산업 분류 정보                                   │
│  - 상장폐지 종목 이력                                    │
├─────────────────────────────────────────────────────────┤
│  Layer C: OpenDartReader (pip install opendartreader)    │
│  - IFRS 재무제표 (재무상태표/손익계산서/현금흐름표)        │
│  - 5% 대량보유 공시                                     │
│  - 임원 지분변동                                        │
│  - 기업 공시 전체 (M&A, 증자, 감자, IPO)                 │
│  - 배당 상세정보                                        │
│  - ※ 무료 DART API 키 필요 (opendart.fss.or.kr)         │
└─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════
  Tier 2: 한투 계좌 필요 - 선택적 확장 (커버리지 100%)
═══════════════════════════════════════════════════════════
┌─────────────────────────────────────────────────────────┐
│  Layer D: 한국투자증권 Open API (계좌 개설 후)            │
│  - 실시간 시세 (WebSocket, 41종목/세션)                  │
│  - 분봉 데이터 (1분/5분/15분)                            │
│  - 호가창 (매수/매도 호가)                               │
│  - 신용/대차 잔고 상세                                   │
│  - 프로그램매매 상세                                     │
│  - 컨센서스/투자의견                                     │
│  - 실제 주문/체결/잔고관리                                │
│  - 조건검색 (서버사이드 스크리너)                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Tier 1 vs Tier 2 데이터 커버리지

| 데이터 | Tier 1 (무계좌) | Tier 2 (한투) | 비고 |
|--------|:--------------:|:------------:|------|
| 일봉/주봉/월봉 OHLCV | PyKRX + FDR | 한투 | 동일 |
| PER/PBR/EPS/DIV | PyKRX | 한투 | 동일 |
| 재무제표 (BS/IS/CF) | DART | 한투+DART | DART가 더 상세 |
| 기관/외국인 매매동향 | **PyKRX (상세 12분류)** | 한투 | PyKRX가 더 상세 |
| 외국인 지분율 | PyKRX | 한투 | 동일 |
| 공매도 잔고/거래량 | **PyKRX** | 한투 | PyKRX가 더 상세 |
| 지수 데이터 | PyKRX + FDR | 한투 | 동일 |
| 업종별 지수 | PyKRX | 한투 | 동일 |
| ETF NAV/괴리율/구성 | **PyKRX** | 한투 | PyKRX가 더 상세 |
| 국채/회사채 수익률 | **PyKRX** | 없음 | PyKRX 고유 |
| 글로벌 지수/환율/원자재 | **FDR** | 한투(해외) | FDR이 더 편리 |
| FRED 경제지표 | **FDR** | 없음 | FDR 고유 |
| 대량보유/지분변동 공시 | **DART** | 없음 | DART 고유 |
| 실시간 시세 | **불가** | 한투 | Tier 2 전용 |
| 분봉 (인트라데이) | **불가** | 한투 | Tier 2 전용 |
| 호가창 | **불가** | 한투 | Tier 2 전용 |
| 신용/대차잔고 상세 | **불가** | 한투 | Tier 2 전용 |
| 컨센서스/투자의견 | **불가** | 한투 | Tier 2 전용 |
| 실제 주문/체결 | **불가** | 한투 | Tier 2 전용 |

> **결론**: Tier 1만으로도 **과거 데이터 기반의 분석/스크리닝/백테스트는 전부 가능**하다.
> 실시간 트레이딩/분봉분석/호가분석만 Tier 2가 필요하다.

### 2.3 API 제약사항

| 소스 | 제한 | 비용 | 계좌 필요 |
|------|------|------|:---------:|
| **PyKRX** | 비공식 크롤링 (과도한 호출 자제) | 무료 | 아니오 |
| **FinanceDataReader** | 비공식 크롤링 (간헐적 오류 가능) | 무료 | 아니오 |
| **OpenDartReader** | 10,000 calls/일 | 무료 | 아니오 (API 키만) |
| **한투 API (실전)** | 20 req/sec | 무료 | **예** |
| **한투 API (모의)** | 5 req/sec | 무료 | **예** |
| **한투 WebSocket** | 41 종목/세션 | 무료 | **예** |

### 2.4 인증 설정

```bash
# ═══ Tier 1: 계좌 불필요 ═══

# DART 전자공시 (무료 API 키 발급: opendart.fss.or.kr)
export DART_API_KEY="your_dart_key"

# PyKRX, FinanceDataReader: API 키 불필요 (pip install만 하면 됨)

# (선택) 한국은행 ECOS
export ECOS_API_KEY="your_ecos_key"

# ═══ Tier 2: 한투 계좌 필요 (선택) ═══

# 한국투자증권 Open API
export KIS_APP_KEY="your_app_key"
export KIS_APP_SECRET="your_app_secret"
export KIS_ACCOUNT_NO="12345678-01"
export KIS_MODE="paper"
```

### 2.5 Python 라이브러리 의존성

```
# ═══ Tier 1: 필수 (계좌 불필요) ═══
pykrx>=1.0                # KRX 시장 데이터 (OHLCV, 밸류에이션, 수급, 공매도)
finance-datareader>=0.9   # 글로벌 시세, 환율, FRED 경제지표
opendartreader>=0.2       # DART 재무제표, 공시

# ═══ Tier 2: 선택 (한투 계좌 필요) ═══
python-kis>=2.0           # 한투 API 래퍼 - 실시간/분봉/주문

# 분석 라이브러리
pandas>=2.0
numpy>=1.24
scipy>=1.10               # 통계 분석 (페어트레이딩 등)
statsmodels>=0.14         # ADF 테스트 등

# 유틸리티
requests>=2.28
python-dotenv>=1.0
```

---

## 3. 스킬 포팅 매핑 (US → KR)

### 3.1 Phase 1: 인프라 & 공통 모듈 (Week 1-2)

구현 대상이 아닌 모든 스킬이 공유하는 **공통 데이터 클라이언트**를 먼저 개발한다.

| 모듈 | 역할 | US 원본 |
|------|------|---------|
| `kr-data-client` | 한투 API 인증/호출 래퍼 | FMP API client |
| `kr-dart-client` | DART API 래퍼 | - (신규) |
| `kr-market-data` | 시장 데이터 통합 조회 | - (신규) |
| `kr-financial-data` | 재무제표 통합 조회 | - (신규) |
| `kr-investor-flow` | 투자자별 매매동향 | - (한국 특화) |

**kr-data-client 핵심 기능**:
```python
class KRDataClient:
    # 시세
    def get_current_price(ticker: str) -> dict
    def get_daily_chart(ticker: str, period: str, count: int) -> DataFrame
    def get_weekly_chart(ticker: str, count: int) -> DataFrame

    # 재무
    def get_financial_statements(ticker: str, period: str) -> dict
    def get_financial_ratios(ticker: str) -> dict

    # 투자자
    def get_investor_trading(ticker: str, days: int) -> DataFrame
    def get_foreign_holdings(ticker: str) -> dict

    # 지수
    def get_index_price(index_code: str) -> dict  # 0001=KOSPI, 1001=KOSDAQ
    def get_sector_prices() -> DataFrame

    # 배당
    def get_dividend_info(ticker: str) -> dict

    # 유틸
    def search_stock(keyword: str) -> list
    def get_market_calendar() -> list
```

### 3.2 Phase 2: 시장 분석 스킬 (Week 3-4) - 7개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 1 | market-environment-analysis | **kr-market-environment** | 코스피/코스닥/원달러환율/국고채 추가, 미국 시장은 WebSearch 유지 |
| 2 | market-news-analyst | **kr-market-news-analyst** | 한국 뉴스 소스 추가 (한경, 매경, 연합인포맥스 등) |
| 3 | market-breadth-analyzer | **kr-market-breadth** | KRX 등락종목수/시장폭 데이터로 대체, 코스피/코스닥 각각 분석 |
| 4 | uptrend-analyzer | **kr-uptrend-analyzer** | KOSPI 200종목 기준 업트렌드 비율 자체 계산 |
| 5 | sector-analyst | **kr-sector-analyst** | KRX 업종지수 활용, 한국 업종 분류 체계 반영 |
| 6 | theme-detector | **kr-theme-detector** | 네이버 금융 테마/업종 데이터 활용, 한국 시장 특유의 테마주 분석 |
| 7 | technical-analyst | **kr-technical-analyst** | 차트 분석 로직 동일, 가격제한폭 ±30% 반영 |

**한국 시장 특화 추가 기능**:
- 기관/외국인 순매수 동향 연동 (US에는 없는 실시간 수급 데이터)
- 프로그램 매매 동향
- 코스피/코스닥 괴리율

### 3.3 Phase 3: 마켓 타이밍 스킬 (Week 5-6) - 5개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 8 | market-top-detector | **kr-market-top-detector** | KOSPI 기반 분배일 카운팅, 외국인 이탈 지표 추가 |
| 9 | ftd-detector | **kr-ftd-detector** | KOSPI + KOSDAQ 이중 추적, 외국인 순매수 전환일 연동 |
| 10 | us-market-bubble-detector | **kr-bubble-detector** | 한국 지표로 교체: 신용잔고/예탁금, 코스피 PER밴드, IPO 과열도 |
| 11 | macro-regime-detector | **kr-macro-regime** | 한국 ETF로 교체: KODEX200, TIGER KRX300, 국고채 ETF 등 |
| 12 | breadth-chart-analyst | **kr-breadth-chart** | 차트 분석 동일, 한국 시장 폭 데이터 참조 프레임워크 |

**한국 시장 특화 지표**:
| 지표 | 설명 | US 대응 |
|------|------|---------|
| 외국인 순매수 연속일수 | 외국인 매매 추세 | 없음 (13F는 분기) |
| 신용잔고 비율 | 레버리지 과열 | 마진 부채 |
| 투자자 예탁금 | 대기 자금 | 없음 |
| 코스피 PER 밴드 | 역사적 밸류에이션 위치 | S&P 500 PER |
| 프로그램 순매수 | 차익/비차익 프로그램 | 없음 |

### 3.4 Phase 4: 종목 스크리닝 스킬 (Week 7-9) - 7개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 13 | canslim-screener | **kr-canslim-screener** | 한투 API 재무비율 + DART 실적 데이터, KOSPI200/KOSDAQ150 대상 |
| 14 | vcp-screener | **kr-vcp-screener** | 한투 API 차트 데이터, 가격제한폭 ±30% 감안 변동성 계산 |
| 15 | value-dividend-screener | **kr-value-dividend** | 한투 배당정보 + DART 재무제표, 한국 배당성향 기준 |
| 16 | dividend-growth-pullback | **kr-dividend-pullback** | RSI 직접 계산 (일봉 기준), 한국 배당주 특성 반영 |
| 17 | pair-trade-screener | **kr-pair-trade** | 동일 업종 내 공적분 페어 탐색, KOSPI 종목 대상 |
| 18 | pead-screener | **kr-pead-screener** | DART 실적 공시일 기준, 한국 실적발표 패턴 반영 |
| 19 | finviz-screener | **kr-stock-screener** | 한투 조건검색 API 활용, FinViz 대신 한투 조건검색 |

**한국 시장 추가 스크리닝 기준**:
| 기준 | 설명 | US에는 없음 |
|------|------|------------|
| 외국인 지분율 변화 | 최근 외국인 순매수/순매도 추세 | 13F는 분기 지연 |
| 신용비율 | 신용거래 과열 여부 | 없음 |
| 공매도 잔고 | 공매도 비율 및 추세 | 별도 API |
| 대주주 지분 변동 | DART 5% 공시 기반 | 13F 유사 |

### 3.5 Phase 5: 캘린더 & 실적 스킬 (Week 10-11) - 4개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 20 | earnings-calendar | **kr-earnings-calendar** | DART 정기보고서 공시일 + 한투 실적추정 데이터 |
| 21 | economic-calendar-fetcher | **kr-economic-calendar** | 한국은행 ECOS API + 한국 경제이벤트 (금통위, 고용률 등) |
| 22 | earnings-trade-analyzer | **kr-earnings-trade** | DART 실적 공시 후 주가 반응 5팩터 분석 |
| 23 | institutional-flow-tracker | **kr-institutional-flow** | 한투 API 기관/외국인 매매동향 (일별/시간별) |

**한국 실적 시즌 특성**:
- 1월 말 ~ 2월: 4Q 잠정실적 (속보치)
- 3월 말: 4Q 확정실적 (사업보고서)
- 5월, 8월, 11월: 분기 실적
- 한국은 "어닝 서프라이즈" 시 갭이 US보다 작은 경향 (가격제한폭 영향)

### 3.6 Phase 6: 전략 & 리스크 관리 스킬 (Week 12-14) - 9개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 24 | backtest-expert | **kr-backtest-expert** | 방법론 동일, 한국 시장 특성(수수료/세금/가격제한폭) 반영 |
| 25 | options-strategy-advisor | **kr-options-advisor** | KOSPI200 옵션 기반, 한국 옵션 승수(25만원) 반영 |
| 26 | portfolio-manager | **kr-portfolio-manager** | 한투 API 잔고조회 연동 (Alpaca 대체) |
| 27 | scenario-analyzer | **kr-scenario-analyzer** | 한국 뉴스/이벤트 기반 시나리오, 한국 섹터 영향 분석 |
| 28 | edge-hint-extractor | **kr-edge-hint** | 한국 시장 관찰 → 엣지 힌트, 수급 데이터 활용 |
| 29 | edge-concept-synthesizer | **kr-edge-concept** | 방법론 동일, 한국 시장 데이터 형식 |
| 30 | edge-strategy-designer | **kr-edge-strategy** | 방법론 동일, 한국 거래 비용 반영 |
| 31 | edge-candidate-agent | **kr-edge-candidate** | 방법론 동일, KR 데이터 파이프라인 |
| 32 | strategy-pivot-designer | **kr-strategy-pivot** | 방법론 동일 |

### 3.7 Phase 7: 배당 & 세금 스킬 (Week 15-16) - 3개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 33 | kanchi-dividend-sop | **kr-dividend-sop** | 한국 배당주 SOP, 한투 배당정보 활용 |
| 34 | kanchi-dividend-review-monitor | **kr-dividend-monitor** | 한국 공시(DART) 기반 트리거, 감배 감지 |
| 35 | kanchi-dividend-us-tax-accounting | **kr-dividend-tax** | **한국 세제로 완전 재작성** |

**한국 배당 세제**:
| 항목 | 한국 | US (참고) |
|------|------|----------|
| 배당소득세 | 15.4% (소득세 14% + 지방세 1.4%) | 적격 0-20%, 비적격 최대 37% |
| 금융소득종합과세 | 연 2,000만원 초과 시 종합과세 | 없음 (전부 종합과세) |
| ISA 계좌 | 비과세 한도 200만원 (서민형 400만원) | IRA/401k 유사 |
| 연금저축/IRP | 세액공제 + 배당 과세이연 | IRA 유사 |

### 3.8 Phase 8: 메타 & 유틸리티 (Week 17-18) - 4개

| # | US 스킬 | KR 스킬명 | 변경사항 |
|---|---------|-----------|----------|
| 36 | us-stock-analysis | **kr-stock-analysis** | 한투+DART 데이터로 종합 분석, 수급 분석 추가 |
| 37 | stanley-druckenmiller-investment | **kr-strategy-synthesizer** | KR 스킬 JSON 결과 통합, 한국 시장 확신도 |
| 38 | dual-axis-skill-reviewer | **kr-skill-reviewer** | 그대로 사용 (메타 스킬) |
| 39 | weekly-trade-strategy | **kr-weekly-strategy** | 한국 시장 주간 전략 워크플로우 |

### 3.9 한국 시장 전용 신규 스킬 (Phase 9: Week 19-20) - 5개

US에는 없지만 한국 시장에서 필수적인 스킬:

| # | 스킬명 | 설명 |
|---|--------|------|
| 40 | **kr-supply-demand-analyzer** | 기관/외국인/개인 수급 종합 분석 (한국 시장의 핵심) |
| 41 | **kr-short-sale-tracker** | 공매도 잔고/거래량 추적 및 숏커버 시그널 감지 |
| 42 | **kr-credit-monitor** | 신용잔고 과열 모니터링 + 반대매매 리스크 평가 |
| 43 | **kr-program-trade-analyzer** | 차익/비차익 프로그램 매매 분석 + 만기일 영향 |
| 44 | **kr-dart-disclosure-monitor** | DART 실시간 공시 모니터링 (M&A, 증자, 감배 등) |

---

## 4. FMP API → 한국 데이터 소스 매핑 상세

> **Tier 1 (T1)** = 계좌 불필요 | **Tier 2 (T2)** = 한투 계좌 필요

### 4.1 시세 데이터

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/quote/{symbol}` | `stock.get_market_ohlcv(today)` | T1 | PyKRX | 당일 종가 (장중 실시간은 T2) |
| | `fdr.DataReader('005930')` | T1 | FDR | OHLCV |
| | `inquire_price` | T2 | 한투 | 실시간 현재가 |
| `/historical-price-full` | `stock.get_market_ohlcv(start, end, ticker, freq)` | T1 | PyKRX | D/W/M/Y 지원 |
| | `fdr.DataReader('005930', '2020')` | T1 | FDR | 일봉 |
| `/quote/{index}` | `stock.get_index_ohlcv(start, end, '0001')` | T1 | PyKRX | 코스피=0001, 코스닥=1001 |
| | `fdr.DataReader('KS11')` | T1 | FDR | KS11=코스피, KQ11=코스닥 |
| `/sector-performance` | `stock.get_index_ohlcv()` + 업종 지수코드 | T1 | PyKRX | 업종별 지수 |

### 4.2 재무 데이터

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/income-statement` | `dart.finstate('삼성전자', 2024)` | T1 | DART | IFRS 상세 |
| `/balance-sheet-statement` | `dart.finstate('삼성전자', 2024)` | T1 | DART | IFRS 상세 |
| `/cash-flow-statement` | `dart.finstate('삼성전자', 2024)` | T1 | DART | IFRS 상세 |
| `/key-metrics` | `stock.get_market_fundamental()` | T1 | PyKRX | PER/PBR/EPS/DIV/BPS |
| `/ratios` | `stock.get_market_fundamental()` | T1 | PyKRX | 전 종목 일괄 조회 가능 |
| `/market-capitalization` | `stock.get_market_cap()` | T1 | PyKRX | 시가총액 + 상장주식수 |
| | `fdr.StockListing('KOSPI')` 의 Marcap 컬럼 | T1 | FDR | 당일 시총 |

### 4.3 투자자/기관 데이터

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/institutional-holder` | `stock.get_market_trading_value_by_date()` | **T1** | PyKRX | **일별 12분류** (금투/보험/투신/사모/은행/연기금/외국인/개인 등) |
| `/insider-trading` | `dart.major_shareholders('삼성전자')` | T1 | DART | 5% 대량보유 공시 |
| - (없음) | `stock.get_exhaustion_rates_of_foreign_investment()` | **T1** | PyKRX | 외국인 한도소진율 (US에 없는 기능) |
| - (없음) | `stock.get_market_net_purchases_of_equities()` | **T1** | PyKRX | 외국인/기관 순매수 상위 종목 |

### 4.4 공매도 데이터 (US FMP에는 없는 기능)

| 한국 함수 | Tier | 소스 | 비고 |
|----------|:----:|------|------|
| `stock.get_shorting_status_by_date()` | **T1** | PyKRX | 공매도 잔고/거래량 일별 |
| `stock.get_shorting_balance_top50()` | **T1** | PyKRX | 공매도 잔고 비율 Top 50 |
| `stock.get_shorting_trade_top50()` | **T1** | PyKRX | 공매도 거래 비율 Top 50 |
| `stock.get_shorting_investor_volume_by_date()` | **T1** | PyKRX | 투자자별 공매도 |

### 4.5 글로벌/매크로 데이터

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/quote/{USD/KRW}` | `fdr.DataReader('USD/KRW')` | T1 | FDR | 환율 |
| `/quote/{oil,gold}` | `fdr.DataReader('CL=F')` | T1 | FDR | 원자재 |
| `/treasury` | `bond.get_otc_treasury_yields()` | T1 | PyKRX | 한국 국채 |
| | `fdr.DataReader('US10YT')` | T1 | FDR | 미국 국채 |
| - | `fdr.DataReader('FRED:M2')` | T1 | FDR | FRED 경제지표 |

### 4.6 이벤트/공시

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/earning_calendar` | `dart.list(corp='삼성전자', kind='A')` | T1 | DART | 분기/반기/사업보고서 |
| `/stock_dividend_calendar` | `dart.report(corp, '배당')` | T1 | DART | 배당 정보 |
| `/sec_filing` | `dart.list()` | T1 | DART | 전체 공시 목록 |
| `/economic_calendar` | ECOS API / WebSearch | T1 | 한국은행 | 금통위 등 |

### 4.7 ETF 데이터

| FMP Endpoint | 한국 대체 | Tier | 소스 | 비고 |
|-------------|----------|:----:|------|------|
| `/etf-holder` | `stock.get_etf_portfolio_deposit_file()` | **T1** | PyKRX | 구성종목+비중 |
| `/etf-info` | `stock.get_etf_ohlcv_by_date()` | **T1** | PyKRX | NAV/괴리율/추적오차 포함 |

> **핵심 포인트**: Tier 1(PyKRX+FDR+DART)만으로 FMP API 기능의 **90% 이상을 대체** 가능.
> 대체 불가 항목: 실시간 시세, 분봉, 호가창, 컨센서스/투자의견만 Tier 2 필요.

---

## 5. 스킬 디렉토리 구조

### 5.1 개별 스킬 구조

```
~/.claude/skills/kr-{skill-name}/
├── SKILL.md                    # 스킬 정의 (YAML frontmatter + 워크플로우)
├── references/                 # 참조 지식 베이스
│   ├── methodology.md          # 분석 방법론 (US 원본 기반)
│   ├── kr-market-specifics.md  # 한국 시장 특성
│   └── api-guide.md            # API 사용 가이드
└── scripts/                    # 실행 스크립트
    ├── main_script.py          # 메인 분석 스크립트
    ├── kr_data_client.py       # 한투 API 클라이언트 (공통 모듈 심링크)
    └── requirements.txt        # 의존성
```

### 5.2 공통 모듈 구조

```
~/.claude/skills/_kr-common/
├── kr_data_client.py           # 한투 API 통합 클라이언트
├── kr_dart_client.py           # DART API 클라이언트
├── kr_market_utils.py          # 시장 유틸리티 (영업일 계산, 티커 변환 등)
├── kr_financial_utils.py       # 재무 분석 유틸리티
├── kr_investor_flow.py         # 투자자별 매매동향 유틸리티
├── kr_tax_calculator.py        # 한국 세금 계산기
├── config.py                   # 환경변수 관리
└── requirements.txt            # 공통 의존성
```

### 5.3 네이밍 규칙

- **접두사**: `kr-` (한국 시장 전용)
- **US 원본 참조**: SKILL.md 내 `based-on: {us-skill-name}` 메타데이터
- **슬래시 명령**: `/kr-canslim-screener`, `/kr-market-breadth` 등

---

## 6. 개발 일정 (20주 계획)

```
Week 1-2   ████ Phase 1: 인프라 & 공통 모듈
Week 3-4   ████ Phase 2: 시장 분석 (7개)
Week 5-6   ████ Phase 3: 마켓 타이밍 (5개)
Week 7-9   ██████ Phase 4: 종목 스크리닝 (7개)
Week 10-11 ████ Phase 5: 캘린더 & 실적 (4개)
Week 12-14 ██████ Phase 6: 전략 & 리스크 (9개)
Week 15-16 ████ Phase 7: 배당 & 세금 (3개)
Week 17-18 ████ Phase 8: 메타 & 유틸리티 (4개)
Week 19-20 ████ Phase 9: 한국 전용 신규 (5개)
```

### 6.1 마일스톤

| MS | 기간 | 산출물 | 스킬 수 |
|----|------|--------|---------|
| **M0** | Week 1-2 | 공통 클라이언트 + 인증 + 기본 조회 동작 확인 | 0 (인프라) |
| **M1** | Week 4 | 시장 분석 7개 스킬 완성 → 일일 루틴 가능 | 7 |
| **M2** | Week 6 | 마켓 타이밍 5개 → 주간 리뷰 가능 | 12 |
| **M3** | Week 9 | 종목 스크리닝 7개 → 종목 발굴 가능 | 19 |
| **M4** | Week 11 | 캘린더/실적 4개 → 실적 시즌 활용 가능 | 23 |
| **M5** | Week 14 | 전략 9개 → 전략 수립/백테스트 가능 | 32 |
| **M6** | Week 16 | 배당/세금 3개 → 배당 투자 가능 | 35 |
| **M7** | Week 18 | 메타 4개 → 종합 분석 가능 | 39 |
| **M8** | Week 20 | 한국 전용 5개 → 풀 패키지 완성 | 44 |

### 6.2 우선순위 기준

1. **즉시 활용 가치**: 매일/매주 사용할 스킬 우선
2. **의존성**: 다른 스킬의 입력이 되는 스킬 우선
3. **난이도**: 간단한 포팅(차트 분석) → 복잡한 포팅(재무 분석) 순서

---

## 7. 한국 시장 특성 반영 사항

### 7.1 거래 제도 차이

| 항목 | 한국 | 미국 | 스킬 영향 |
|------|------|------|----------|
| 가격제한폭 | ±30% | 없음 | VCP 변동성 계산, 갭 분석 |
| 결제 | T+2 | T+1 (2024~) | 포트폴리오 잔고 계산 |
| 거래시간 | 09:00-15:30 | 09:30-16:00 (ET) | 시간대 처리 |
| 공매도 | 개인 제한적 | 자유 | 공매도 분석 스킬 |
| 프로그램매매 | 사이드카/서킷브레이커 | 서킷브레이커만 | 시장 안정 장치 반영 |
| 배당기준일 | 12월 말 집중 | 분기 분산 | 배당 캘린더 패턴 |
| 세금 | 배당소득세 15.4% | 적격/비적격 구분 | 세금 계산 로직 |

### 7.2 수급 분석 (한국 시장의 핵심)

한국 시장은 미국과 달리 **투자자별 매매동향이 실시간 공개**되어 수급 분석이 매우 중요:

```
한국 시장 3대 투자자:
┌──────────────┐
│  외국인 (35%) │ → 코스피 방향성 결정의 핵심
├──────────────┤
│  기관 (25%)   │ → 연기금/보험/투신 구분 가능
├──────────────┤
│  개인 (40%)   │ → 반대지표로 활용 가능
└──────────────┘

활용 포인트:
- 외국인 20일 연속 순매수 → 강한 매수 시그널
- 기관 중 연기금 순매수 + 외국인 순매수 → 매우 강한 시그널
- 개인 폭발적 순매수 + 외국인/기관 순매도 → 주의 (천장 시그널)
```

### 7.3 한국 업종 분류

한투 API는 KRX 업종 분류를 사용:

| 업종코드 | 업종명 | US 대응 |
|----------|--------|---------|
| 0001 | 종합(KOSPI) | S&P 500 |
| 1001 | 종합(KOSDAQ) | NASDAQ |
| 0002 | 대형주 | Large Cap |
| 0003 | 중형주 | Mid Cap |
| 0004 | 소형주 | Small Cap |
| 업종별 | 반도체, 자동차, 금융 등 | Technology, Financials 등 |

---

## 8. 리스크 & 제약사항

### 8.1 기술적 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 한투 API 서비스 1년 갱신 | 서비스 중단 가능 | 연간 갱신 알림 |
| 한투 API 속도 제한 (20/sec) | 대량 스크리닝 시 지연 | 캐싱 + 요청 큐 구현 |
| PyKRX 비공식 API | 언제든 차단 가능 | DART + 한투로 대체 경로 확보 |
| DART 일일 10,000건 | 대량 재무 분석 시 부족 | 결과 캐싱 + 필요시만 호출 |

### 8.2 비용 구조

| 항목 | 비용 | Tier | 비고 |
|------|------|:----:|------|
| PyKRX | **무료** | T1 | pip install |
| FinanceDataReader | **무료** | T1 | pip install |
| DART API (OpenDartReader) | **무료** | T1 | API 키 등록만 |
| ECOS | **무료** | T1 | API 키 등록 |
| 한투 API | **무료** | T2 | 계좌 필요 (선택) |
| **합계** | **$0/월** | - | **전부 무료** |

→ US 스킬 대비 **완전 무료** 운영 가능 (FMP 유료 티어, FINVIZ Elite 불필요)
→ **계좌 없이도 Tier 1만으로 즉시 시작 가능**

### 8.3 전제조건

**Tier 1 (즉시 시작 - 필수)**:
- [ ] Python 3.9+ 환경 준비
- [ ] `pip install pykrx finance-datareader opendartreader` 설치
- [ ] DART API 키 발급 (opendart.fss.or.kr - 무료, 5분 소요)

**Tier 2 (선택 - 실시간/주문 필요 시)**:
- [ ] 한국투자증권 계좌 개설 (비대면 가능)
- [ ] 한투 API 서비스 신청 (KIS Developers 포털)
- [ ] App Key / App Secret 발급
- [ ] python-kis 설치

---

## 9. 빠른 시작 가이드 (MVP)

전체 44개를 다 만들기 전에, **최소 기능 세트**로 즉시 시작할 수 있는 경로:

### 0단계: 환경 설정 (10분)

```bash
# 라이브러리 설치 (계좌 불필요!)
pip install pykrx finance-datareader opendartreader pandas

# DART API 키 설정 (opendart.fss.or.kr에서 무료 발급)
export DART_API_KEY="your_dart_key"

# 동작 확인
python3 -c "
from pykrx import stock
import FinanceDataReader as fdr

# 오늘 코스피 시가총액 Top 5
print('=== KOSPI Top 5 ===')
tickers = stock.get_market_ticker_list(market='KOSPI')
for t in tickers[:5]:
    print(f'{t} {stock.get_market_ticker_name(t)}')

# 삼성전자 최근 5일 종가
df = fdr.DataReader('005930', '2026-02-20')
print(df.tail())
"
```

### Week 1-2 MVP: "한국 시장 일일 브리핑"

```
1. kr-data-client (공통 모듈)     → PyKRX + FDR + DART 통합 래퍼
2. kr-market-breadth              → 코스피/코스닥 등락 종목수 분석 (PyKRX)
3. kr-market-news-analyst         → 한국 시장 뉴스 분석 (WebSearch 기반)
4. kr-market-environment          → 코스피/코스닥/환율/채권 종합 (FDR+PyKRX)

→ 매일 아침 3개 스킬로 시장 체크 가능 (계좌 불필요!)
```

### Week 3-4 MVP: "종목 발굴 시작"

```
5. kr-stock-analysis              → 개별 종목 종합 분석 (PyKRX+DART)
6. kr-institutional-flow          → 기관/외국인 수급 분석 (PyKRX 12분류)
7. kr-supply-demand-analyzer      → 수급 종합 분석 (PyKRX - 한국 전용)
8. kr-short-sale-tracker          → 공매도 분석 (PyKRX)

→ 관심 종목 심층 분석 가능 (계좌 불필요!)
```

---

## 10. 성공 기준

| 기준 | 목표 | 측정 방법 |
|------|------|----------|
| 스킬 수 | 44개 (US 39 + KR 전용 5) | 스킬 디렉토리 카운트 |
| API 커버리지 | FMP 기능 90% 이상 대체 | 엔드포인트 매핑 체크리스트 |
| 일일 루틴 | 10분 내 시장 브리핑 가능 | 실행 시간 측정 |
| 스크리닝 | KOSPI 200 + KOSDAQ 150 커버 | 스크리닝 대상 수 |
| 비용 | $0/월 | API 비용 없음 확인 |

---

## 변경 이력

| 날짜 | 버전 | 작업 내용 | 관련 섹션 |
|------|------|----------|----------|
| 2026-02-27 | 1.0 | 한국 주식 스킬 개발 계획 초안 작성 | 전체 |
| 2026-02-27 | 1.1 | Tier 1/Tier 2 아키텍처 도입 - PyKRX+FDR+DART로 계좌 없이 시작 가능하도록 변경 | 2, 4, 8, 9 |
