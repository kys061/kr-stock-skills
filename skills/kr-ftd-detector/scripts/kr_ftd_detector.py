"""
kr-ftd-detector: 한국 FTD 탐지기 메인 오케스트레이터.
KOSPI + KOSDAQ 이중 추적, 외국인 순매수 전환 연동.

Usage:
    python kr_ftd_detector.py --output-dir ./output
    python kr_ftd_detector.py --output-dir ./output --breadth-json path/to/breadth.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

from rally_tracker import RallyTracker, RallyState
from ftd_qualifier import FTDQualifier
from post_ftd_monitor import PostFTDMonitor
from report_generator import ReportGenerator


def _load_json(path: str) -> dict:
    """JSON 파일 로드."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze(output_dir: str = './output', breadth_json: str = None) -> dict:
    """FTD 탐지 메인 분석.

    Args:
        output_dir: 리포트 출력 디렉토리
        breadth_json: kr-market-breadth JSON 경로 (선택)
    Returns:
        분석 결과 dict
    """
    # 1. 추적기 초기화
    kospi_tracker = RallyTracker('KOSPI')
    kosdaq_tracker = RallyTracker('KOSDAQ')
    qualifier = FTDQualifier()
    reporter = ReportGenerator(output_dir)

    # 2. 데이터 수집 (실제 운영 시 KRClient 사용)
    # 현재는 인터페이스만 정의
    # kospi_data = client.get_index('0001', days=60)
    # kosdaq_data = client.get_index('1001', days=60)
    # investor_data = client.get_investor_trading_market(days=10)

    # 3. 시장폭 데이터 (크로스레퍼런스)
    breadth_data = _load_json(breadth_json) if breadth_json else {}
    breadth_change = 0.0
    if breadth_data:
        # breadth_ratio 변화 추정 (현재 단순화)
        raw = breadth_data.get('components', {}).get('breadth_level', {})
        if raw.get('raw') is not None:
            breadth_change = 0.0  # 실제 운영 시 이전 데이터 대비 변화

    # 4. 상태 머신 업데이트 (실제 운영 시 일별 loop)
    # for day_data in kospi_data:
    #     kospi_tracker.update(day_data['date'], day_data['close'],
    #                          day_data['prev_close'], day_data['volume'],
    #                          day_data['prev_volume'])

    # 5. FTD 확인
    kospi_state = kospi_tracker.get_state()
    kosdaq_state = kosdaq_tracker.get_state()

    # 6. 이중 FTD 체크
    dual_ftd = (kospi_state['state'] == 'ftd_confirmed' and
                kosdaq_state['state'] == 'ftd_confirmed')

    # 7. FTD 품질 점수 (FTD가 확인된 경우)
    ftd_result = None
    for tracker_state in [kospi_state, kosdaq_state]:
        if tracker_state['state'] == 'ftd_confirmed':
            ftd_result = qualifier.qualify(
                rally_day=tracker_state.get('rally_day', 0),
                daily_return=0.02,  # placeholder
                volume_ratio=1.3,   # placeholder
                breadth_change=breadth_change,
                foreign_net_today=0.0,
                foreign_net_yesterday=0.0,
                was_selling=False,
            )
            if dual_ftd and ftd_result.get('is_ftd'):
                # 양쪽 FTD → 품질 점수 +15 보너스
                ftd_result['quality_score'] = min(
                    ftd_result['quality_score'] + 15.0, 100.0)
            break

    # 8. 결과 조합
    result = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'kospi': kospi_state,
        'kosdaq': kosdaq_state,
        'ftd_result': ftd_result,
        'dual_ftd': dual_ftd,
    }

    # 9. 리포트 생성
    report = reporter.generate(result)

    return {**result, **report}


def main():
    parser = argparse.ArgumentParser(description='kr-ftd-detector: 한국 FTD 탐지기')
    parser.add_argument('--output-dir', default='./output', help='리포트 출력 디렉토리')
    parser.add_argument('--breadth-json', default=None,
                        help='kr-market-breadth JSON 경로 (선택)')
    args = parser.parse_args()

    result = analyze(output_dir=args.output_dir, breadth_json=args.breadth_json)

    ftd = result.get('ftd_result') or {}
    print(f"[kr-ftd-detector] KOSPI: {result['kospi']['state']}")
    print(f"[kr-ftd-detector] KOSDAQ: {result['kosdaq']['state']}")
    print(f"[kr-ftd-detector] FTD: {'✅' if ftd.get('is_ftd') else '❌'}")
    if ftd.get('is_ftd'):
        print(f"[kr-ftd-detector] 품질: {ftd['quality_score']:.1f}/100")
        print(f"[kr-ftd-detector] 노출: {ftd['exposure'].get('exposure', 'N/A')}")


if __name__ == '__main__':
    main()
