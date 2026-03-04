"""kr-earnings-trade: 실적 트레이드 5팩터 분석 오케스트레이터.

Usage:
    python kr_earnings_trade_analyzer.py --lookback-days 14 --output-dir ./output
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'common'))

from gap_analyzer import calc_gap, score_gap
from trend_analyzer import calc_pre_earnings_trend, score_trend
from volume_analyzer import calc_volume_ratio, score_volume
from ma_position_analyzer import calc_sma, calc_ma_distance, score_ma200, score_ma50
from scorer import calc_composite_score, apply_foreign_bonus, LOOKBACK_DAYS, MARKET_CAP_MIN
from report_generator import EarningsTradeReportGenerator


def analyze_earnings_stock(ticker: str, earnings_date: str,
                            timing: str = 'after_close',
                            client=None) -> dict:
    """단일 종목 실적 트레이드 분석.

    Args:
        ticker: 종목 코드
        earnings_date: 실적 발표일
        timing: 'before_open'|'during_market'|'after_close'
        client: KRClient 인스턴스

    Returns:
        분석 결과 dict
    """
    if client is None:
        return {'ticker': ticker, 'error': 'No client'}

    try:
        info = client.get_stock_info(ticker)
        ohlcv = client.get_ohlcv(ticker, period=300)

        if not ohlcv or len(ohlcv) < 200:
            return {'ticker': ticker, 'error': 'Insufficient data'}

        # 실적일 인덱스 찾기
        earnings_idx = -1
        for i, d in enumerate(ohlcv):
            if d.get('date', '') == earnings_date:
                earnings_idx = i
                break
        if earnings_idx < 0:
            earnings_idx = len(ohlcv) - 1  # fallback

        closes = [d['close'] for d in ohlcv]
        volumes = [d['volume'] for d in ohlcv]

        # Factor 1: Gap
        gap = calc_gap(ohlcv, earnings_idx, timing) * 100
        gap_result = score_gap(gap)

        # Factor 2: Pre-Earnings Trend
        trend = calc_pre_earnings_trend(ohlcv, earnings_idx)
        trend_result = score_trend(trend)

        # Factor 3: Volume
        vol_ratio = calc_volume_ratio(volumes, earnings_idx)
        vol_result = score_volume(vol_ratio)

        # Factor 4: MA200
        ma200 = calc_sma(closes[:earnings_idx + 1], 200)
        ma200_dist = calc_ma_distance(closes[earnings_idx], ma200)
        ma200_result = score_ma200(ma200_dist)

        # Factor 5: MA50
        ma50 = calc_sma(closes[:earnings_idx + 1], 50)
        ma50_dist = calc_ma_distance(closes[earnings_idx], ma50)
        ma50_result = score_ma50(ma50_dist)

        # Composite
        components = {
            'gap_size': gap_result['score'],
            'pre_earnings_trend': trend_result['score'],
            'volume_trend': vol_result['score'],
            'ma200_position': ma200_result['score'],
            'ma50_position': ma50_result['score'],
        }
        score_data = calc_composite_score(components)

        # Foreign bonus
        try:
            investor_data = client.get_investor_trading(ticker, period=10)
            foreign_buys = [d.get('foreign_net', 0) for d in investor_data[:5]]
        except Exception:
            foreign_buys = []
        bonus = apply_foreign_bonus(score_data['composite_score'], foreign_buys)

        return {
            'ticker': ticker,
            'name': info.get('name', ''),
            'earnings_date': earnings_date,
            'gap_pct': gap_result['gap_pct'],
            'trend_pct': trend_result['trend_pct'],
            'volume_ratio': vol_result['ratio'],
            'ma200_distance': ma200_result['distance_pct'],
            'ma50_distance': ma50_result['distance_pct'],
            'grade': score_data['grade'],
            'composite_score': score_data['composite_score'],
            'final_score': bonus['final_score'],
            'bonus_applied': bonus['bonus_applied'],
            'score_data': score_data,
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='한국 실적 트레이드 분석기')
    parser.add_argument('--lookback-days', type=int, default=LOOKBACK_DAYS)
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    try:
        from kr_client import KRClient
        client = KRClient()
    except ImportError:
        print('[ERROR] KRClient를 찾을 수 없습니다.')
        return

    print(f'[EarningsTrade] 최근 {args.lookback_days}일 실적 공시 조회 중...')
    # 실제로는 DART 공시 조회 후 각 종목 분석
    print('[EarningsTrade] 완료')


if __name__ == '__main__':
    main()
