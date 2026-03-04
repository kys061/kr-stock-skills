# 한국 주식 스킬 - Phase 1 공통 모듈 상세 설계

> **Feature**: kr-stock-skills (Phase 1)
> **Created**: 2026-02-27
> **Status**: Design Phase
> **Plan Reference**: `docs/01-plan/features/kr-stock-skills.plan.md`

---

## 1. 설계 개요

### 1.1 Phase 1 목표
모든 KR 스킬이 공유하는 **통합 데이터 클라이언트**를 개발한다.
3개 오픈소스 라이브러리(PyKRX + FinanceDataReader + OpenDartReader)를 하나의 일관된 인터페이스로 추상화하여, 개별 스킬 개발자가 데이터 소스를 신경쓰지 않고 분석에 집중할 수 있도록 한다.

### 1.2 설계 원칙
- **Tier 1 First**: 계좌 없이 즉시 동작하는 것이 기본 (Tier 2는 선택적 확장)
- **Fail-Graceful**: 하나의 데이터 소스가 실패해도 대체 소스로 자동 폴백
- **캐싱**: 동일 데이터 반복 호출 방지 (크롤링 부하 최소화)
- **DataFrame 표준화**: 모든 메서드는 pandas DataFrame 또는 dict를 반환

### 1.3 디렉토리 구조

```
~/.claude/skills/_kr-common/
├── __init__.py
├── kr_client.py              # 통합 클라이언트 (메인 진입점)
├── providers/
│   ├── __init__.py
│   ├── pykrx_provider.py     # PyKRX 래퍼
│   ├── fdr_provider.py       # FinanceDataReader 래퍼
│   ├── dart_provider.py      # OpenDartReader 래퍼
│   └── kis_provider.py       # 한투 API 래퍼 (Tier 2, 선택)
├── models/
│   ├── __init__.py
│   ├── stock.py              # 종목 데이터 모델
│   ├── market.py             # 시장/지수 데이터 모델
│   └── financial.py          # 재무 데이터 모델
├── utils/
│   ├── __init__.py
│   ├── cache.py              # 파일 기반 캐시
│   ├── date_utils.py         # 영업일/날짜 유틸
│   ├── ticker_utils.py       # 종목코드 ↔ 종목명 변환
│   └── ta_utils.py           # 기술적 분석 유틸 (RSI, MA 등)
├── config.py                 # 환경변수 + 설정
├── requirements.txt
└── tests/
    ├── test_kr_client.py
    ├── test_pykrx_provider.py
    ├── test_fdr_provider.py
    └── test_dart_provider.py
```

---

## 2. 모듈 상세 설계

### 2.1 kr_client.py - 통합 클라이언트 (메인 진입점)

모든 스킬에서 `from _kr_common.kr_client import KRClient` 하나로 모든 데이터에 접근.

```python
class KRClient:
    """한국 주식 시장 통합 데이터 클라이언트.

    Tier 1 (계좌 불필요): PyKRX + FinanceDataReader + OpenDartReader
    Tier 2 (선택): 한국투자증권 Open API (실시간/분봉/주문)
    """

    def __init__(self, dart_api_key: str = None, cache_dir: str = None):
        """
        Args:
            dart_api_key: DART API 키. None이면 환경변수 DART_API_KEY에서 읽음.
                         없으면 DART 기능만 비활성화 (PyKRX/FDR은 정상 동작).
            cache_dir: 캐시 디렉토리. 기본값 ~/.cache/kr-stock-skills/
        """

    # ─────────────────────────────────────────
    # 시세 (Price)
    # ─────────────────────────────────────────

    def get_price(self, ticker: str) -> dict:
        """종목 현재가 (당일 종가 기준).

        Returns:
            {
                'ticker': '005930',
                'name': '삼성전자',
                'close': 72000,
                'open': 71500,
                'high': 72500,
                'low': 71000,
                'volume': 12345678,
                'change_pct': 1.41,
                'market_cap': 429760000000000,
                'date': '2026-02-27'
            }
        Source: PyKRX (T1)
        """

    def get_ohlcv(self, ticker: str, start: str, end: str = None,
                  freq: str = 'd') -> pd.DataFrame:
        """OHLCV 시계열 데이터.

        Args:
            ticker: 종목코드 (예: '005930') 또는 종목명 (예: '삼성전자')
            start: 시작일 'YYYY-MM-DD'
            end: 종료일. None이면 오늘.
            freq: 'd'=일봉, 'w'=주봉, 'm'=월봉, 'y'=연봉

        Returns:
            DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            index: DatetimeIndex

        Source: PyKRX (T1), FDR 폴백
        """

    def get_ohlcv_multi(self, tickers: list[str], start: str,
                        end: str = None) -> pd.DataFrame:
        """복수 종목 종가 비교 (Close만).

        Returns:
            DataFrame(columns=[ticker1, ticker2, ...])
        Source: FDR (T1) - 멀티 티커 지원
        """

    # ─────────────────────────────────────────
    # 밸류에이션 (Valuation)
    # ─────────────────────────────────────────

    def get_fundamentals(self, ticker: str, start: str = None,
                         end: str = None) -> pd.DataFrame:
        """PER/PBR/EPS/DIV/BPS 시계열.

        Returns:
            DataFrame(columns=['PER', 'PBR', 'EPS', 'DIV', 'BPS'])

        Source: PyKRX (T1)
        """

    def get_fundamentals_market(self, date: str,
                                market: str = 'KOSPI') -> pd.DataFrame:
        """전체 시장 밸류에이션 스냅샷 (특정일 기준).

        Returns:
            DataFrame(index=ticker, columns=['PER', 'PBR', 'EPS', 'DIV', 'BPS'])

        Source: PyKRX (T1)
        """

    def get_market_cap(self, ticker: str, start: str = None,
                       end: str = None) -> pd.DataFrame:
        """시가총액 시계열.

        Returns:
            DataFrame(columns=['MarketCap', 'Volume', 'TradingValue', 'ListedShares'])

        Source: PyKRX (T1)
        """

    # ─────────────────────────────────────────
    # 재무제표 (Financial Statements)
    # ─────────────────────────────────────────

    def get_financial_statements(self, ticker: str, year: int,
                                 report_type: str = 'annual') -> dict:
        """IFRS 재무제표.

        Args:
            report_type: 'annual', 'semi', 'q1', 'q3'

        Returns:
            {
                'income_statement': DataFrame,  # 손익계산서
                'balance_sheet': DataFrame,      # 재무상태표
                'cash_flow': DataFrame           # 현금흐름표
            }

        Source: DART (T1) - dart_api_key 필요
        Fallback: PyKRX financial ratios (부분적)
        """

    def get_financial_ratios(self, ticker: str) -> dict:
        """재무비율 요약.

        Returns:
            {
                'per': 12.5, 'pbr': 1.3, 'eps': 5760,
                'div_yield': 2.1, 'bps': 55000,
                'roe': 11.5, 'debt_ratio': 35.2,
                ...
            }

        Source: PyKRX + DART 조합
        """

    # ─────────────────────────────────────────
    # 투자자별 매매동향 (Investor Flow)
    # ─────────────────────────────────────────

    def get_investor_trading(self, ticker: str, start: str, end: str = None,
                             detail: bool = True) -> pd.DataFrame:
        """종목별 투자자 매매동향.

        Args:
            detail: True면 12분류 (금투/보험/투신/사모/은행/기타금융/연기금/기타법인/외국인/개인/기타외국인)
                    False면 3분류 (기관/외국인/개인)

        Returns:
            DataFrame(columns=[투자자분류별 순매수금액])

        Source: PyKRX (T1)
        """

    def get_investor_trading_market(self, start: str, end: str = None,
                                    market: str = 'KOSPI') -> pd.DataFrame:
        """시장 전체 투자자별 매매동향.

        Source: PyKRX (T1)
        """

    def get_foreign_exhaustion(self, ticker: str = None,
                               date: str = None) -> pd.DataFrame:
        """외국인 한도소진율.

        ticker가 None이면 전 종목, 아니면 특정 종목 시계열.

        Returns (전 종목):
            DataFrame(index=ticker, columns=['ListedShares', 'ForeignLimit',
                      'ForeignHoldings', 'ExhaustionRate'])

        Source: PyKRX (T1)
        """

    def get_top_net_purchases(self, start: str, end: str = None,
                              market: str = 'KOSPI',
                              investor: str = '외국인') -> pd.DataFrame:
        """특정 투자자 순매수 상위 종목.

        Args:
            investor: '외국인', '기관합계', '개인', '연기금' 등

        Source: PyKRX (T1)
        """

    # ─────────────────────────────────────────
    # 공매도 (Short Selling)
    # ─────────────────────────────────────────

    def get_short_selling(self, ticker: str, start: str,
                          end: str = None) -> pd.DataFrame:
        """종목별 공매도 거래량/잔고 시계열.

        Returns:
            DataFrame(columns=['ShortVolume', 'ShortBalance', 'ShortBalanceRatio'])

        Source: PyKRX (T1)
        """

    def get_short_top50(self, date: str,
                        by: str = 'balance') -> pd.DataFrame:
        """공매도 상위 50 종목.

        Args:
            by: 'balance' (잔고비율) 또는 'trade' (거래비율)

        Source: PyKRX (T1)
        """

    # ─────────────────────────────────────────
    # 지수 & 업종 (Index & Sector)
    # ─────────────────────────────────────────

    def get_index(self, index_code: str, start: str,
                  end: str = None) -> pd.DataFrame:
        """지수 OHLCV.

        주요 코드:
            KOSPI='0001', KOSDAQ='1001', KOSPI200='0028',
            KRX300='0043', KOSDAQ150='0177'

        Source: PyKRX (T1)
        """

    def get_index_fundamentals(self, index_code: str, start: str,
                               end: str = None) -> pd.DataFrame:
        """지수 PER/PBR/배당수익률.

        Source: PyKRX (T1)
        """

    def get_index_constituents(self, index_code: str) -> list[str]:
        """지수 구성종목 리스트.

        Source: PyKRX (T1)
        """

    def get_sector_performance(self, start: str,
                               end: str = None) -> pd.DataFrame:
        """업종별 수익률 비교.

        Returns:
            DataFrame(index=업종명, columns=['Close', 'Change%', ...])

        Source: PyKRX 업종지수 (T1)
        """

    # ─────────────────────────────────────────
    # 글로벌 & 매크로 (Global & Macro)
    # ─────────────────────────────────────────

    def get_global_index(self, symbol: str, start: str,
                         end: str = None) -> pd.DataFrame:
        """글로벌 지수/환율/원자재.

        주요 심볼:
            'KS11'=코스피, 'KQ11'=코스닥, 'DJI'=다우,
            'IXIC'=나스닥, 'US500'=S&P500, 'N225'=니케이,
            'USD/KRW'=원달러, 'CL=F'=WTI유가, 'GC=F'=금

        Source: FDR (T1)
        """

    def get_fred(self, series_id: str, start: str = None) -> pd.DataFrame:
        """FRED 경제지표.

        주요 시리즈: 'M2', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS'

        Source: FDR (T1)
        """

    def get_bond_yields(self, date: str = None) -> pd.DataFrame:
        """한국 국채/회사채 수익률.

        Returns:
            DataFrame(columns=['국고채1Y', '국고채3Y', '국고채5Y', '국고채10Y',
                               '국고채20Y', '국고채30Y', '회사채AA-', '회사채BBB-'])

        Source: PyKRX bond (T1)
        """

    def get_us_treasury(self, start: str, end: str = None) -> pd.DataFrame:
        """미국 국채 수익률.

        Source: FDR (T1)
        """

    # ─────────────────────────────────────────
    # ETF
    # ─────────────────────────────────────────

    def get_etf_list(self, date: str = None) -> list[str]:
        """한국 ETF 전체 목록.

        Source: PyKRX (T1)
        """

    def get_etf_nav(self, ticker: str, start: str,
                    end: str = None) -> pd.DataFrame:
        """ETF NAV/괴리율/추적오차.

        Returns:
            DataFrame(columns=['Close', 'NAV', 'DeviationRate', 'TrackingError'])

        Source: PyKRX (T1)
        """

    def get_etf_holdings(self, ticker: str) -> pd.DataFrame:
        """ETF 구성종목 및 비중.

        Source: PyKRX (T1)
        """

    # ─────────────────────────────────────────
    # 공시 (Disclosure)
    # ─────────────────────────────────────────

    def get_disclosures(self, ticker: str = None, start: str = None,
                        end: str = None, kind: str = None) -> pd.DataFrame:
        """DART 공시 목록.

        Args:
            kind: 'A'=정기보고서, 'B'=주요사항, 'C'=발행공시, 'D'=지분공시, 'E'=기타

        Source: DART (T1)
        """

    def get_major_shareholders(self, ticker: str) -> pd.DataFrame:
        """5% 대량보유자 현황.

        Source: DART (T1)
        """

    def get_dividend_info(self, ticker: str, year: int = None) -> dict:
        """배당 정보.

        Returns:
            {
                'dividend_per_share': 1444,
                'dividend_yield': 2.0,
                'payout_ratio': 25.1,
                'ex_date': '2025-12-30',
                'pay_date': '2026-04-20'
            }

        Source: DART (T1), PyKRX DIV 폴백
        """

    # ─────────────────────────────────────────
    # 종목 검색 & 유틸 (Search & Utils)
    # ─────────────────────────────────────────

    def search(self, keyword: str) -> list[dict]:
        """종목명/코드 검색.

        Returns:
            [{'ticker': '005930', 'name': '삼성전자', 'market': 'KOSPI'}, ...]

        Source: PyKRX + FDR (T1)
        """

    def get_ticker_list(self, market: str = 'ALL') -> pd.DataFrame:
        """전체 종목 목록.

        Args:
            market: 'KOSPI', 'KOSDAQ', 'ALL'

        Returns:
            DataFrame(columns=['ticker', 'name', 'market', 'sector', 'industry'])

        Source: FDR StockListing (T1)
        """

    def resolve_ticker(self, name_or_code: str) -> str:
        """종목명 → 종목코드 변환.

        '삼성전자' → '005930'
        '005930' → '005930' (이미 코드면 그대로)
        """

    def is_trading_day(self, date: str) -> bool:
        """해당 일자가 영업일인지 확인.

        Source: PyKRX chk_holiday (T1)
        """

    def get_recent_trading_day(self) -> str:
        """가장 최근 영업일 반환."""
```

---

## 3. Provider 상세 설계

### 3.1 pykrx_provider.py

PyKRX 라이브러리의 얇은 래퍼. 날짜 형식 변환과 에러 핸들링 담당.

```python
class PyKRXProvider:
    """PyKRX 데이터 프로바이더.

    PyKRX는 YYYYMMDD 문자열 형식을 요구하므로
    YYYY-MM-DD → YYYYMMDD 변환을 자동 처리.
    """

    # 날짜 변환
    @staticmethod
    def _to_krx_date(date_str: str) -> str:
        """'2026-02-27' → '20260227'"""

    # 시세
    def get_market_ohlcv_by_ticker(self, date: str, market: str) -> DataFrame
    def get_market_ohlcv_by_date(self, start, end, ticker, freq) -> DataFrame

    # 밸류에이션
    def get_market_fundamental_by_ticker(self, date, market) -> DataFrame
    def get_market_fundamental_by_date(self, start, end, ticker) -> DataFrame

    # 시가총액
    def get_market_cap_by_ticker(self, date, market) -> DataFrame
    def get_market_cap_by_date(self, start, end, ticker) -> DataFrame

    # 투자자 매매동향
    def get_trading_value_by_date(self, start, end, ticker, detail) -> DataFrame
    def get_trading_volume_by_date(self, start, end, ticker, detail) -> DataFrame
    def get_trading_by_investor(self, start, end, ticker) -> DataFrame
    def get_net_purchases(self, start, end, market, investor) -> DataFrame
    def get_foreign_exhaustion(self, date=None, market=None,
                               ticker=None, start=None, end=None) -> DataFrame

    # 공매도
    def get_shorting_by_date(self, start, end, ticker) -> DataFrame
    def get_shorting_balance_top50(self, date, market) -> DataFrame
    def get_shorting_trade_top50(self, date, market) -> DataFrame

    # 지수
    def get_index_ohlcv(self, start, end, ticker, freq) -> DataFrame
    def get_index_fundamental(self, start, end, ticker) -> DataFrame
    def get_index_constituents(self, ticker) -> list
    def get_index_ticker_list(self, date, market) -> list

    # ETF
    def get_etf_ohlcv(self, start, end, ticker) -> DataFrame
    def get_etf_holdings(self, ticker, date) -> DataFrame
    def get_etf_deviation(self, start, end, ticker) -> DataFrame

    # 채권
    def get_bond_yields(self, date) -> DataFrame
    def get_bond_yields_series(self, start, end, bond_type) -> DataFrame

    # 유틸
    def get_ticker_list(self, date, market) -> list
    def get_ticker_name(self, ticker) -> str
```

### 3.2 fdr_provider.py

FinanceDataReader 래퍼. 글로벌 데이터와 한국 시장 데이터 동시 지원.

```python
class FDRProvider:
    """FinanceDataReader 데이터 프로바이더.

    글로벌 시세, 환율, 원자재, FRED 경제지표 전담.
    한국 주식 OHLCV는 PyKRX의 폴백으로만 사용.
    """

    # 시세 (한국 + 글로벌)
    def get_data(self, symbol, start, end=None) -> DataFrame
    def get_data_multi(self, symbols: list, start, end=None) -> DataFrame

    # 종목 목록
    def get_stock_listing(self, market) -> DataFrame  # KOSPI/KOSDAQ/KRX
    def get_stock_listing_desc(self, market) -> DataFrame  # 업종/산업 포함

    # 지수 구성
    def get_index_constituents(self, index_code) -> DataFrame

    # 심볼 매핑
    KR_INDEX_MAP = {
        'KOSPI': 'KS11', 'KOSDAQ': 'KQ11', 'KOSPI200': 'KS200',
    }
    GLOBAL_INDEX_MAP = {
        'S&P500': 'US500', 'NASDAQ': 'IXIC', 'DOW': 'DJI',
        'NIKKEI': 'N225', 'SHANGHAI': '000001.SS',
    }
```

### 3.3 dart_provider.py

OpenDartReader 래퍼. DART API 키가 없으면 graceful하게 비활성화.

```python
class DARTProvider:
    """DART 전자공시 데이터 프로바이더.

    dart_api_key가 없으면 초기화 시 warning 로그만 남기고
    모든 메서드는 None 또는 빈 DataFrame을 반환.
    """

    def __init__(self, api_key: str = None):
        """api_key가 None이면 DART_API_KEY 환경변수에서 읽음.
        둘 다 없으면 self.available = False로 설정."""

    @property
    def available(self) -> bool:
        """DART 기능 사용 가능 여부."""

    # 재무제표
    def get_financial_statements(self, corp, year, report_type) -> dict
    def get_financial_statements_all(self, corp, year) -> DataFrame

    # 공시
    def get_disclosure_list(self, corp=None, start=None,
                            end=None, kind=None) -> DataFrame
    def get_company_info(self, corp) -> dict

    # 지분
    def get_major_shareholders(self, corp) -> DataFrame
    def get_executive_shareholding(self, corp) -> DataFrame

    # 배당
    def get_dividend_info(self, corp, year) -> dict

    # 기업검색
    def search_company(self, name) -> list[dict]
    def resolve_corp_code(self, ticker_or_name) -> str
```

### 3.4 kis_provider.py (Tier 2 - 선택)

한투 API 래퍼. 설치/설정되지 않으면 자동 비활성화.

```python
class KISProvider:
    """한국투자증권 Open API 프로바이더 (Tier 2 - 선택적).

    python-kis 미설치 또는 환경변수 미설정 시 자동 비활성화.
    Tier 1 스킬은 이 Provider 없이도 정상 동작.
    """

    def __init__(self):
        """python-kis import 시도. 실패하면 self.available = False."""

    @property
    def available(self) -> bool

    # 실시간 시세 (Tier 2 전용)
    def get_realtime_price(self, ticker) -> dict
    def get_minute_chart(self, ticker, period='1') -> DataFrame  # 분봉
    def get_orderbook(self, ticker) -> dict  # 호가

    # 주문 (Tier 2 전용)
    def get_balance(self) -> DataFrame  # 잔고
    def get_available_amount(self, ticker) -> dict
```

---

## 4. Utils 모듈 설계

### 4.1 cache.py - 파일 기반 캐시

```python
class FileCache:
    """일별 데이터 캐시.

    크롤링 부하 최소화를 위해 동일 데이터 반복 호출 방지.
    캐시 키: {method}_{args_hash}_{date}
    저장 형식: pickle (DataFrame용)
    기본 TTL: 당일 데이터 = 장 마감 후까지, 과거 데이터 = 영구
    """

    def __init__(self, cache_dir: str = '~/.cache/kr-stock-skills/'):
        ...

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 조회. 없거나 만료되면 None."""

    def set(self, key: str, value: Any, ttl: str = 'eod'):
        """캐시 저장.
        ttl: 'eod' (장마감까지), 'permanent' (영구), 초 단위 int
        """

    def invalidate(self, pattern: str = None):
        """캐시 삭제. pattern이 None이면 전체 삭제."""

    def cache_decorator(self, ttl: str = 'eod'):
        """메서드 데코레이터 버전."""
```

### 4.2 date_utils.py - 날짜 유틸리티

```python
def today() -> str:
    """오늘 날짜 'YYYY-MM-DD'."""

def to_krx_format(date_str: str) -> str:
    """'YYYY-MM-DD' → 'YYYYMMDD'."""

def from_krx_format(date_str: str) -> str:
    """'YYYYMMDD' → 'YYYY-MM-DD'."""

def get_recent_trading_day(date_str: str = None) -> str:
    """가장 최근 영업일. 주말/공휴일이면 직전 금요일."""

def get_n_days_ago(n: int, from_date: str = None) -> str:
    """n 영업일 전 날짜."""

def date_range(start: str, end: str) -> list[str]:
    """영업일 목록."""
```

### 4.3 ticker_utils.py - 종목코드 유틸리티

```python
# 종목코드 ↔ 종목명 캐시 (세션 시작 시 1회 로드)
_TICKER_CACHE: dict = {}

def name_to_ticker(name: str) -> str:
    """'삼성전자' → '005930'. 못 찾으면 ValueError."""

def ticker_to_name(ticker: str) -> str:
    """'005930' → '삼성전자'."""

def resolve(name_or_code: str) -> str:
    """종목명이든 코드든 → 코드로 변환."""

def is_valid_ticker(code: str) -> bool:
    """유효한 종목코드인지 확인 (6자리 숫자)."""

def get_market(ticker: str) -> str:
    """종목의 시장 반환: 'KOSPI' 또는 'KOSDAQ'."""
```

### 4.4 ta_utils.py - 기술적 분석 유틸리티

스킬별 별도 구현 없이 공통으로 사용할 기술 지표 계산기.

```python
def sma(series: pd.Series, period: int) -> pd.Series:
    """단순이동평균."""

def ema(series: pd.Series, period: int) -> pd.Series:
    """지수이동평균."""

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index)."""

def macd(series: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """MACD. columns=['MACD', 'Signal', 'Histogram']"""

def bollinger_bands(series: pd.Series, period=20, std=2) -> pd.DataFrame:
    """볼린저밴드. columns=['Upper', 'Middle', 'Lower']"""

def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """ATR (Average True Range)."""

def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """거래량 비율 (현재 / 평균)."""

def disparity(close: pd.Series, period: int = 20) -> pd.Series:
    """이격도 (현재가 / 이동평균 * 100)."""

def stochastic(high, low, close, k_period=14, d_period=3) -> pd.DataFrame:
    """스토캐스틱. columns=['%K', '%D']"""
```

---

## 5. 설정 (config.py)

```python
import os
from dataclasses import dataclass

@dataclass
class KRConfig:
    """환경 설정."""

    # Tier 1
    dart_api_key: str = os.getenv('DART_API_KEY', '')
    ecos_api_key: str = os.getenv('ECOS_API_KEY', '')

    # Tier 2 (선택)
    kis_app_key: str = os.getenv('KIS_APP_KEY', '')
    kis_app_secret: str = os.getenv('KIS_APP_SECRET', '')
    kis_account_no: str = os.getenv('KIS_ACCOUNT_NO', '')
    kis_mode: str = os.getenv('KIS_MODE', 'paper')

    # 캐시
    cache_dir: str = os.path.expanduser('~/.cache/kr-stock-skills/')
    cache_enabled: bool = True

    # 크롤링 보호
    request_delay: float = 0.5   # 연속 호출 시 최소 간격 (초)
    max_retries: int = 3         # 실패 시 재시도 횟수

    @property
    def dart_available(self) -> bool:
        return bool(self.dart_api_key)

    @property
    def kis_available(self) -> bool:
        return bool(self.kis_app_key and self.kis_app_secret)

    @property
    def tier(self) -> int:
        """현재 사용 가능한 Tier."""
        return 2 if self.kis_available else 1
```

---

## 6. 에러 핸들링 & 폴백 전략

### 6.1 폴백 체인

```
데이터 요청 → 1차 소스 시도 → 실패 시 폴백 소스 시도 → 실패 시 에러

예시:
get_ohlcv('005930') →
  1차: PyKRX.get_market_ohlcv() →
  폴백: FDR.DataReader('005930') →
  에러: DataNotAvailableError

get_financial_statements('005930') →
  1차: DART.finstate() →
  폴백: PyKRX.get_market_fundamental() (부분 데이터) →
  에러: DARTKeyNotSetError (키 없음 안내)
```

### 6.2 커스텀 예외

```python
class KRClientError(Exception):
    """기본 예외."""

class DataNotAvailableError(KRClientError):
    """데이터 없음 (종목 미존재, 기간 범위 초과 등)."""

class ProviderError(KRClientError):
    """특정 프로바이더 오류 (크롤링 차단, API 에러 등)."""

class DARTKeyNotSetError(KRClientError):
    """DART API 키 미설정. 안내 메시지 포함."""

class RateLimitError(KRClientError):
    """호출 빈도 초과."""
```

---

## 7. 스킬에서 사용하는 방법

### 7.1 스킬 스크립트에서의 임포트

각 스킬의 `scripts/` 디렉토리에서:

```python
import sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/_kr-common'))
from kr_client import KRClient

client = KRClient()  # 자동으로 Tier 1 구성

# 삼성전자 최근 1년 일봉
df = client.get_ohlcv('삼성전자', '2025-03-01')

# 외국인 순매수 상위
top = client.get_top_net_purchases('2026-02-01', investor='외국인')

# 재무제표 (DART 키 있을 때)
fs = client.get_financial_statements('005930', 2025)
```

### 7.2 SKILL.md에서의 안내

```yaml
---
name: kr-canslim-screener
description: KOSPI/KOSDAQ 종목 CANSLIM 스크리닝 (한국 시장 버전)
---

## Prerequisites
- `~/.claude/skills/_kr-common/` 공통 모듈 설치 필요
- `pip install pykrx finance-datareader opendartreader`
- (선택) DART_API_KEY 환경변수 설정
```

---

## 8. 구현 순서

| # | 파일 | 의존성 | 예상 시간 |
|---|------|--------|----------|
| 1 | `config.py` | 없음 | 30분 |
| 2 | `utils/date_utils.py` | 없음 | 30분 |
| 3 | `utils/ticker_utils.py` | pykrx | 30분 |
| 4 | `utils/cache.py` | 없음 | 45분 |
| 5 | `utils/ta_utils.py` | pandas, numpy | 1시간 |
| 6 | `providers/pykrx_provider.py` | pykrx, date_utils | 2시간 |
| 7 | `providers/fdr_provider.py` | finance-datareader | 1시간 |
| 8 | `providers/dart_provider.py` | opendartreader | 1.5시간 |
| 9 | `providers/kis_provider.py` | python-kis (선택) | 1시간 |
| 10 | `kr_client.py` | 모든 provider + utils | 2시간 |
| 11 | `models/*.py` | 없음 | 1시간 |
| 12 | `tests/*.py` | 전체 | 2시간 |

**총 예상**: ~13시간 (약 2일 작업)

---

## 9. 테스트 전략

### 9.1 단위 테스트

```python
# tests/test_kr_client.py

def test_get_price_samsung():
    """삼성전자 현재가 조회."""
    client = KRClient()
    price = client.get_price('005930')
    assert price['ticker'] == '005930'
    assert price['name'] == '삼성전자'
    assert price['close'] > 0

def test_get_ohlcv():
    """OHLCV 조회 - 일봉/주봉."""
    client = KRClient()
    df = client.get_ohlcv('005930', '2026-01-01', '2026-02-27')
    assert len(df) > 0
    assert 'Close' in df.columns

def test_get_fundamentals():
    """PER/PBR 밸류에이션."""
    client = KRClient()
    df = client.get_fundamentals('005930', '2026-01-01', '2026-02-27')
    assert 'PER' in df.columns
    assert 'PBR' in df.columns

def test_get_investor_trading():
    """투자자별 매매동향."""
    client = KRClient()
    df = client.get_investor_trading('005930', '2026-02-01', '2026-02-27')
    assert len(df) > 0

def test_resolve_ticker():
    """종목명 → 코드 변환."""
    client = KRClient()
    assert client.resolve_ticker('삼성전자') == '005930'
    assert client.resolve_ticker('005930') == '005930'

def test_dart_fallback():
    """DART 키 없을 때 graceful fallback."""
    client = KRClient(dart_api_key='')
    # 재무제표는 None 반환 (에러 아님)
    fs = client.get_financial_statements('005930', 2025)
    assert fs is None or isinstance(fs, dict)

def test_short_selling():
    """공매도 데이터 조회."""
    client = KRClient()
    df = client.get_short_selling('005930', '2026-02-01')
    assert len(df) >= 0  # 공매도 금지 기간일 수 있음
```

### 9.2 통합 테스트 (수동)

```bash
# 전체 기능 확인 스크립트
python3 ~/.claude/skills/_kr-common/tests/test_kr_client.py -v

# 개별 프로바이더 테스트
python3 -m pytest ~/.claude/skills/_kr-common/tests/ -v --tb=short
```

---

## 10. 성공 기준

| 기준 | 목표 |
|------|------|
| 시세 조회 | KOSPI/KOSDAQ 전 종목 OHLCV 조회 가능 |
| 밸류에이션 | PER/PBR/EPS/DIV 전 종목 조회 가능 |
| 투자자 매매 | 12분류 투자자별 매매동향 조회 가능 |
| 공매도 | 잔고/거래량 Top 50 조회 가능 |
| 재무제표 | DART 키 있을 때 BS/IS/CF 조회 가능 |
| 재무제표 없이 | DART 키 없어도 PyKRX/FDR 정상 동작 |
| 글로벌 | 주요 지수/환율/원자재 조회 가능 |
| 캐시 | 동일 데이터 재호출 시 캐시 히트 |
| 에러 처리 | 프로바이더 실패 시 폴백 동작 |
| 테스트 | 핵심 7개 테스트 케이스 통과 |

---

## 변경 이력

| 날짜 | 버전 | 작업 내용 | 관련 섹션 |
|------|------|----------|----------|
| 2026-02-27 | 1.0 | Phase 1 공통 모듈 상세 설계 작성 | 전체 |
