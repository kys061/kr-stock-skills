"""미국 경제지표 발표 일정 추적 모듈.

release_calendar.json 기반 정적 일정 + WebSearch 동적 컨센서스 병합.
"""

import json
import os
from datetime import datetime, timedelta

# 중요도 → 별 매핑
IMPORTANCE_STARS = {1: '★', 2: '★★', 3: '★★★', 4: '★★★★', 5: '★★★★★'}

# 기본 발표 패턴 (release_calendar.json 미존재 시 폴백)
DEFAULT_RELEASE_PATTERNS = {
    'cpi': {'name_kr': 'CPI', 'importance': 5, 'source': 'BLS'},
    'ppi': {'name_kr': 'PPI', 'importance': 3, 'source': 'BLS'},
    'pce': {'name_kr': 'PCE', 'importance': 5, 'source': 'BEA'},
    'unemployment': {'name_kr': '고용보고서', 'importance': 5, 'source': 'BLS'},
    'jobless_claims': {'name_kr': '실업수당', 'importance': 2, 'source': 'DOL'},
    'retail_sales': {'name_kr': '소매판매', 'importance': 4, 'source': 'Census'},
    'ism_pmi': {'name_kr': 'ISM PMI', 'importance': 4, 'source': 'ISM'},
    'consumer_sentiment': {'name_kr': '소비자심리', 'importance': 3, 'source': 'UMich'},
    'consumer_confidence': {'name_kr': '소비자신뢰', 'importance': 3, 'source': 'CB'},
    'gdp': {'name_kr': 'GDP', 'importance': 5, 'source': 'BEA'},
    'fed_rate': {'name_kr': 'FOMC 금리결정', 'importance': 5, 'source': 'Fed'},
    'housing_starts': {'name_kr': '주택착공', 'importance': 2, 'source': 'Census'},
    'business_inventories': {'name_kr': '기업재고', 'importance': 2, 'source': 'Census'},
    'inflation_exp': {'name_kr': '인플레 기대', 'importance': 3, 'source': 'UMich'},
    'current_account': {'name_kr': '경상수지', 'importance': 3, 'source': 'BEA'},
}


def load_release_calendar() -> dict:
    """references/release_calendar.json 로드."""
    cal_path = os.path.join(
        os.path.dirname(__file__), '..', 'references', 'release_calendar.json'
    )
    try:
        with open(cal_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_upcoming_releases(days: int = 14,
                          websearch_context: dict = None) -> list:
    """향후 N일간 발표 예정 일정 조회.

    Args:
        days: 조회 기간 (기본 14일)
        websearch_context: WebSearch로 수집한 일정 + 컨센서스
            {
                'events': [
                    {'date': '2026-03-12', 'indicator': 'cpi',
                     'forecast': '2.8%', 'previous': '2.9%'},
                ]
            }

    Returns:
        정렬된 발표 일정 리스트
    """
    calendar = load_release_calendar()
    release_patterns = calendar.get('release_patterns', DEFAULT_RELEASE_PATTERNS)

    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    # 1. 정적 일정에서 범위 내 이벤트 수집
    events = []
    seen_keys = set()

    for month_key, month_data in calendar.items():
        if not isinstance(month_data, dict) or 'events' not in month_data:
            continue
        for evt in month_data['events']:
            try:
                evt_date = datetime.strptime(evt['date'], '%Y-%m-%d').date()
            except (ValueError, KeyError):
                continue

            if today <= evt_date <= end_date:
                ind_id = evt.get('indicator', '')
                pattern = release_patterns.get(ind_id, {})
                importance = pattern.get('importance',
                                         evt.get('importance', 3))
                event_entry = {
                    'date': evt['date'],
                    'indicator_id': ind_id,
                    'name_kr': evt.get('name', pattern.get('name_kr', ind_id)),
                    'forecast': None,
                    'previous': None,
                    'importance': importance,
                    'stars': IMPORTANCE_STARS.get(importance, '★★★'),
                    'source': pattern.get('source', ''),
                }
                key = (evt['date'], ind_id)
                if key not in seen_keys:
                    events.append(event_entry)
                    seen_keys.add(key)

    # 2. FOMC 일정 추가
    fomc_dates = calendar.get('fomc_dates_2026', [])
    for fomc_date_str in fomc_dates:
        try:
            fomc_date = datetime.strptime(fomc_date_str, '%Y-%m-%d').date()
        except ValueError:
            continue
        if today <= fomc_date <= end_date:
            key = (fomc_date_str, 'fed_rate')
            if key not in seen_keys:
                events.append({
                    'date': fomc_date_str,
                    'indicator_id': 'fed_rate',
                    'name_kr': 'FOMC 금리 결정',
                    'forecast': None,
                    'previous': None,
                    'importance': 5,
                    'stars': '★★★★★',
                    'source': 'Fed',
                })
                seen_keys.add(key)

    # 3. WebSearch 컨텍스트에서 동적 일정/컨센서스 병합
    ws = websearch_context or {}
    ws_events = ws.get('events', [])

    for ws_evt in ws_events:
        ws_date = ws_evt.get('date', '')
        ws_ind = ws_evt.get('indicator', '')

        # 기존 이벤트에 forecast/previous 병합
        merged = False
        for evt in events:
            if evt['date'] == ws_date and evt['indicator_id'] == ws_ind:
                if ws_evt.get('forecast'):
                    evt['forecast'] = ws_evt['forecast']
                if ws_evt.get('previous'):
                    evt['previous'] = ws_evt['previous']
                merged = True
                break

        # 새로운 이벤트 추가
        if not merged:
            try:
                evt_date = datetime.strptime(ws_date, '%Y-%m-%d').date()
            except (ValueError, KeyError):
                continue
            if today <= evt_date <= end_date:
                pattern = release_patterns.get(ws_ind, {})
                importance = pattern.get('importance', 3)
                key = (ws_date, ws_ind)
                if key not in seen_keys:
                    events.append({
                        'date': ws_date,
                        'indicator_id': ws_ind,
                        'name_kr': ws_evt.get('name',
                                              pattern.get('name_kr', ws_ind)),
                        'forecast': ws_evt.get('forecast'),
                        'previous': ws_evt.get('previous'),
                        'importance': importance,
                        'stars': IMPORTANCE_STARS.get(importance, '★★★'),
                        'source': pattern.get('source', ''),
                    })
                    seen_keys.add(key)

    # 4. 정렬: 날짜 오름차순, 같은 날짜면 중요도 내림차순
    events.sort(key=lambda e: (e['date'], -e['importance']))

    return events


def get_next_fomc(calendar: dict = None) -> dict:
    """다음 FOMC 일정 조회."""
    if calendar is None:
        calendar = load_release_calendar()

    today = datetime.now().date()
    fomc_dates = calendar.get('fomc_dates_2026', [])

    for fomc_str in fomc_dates:
        try:
            fomc_date = datetime.strptime(fomc_str, '%Y-%m-%d').date()
            if fomc_date >= today:
                days_until = (fomc_date - today).days
                return {
                    'date': fomc_str,
                    'days_until': days_until,
                    'label': f"FOMC {fomc_str} (D-{days_until})",
                }
        except ValueError:
            continue

    return {'date': None, 'days_until': None, 'label': 'FOMC 일정 없음'}


def format_calendar_section(upcoming: list) -> str:
    """발표 일정을 마크다운 테이블로 포맷팅."""
    lines = ['## 향후 2주 발표 일정', '']

    if not upcoming:
        lines.append('> 향후 14일 내 주요 발표 일정이 없습니다.')
        return '\n'.join(lines)

    lines.append('| 날짜 | 지표 | 예상 | 이전 | 중요도 |')
    lines.append('|------|------|------|------|:------:|')

    for evt in upcoming:
        date_str = evt['date']
        # YYYY-MM-DD → M/DD 형식
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            short_date = f"{dt.month}/{dt.day}"
        except ValueError:
            short_date = date_str

        name = evt.get('name_kr', evt.get('indicator_id', ''))
        forecast = evt.get('forecast') or '-'
        previous = evt.get('previous') or '-'
        stars = evt.get('stars', '★★★')

        lines.append(f"| {short_date} | {name} | {forecast} | {previous} | {stars} |")

    lines.append('')
    return '\n'.join(lines)
