"""kr-vcp-screener: VCP 패턴 스크리닝 오케스트레이터.

Usage:
    python kr_vcp_screener.py --market KOSPI200 --output-dir ./output
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'common'))

from trend_template_calculator import check_trend_template
from vcp_pattern_calculator import (detect_contractions, calc_pivot_point,
                                     score_contraction_quality)
from volume_pattern_calculator import calc_dryup_ratio, calc_pivot_proximity
from scorer import calc_vcp_total
from report_generator import VCPReportGenerator


def screen_stock(ticker: str, client=None) -> dict:
    """단일 종목 VCP 스크리닝.

    Args:
        ticker: 종목 코드 (예: '005930')
        client: KRClient 인스턴스
    Returns:
        {'ticker': str, 'name': str, 'score_data': dict, ...}
    """
    if client is None:
        return {'ticker': ticker, 'name': '', 'error': 'No client'}

    try:
        info = client.get_stock_info(ticker)
        ohlcv = client.get_ohlcv(ticker, period=325)

        if not ohlcv or len(ohlcv) < 200:
            return {'ticker': ticker, 'name': info.get('name', ''),
                    'error': 'Insufficient data'}

        closes = [d['close'] for d in ohlcv]
        volumes = [d['volume'] for d in ohlcv]

        # SMA 계산
        sma50 = sum(closes[-50:]) / 50
        sma150 = sum(closes[-150:]) / 150
        sma200 = sum(closes[-200:]) / 200
        sma200_22d = sum(closes[-222:-22]) / 200 if len(closes) >= 222 else sma200

        price = closes[-1]
        high_52w = max(closes[-252:])
        low_52w = min(closes[-252:])

        # RS Rank (간소화 — 실전에서는 전종목 대비 계산)
        rs_rank = 75  # placeholder

        # 1. Stage 2 트렌드 템플릿
        template = check_trend_template(
            price, sma50, sma150, sma200, sma200_22d,
            high_52w, low_52w, rs_rank)

        # 2. VCP 패턴 탐지 (간소화 스윙 탐지)
        swing_highs, swing_lows = _detect_swings(closes)
        contractions = detect_contractions(swing_highs, swing_lows)
        contraction_quality = score_contraction_quality(contractions)
        pivot_data = calc_pivot_point(contractions)

        # 3. Volume Pattern
        if contractions:
            last_c = contractions[-1]
            c_vols = volumes[last_c['high_idx']:last_c['low_idx'] + 1]
            a_start = max(0, last_c['high_idx'] - 30)
            a_vols = volumes[a_start:last_c['high_idx']]
            vol_pattern = calc_dryup_ratio(c_vols, a_vols)
        else:
            vol_pattern = calc_dryup_ratio([], [])

        # 4. Pivot Proximity
        pivot_prox = calc_pivot_proximity(price, pivot_data['pivot'])

        # 5. 종합 스코어
        components = {
            'trend_template': template['score'],
            'contraction_quality': contraction_quality['score'],
            'volume_pattern': vol_pattern['score'],
            'pivot_proximity': pivot_prox['score'],
            'relative_strength': min(100, round(rs_rank)),
        }
        score_data = calc_vcp_total(components, template['points'])

        return {
            'ticker': ticker,
            'name': info.get('name', ''),
            'price': price,
            'score_data': score_data,
            'template': template,
            'contraction': contraction_quality,
            'pivot': pivot_data,
            'volume': vol_pattern,
            'pivot_proximity': pivot_prox,
        }
    except Exception as e:
        return {'ticker': ticker, 'name': '', 'error': str(e)}


def _detect_swings(prices: list, window: int = 10) -> tuple:
    """간소화 스윙 고저점 탐지."""
    highs = []
    lows = []
    for i in range(window, len(prices) - window):
        segment = prices[i - window:i + window + 1]
        if prices[i] == max(segment):
            highs.append((i, prices[i]))
        elif prices[i] == min(segment):
            lows.append((i, prices[i]))
    return highs, lows


def main():
    parser = argparse.ArgumentParser(description='한국 VCP 패턴 스크리너')
    parser.add_argument('--market', default='KOSPI200', help='시장 (KOSPI200, KOSDAQ150)')
    parser.add_argument('--output-dir', default='./output', help='출력 디렉토리')
    args = parser.parse_args()

    try:
        from kr_client import KRClient
        client = KRClient()
    except ImportError:
        print('[ERROR] KRClient를 찾을 수 없습니다. common/ 경로를 확인하세요.')
        return

    tickers = client.get_market_tickers(args.market)
    print(f'[VCP] {args.market}: {len(tickers)}종목 스크리닝 시작')

    results = []
    for i, ticker in enumerate(tickers):
        result = screen_stock(ticker, client)
        if 'error' not in result:
            results.append(result)
        if (i + 1) % 50 == 0:
            print(f'  ... {i + 1}/{len(tickers)}')

    # 등급별 필터링
    actionable = [r for r in results
                  if r['score_data']['total_score'] >= 60]
    actionable.sort(key=lambda x: x['score_data']['total_score'], reverse=True)

    print(f'[VCP] 완료: {len(results)}종목 분석, {len(actionable)}종목 관심')

    reporter = VCPReportGenerator(args.output_dir)
    reporter.generate_json(actionable)
    reporter.generate_markdown(actionable)
    print(f'[VCP] 리포트 저장: {args.output_dir}/')


if __name__ == '__main__':
    main()
