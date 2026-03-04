"""kr-institutional-flow: 수급 동향 분석 오케스트레이터.

Usage:
    python kr_institutional_flow_tracker.py --ticker 005930 --period 20
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', '..', '..', 'common'))

from investor_flow_analyzer import (aggregate_by_group, calc_consecutive_days,
                                     score_foreign_flow,
                                     score_institutional_flow,
                                     ANALYSIS_WINDOW)
from foreign_flow_tracker import calc_ownership_trend, detect_turning_point
from accumulation_detector import (detect_accumulation, detect_retail_counter,
                                    apply_retail_counter_bonus)
from scorer import (calc_flow_consistency, calc_volume_confirmation,
                    calc_composite_score, MARKET_CAP_MIN)
from report_generator import InstitutionalFlowReportGenerator


def analyze_institutional_flow(ticker: str, period: int = ANALYSIS_WINDOW,
                                client=None) -> dict:
    """단일 종목 수급 분석.

    Args:
        ticker: 종목 코드
        period: 분석 기간 (거래일)
        client: KRClient 인스턴스

    Returns:
        분석 결과 dict
    """
    if client is None:
        return {'ticker': ticker, 'error': 'No client'}

    try:
        info = client.get_stock_info(ticker)
        investor_data = client.get_investor_trading(ticker, period=period)
        ohlcv = client.get_ohlcv(ticker, period=period)

        if not investor_data or len(investor_data) < 5:
            return {'ticker': ticker, 'error': 'Insufficient data'}

        # 투자자별 순매수 추출
        foreign_net = aggregate_by_group(investor_data, 'foreign')
        inst_net = aggregate_by_group(investor_data, 'institutional')
        retail_net = aggregate_by_group(investor_data, 'retail')
        volumes = [d.get('volume', 0) for d in ohlcv] if ohlcv else []

        # Factor 1: Foreign Flow
        foreign_consec = calc_consecutive_days(foreign_net)
        foreign_result = score_foreign_flow(foreign_consec)

        # Factor 2: Institutional Flow
        inst_consec = calc_consecutive_days(inst_net)
        inst_result = score_institutional_flow(inst_consec)

        # Factor 3: Flow Consistency (외국인+기관 합산)
        smart_money = [f + i for f, i in zip(foreign_net, inst_net)]
        consistency = calc_flow_consistency(smart_money)

        # Factor 4: Volume Confirmation
        vol_confirm = calc_volume_confirmation(smart_money, volumes)

        # Composite Score
        components = {
            'foreign_flow': foreign_result['score'],
            'institutional_flow': inst_result['score'],
            'flow_consistency': consistency['score'],
            'volume_confirmation': vol_confirm['score'],
        }
        score_data = calc_composite_score(components)

        # Retail-Counter Bonus
        retail_counter = detect_retail_counter(retail_net, smart_money)
        bonus = apply_retail_counter_bonus(score_data['composite_score'],
                                           retail_counter)

        # Accumulation Pattern
        acc_pattern = detect_accumulation(foreign_net, inst_net, retail_net)

        # Turning Point
        turning = detect_turning_point(foreign_net)

        return {
            'ticker': ticker,
            'name': info.get('name', ''),
            'rating': score_data['rating'],
            'composite_score': score_data['composite_score'],
            'final_score': bonus['final_score'],
            'bonus_applied': bonus['bonus_applied'],
            'foreign_signal': foreign_result['signal'],
            'inst_signal': inst_result['signal'],
            'consistency_ratio': consistency['ratio'],
            'volume_ratio': vol_confirm['ratio'],
            'accumulation_pattern': acc_pattern['pattern'],
            'turning_point': turning['turning_point'],
            'turning_direction': turning['direction'],
            'score_data': score_data,
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='한국 수급 동향 분석기')
    parser.add_argument('--ticker', required=True)
    parser.add_argument('--period', type=int, default=ANALYSIS_WINDOW)
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    try:
        from kr_client import KRClient
        client = KRClient()
    except ImportError:
        print('[ERROR] KRClient를 찾을 수 없습니다.')
        return

    result = analyze_institutional_flow(args.ticker, args.period, client)
    if 'error' in result:
        print(f'[ERROR] {result["error"]}')
    else:
        print(f'[InstitutionalFlow] {result["ticker"]} {result["name"]}: '
              f'{result["rating"]} ({result["final_score"]}점)')


if __name__ == '__main__':
    main()
