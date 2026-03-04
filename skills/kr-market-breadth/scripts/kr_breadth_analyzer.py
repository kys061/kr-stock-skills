"""한국 시장폭 분석기 메인.

Usage:
    python3 kr_breadth_analyzer.py --market KOSPI200 --output-dir reports/
    python3 kr_breadth_analyzer.py --market KOSDAQ150 --output-dir reports/
    python3 kr_breadth_analyzer.py --market ALL --output-dir reports/
"""

import sys
import os
import argparse
import logging

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from breadth_calculator import BreadthCalculator
from scorer import BreadthScorer
from report_generator import ReportGenerator
from history_tracker import HistoryTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def analyze_market(market: str, output_dir: str, lookback_days: int = 250):
    """단일 시장 분석."""
    from _kr_common.kr_client import KRClient

    logger.info(f"=== {market} 시장폭 분석 시작 ===")

    client = KRClient()
    calculator = BreadthCalculator(client, market)
    scorer = BreadthScorer()
    reporter = ReportGenerator(output_dir)
    tracker = HistoryTracker()

    # 1. 히스토리에서 이전 breadth_raw 로드
    prev_history = tracker.get_breadth_raw_history(market)

    # 2. 시장폭 계산
    if prev_history:
        breadth_data = calculator.calculate_with_history(prev_history)
    else:
        breadth_data = calculator.calculate(lookback_days)

    logger.info(f"Breadth Raw: {breadth_data['breadth_raw']:.1f}% "
                f"({breadth_data['above_200ma']}/{breadth_data['total_stocks']})")

    # 3. 스코어링
    score_data = scorer.score(breadth_data)
    logger.info(f"Composite Score: {score_data['composite_score']}/100 "
                f"({score_data['health_zone']})")

    # 4. 히스토리 업데이트
    tracker.save({
        'date': breadth_data['date'],
        'market': market,
        'composite_score': score_data['composite_score'],
        'breadth_raw': breadth_data['breadth_raw'],
        'health_zone': score_data['health_zone'],
    })

    # 5. 추세 판단
    trend = tracker.get_trend(market)

    # 6. 리포트 생성
    paths = reporter.generate(breadth_data, score_data, trend)
    logger.info(f"JSON: {paths['json_path']}")
    logger.info(f"Markdown: {paths['md_path']}")

    return {
        'breadth': breadth_data,
        'score': score_data,
        'trend': trend,
        'report_paths': paths,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 시장폭 분석기')
    parser.add_argument('--market', default='KOSPI200',
                        choices=['KOSPI200', 'KOSDAQ150', 'ALL'],
                        help='분석 대상 시장')
    parser.add_argument('--output-dir', default='reports/',
                        help='리포트 출력 디렉토리')
    parser.add_argument('--lookback-days', type=int, default=250,
                        help='히스토리 기간 (영업일)')
    args = parser.parse_args()

    markets = ['KOSPI200', 'KOSDAQ150'] if args.market == 'ALL' else [args.market]

    for market in markets:
        try:
            result = analyze_market(market, args.output_dir, args.lookback_days)
            print(f"\n{'='*50}")
            print(f"{market}: {result['score']['composite_score']}/100 "
                  f"({result['score']['health_zone_kr']})")
            print(f"권장 비중: {result['score']['equity_exposure']}")
            print(f"{'='*50}\n")
        except Exception as e:
            logger.error(f"{market} 분석 실패: {e}")


if __name__ == '__main__':
    main()
