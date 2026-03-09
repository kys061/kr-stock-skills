"""당월 주요 일정 수집 모듈.

정적 일정(monthly_events.json) + 동적 일정(WebSearch)을 병합하여 제공.
"""

import calendar
import json
import logging
import os
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

EVENTS_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'references', 'monthly_events.json'
)


def get_recurring_date(year: int, month: int, rule: str) -> Optional[str]:
    """반복 일정의 실제 날짜를 계산.

    Args:
        year: 연도
        month: 월
        rule: '2nd_thursday', '3rd_friday' 등

    Returns:
        'YYYY-MM-DD' 형식 날짜 문자열, 해당 없으면 None
    """
    parts = rule.split('_')
    if len(parts) != 2:
        return None

    ordinal_map = {'1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5}
    day_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2,
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
    }

    ordinal_str = parts[0].lower()
    day_str = parts[1].lower()

    ordinal = ordinal_map.get(ordinal_str)
    target_weekday = day_map.get(day_str)

    if ordinal is None or target_weekday is None:
        return None

    count = 0
    _, days_in_month = calendar.monthrange(year, month)
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() == target_weekday:
            count += 1
            if count == ordinal:
                return d.strftime('%Y-%m-%d')

    return None


def load_static_events(year: int, month: int) -> list:
    """정적 일정 파일에서 당월 일정 로드.

    Args:
        year: 연도
        month: 월

    Returns:
        [{'date': str, 'event': str, 'category': str, 'source': 'static'}, ...]
    """
    events = []

    try:
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"일정 파일 로드 실패: {e}")
        return events

    # 반복 일정 (recurring)
    recurring = data.get('recurring', {})
    for key, info in recurring.items():
        months = info.get('months', [])
        if months == 'all' or month in months:
            day_rule = info.get('day_rule')
            if day_rule:
                event_date = get_recurring_date(year, month, day_rule)
                if event_date:
                    events.append({
                        'date': event_date,
                        'event': info['description'],
                        'category': info.get('category', '기타'),
                        'source': 'static',
                    })
            else:
                # day_rule 없으면 날짜 미정 — 월 중순으로 임시 배치
                events.append({
                    'date': f'{year}-{month:02d}-15',
                    'event': info['description'],
                    'category': info.get('category', '기타'),
                    'source': 'static',
                })

    # 연도별 특수 일정
    year_data = data.get(str(year), {})
    month_data = year_data.get(f'{month:02d}', [])
    for item in month_data:
        events.append({
            'date': item['date'],
            'event': item['event'],
            'category': item.get('category', '기타'),
            'source': 'static',
        })

    events.sort(key=lambda x: x['date'])
    return events


def merge_events(static: list, dynamic: list = None) -> list:
    """정적 + 동적 일정을 병합하고 중복 제거.

    Args:
        static: load_static_events() 결과
        dynamic: WebSearch 등에서 가져온 일정

    Returns:
        date 순 정렬된 병합 일정 리스트
    """
    if not dynamic:
        return sorted(static, key=lambda x: x['date'])

    merged = list(static)
    existing_events = {(e['date'], e['event'][:10]) for e in static}

    for item in dynamic:
        key = (item.get('date', ''), item.get('event', '')[:10])
        if key not in existing_events:
            item.setdefault('source', 'dynamic')
            merged.append(item)
            existing_events.add(key)

    merged.sort(key=lambda x: x['date'])
    return merged


def format_calendar(events: list, month: int) -> str:
    """일정 리스트를 마크다운 체크리스트로 포맷팅.

    Returns:
        마크다운 문자열
    """
    if not events:
        return f'**{month}월 주요일정 체크리스트**\n- 등록된 일정 없음\n'

    lines = [f'**{month}월 주요일정 체크리스트**']
    for e in events:
        day = e['date'].split('-')[2] if '-' in e['date'] else '??'
        # 앞의 0 제거
        day = day.lstrip('0') or '0'
        lines.append(f"- {month}/{day} {e['event']}")

    return '\n'.join(lines) + '\n'
