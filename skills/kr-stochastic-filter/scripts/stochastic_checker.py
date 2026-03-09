"""
kr-stochastic-filter: Stochastic Slow (18,10,10) 확인 필터.
Slow %K >= Slow %D 조건 판정.

Usage (standalone):
    python stochastic_checker.py --ticker 005930
    python stochastic_checker.py --ticker 삼성전자

Usage (import from other skills):
    from kr_stochastic_filter.scripts.stochastic_checker import check_stochastic
    result = check_stochastic(ticker='005930', client=client)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from _kr_common.utils.ta_utils import stochastic_slow

# Stochastic Slow 기본 파라미터
DEFAULT_K_PERIOD = 18
DEFAULT_SLOW_K_PERIOD = 10
DEFAULT_SLOW_D_PERIOD = 10

# 영역 임계값
OVERBOUGHT = 80
OVERSOLD = 20


def _classify_zone(slow_k: float) -> str:
    """Stochastic 영역 분류."""
    if slow_k > OVERBOUGHT:
        return '과매수'
    elif slow_k < OVERSOLD:
        return '과매도'
    return '중립'


def check_stochastic(ticker: str, client=None, ohlcv: pd.DataFrame = None,
                     k_period: int = DEFAULT_K_PERIOD,
                     slow_k_period: int = DEFAULT_SLOW_K_PERIOD,
                     slow_d_period: int = DEFAULT_SLOW_D_PERIOD) -> dict:
    """Stochastic Slow 필터.

    Args:
        ticker: 종목코드 또는 종목명
        client: KRClient 인스턴스 (ohlcv 미제공 시 필수)
        ohlcv: 일봉 OHLCV DataFrame (제공 시 API 호출 생략)
        k_period: Fast %K 기간 (기본 18)
        slow_k_period: Slow %K 평활 기간 (기본 10)
        slow_d_period: Slow %D 평활 기간 (기본 10)

    Returns:
        {
            'ticker': str,
            'pass': bool,          # Slow %K >= Slow %D
            'slow_k': float,       # Slow %K 값
            'slow_d': float,       # Slow %D 값
            'diff': float,         # Slow %K - Slow %D
            'zone': str,           # 과매수/중립/과매도
            'prev_slow_k': float,  # 전일 Slow %K
            'prev_slow_d': float,  # 전일 Slow %D
            'cross_up': bool,      # 금일 골든크로스 발생 여부
            'date': str,
            'params': str,         # 사용된 파라미터
            'error': str or None,
        }
    """
    result = {
        'ticker': ticker,
        'pass': False,
        'slow_k': None,
        'slow_d': None,
        'diff': None,
        'zone': None,
        'prev_slow_k': None,
        'prev_slow_d': None,
        'cross_up': None,
        'date': None,
        'params': f'({k_period},{slow_k_period},{slow_d_period})',
        'error': None,
    }

    min_bars = k_period + slow_k_period + slow_d_period + 5

    try:
        if ohlcv is None:
            if client is None:
                from _kr_common.kr_client import KRClient
                client = KRClient()

            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            ohlcv = client.get_ohlcv(ticker, start=start, end=end)

        if ohlcv is None or len(ohlcv) < min_bars:
            result['error'] = f'데이터 부족: {len(ohlcv) if ohlcv is not None else 0}일 (최소 {min_bars}일 필요)'
            return result

        high = ohlcv['High'] if 'High' in ohlcv.columns else ohlcv['high']
        low = ohlcv['Low'] if 'Low' in ohlcv.columns else ohlcv['low']
        close = ohlcv['Close'] if 'Close' in ohlcv.columns else ohlcv['close']

        stoch = stochastic_slow(high, low, close,
                                k_period=k_period,
                                slow_k_period=slow_k_period,
                                slow_d_period=slow_d_period)

        curr_k = float(stoch['Slow%K'].iloc[-1])
        curr_d = float(stoch['Slow%D'].iloc[-1])
        prev_k = float(stoch['Slow%K'].iloc[-2])
        prev_d = float(stoch['Slow%D'].iloc[-2])

        if pd.isna(curr_k) or pd.isna(curr_d):
            result['error'] = '지표 계산 불가 (NaN)'
            return result

        is_pass = curr_k >= curr_d
        cross_up = (prev_k < prev_d) and (curr_k >= curr_d)

        result.update({
            'pass': is_pass,
            'slow_k': round(curr_k, 2),
            'slow_d': round(curr_d, 2),
            'diff': round(curr_k - curr_d, 2),
            'zone': _classify_zone(curr_k),
            'prev_slow_k': round(prev_k, 2),
            'prev_slow_d': round(prev_d, 2),
            'cross_up': cross_up,
            'date': str(ohlcv.index[-1].date()) if hasattr(ohlcv.index[-1], 'date') else str(ohlcv.index[-1]),
        })

    except Exception as e:
        result['error'] = str(e)

    return result


def check_stochastic_batch(tickers: list, client=None) -> list:
    """여러 종목 일괄 확인.

    Args:
        tickers: 종목코드 리스트
        client: KRClient 인스턴스

    Returns:
        list of check_stochastic results
    """
    if client is None:
        from _kr_common.kr_client import KRClient
        client = KRClient()

    results = []
    for ticker in tickers:
        result = check_stochastic(ticker, client=client)
        results.append(result)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stochastic Slow 필터')
    parser.add_argument('--ticker', required=True, help='종목코드 또는 종목명')
    parser.add_argument('--k-period', type=int, default=DEFAULT_K_PERIOD)
    parser.add_argument('--slow-k', type=int, default=DEFAULT_SLOW_K_PERIOD)
    parser.add_argument('--slow-d', type=int, default=DEFAULT_SLOW_D_PERIOD)
    args = parser.parse_args()

    result = check_stochastic(args.ticker,
                              k_period=args.k_period,
                              slow_k_period=args.slow_k,
                              slow_d_period=args.slow_d)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result['error']:
        status = 'PASS' if result['pass'] else 'FAIL'
        cross = ' [Golden Cross!]' if result['cross_up'] else ''
        print(f"\n[{status}] {result['ticker']} | "
              f"Slow%K={result['slow_k']:.1f} vs Slow%D={result['slow_d']:.1f} "
              f"({result['diff']:+.1f}) | {result['zone']}{cross}")
