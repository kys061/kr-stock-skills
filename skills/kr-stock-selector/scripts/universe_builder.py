"""유니버스 구축 모듈.

KRX Open API로 시가총액 >= 1,000억원 종목을 필터링하고,
yfinance 배치 다운로드로 OHLCV 데이터를 수집한다.

폴백 전략:
  - 유니버스: KRX Open API → yfinance (시총 상위 종목)
  - OHLCV: yfinance batch → 개별 yfinance → pykrx
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'references', 'selector_config.json'
)

# 시장별 yfinance 접미사
MARKET_SUFFIX = {'KOSPI': '.KS', 'KOSDAQ': '.KQ'}


def load_config() -> dict:
    """selector_config.json 로드."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def to_yf_ticker(ticker: str, market: str) -> str:
    """종목코드 -> yfinance 티커 변환.

    '005930' + 'KOSPI' -> '005930.KS'
    '035720' + 'KOSDAQ' -> '035720.KQ'
    """
    suffix = MARKET_SUFFIX.get(market, '.KS')
    return f"{ticker}{suffix}"


def build_universe(
    provider=None,
    date: str = None,
    market: str = None,
    min_market_cap: int = None,
) -> list[dict]:
    """시가총액 기준 유니버스 구축.

    Args:
        provider: KRXOpenAPIProvider 인스턴스 (None이면 폴백)
        date: 기준일 'YYYY-MM-DD' (기본: 최근 거래일)
        market: 'KOSPI', 'KOSDAQ', None(전체)
        min_market_cap: 최소 시가총액 (원). 기본값 config에서 로드.

    Returns:
        list[UniverseStock] -- 시총 필터 통과 종목 리스트
    """
    config = load_config()
    if min_market_cap is None:
        min_market_cap = config['conditions']['market_cap']['min_krw']

    if date is None:
        date = _get_latest_trading_date()

    # 1차: KRX Open API
    if provider is not None:
        try:
            universe = _build_from_krx(provider, date, market, min_market_cap)
            if universe:
                logger.info(f"KRX API: {len(universe)}개 종목 (시총 >= {min_market_cap/1e8:.0f}억)")
                return universe
        except Exception as e:
            logger.warning(f"KRX API 실패: {e}, yfinance 폴백 시도")

    # 2차: yfinance 폴백
    try:
        universe = _build_from_yfinance(market, min_market_cap)
        if universe:
            logger.info(f"yfinance 폴백: {len(universe)}개 종목")
            return universe
    except Exception as e:
        logger.warning(f"yfinance 폴백 실패: {e}")

    return []


def _get_latest_trading_date() -> str:
    """최근 거래일 반환 (주말/공휴일 보정)."""
    today = datetime.now()
    # 주말이면 금요일로
    weekday = today.weekday()
    if weekday == 5:  # 토요일
        today -= timedelta(days=1)
    elif weekday == 6:  # 일요일
        today -= timedelta(days=2)
    return today.strftime('%Y-%m-%d')


def _build_from_krx(
    provider,
    date: str,
    market: str,
    min_market_cap: int,
) -> list[dict]:
    """KRX Open API로 유니버스 구축."""
    df = provider.get_stock_daily(date, market=market)
    if df.empty:
        return []

    # 시가총액 필터
    df = df[df['MKTCAP'] >= min_market_cap].copy()
    if df.empty:
        return []

    universe = []
    for _, row in df.iterrows():
        ticker = str(row.get('ISU_CD', '')).strip()
        if not ticker or len(ticker) != 6:
            continue

        mkt = _detect_market(row)
        stock = {
            'ticker': ticker,
            'name': str(row.get('ISU_NM', '')).strip(),
            'market': mkt,
            'market_cap': int(row.get('MKTCAP', 0)),
            'yf_ticker': to_yf_ticker(ticker, mkt),
            'close': int(row.get('TDD_CLSPRC', 0)),
        }
        universe.append(stock)

    return universe


def _detect_market(row) -> str:
    """DataFrame 행에서 시장 구분."""
    mkt = str(row.get('MKT_NM', '')).strip()
    if 'KOSDAQ' in mkt.upper():
        return 'KOSDAQ'
    return 'KOSPI'


def _build_from_yfinance(
    market: str,
    min_market_cap: int,
) -> list[dict]:
    """yfinance 폴백으로 유니버스 구축.

    KOSPI/KOSDAQ 주요 종목을 조회하여 시총 필터링.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return []

    # 주요 지수 구성종목 조회
    tickers_to_check = []

    if market in (None, 'KOSPI'):
        # KOSPI 200 ETF에서 대형주 추출 시도
        try:
            kospi_etf = yf.Ticker("069500.KS")  # KODEX 200
            info = kospi_etf.info or {}
            holdings = kospi_etf.get_holdings() if hasattr(kospi_etf, 'get_holdings') else None
            if holdings is not None and not holdings.empty:
                for _, h in holdings.iterrows():
                    sym = str(h.get('Symbol', '')).strip()
                    if sym.endswith('.KS'):
                        tickers_to_check.append(sym)
        except Exception:
            pass

    if market in (None, 'KOSDAQ'):
        try:
            kosdaq_etf = yf.Ticker("229200.KQ")  # KODEX KOSDAQ150
            holdings = kosdaq_etf.get_holdings() if hasattr(kosdaq_etf, 'get_holdings') else None
            if holdings is not None and not holdings.empty:
                for _, h in holdings.iterrows():
                    sym = str(h.get('Symbol', '')).strip()
                    if sym.endswith('.KQ'):
                        tickers_to_check.append(sym)
        except Exception:
            pass

    # pykrx 폴백으로 전 종목 리스트 확보
    if not tickers_to_check:
        tickers_to_check = _get_tickers_from_pykrx(market)

    if not tickers_to_check:
        return []

    # 배치로 시총 조회
    universe = []
    batch_size = 50
    for i in range(0, len(tickers_to_check), batch_size):
        batch = tickers_to_check[i:i + batch_size]
        try:
            tickers_obj = yf.Tickers(' '.join(batch))
            for sym in batch:
                try:
                    t = tickers_obj.tickers.get(sym)
                    if t is None:
                        continue
                    info = t.info or {}
                    mcap = info.get('marketCap', 0) or 0
                    if mcap < min_market_cap:
                        continue

                    ticker_code = sym.split('.')[0]
                    mkt = 'KOSDAQ' if sym.endswith('.KQ') else 'KOSPI'
                    universe.append({
                        'ticker': ticker_code,
                        'name': info.get('shortName', info.get('longName', '')),
                        'market': mkt,
                        'market_cap': int(mcap),
                        'yf_ticker': sym,
                        'close': int(info.get('currentPrice', info.get('previousClose', 0)) or 0),
                    })
                except Exception:
                    continue
        except Exception:
            continue

    return universe


def _get_tickers_from_pykrx(market: str) -> list[str]:
    """pykrx로 전 종목 yfinance 티커 리스트 반환."""
    try:
        from pykrx import stock as pykrx_stock
    except ImportError:
        return []

    today = datetime.now().strftime('%Y%m%d')
    tickers = []

    try:
        if market in (None, 'KOSPI'):
            for t in pykrx_stock.get_market_ticker_list(today, market='KOSPI'):
                tickers.append(f"{t}.KS")
        if market in (None, 'KOSDAQ'):
            for t in pykrx_stock.get_market_ticker_list(today, market='KOSDAQ'):
                tickers.append(f"{t}.KQ")
    except Exception as e:
        logger.warning(f"pykrx 종목 리스트 실패: {e}")

    return tickers


def fetch_ohlcv_batch(
    universe: list[dict],
    period: str = "2y",
    min_trading_days: int = None,
) -> dict[str, pd.DataFrame]:
    """yfinance 배치 다운로드.

    Args:
        universe: build_universe() 결과
        period: yfinance period 문자열
        min_trading_days: 최소 거래일 수 (기본: config에서 로드)

    Returns:
        {ticker: DataFrame(Date, Open, High, Low, Close, Volume)}
        다운로드 실패 종목은 빈 DataFrame.
    """
    if not universe:
        return {}

    config = load_config()
    if min_trading_days is None:
        min_trading_days = config['universe'].get('min_trading_days', 220)

    yf_tickers = [s['yf_ticker'] for s in universe]
    ticker_map = {s['yf_ticker']: s['ticker'] for s in universe}

    # 1차: yfinance 배치 다운로드
    result = _fetch_batch_yfinance(yf_tickers, ticker_map, period, min_trading_days)

    # 실패 종목 2차 폴백: 개별 yfinance
    missing = [s for s in universe if s['ticker'] not in result]
    if missing:
        logger.info(f"배치 실패 {len(missing)}개 → 개별 다운로드 시도")
        individual = _fetch_individual_yfinance(missing, period, min_trading_days)
        result.update(individual)

    # 여전히 실패 종목 3차 폴백: pykrx
    still_missing = [s for s in universe if s['ticker'] not in result]
    if still_missing:
        logger.info(f"yfinance 실패 {len(still_missing)}개 → pykrx 폴백 시도")
        pykrx_data = _fetch_from_pykrx(still_missing, min_trading_days)
        result.update(pykrx_data)

    return result


def _fetch_batch_yfinance(
    yf_tickers: list[str],
    ticker_map: dict[str, str],
    period: str,
    min_trading_days: int,
) -> dict[str, pd.DataFrame]:
    """yfinance 배치 다운로드."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    result = {}
    try:
        data = yf.download(
            yf_tickers,
            period=period,
            group_by='ticker',
            threads=True,
            progress=False,
        )
        if data.empty:
            return {}

        for yf_sym in yf_tickers:
            ticker = ticker_map.get(yf_sym, yf_sym.split('.')[0])
            try:
                if len(yf_tickers) == 1:
                    stock_df = data.copy()
                else:
                    stock_df = data[yf_sym].copy()

                stock_df = stock_df.dropna(subset=['Close'])
                if len(stock_df) >= min_trading_days:
                    result[ticker] = stock_df
            except (KeyError, TypeError):
                continue
    except Exception as e:
        logger.warning(f"yfinance 배치 다운로드 실패: {e}")

    return result


def _fetch_individual_yfinance(
    stocks: list[dict],
    period: str,
    min_trading_days: int,
) -> dict[str, pd.DataFrame]:
    """개별 종목 yfinance 다운로드."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    result = {}
    for stock in stocks:
        try:
            t = yf.Ticker(stock['yf_ticker'])
            df = t.history(period=period)
            if df is not None and len(df) >= min_trading_days:
                result[stock['ticker']] = df
        except Exception:
            continue

    return result


def _fetch_from_pykrx(
    stocks: list[dict],
    min_trading_days: int,
) -> dict[str, pd.DataFrame]:
    """pykrx 폴백으로 OHLCV 수집."""
    try:
        from pykrx import stock as pykrx_stock
    except ImportError:
        return {}

    end = datetime.now()
    start = end - timedelta(days=730)  # 2년
    start_str = start.strftime('%Y%m%d')
    end_str = end.strftime('%Y%m%d')

    result = {}
    for stock in stocks:
        try:
            df = pykrx_stock.get_market_ohlcv(start_str, end_str, stock['ticker'])
            if df is not None and len(df) >= min_trading_days:
                # 컬럼명 통일 (pykrx → yfinance 호환)
                col_map = {'시가': 'Open', '고가': 'High', '저가': 'Low',
                           '종가': 'Close', '거래량': 'Volume'}
                df = df.rename(columns=col_map)
                result[stock['ticker']] = df
        except Exception:
            continue

    return result
