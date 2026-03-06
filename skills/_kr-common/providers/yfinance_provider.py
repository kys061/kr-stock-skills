"""yfinance 데이터 프로바이더.

Yahoo Finance 비공식 API (yfinance 라이브러리).
한국 종목: KOSPI → .KS, KOSDAQ → .KQ 접미사 사용.
무료, 호출 제한 없음, OHLCV + 재무제표 + 기본 밸류에이션 제공.

주의: 투자자별 매매동향, 공매도 데이터는 미제공.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False
    logger.warning("yfinance not installed. Run: pip install yfinance")


class YFinanceError(Exception):
    """yfinance 프로바이더 오류."""


class YFinanceProvider:
    """yfinance 데이터 프로바이더."""

    # 시장별 접미사 매핑
    MARKET_SUFFIX = {
        'KOSPI': '.KS',
        'KOSDAQ': '.KQ',
    }

    def __init__(self):
        if not _YF_AVAILABLE:
            raise YFinanceError("yfinance package not installed")

    @property
    def available(self) -> bool:
        return _YF_AVAILABLE

    def _to_yf_ticker(self, ticker: str, market: str = None) -> str:
        """6자리 코드 → yfinance 심볼 (005930 → 005930.KS)."""
        if '.' in ticker:
            return ticker

        if market:
            suffix = self.MARKET_SUFFIX.get(market, '.KS')
            return f"{ticker}{suffix}"

        # 시장 미지정 시 .KS 먼저 시도
        return f"{ticker}.KS"

    def _try_both_markets(self, ticker: str) -> Optional['yf.Ticker']:
        """KS/KQ 둘 다 시도하여 유효한 Ticker 반환."""
        for suffix in ['.KS', '.KQ']:
            yf_ticker = f"{ticker}{suffix}"
            try:
                t = yf.Ticker(yf_ticker)
                hist = t.history(period='1d')
                if not hist.empty:
                    return t
            except Exception:
                continue
        return None

    # ─────────────────────────────────────────
    # 시세 (Price)
    # ─────────────────────────────────────────

    def get_price(self, ticker: str, market: str = None) -> Optional[dict]:
        """종목 현재가."""
        t = self._get_ticker(ticker, market)
        if t is None:
            return None

        try:
            fi = t.fast_info
            info = t.info

            result = {
                'ticker': ticker,
                'name': info.get('shortName', ticker),
                'close': int(fi.last_price) if fi.last_price else 0,
                'market_cap': int(fi.market_cap) if fi.market_cap else 0,
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'currency': getattr(fi, 'currency', 'KRW'),
                'source': 'yfinance',
            }
            return result
        except Exception as e:
            logger.warning(f"yfinance get_price failed for {ticker}: {e}")
            return None

    def get_ohlcv(self, ticker: str, start: str, end: str = None,
                  market: str = None) -> pd.DataFrame:
        """OHLCV 시계열."""
        t = self._get_ticker(ticker, market)
        if t is None:
            return pd.DataFrame()

        try:
            hist = t.history(start=start, end=end)
            if hist.empty:
                return pd.DataFrame()

            # 컬럼명 표준화 (PyKRX 호환)
            df = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.columns = ['시가', '고가', '저가', '종가', '거래량']
            return df
        except Exception as e:
            logger.warning(f"yfinance get_ohlcv failed for {ticker}: {e}")
            return pd.DataFrame()

    def get_fundamentals(self, ticker: str,
                         market: str = None) -> Optional[dict]:
        """밸류에이션 지표 (PER/PBR/EPS/BPS/배당)."""
        t = self._get_ticker(ticker, market)
        if t is None:
            return None

        try:
            info = t.info
            return {
                'ticker': ticker,
                'per': info.get('trailingPE', 0) or 0,
                'forward_per': info.get('forwardPE', 0) or 0,
                'pbr': info.get('priceToBook', 0) or 0,
                'eps': info.get('trailingEps', 0) or 0,
                'bps': info.get('bookValue', 0) or 0,
                'div_yield': (info.get('dividendYield', 0) or 0) * 100,
                'roe': (info.get('returnOnEquity', 0) or 0) * 100,
                'debt_to_equity': info.get('debtToEquity', 0) or 0,
                'revenue': info.get('totalRevenue', 0) or 0,
                'operating_margin': (info.get('operatingMargins', 0) or 0) * 100,
                'profit_margin': (info.get('profitMargins', 0) or 0) * 100,
                'source': 'yfinance',
            }
        except Exception as e:
            logger.warning(f"yfinance get_fundamentals failed: {e}")
            return None

    def get_financials(self, ticker: str,
                       market: str = None) -> Optional[dict]:
        """재무제표 (매출/영업이익/순이익)."""
        t = self._get_ticker(ticker, market)
        if t is None:
            return None

        try:
            fin = t.financials
            if fin is None or fin.empty:
                return None

            # 최근 연도 데이터
            latest = fin.iloc[:, 0]
            result = {
                'ticker': ticker,
                'period': str(fin.columns[0].date()) if hasattr(fin.columns[0], 'date') else str(fin.columns[0]),
                'total_revenue': self._safe_int(latest, 'Total Revenue'),
                'operating_income': self._safe_int(latest, 'Operating Income'),
                'net_income': self._safe_int(latest, 'Net Income'),
                'ebitda': self._safe_int(latest, 'EBITDA'),
                'gross_profit': self._safe_int(latest, 'Gross Profit'),
                'source': 'yfinance',
            }
            return result
        except Exception as e:
            logger.warning(f"yfinance get_financials failed: {e}")
            return None

    # ─────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────

    def _get_ticker(self, ticker: str, market: str = None) -> Optional['yf.Ticker']:
        """yf.Ticker 인스턴스 반환. 지정 시장 실패 시 반대쪽도 시도."""
        if '.' in ticker:
            t = yf.Ticker(ticker)
            try:
                if not t.history(period='1d').empty:
                    return t
            except Exception:
                pass
            # .KQ 실패 → .KS, .KS 실패 → .KQ
            alt = ticker.replace('.KQ', '.KS') if '.KQ' in ticker else ticker.replace('.KS', '.KQ')
            if alt != ticker:
                logger.info(f"yfinance fallback: {ticker} → {alt}")
                return yf.Ticker(alt)
            return t

        if market:
            yf_sym = self._to_yf_ticker(ticker, market)
            t = yf.Ticker(yf_sym)
            try:
                if not t.history(period='1d').empty:
                    return t
            except Exception:
                pass
            # 지정 시장 실패 → 반대쪽 시도
            logger.info(f"yfinance: {yf_sym} empty, trying other market")
            return self._try_both_markets(ticker)

        # 시장 미지정 → 양쪽 시도
        return self._try_both_markets(ticker)

    @staticmethod
    def _safe_int(series: pd.Series, key: str) -> int:
        """Series에서 안전하게 int 추출."""
        try:
            val = series.get(key, 0)
            if pd.isna(val):
                return 0
            return int(val)
        except (ValueError, TypeError):
            return 0
