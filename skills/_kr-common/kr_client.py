"""한국 주식 시장 통합 데이터 클라이언트.

Tier 0 (최우선): KRX Open API (인증키 기반, 일 10,000회)
Tier 1 (무료): yfinance (Yahoo Finance, OHLCV+재무+밸류에이션)
Tier 2 (계좌 불필요): PyKRX + FinanceDataReader + OpenDartReader
Tier 3 (선택): 한국투자증권 Open API (실시간/분봉/주문)

Usage:
    from kr_client import KRClient
    client = KRClient()
    df = client.get_ohlcv('삼성전자', '2025-03-01')
"""

import logging
import pandas as pd

from .config import KRConfig, get_config
from .providers.krx_openapi_provider import KRXOpenAPIProvider, KRXOpenAPIError
from .providers.yfinance_provider import YFinanceProvider, YFinanceError
from .providers.pykrx_provider import PyKRXProvider
from .providers.fdr_provider import FDRProvider
from .providers.dart_provider import DARTProvider
from .providers.kis_provider import KISProvider
from .utils.cache import FileCache
from .utils import date_utils, ticker_utils

logger = logging.getLogger(__name__)


class KRClientError(Exception):
    """기본 예외."""


class DataNotAvailableError(KRClientError):
    """데이터 없음."""


class ProviderError(KRClientError):
    """프로바이더 오류."""


class DARTKeyNotSetError(KRClientError):
    """DART API 키 미설정."""


class RateLimitError(KRClientError):
    """호출 빈도 초과."""


class KRClient:
    """한국 주식 시장 통합 데이터 클라이언트."""

    def __init__(self, dart_api_key: str = None, cache_dir: str = None,
                 config: KRConfig = None):
        self._config = config or get_config()

        if dart_api_key is not None:
            self._config.dart_api_key = dart_api_key
        if cache_dir is not None:
            self._config.cache_dir = cache_dir

        # 프로바이더 초기화
        self._krx_api = KRXOpenAPIProvider(
            api_key=self._config.krx_api_key,
            request_delay=self._config.request_delay,
        ) if self._config.krx_available else None

        try:
            self._yfinance = YFinanceProvider()
        except YFinanceError:
            self._yfinance = None

        self._pykrx = PyKRXProvider(request_delay=self._config.request_delay)
        self._fdr = FDRProvider()
        self._dart = DARTProvider(api_key=self._config.dart_api_key)
        self._kis = KISProvider()

        # 캐시
        self._cache = FileCache(self._config.cache_dir) if self._config.cache_enabled else None

        providers = []
        if self._krx_api:
            providers.append("KRX-API")
        if self._yfinance:
            providers.append("yfinance")
        providers.append("PyKRX/FDR")
        logger.info(f"KRClient initialized (Tier {self._config.tier}, providers: {'+'.join(providers)})")

    @property
    def tier(self) -> int:
        return self._config.tier

    def _resolve(self, name_or_code: str) -> str:
        """종목명/코드 → 종목코드."""
        return ticker_utils.resolve(name_or_code)

    def _today(self) -> str:
        return date_utils.today()

    def _recent_day(self) -> str:
        return date_utils.get_recent_trading_day()

    def _cached(self, key: str, func, ttl: str = 'eod'):
        """캐시 래퍼. 캐시 비활성화 시 바로 실행."""
        if self._cache is None:
            return func()
        result = self._cache.get(key)
        if result is not None:
            logger.debug(f"Cache hit: {key}")
            return result
        result = func()
        if result is not None:
            self._cache.set(key, result, ttl=ttl)
        return result

    # ─────────────────────────────────────────
    # 시세 (Price)
    # ─────────────────────────────────────────

    def get_price(self, ticker: str) -> dict:
        """종목 현재가 (당일 종가 기준)."""
        ticker = self._resolve(ticker)
        date = self._recent_day()

        # Tier 0: KRX Open API (최우선)
        if self._krx_api:
            try:
                result = self._krx_api.get_stock_by_ticker(date, ticker)
                if result:
                    logger.info(f"KRX Open API: get_price({ticker}) OK")
                    return result
            except KRXOpenAPIError as e:
                logger.warning(f"KRX Open API failed, falling back to PyKRX: {e}")

        # Tier 1: yfinance 폴백
        if self._yfinance:
            try:
                market = ticker_utils.get_market(ticker)
                result = self._yfinance.get_price(ticker, market=market)
                if result and result.get('close'):
                    logger.info(f"yfinance: get_price({ticker}) OK")
                    return result
            except Exception as e:
                logger.warning(f"yfinance get_price failed: {e}")

        # Tier 2: PyKRX 폴백
        try:
            ohlcv = self._pykrx.get_market_ohlcv_by_date(date, date, ticker)
            cap = self._pykrx.get_market_cap_by_date(date, date, ticker)

            if ohlcv.empty:
                raise DataNotAvailableError(f"No price data for {ticker}")

            row = ohlcv.iloc[-1]
            name = ticker_utils.ticker_to_name(ticker)

            result = {
                'ticker': ticker,
                'name': name,
                'close': int(row.get('종가', row.get('Close', 0))),
                'open': int(row.get('시가', row.get('Open', 0))),
                'high': int(row.get('고가', row.get('High', 0))),
                'low': int(row.get('저가', row.get('Low', 0))),
                'volume': int(row.get('거래량', row.get('Volume', 0))),
                'change_pct': float(row.get('등락률', row.get('Change', 0))),
                'date': date,
            }

            if not cap.empty:
                cap_row = cap.iloc[-1]
                result['market_cap'] = int(cap_row.get('시가총액', cap_row.get('MarketCap', 0)))

            return result
        except KRClientError:
            raise
        except Exception as e:
            raise ProviderError(f"get_price failed: {e}") from e

    def get_ohlcv(self, ticker: str, start: str, end: str = None,
                  freq: str = 'd') -> pd.DataFrame:
        """OHLCV 시계열 데이터."""
        ticker = self._resolve(ticker)
        end = end or self._today()
        cache_key = f"ohlcv_{ticker}_{start}_{end}_{freq}"

        def _fetch():
            # Tier 1: yfinance (무료, 무제한)
            if self._yfinance:
                try:
                    market = ticker_utils.get_market(ticker)
                    df = self._yfinance.get_ohlcv(ticker, start, end, market=market)
                    if not df.empty:
                        logger.info(f"yfinance: get_ohlcv({ticker}) OK, {len(df)} rows")
                        return df
                except Exception as e:
                    logger.warning(f"yfinance OHLCV failed: {e}")

            # Tier 2: PyKRX
            try:
                df = self._pykrx.get_market_ohlcv_by_date(start, end, ticker, freq=freq)
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"PyKRX OHLCV failed, trying FDR: {e}")

            # Tier 2: FDR 폴백
            try:
                df = self._fdr.get_data(ticker, start, end)
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"FDR OHLCV fallback also failed: {e}")
            return pd.DataFrame()

        return self._cached(cache_key, _fetch)

    def get_ohlcv_multi(self, tickers: list, start: str,
                        end: str = None) -> pd.DataFrame:
        """복수 종목 종가 비교 (Close만)."""
        resolved = [self._resolve(t) for t in tickers]
        return self._fdr.get_data_multi(resolved, start, end)

    # ─────────────────────────────────────────
    # 밸류에이션 (Valuation)
    # ─────────────────────────────────────────

    def get_fundamentals(self, ticker: str, start: str = None,
                         end: str = None) -> pd.DataFrame:
        """PER/PBR/EPS/DIV/BPS 시계열."""
        ticker = self._resolve(ticker)
        if not start:
            start = date_utils.get_n_days_ago(90)
        end = end or self._today()
        cache_key = f"fund_{ticker}_{start}_{end}"

        def _fetch():
            return self._pykrx.get_market_fundamental_by_date(start, end, ticker)

        try:
            return self._cached(cache_key, _fetch)
        except Exception as e:
            raise ProviderError(f"get_fundamentals failed: {e}") from e

    def get_fundamentals_market(self, date: str,
                                market: str = 'KOSPI') -> pd.DataFrame:
        """전체 시장 밸류에이션 스냅샷."""
        # Tier 0: KRX Open API
        if self._krx_api:
            try:
                df = self._krx_api.get_stock_base_info(date)
                if not df.empty:
                    if market != 'ALL' and 'MKT_NM' in df.columns:
                        df = df[df['MKT_NM'].str.contains(market, na=False)]
                    logger.info(f"KRX Open API: get_fundamentals_market({date}) OK")
                    return df
            except KRXOpenAPIError as e:
                logger.warning(f"KRX Open API failed: {e}")

        try:
            return self._pykrx.get_market_fundamental_by_ticker(date, market=market)
        except Exception as e:
            raise ProviderError(f"get_fundamentals_market failed: {e}") from e

    def get_market_cap(self, ticker: str, start: str = None,
                       end: str = None) -> pd.DataFrame:
        """시가총액 시계열."""
        ticker = self._resolve(ticker)
        if not start:
            start = date_utils.get_n_days_ago(90)
        end = end or self._today()

        try:
            return self._pykrx.get_market_cap_by_date(start, end, ticker)
        except Exception as e:
            raise ProviderError(f"get_market_cap failed: {e}") from e

    # ─────────────────────────────────────────
    # 재무제표 (Financial Statements)
    # ─────────────────────────────────────────

    def get_financial_statements(self, ticker: str, year: int,
                                 report_type: str = 'annual') -> dict:
        """IFRS 재무제표."""
        ticker = self._resolve(ticker)

        # report_type 매핑
        type_map = {
            'annual': '11011', 'semi': '11012',
            'q1': '11013', 'q3': '11014',
        }
        dart_type = type_map.get(report_type, report_type)

        if self._dart.available:
            result = self._dart.get_financial_statements(ticker, year, dart_type)
            if result:
                return result

        # yfinance 폴백 (재무제표)
        if self._yfinance:
            try:
                market = ticker_utils.get_market(ticker)
                result = self._yfinance.get_financials(ticker, market=market)
                if result:
                    logger.info(f"yfinance: get_financial_statements({ticker}) OK")
                    return result
            except Exception as e:
                logger.warning(f"yfinance get_financials failed: {e}")

        logger.info("DART/yfinance unavailable, returning None")
        return None

    def get_financial_ratios(self, ticker: str) -> dict:
        """재무비율 요약."""
        ticker = self._resolve(ticker)
        date = self._recent_day()

        # Tier 0: KRX Open API
        if self._krx_api:
            try:
                result = self._krx_api.get_fundamentals_by_ticker(date, ticker)
                if result:
                    logger.info(f"KRX Open API: get_financial_ratios({ticker}) OK")
                    return result
            except KRXOpenAPIError as e:
                logger.warning(f"KRX Open API failed: {e}")

        # Tier 1: yfinance 폴백
        if self._yfinance:
            try:
                market = ticker_utils.get_market(ticker)
                result = self._yfinance.get_fundamentals(ticker, market=market)
                if result and (result.get('per') or result.get('pbr')):
                    logger.info(f"yfinance: get_financial_ratios({ticker}) OK")
                    return result
            except Exception as e:
                logger.warning(f"yfinance get_financial_ratios failed: {e}")

        # Tier 2: PyKRX 폴백
        try:
            fund = self._pykrx.get_market_fundamental_by_date(date, date, ticker)
            if fund.empty:
                return {}

            row = fund.iloc[-1]
            result = {
                'per': float(row.get('PER', 0)),
                'pbr': float(row.get('PBR', 0)),
                'eps': float(row.get('EPS', 0)),
                'div_yield': float(row.get('DIV', 0)),
                'bps': float(row.get('BPS', 0)),
            }
            return result
        except Exception as e:
            raise ProviderError(f"get_financial_ratios failed: {e}") from e

    # ─────────────────────────────────────────
    # 투자자별 매매동향 (Investor Flow)
    # ─────────────────────────────────────────

    def get_investor_trading(self, ticker: str, start: str, end: str = None,
                             detail: bool = True) -> pd.DataFrame:
        """종목별 투자자 매매동향."""
        ticker = self._resolve(ticker)
        end = end or self._today()
        cache_key = f"inv_{ticker}_{start}_{end}_{detail}"

        def _fetch():
            return self._pykrx.get_trading_value_by_date(
                start, end, ticker, detail=detail
            )

        try:
            return self._cached(cache_key, _fetch)
        except Exception as e:
            raise ProviderError(f"get_investor_trading failed: {e}") from e

    def get_investor_trading_market(self, start: str, end: str = None,
                                    market: str = 'KOSPI') -> pd.DataFrame:
        """시장 전체 투자자별 매매동향."""
        end = end or self._today()
        # 시장 전체는 대표 지수(KOSPI/KOSDAQ)로 조회
        index_map = {'KOSPI': '0001', 'KOSDAQ': '1001'}
        index_code = index_map.get(market, '0001')

        try:
            return self._pykrx.get_trading_value_by_date(
                start, end, index_code, detail=True
            )
        except Exception as e:
            raise ProviderError(f"get_investor_trading_market failed: {e}") from e

    def get_foreign_exhaustion(self, ticker: str = None,
                               date: str = None) -> pd.DataFrame:
        """외국인 한도소진율."""
        if ticker:
            ticker = self._resolve(ticker)
        date = date or self._recent_day()

        try:
            return self._pykrx.get_foreign_exhaustion(
                date=date, ticker=ticker
            )
        except Exception as e:
            raise ProviderError(f"get_foreign_exhaustion failed: {e}") from e

    def get_top_net_purchases(self, start: str, end: str = None,
                              market: str = 'KOSPI',
                              investor: str = '외국인') -> pd.DataFrame:
        """특정 투자자 순매수 상위 종목."""
        end = end or self._today()

        try:
            return self._pykrx.get_net_purchases(start, end, market, investor)
        except Exception as e:
            raise ProviderError(f"get_top_net_purchases failed: {e}") from e

    # ─────────────────────────────────────────
    # 공매도 (Short Selling)
    # ─────────────────────────────────────────

    def get_short_selling(self, ticker: str, start: str,
                          end: str = None) -> pd.DataFrame:
        """종목별 공매도 거래량/잔고 시계열."""
        ticker = self._resolve(ticker)
        end = end or self._today()

        try:
            return self._pykrx.get_shorting_by_date(start, end, ticker)
        except Exception as e:
            raise ProviderError(f"get_short_selling failed: {e}") from e

    def get_short_top50(self, date: str,
                        by: str = 'balance') -> pd.DataFrame:
        """공매도 상위 50 종목.

        Args:
            date: 조회일 (YYYY-MM-DD)
            by: 'balance' (잔고 기준) 또는 'trade' (거래량 기준)
        """
        try:
            if by == 'trade':
                return self._pykrx.get_shorting_trade_top50(date)
            return self._pykrx.get_shorting_balance_top50(date)
        except Exception as e:
            raise ProviderError(f"get_short_top50 failed: {e}") from e

    # ─────────────────────────────────────────
    # 지수 & 업종 (Index & Sector)
    # ─────────────────────────────────────────

    def get_index(self, index_code: str, start: str,
                  end: str = None) -> pd.DataFrame:
        """지수 OHLCV."""
        end = end or self._today()
        cache_key = f"index_{index_code}_{start}_{end}"

        def _fetch():
            return self._pykrx.get_index_ohlcv(start, end, index_code)

        try:
            return self._cached(cache_key, _fetch)
        except Exception as e:
            raise ProviderError(f"get_index failed: {e}") from e

    def get_index_fundamentals(self, index_code: str, start: str,
                               end: str = None) -> pd.DataFrame:
        """지수 PER/PBR/배당수익률."""
        end = end or self._today()

        try:
            return self._pykrx.get_index_fundamental(start, end, index_code)
        except Exception as e:
            raise ProviderError(f"get_index_fundamentals failed: {e}") from e

    def get_index_constituents(self, index_code: str) -> list:
        """지수 구성종목 리스트."""
        try:
            return self._pykrx.get_index_constituents(index_code)
        except Exception as e:
            raise ProviderError(f"get_index_constituents failed: {e}") from e

    def get_sector_performance(self, start: str,
                               end: str = None) -> pd.DataFrame:
        """업종별 수익률 비교."""
        end = end or self._today()

        try:
            # KOSPI 업종 지수 목록 가져오기
            indices = self._pykrx.get_index_ticker_list(market='KOSPI')
            results = {}
            for idx in indices[:20]:  # 상위 20개 업종
                try:
                    df = self._pykrx.get_index_ohlcv(start, end, idx)
                    if not df.empty:
                        name = idx  # 지수명
                        start_price = df.iloc[0].get('종가', df.iloc[0].get('Close', 0))
                        end_price = df.iloc[-1].get('종가', df.iloc[-1].get('Close', 0))
                        if start_price > 0:
                            change = ((end_price - start_price) / start_price) * 100
                            results[name] = {
                                'Close': end_price,
                                'Change%': round(change, 2),
                            }
                except Exception:
                    continue

            return pd.DataFrame(results).T if results else pd.DataFrame()
        except Exception as e:
            raise ProviderError(f"get_sector_performance failed: {e}") from e

    # ─────────────────────────────────────────
    # 글로벌 & 매크로 (Global & Macro)
    # ─────────────────────────────────────────

    def get_global_index(self, symbol: str, start: str,
                         end: str = None) -> pd.DataFrame:
        """글로벌 지수/환율/원자재."""
        return self._fdr.get_global_index(symbol, start, end)

    def get_fred(self, series_id: str, start: str = None) -> pd.DataFrame:
        """FRED 경제지표."""
        return self._fdr.get_fred(series_id, start)

    def get_bond_yields(self, date: str = None) -> pd.DataFrame:
        """한국 국채/회사채 수익률."""
        try:
            return self._pykrx.get_bond_yields(date)
        except Exception as e:
            raise ProviderError(f"get_bond_yields failed: {e}") from e

    def get_us_treasury(self, start: str,
                        end: str = None) -> pd.DataFrame:
        """미국 국채 수익률."""
        return self._fdr.get_us_treasury(start, end)

    # ─────────────────────────────────────────
    # ETF
    # ─────────────────────────────────────────

    def get_etf_list(self, date: str = None) -> list:
        """한국 ETF 전체 목록."""
        try:
            date = date or self._recent_day()
            return self._pykrx.get_ticker_list(date, market='ETF')
        except Exception as e:
            raise ProviderError(f"get_etf_list failed: {e}") from e

    def get_etf_nav(self, ticker: str, start: str,
                    end: str = None) -> pd.DataFrame:
        """ETF NAV/괴리율/추적오차."""
        end = end or self._today()

        try:
            return self._pykrx.get_etf_deviation(start, end, ticker)
        except Exception as e:
            raise ProviderError(f"get_etf_nav failed: {e}") from e

    def get_etf_holdings(self, ticker: str) -> pd.DataFrame:
        """ETF 구성종목 및 비중."""
        try:
            return self._pykrx.get_etf_holdings(ticker)
        except Exception as e:
            raise ProviderError(f"get_etf_holdings failed: {e}") from e

    # ─────────────────────────────────────────
    # 공시 (Disclosure)
    # ─────────────────────────────────────────

    def get_disclosures(self, ticker: str = None, start: str = None,
                        end: str = None, kind: str = None) -> pd.DataFrame:
        """DART 공시 목록."""
        if ticker:
            ticker = self._resolve(ticker)

        if not self._dart.available:
            logger.info("DART not available. Set DART_API_KEY environment variable.")
            return pd.DataFrame()

        return self._dart.get_disclosure_list(ticker, start, end, kind)

    def get_major_shareholders(self, ticker: str) -> pd.DataFrame:
        """5% 대량보유자 현황."""
        ticker = self._resolve(ticker)

        if not self._dart.available:
            return pd.DataFrame()

        return self._dart.get_major_shareholders(ticker)

    def get_dividend_info(self, ticker: str, year: int = None) -> dict:
        """배당 정보."""
        ticker = self._resolve(ticker)

        # DART 우선
        if self._dart.available:
            result = self._dart.get_dividend_info(ticker, year)
            if result:
                return result

        # PyKRX DIV 폴백
        try:
            date = self._recent_day()
            fund = self._pykrx.get_market_fundamental_by_date(date, date, ticker)
            if not fund.empty:
                row = fund.iloc[-1]
                return {
                    'dividend_yield': float(row.get('DIV', 0)),
                    'source': 'pykrx_fallback',
                }
        except Exception:
            pass

        return {}

    # ─────────────────────────────────────────
    # 종목 검색 & 유틸 (Search & Utils)
    # ─────────────────────────────────────────

    def search(self, keyword: str) -> list:
        """종목명/코드 검색."""
        return ticker_utils.search(keyword)

    def get_ticker_list(self, market: str = 'ALL') -> pd.DataFrame:
        """전체 종목 목록."""
        try:
            return self._fdr.get_stock_listing(market)
        except Exception as e:
            raise ProviderError(f"get_ticker_list failed: {e}") from e

    def resolve_ticker(self, name_or_code: str) -> str:
        """종목명 → 종목코드 변환."""
        return self._resolve(name_or_code)

    def is_trading_day(self, date: str) -> bool:
        """해당 일자가 영업일인지 확인."""
        try:
            ohlcv = self._pykrx.get_market_ohlcv_by_ticker(date, market='KOSPI')
            return not ohlcv.empty
        except Exception:
            return False

    def get_recent_trading_day(self) -> str:
        """가장 최근 영업일 반환."""
        return self._recent_day()
