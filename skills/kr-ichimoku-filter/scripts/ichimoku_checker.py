"""
kr-ichimoku-filter: 일목균형표 전환선 확인 필터.
일봉 기준 종가가 전환선(9일) 위에서 마감했는지 판정.

Usage (standalone):
    python ichimoku_checker.py --ticker 005930
    python ichimoku_checker.py --ticker 삼성전자

Usage (import from other skills):
    from kr_ichimoku_filter.scripts.ichimoku_checker import check_ichimoku
    result = check_ichimoku(ticker='005930', client=client)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from _kr_common.utils.ta_utils import ichimoku


def check_ichimoku(ticker: str, client=None, ohlcv: pd.DataFrame = None,
                   tenkan_period: int = 9) -> dict:
    """일목균형표 전환선 필터.

    Args:
        ticker: 종목코드 또는 종목명
        client: KRClient 인스턴스 (ohlcv 미제공 시 필수)
        ohlcv: 일봉 OHLCV DataFrame (제공 시 API 호출 생략)
        tenkan_period: 전환선 기간 (기본 9)

    Returns:
        {
            'ticker': str,
            'pass': bool,          # 종가 > 전환선
            'close': float,        # 당일 종가
            'tenkan': float,       # 전환선 값
            'kijun': float,        # 기준선 값
            'margin_pct': float,   # (종가-전환선)/전환선 * 100
            'tenkan_above_kijun': bool,  # 전환선 > 기준선 여부
            'date': str,           # 기준일
            'error': str or None,
        }
    """
    result = {
        'ticker': ticker,
        'pass': False,
        'close': None,
        'tenkan': None,
        'kijun': None,
        'margin_pct': None,
        'tenkan_above_kijun': None,
        'date': None,
        'error': None,
    }

    try:
        if ohlcv is None:
            if client is None:
                from _kr_common.kr_client import KRClient
                client = KRClient()

            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            ohlcv = client.get_ohlcv(ticker, start=start, end=end)

        if ohlcv is None or len(ohlcv) < 52:
            result['error'] = f'데이터 부족: {len(ohlcv) if ohlcv is not None else 0}일'
            return result

        high = ohlcv['High'] if 'High' in ohlcv.columns else ohlcv['high']
        low = ohlcv['Low'] if 'Low' in ohlcv.columns else ohlcv['low']
        close = ohlcv['Close'] if 'Close' in ohlcv.columns else ohlcv['close']

        ichi = ichimoku(high, low, close, tenkan_period=tenkan_period)

        last_close = float(close.iloc[-1])
        last_tenkan = float(ichi['Tenkan'].iloc[-1])
        last_kijun = float(ichi['Kijun'].iloc[-1])

        if pd.isna(last_tenkan) or pd.isna(last_kijun):
            result['error'] = '지표 계산 불가 (NaN)'
            return result

        is_pass = last_close > last_tenkan
        margin_pct = ((last_close - last_tenkan) / last_tenkan) * 100

        result.update({
            'pass': is_pass,
            'close': round(last_close, 2),
            'tenkan': round(last_tenkan, 2),
            'kijun': round(last_kijun, 2),
            'margin_pct': round(margin_pct, 2),
            'tenkan_above_kijun': last_tenkan > last_kijun,
            'date': str(ohlcv.index[-1].date()) if hasattr(ohlcv.index[-1], 'date') else str(ohlcv.index[-1]),
        })

    except Exception as e:
        result['error'] = str(e)

    return result


def check_ichimoku_batch(tickers: list, client=None) -> list:
    """여러 종목 일괄 확인.

    Args:
        tickers: 종목코드 리스트
        client: KRClient 인스턴스

    Returns:
        list of check_ichimoku results
    """
    if client is None:
        from _kr_common.kr_client import KRClient
        client = KRClient()

    results = []
    for ticker in tickers:
        result = check_ichimoku(ticker, client=client)
        results.append(result)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='일목균형표 전환선 필터')
    parser.add_argument('--ticker', required=True, help='종목코드 또는 종목명')
    args = parser.parse_args()

    result = check_ichimoku(args.ticker)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    status = 'PASS' if result['pass'] else 'FAIL'
    if result['error']:
        status = f'ERROR: {result["error"]}'
    print(f"\n[{status}] {result['ticker']} | 종가 {result['close']} vs 전환선 {result['tenkan']} ({result['margin_pct']:+.2f}%)" if not result['error'] else '')
