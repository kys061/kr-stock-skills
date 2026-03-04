"""PyKRX 데이터 프로바이더.

PyKRX는 KRX(한국거래소) 크롤링 라이브러리.
날짜 형식: YYYYMMDD 문자열 요구 → 자동 변환 처리.
"""

import logging
import time
import pandas as pd

logger = logging.getLogger(__name__)

# PyKRX import
from pykrx import stock as krx_stock
from pykrx import bond as krx_bond


class PyKRXProvider:
    """PyKRX 데이터 프로바이더."""

    def __init__(self, request_delay: float = 0.5):
        self._delay = request_delay
        self._last_request = 0

    def _throttle(self):
        """연속 호출 방지."""
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    @staticmethod
    def _to_krx(date_str: str) -> str:
        """'YYYY-MM-DD' → 'YYYYMMDD'."""
        if date_str and '-' in date_str:
            return date_str.replace('-', '')
        return date_str

    # ─────────────────────────────────────────
    # 시세 (OHLCV)
    # ─────────────────────────────────────────

    def get_market_ohlcv_by_ticker(self, date: str, market: str = 'ALL') -> pd.DataFrame:
        """특정일 전체 종목 OHLCV."""
        self._throttle()
        return krx_stock.get_market_ohlcv_by_ticker(self._to_krx(date), market=market)

    def get_market_ohlcv_by_date(self, start: str, end: str, ticker: str,
                                  freq: str = 'd') -> pd.DataFrame:
        """종목별 OHLCV 시계열."""
        self._throttle()
        return krx_stock.get_market_ohlcv_by_date(
            self._to_krx(start), self._to_krx(end), ticker, freq=freq
        )

    # ─────────────────────────────────────────
    # 밸류에이션 (Fundamental)
    # ─────────────────────────────────────────

    def get_market_fundamental_by_ticker(self, date: str,
                                          market: str = 'ALL') -> pd.DataFrame:
        """특정일 전체 종목 PER/PBR/EPS/DIV/BPS."""
        self._throttle()
        return krx_stock.get_market_fundamental_by_ticker(
            self._to_krx(date), market=market
        )

    def get_market_fundamental_by_date(self, start: str, end: str,
                                        ticker: str) -> pd.DataFrame:
        """종목별 PER/PBR/EPS/DIV/BPS 시계열."""
        self._throttle()
        return krx_stock.get_market_fundamental_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    # ─────────────────────────────────────────
    # 시가총액 (Market Cap)
    # ─────────────────────────────────────────

    def get_market_cap_by_ticker(self, date: str,
                                  market: str = 'ALL') -> pd.DataFrame:
        """특정일 전체 종목 시가총액."""
        self._throttle()
        return krx_stock.get_market_cap_by_ticker(self._to_krx(date), market=market)

    def get_market_cap_by_date(self, start: str, end: str,
                                ticker: str) -> pd.DataFrame:
        """종목별 시가총액 시계열."""
        self._throttle()
        return krx_stock.get_market_cap_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    # ─────────────────────────────────────────
    # 투자자 매매동향 (Investor Trading)
    # ─────────────────────────────────────────

    def get_trading_value_by_date(self, start: str, end: str, ticker: str,
                                   detail: bool = True) -> pd.DataFrame:
        """종목별 투자자 매매동향 (금액 기준)."""
        self._throttle()
        if detail:
            return krx_stock.get_market_trading_value_by_date(
                self._to_krx(start), self._to_krx(end), ticker
            )
        else:
            return krx_stock.get_market_trading_value_by_date(
                self._to_krx(start), self._to_krx(end), ticker,
                on='순매수'
            )

    def get_trading_volume_by_date(self, start: str, end: str, ticker: str,
                                    detail: bool = True) -> pd.DataFrame:
        """종목별 투자자 매매동향 (수량 기준)."""
        self._throttle()
        return krx_stock.get_market_trading_volume_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    def get_net_purchases(self, start: str, end: str, market: str = 'KOSPI',
                          investor: str = '외국인') -> pd.DataFrame:
        """투자자 순매수 상위 종목."""
        self._throttle()
        return krx_stock.get_market_net_purchases_of_equities_by_ticker(
            self._to_krx(start), self._to_krx(end), market, investor
        )

    def get_foreign_exhaustion(self, date: str = None, market: str = 'ALL',
                                ticker: str = None, start: str = None,
                                end: str = None) -> pd.DataFrame:
        """외국인 한도소진율."""
        self._throttle()
        if ticker and start:
            # 특정 종목 시계열
            return krx_stock.get_exhaustion_rates_of_foreign_investment_by_date(
                self._to_krx(start),
                self._to_krx(end or start),
                ticker
            )
        elif date:
            # 전 종목 스냅샷
            return krx_stock.get_exhaustion_rates_of_foreign_investment_by_ticker(
                self._to_krx(date), market=market
            )
        return pd.DataFrame()

    # ─────────────────────────────────────────
    # 공매도 (Short Selling)
    # ─────────────────────────────────────────

    def get_shorting_by_date(self, start: str, end: str,
                              ticker: str) -> pd.DataFrame:
        """종목별 공매도 거래량 시계열."""
        self._throttle()
        return krx_stock.get_shorting_volume_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    def get_shorting_balance_top50(self, date: str,
                                    market: str = 'KOSPI') -> pd.DataFrame:
        """공매도 잔고 상위 50."""
        self._throttle()
        return krx_stock.get_shorting_volume_top50(
            self._to_krx(date), market
        )

    def get_shorting_trade_top50(self, date: str,
                                  market: str = 'KOSPI') -> pd.DataFrame:
        """공매도 거래량 상위 50."""
        self._throttle()
        return krx_stock.get_shorting_trading_value_by_date(
            self._to_krx(date), self._to_krx(date), market
        )

    # ─────────────────────────────────────────
    # 지수 (Index)
    # ─────────────────────────────────────────

    def get_index_ohlcv(self, start: str, end: str, ticker: str,
                         freq: str = 'd') -> pd.DataFrame:
        """지수 OHLCV."""
        self._throttle()
        return krx_stock.get_index_ohlcv_by_date(
            self._to_krx(start), self._to_krx(end), ticker, freq=freq
        )

    def get_index_fundamental(self, start: str, end: str,
                               ticker: str) -> pd.DataFrame:
        """지수 PER/PBR/배당수익률."""
        self._throttle()
        return krx_stock.get_index_fundamental_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    def get_index_constituents(self, ticker: str, date: str = None) -> list:
        """지수 구성종목 목록."""
        self._throttle()
        if date:
            return krx_stock.get_index_portfolio_deposit_file(
                self._to_krx(date), ticker
            )
        # date 미지정 시 최근 영업일
        from ..utils.date_utils import get_recent_trading_day
        recent = get_recent_trading_day()
        return krx_stock.get_index_portfolio_deposit_file(
            self._to_krx(recent), ticker
        )

    def get_index_ticker_list(self, date: str = None,
                               market: str = 'KOSPI') -> list:
        """지수 목록."""
        self._throttle()
        if not date:
            from ..utils.date_utils import get_recent_trading_day
            date = get_recent_trading_day()
        return krx_stock.get_index_ticker_list(self._to_krx(date), market)

    # ─────────────────────────────────────────
    # ETF
    # ─────────────────────────────────────────

    def get_etf_ohlcv(self, start: str, end: str,
                       ticker: str) -> pd.DataFrame:
        """ETF OHLCV."""
        self._throttle()
        return krx_stock.get_etf_ohlcv_by_date(
            self._to_krx(start), self._to_krx(end), ticker
        )

    def get_etf_holdings(self, ticker: str, date: str = None) -> pd.DataFrame:
        """ETF 구성종목."""
        self._throttle()
        if not date:
            from ..utils.date_utils import get_recent_trading_day
            date = get_recent_trading_day()
        return krx_stock.get_etf_portfolio_deposit_file(
            self._to_krx(date), ticker
        )

    def get_etf_deviation(self, start: str, end: str,
                           ticker: str) -> pd.DataFrame:
        """ETF 괴리율/추적오차."""
        self._throttle()
        return krx_stock.get_etf_tracking_error(
            self._to_krx(start), self._to_krx(end), ticker
        )

    # ─────────────────────────────────────────
    # 채권 (Bond)
    # ─────────────────────────────────────────

    def get_bond_yields(self, date: str = None) -> pd.DataFrame:
        """채권 수익률."""
        self._throttle()
        if not date:
            from ..utils.date_utils import get_recent_trading_day
            date = get_recent_trading_day()
        return krx_bond.get_otc_treasury_yields(self._to_krx(date))

    def get_bond_yields_series(self, start: str, end: str,
                                bond_type: str = '국고채3년') -> pd.DataFrame:
        """채권 수익률 시계열."""
        self._throttle()
        return krx_bond.get_otc_treasury_yields_by_date(
            self._to_krx(start), self._to_krx(end), bond_type
        )

    # ─────────────────────────────────────────
    # 유틸 (Utils)
    # ─────────────────────────────────────────

    def get_ticker_list(self, date: str = None,
                         market: str = 'ALL') -> list:
        """종목 목록."""
        self._throttle()
        if not date:
            from ..utils.date_utils import get_recent_trading_day
            date = get_recent_trading_day()
        return krx_stock.get_market_ticker_list(self._to_krx(date), market=market)

    def get_ticker_name(self, ticker: str) -> str:
        """종목명 조회."""
        return krx_stock.get_market_ticker_name(ticker)
