"""한국 업트렌드 분석기 메인.

Usage:
    python3 kr_uptrend_analyzer.py --output-dir reports/
"""

import sys
import os
import argparse
import logging

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from uptrend_calculator import UptrendCalculator
from scorer import UptrendScorer
from report_generator import ReportGenerator
from history_tracker import HistoryTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def analyze(output_dir: str, lookback_days: int = 250):
    """업트렌드 분석 실행."""
    from _kr_common.kr_client import KRClient

    logger.info("=== 한국 업트렌드 분석 시작 ===")

    client = KRClient()
    calculator = UptrendCalculator(client)
    scorer = UptrendScorer()
    reporter = ReportGenerator(output_dir)
    tracker = HistoryTracker()

    # 1. 업종별 업트렌드 비율 계산
    sector_data = calculator.calculate_all_sectors(lookback_days)

    # 2. 전체 비율 / 그룹 평균 / 스프레드
    overall_ratio = calculator.calculate_overall_ratio(sector_data)
    group_averages = calculator.calculate_group_averages(sector_data)
    sector_spread = calculator.calculate_sector_spread(sector_data)
    group_std = calculator.calculate_group_std(sector_data)

    logger.info(f"전체 업트렌드 비율: {overall_ratio:.1f}%")

    # 3. 히스토리에서 이전 데이터 가져오기
    prev_history = tracker.get_overall_ratio_history()
    prev_ratio = prev_history[-1] if prev_history else None

    # 4. 스코어링
    score_input = {
        'overall_ratio': overall_ratio,
        'sector_data': sector_data,
        'group_averages': group_averages,
        'sector_spread': sector_spread,
        'group_std': group_std,
        'history': prev_history,
        'prev_ratio': prev_ratio,
    }

    score_data = scorer.score(score_input)
    logger.info(f"Composite Score: {score_data['composite_score']}/100 "
                f"({score_data['uptrend_zone']})")

    # 5. 히스토리 업데이트
    tracker.save({
        'date': reporter._get_date(),
        'market': 'KRX',
        'composite_score': score_data['composite_score'],
        'overall_ratio': overall_ratio,
        'uptrend_zone': score_data['uptrend_zone'],
    })

    # 6. 추세 판단
    trend = tracker.get_trend('KRX')

    # 7. 리포트 생성
    paths = reporter.generate(
        sector_data, score_data, trend,
        overall_ratio, group_averages,
    )
    logger.info(f"JSON: {paths['json_path']}")
    logger.info(f"Markdown: {paths['md_path']}")

    return {
        'sector_data': sector_data,
        'score': score_data,
        'overall_ratio': overall_ratio,
        'trend': trend,
        'report_paths': paths,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 업트렌드 분석기')
    parser.add_argument('--output-dir', default='reports/',
                        help='리포트 출력 디렉토리')
    parser.add_argument('--lookback-days', type=int, default=250,
                        help='히스토리 기간 (영업일)')
    args = parser.parse_args()

    try:
        result = analyze(args.output_dir, args.lookback_days)
        print(f"\n{'='*50}")
        print(f"업트렌드 점수: {result['score']['composite_score']}/100 "
              f"({result['score']['uptrend_zone_kr']})")
        print(f"전체 업트렌드: {result['overall_ratio']:.1f}%")
        print(f"권장 노출도: {result['score']['equity_exposure']}")
        print(f"{'='*50}\n")
    except Exception as e:
        logger.error(f"분석 실패: {e}")


if __name__ == '__main__':
    main()
