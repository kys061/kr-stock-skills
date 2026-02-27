"""종목코드 유틸리티 - 종목명 ↔ 코드 변환."""

import re
import logging

logger = logging.getLogger(__name__)

# 종목코드 ↔ 종목명 캐시 (세션 시작 시 1회 로드)
_TICKER_CACHE: dict = {}
_NAME_CACHE: dict = {}
_MARKET_CACHE: dict = {}
_CACHE_LOADED = False


def _load_cache():
    """종목 목록 캐시 로드 (lazy)."""
    global _TICKER_CACHE, _NAME_CACHE, _MARKET_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return

    try:
        from pykrx import stock as pykrx_stock
        from .date_utils import get_recent_trading_day

        date = get_recent_trading_day()
        krx_date = date.replace('-', '')

        for market in ['KOSPI', 'KOSDAQ']:
            tickers = pykrx_stock.get_market_ticker_list(krx_date, market=market)
            for ticker in tickers:
                name = pykrx_stock.get_market_ticker_name(ticker)
                _TICKER_CACHE[name] = ticker
                _NAME_CACHE[ticker] = name
                _MARKET_CACHE[ticker] = market

        _CACHE_LOADED = True
        logger.debug(f"Ticker cache loaded: {len(_TICKER_CACHE)} items")
    except Exception as e:
        logger.warning(f"Failed to load ticker cache: {e}")


def name_to_ticker(name: str) -> str:
    """'삼성전자' → '005930'. 못 찾으면 ValueError."""
    _load_cache()
    ticker = _TICKER_CACHE.get(name)
    if ticker is None:
        raise ValueError(f"종목을 찾을 수 없습니다: {name}")
    return ticker


def ticker_to_name(ticker: str) -> str:
    """'005930' → '삼성전자'. 못 찾으면 코드 그대로 반환."""
    _load_cache()
    return _NAME_CACHE.get(ticker, ticker)


def resolve(name_or_code: str) -> str:
    """종목명이든 코드든 → 코드로 변환.

    '삼성전자' → '005930'
    '005930' → '005930'
    """
    name_or_code = name_or_code.strip()
    if is_valid_ticker(name_or_code):
        return name_or_code
    return name_to_ticker(name_or_code)


def is_valid_ticker(code: str) -> bool:
    """유효한 종목코드인지 확인 (6자리 숫자)."""
    return bool(re.match(r'^\d{6}$', code.strip()))


def get_market(ticker: str) -> str:
    """종목의 시장 반환: 'KOSPI' 또는 'KOSDAQ'."""
    _load_cache()
    return _MARKET_CACHE.get(ticker, 'UNKNOWN')


def search(keyword: str) -> list:
    """종목명 키워드로 검색.

    Args:
        keyword: 검색어 (부분 매치 지원)

    Returns:
        [{'ticker': '005930', 'name': '삼성전자', 'market': 'KOSPI'}, ...]
    """
    _load_cache()
    keyword = keyword.strip().lower()
    results = []
    for name, ticker in _TICKER_CACHE.items():
        if keyword in name.lower():
            results.append({
                'ticker': ticker,
                'name': name,
                'market': _MARKET_CACHE.get(ticker, 'UNKNOWN'),
            })
    return results


def clear_cache():
    """캐시 초기화 (테스트용)."""
    global _TICKER_CACHE, _NAME_CACHE, _MARKET_CACHE, _CACHE_LOADED
    _TICKER_CACHE = {}
    _NAME_CACHE = {}
    _MARKET_CACHE = {}
    _CACHE_LOADED = False
