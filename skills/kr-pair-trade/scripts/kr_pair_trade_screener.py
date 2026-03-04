"""kr-pair-trade: 페어 트레이딩 스크리닝 오케스트레이터.

Usage:
    python kr_pair_trade_screener.py --sector 반도체 --output-dir ./output
"""

import argparse
import sys
import os
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'common'))

from correlation_analyzer import calc_correlation, calc_rolling_correlation, check_stability, score_correlation
from cointegration_tester import calc_beta, calc_spread, run_adf_test, calc_half_life, score_cointegration
from spread_analyzer import calc_zscore, classify_signal, score_zscore, calc_risk_reward
from scorer import calc_pair_total, calc_risk_reward_score
from report_generator import PairTradeReportGenerator


def analyze_pair(ticker_a: str, ticker_b: str, client=None) -> dict:
    """단일 페어 분석.

    Args:
        ticker_a, ticker_b: 종목 코드
        client: KRClient 인스턴스
    Returns:
        페어 분석 결과 dict
    """
    if client is None:
        return {'ticker_a': ticker_a, 'ticker_b': ticker_b, 'error': 'No client'}

    try:
        info_a = client.get_stock_info(ticker_a)
        info_b = client.get_stock_info(ticker_b)
        ohlcv_a = client.get_ohlcv(ticker_a, period=500)
        ohlcv_b = client.get_ohlcv(ticker_b, period=500)

        if not ohlcv_a or not ohlcv_b or len(ohlcv_a) < 252 or len(ohlcv_b) < 252:
            return {'ticker_a': ticker_a, 'ticker_b': ticker_b,
                    'error': 'Insufficient data'}

        prices_a = [d['close'] for d in ohlcv_a]
        prices_b = [d['close'] for d in ohlcv_b]

        # 1. 상관 분석
        correlation = calc_correlation(prices_a, prices_b)
        rolling = calc_rolling_correlation(prices_a, prices_b)
        stability = check_stability(rolling)
        corr_score = score_correlation(correlation, stability)

        # 2. 공적분 테스트
        beta = calc_beta(prices_a, prices_b)
        spread = calc_spread(prices_a, prices_b, beta)
        adf_result = run_adf_test(spread)
        half_life = calc_half_life(spread)
        coint_score = score_cointegration(adf_result['p_value'], half_life)

        # 3. Z-Score 분석
        zscore_data = calc_zscore(spread)
        signal = classify_signal(zscore_data['zscore'])
        z_score_result = score_zscore(zscore_data['zscore'])

        # 4. Risk/Reward
        rr = calc_risk_reward(zscore_data['zscore'], zscore_data['std'])
        rr_score = calc_risk_reward_score(rr['ratio'])

        # 5. 종합 스코어
        components = {
            'correlation': corr_score['score'],
            'cointegration': coint_score['score'],
            'zscore_signal': z_score_result['score'],
            'risk_reward': rr_score,
        }
        score_data = calc_pair_total(
            components, correlation=correlation,
            is_cointegrated=adf_result['is_cointegrated'])

        return {
            'ticker_a': ticker_a, 'name_a': info_a.get('name', ''),
            'ticker_b': ticker_b, 'name_b': info_b.get('name', ''),
            'correlation': round(correlation, 4),
            'is_cointegrated': adf_result['is_cointegrated'],
            'zscore': zscore_data['zscore'],
            'half_life': half_life,
            'beta': round(beta, 4),
            'signal': signal,
            'score_data': score_data,
        }
    except Exception as e:
        return {'ticker_a': ticker_a, 'ticker_b': ticker_b, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='한국 페어 트레이딩 스크리너')
    parser.add_argument('--sector', default='반도체', help='업종명')
    parser.add_argument('--output-dir', default='./output', help='출력 디렉토리')
    args = parser.parse_args()

    try:
        from kr_client import KRClient
        client = KRClient()
    except ImportError:
        print('[ERROR] KRClient를 찾을 수 없습니다.')
        return

    tickers = client.get_sector_tickers(args.sector)
    print(f'[PairTrade] {args.sector}: {len(tickers)}종목, '
          f'{len(tickers) * (len(tickers) - 1) // 2}페어 분석 시작')

    results = []
    for a, b in combinations(tickers, 2):
        result = analyze_pair(a, b, client)
        if 'error' not in result:
            results.append(result)

    actionable = [r for r in results if r['score_data']['total_score'] >= 55]
    actionable.sort(key=lambda x: x['score_data']['total_score'], reverse=True)

    print(f'[PairTrade] 완료: {len(results)}페어 분석, {len(actionable)}페어 관심')

    reporter = PairTradeReportGenerator(args.output_dir)
    reporter.generate_json(actionable)
    reporter.generate_markdown(actionable)
    print(f'[PairTrade] 리포트 저장: {args.output_dir}/')


if __name__ == '__main__':
    main()
