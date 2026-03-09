"""kr-morning-briefing 메인 오케스트레이터.

KST 08:00~09:00 실행, 글로벌 시장 + 월간 일정 + 핫 키워드 브리핑.

Usage (standalone — yfinance only):
    python kr_morning_briefing.py

Usage (SKILL.md — Claude 실행):
    /kr-morning-briefing
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from market_data_collector import collect_all
from monthly_calendar import load_static_events, merge_events
from hot_keyword_analyzer import analyze_hot_keywords
from report_generator import generate_report, save_report


def run_briefing(
    websearch_market: dict = None,
    websearch_calendar: list = None,
    websearch_keywords: dict = None,
) -> dict:
    """장 초반 브리핑 전체 실행.

    Args:
        websearch_market: WebSearch 시장 데이터 (10개 항목)
        websearch_calendar: WebSearch 동적 일정
        websearch_keywords: WebSearch 핫 키워드 뉴스

    Returns:
        {
            'success': bool,
            'report_path': str,
            'execution_time_sec': float,
            'sections': {market_data, calendar, hot_keywords},
        }
    """
    start_time = time.time()
    now = datetime.now()

    # Section 1: 글로벌 시장 데이터
    try:
        market_data = collect_all(websearch_market)
    except Exception as e:
        market_data = {
            'items': {}, 'categories': {},
            'summary': {'total': 27, 'success': 0, 'failed': 27,
                        'timestamp': now.strftime('%Y-%m-%d %H:%M')},
        }

    # Section 2: 당월 일정
    try:
        static_events = load_static_events(now.year, now.month)
        calendar_events = merge_events(static_events, websearch_calendar)
    except Exception as e:
        calendar_events = []

    # Section 3: 핫 키워드
    try:
        hot_keywords = analyze_hot_keywords(websearch_keywords)
    except Exception as e:
        hot_keywords = {'keywords': [], 'one_liner': '', 'keyword_count': 0}

    # 리포트 생성
    execution_time = now.strftime('%Y-%m-%d %H:%M')
    report = generate_report(market_data, calendar_events, hot_keywords, execution_time)

    elapsed = round(time.time() - start_time, 1)

    return {
        'success': True,
        'report_path': report['file_path'],
        'md_content': report['md_content'],
        'execution_time_sec': elapsed,
        'sections': {
            'market_data': market_data.get('summary', {}),
            'calendar': {'events': len(calendar_events)},
            'hot_keywords': {'count': hot_keywords.get('keyword_count', 0)},
        },
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='장 초반 브리핑')
    parser.add_argument('--no-websearch', action='store_true',
                        help='WebSearch 없이 yfinance만 사용')
    parser.add_argument('--month', type=int, default=None,
                        help='일정 조회 월 (기본: 현재 월)')
    args = parser.parse_args()

    result = run_briefing()
    # md_content는 출력에서 제외 (길이)
    output = {k: v for k, v in result.items() if k != 'md_content'}
    print(json.dumps(output, ensure_ascii=False, indent=2))
