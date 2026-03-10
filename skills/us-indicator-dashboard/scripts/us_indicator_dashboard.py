"""미국 경제지표 대시보드 오케스트레이터.

5개 모듈을 순차 실행하여 4-Section 리포트를 생성한다.
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from indicator_collector import collect_all, get_collection_stats
from regime_classifier import analyze_regime
from kr_impact_analyzer import analyze_impact
from calendar_tracker import get_upcoming_releases
from report_generator import generate_report, save_report


def run(websearch_context: dict = None,
        calendar_context: dict = None) -> dict:
    """대시보드 전체 실행.

    Args:
        websearch_context: SKILL.md에서 Claude가 주입하는 지표 데이터
            {
                'gdp': {'value': 2.3, 'prev_value': 3.1, 'release_date': '2026-01-30'},
                ...
            }
        calendar_context: WebSearch로 수집한 발표 일정
            {
                'events': [{'date': '...', 'indicator': '...', 'forecast': '...'}]
            }

    Returns:
        {
            'success': True,
            'report_path': 'reports/us-indicator-dashboard_macro_미국경제지표_20260310.md',
            'collection_stats': {'total': 21, 'collected': 18, 'rate': 85.7},
            'regime': 'Goldilocks',
            'net_impact': 'mildly_positive',
            'errors': []
        }
    """
    result = {
        'success': False,
        'report_path': None,
        'collection_stats': {},
        'regime': 'Unknown',
        'net_impact': 'unknown',
        'errors': [],
    }

    # Step 1: 지표 수집
    try:
        indicators = collect_all(websearch_context)
        stats = get_collection_stats(indicators)
        result['collection_stats'] = stats
    except Exception as e:
        result['errors'].append(f'[collect] {e}')
        return result

    # Step 2: 레짐 판정
    regime = None
    try:
        regime = analyze_regime(indicators)
        result['regime'] = regime['regime'].value
    except Exception as e:
        regime = {
            'regime_kr': 'Unknown',
            'composite_score': 0,
            'kr_impact': '',
            'components': {},
            'component_details': {},
        }
        result['errors'].append(f'[regime] {e}')

    # Step 3: 한국 영향 분석
    impact = None
    try:
        impact = analyze_impact(indicators)
        result['net_impact'] = impact.get('net_impact', 'unknown')
    except Exception as e:
        impact = {
            'positive': [], 'negative': [], 'neutral': [],
            'summary': '', 'net_impact': 'unknown',
        }
        result['errors'].append(f'[impact] {e}')

    # Step 4: 발표 일정
    upcoming = []
    try:
        upcoming = get_upcoming_releases(websearch_context=calendar_context)
    except Exception as e:
        result['errors'].append(f'[calendar] {e}')

    # Step 5: 리포트 생성 & 저장
    try:
        content = generate_report(indicators, regime, impact, upcoming, stats)
        path = save_report(content)
        result['report_path'] = path
        result['success'] = True
    except Exception as e:
        result['errors'].append(f'[report] {e}')

    return result


if __name__ == '__main__':
    res = run()
    print(f"Success: {res['success']}")
    print(f"Report: {res['report_path']}")
    print(f"Stats: {res['collection_stats']}")
    print(f"Regime: {res['regime']}")
    if res['errors']:
        print(f"Errors: {res['errors']}")
