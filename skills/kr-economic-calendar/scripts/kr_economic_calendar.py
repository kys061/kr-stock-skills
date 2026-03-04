"""kr-economic-calendar: 한국 경제 캘린더 메인 오케스트레이터.

Usage:
    python kr_economic_calendar.py --days-ahead 14
    python kr_economic_calendar.py --days-ahead 30 --impact H,M
    python kr_economic_calendar.py --output-dir ./output
"""

import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from ecos_fetcher import (
    get_upcoming_events, classify_impact,
    KR_INDICATORS, DEFAULT_LOOKAHEAD_DAYS, MAX_LOOKAHEAD_DAYS,
)
from report_generator import EconomicCalendarReportGenerator


def run_calendar(days_ahead: int = DEFAULT_LOOKAHEAD_DAYS,
                 impact_filter: list = None,
                 output_dir: str = './output',
                 base_date: datetime = None) -> dict:
    """경제 캘린더 조회 + 리포트 생성.

    Args:
        days_ahead: 향후 조회 일수
        impact_filter: 임팩트 필터 (['H', 'M'] 등)
        output_dir: 출력 디렉토리
        base_date: 기준일

    Returns:
        {'events': list, 'summary': dict}
    """
    events = get_upcoming_events(
        days_ahead=days_ahead,
        impact_filter=impact_filter,
        base_date=base_date,
    )

    summary = {
        'total': len(events),
        'high_impact': sum(1 for e in events if e.get('impact') == 'H'),
        'medium_impact': sum(1 for e in events if e.get('impact') == 'M'),
        'low_impact': sum(1 for e in events if e.get('impact') == 'L'),
        'days_ahead': days_ahead,
        'impact_filter': impact_filter,
    }

    reporter = EconomicCalendarReportGenerator(output_dir)
    reporter.generate_json(events, metadata={'days_ahead': days_ahead})
    reporter.generate_markdown(events, metadata={'days_ahead': days_ahead})

    return {'events': events, 'summary': summary}


def main():
    parser = argparse.ArgumentParser(description='한국 경제 캘린더')
    parser.add_argument('--days-ahead', type=int, default=DEFAULT_LOOKAHEAD_DAYS,
                        help=f'향후 조회 일수 (기본: {DEFAULT_LOOKAHEAD_DAYS}, 최대: {MAX_LOOKAHEAD_DAYS})')
    parser.add_argument('--impact', default=None,
                        help='임팩트 필터 (예: H,M)')
    parser.add_argument('--output-dir', default='./output',
                        help='출력 디렉토리')
    args = parser.parse_args()

    impact_filter = None
    if args.impact:
        impact_filter = [x.strip().upper() for x in args.impact.split(',')]

    result = run_calendar(
        days_ahead=args.days_ahead,
        impact_filter=impact_filter,
        output_dir=args.output_dir,
    )

    s = result['summary']
    print(f'[EconomicCalendar] 향후 {s["days_ahead"]}일: '
          f'{s["total"]}개 이벤트 '
          f'(H:{s["high_impact"]}, M:{s["medium_impact"]}, L:{s["low_impact"]})')
    print(f'[EconomicCalendar] 리포트 저장: {args.output_dir}/')


if __name__ == '__main__':
    main()
