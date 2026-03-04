"""kr-earnings-calendar: 한국 실적 캘린더 메인 오케스트레이터.

Usage:
    python kr_earnings_calendar.py --days-back 7 --days-ahead 14
    python kr_earnings_calendar.py --output-dir ./output
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'common'))

from dart_earnings_fetcher import (
    fetch_recent_disclosures, filter_earnings_disclosures,
    classify_disclosure_timing, get_current_earnings_season,
    LOOKBACK_DAYS, LOOKAHEAD_DAYS, MARKET_CAP_MIN,
)
from report_generator import EarningsCalendarReportGenerator


def run_earnings_calendar(days_back: int = LOOKBACK_DAYS,
                           days_ahead: int = LOOKAHEAD_DAYS,
                           min_market_cap: int = MARKET_CAP_MIN,
                           output_dir: str = './output',
                           client=None) -> dict:
    """실적 캘린더 조회 + 리포트 생성.

    Args:
        days_back: 과거 조회 일수
        days_ahead: 향후 조회 일수
        min_market_cap: 최소 시총
        output_dir: 출력 디렉토리
        client: KRClient 인스턴스

    Returns:
        {'disclosures': list, 'season': dict, 'summary': dict}
    """
    season = get_current_earnings_season()

    if client is None:
        return {
            'disclosures': [],
            'season': season,
            'summary': {'total': 0, 'confirmed': 0, 'preliminary': 0},
            'error': 'No KRClient provided',
        }

    # DART 공시 조회
    raw = fetch_recent_disclosures(
        days_back=days_back,
        days_ahead=days_ahead,
        client=client,
    )

    # 시총 필터 + 유형 분류
    filtered = filter_earnings_disclosures(
        raw, min_market_cap=min_market_cap, client=client)

    # 공시 시간 분류
    for disc in filtered:
        disc['timing'] = classify_disclosure_timing(disc)

    summary = {
        'total': len(filtered),
        'confirmed': sum(1 for d in filtered if d.get('is_confirmed')),
        'preliminary': sum(1 for d in filtered if d.get('is_preliminary')),
    }

    reporter = EarningsCalendarReportGenerator(output_dir)
    reporter.generate_json(filtered, metadata={'season': season})
    reporter.generate_markdown(filtered, metadata={'season': season})

    return {
        'disclosures': filtered,
        'season': season,
        'summary': summary,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 실적 캘린더')
    parser.add_argument('--days-back', type=int, default=LOOKBACK_DAYS)
    parser.add_argument('--days-ahead', type=int, default=LOOKAHEAD_DAYS)
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    try:
        from kr_client import KRClient
        client = KRClient()
    except ImportError:
        print('[ERROR] KRClient를 찾을 수 없습니다.')
        return

    result = run_earnings_calendar(
        days_back=args.days_back,
        days_ahead=args.days_ahead,
        output_dir=args.output_dir,
        client=client,
    )

    s = result['summary']
    season = result['season']
    print(f'[EarningsCalendar] 현재 시즌: {season.get("quarter", "N/A")} '
          f'({season.get("type", "N/A")})')
    print(f'[EarningsCalendar] {s["total"]}건 '
          f'(확정: {s["confirmed"]}, 잠정: {s["preliminary"]})')


if __name__ == '__main__':
    main()
