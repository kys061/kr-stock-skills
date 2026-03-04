"""kr-economic-calendar: ECOS API 조회 + 정적 경제 캘린더.

한국은행 ECOS API로 경제지표 최근값을 조회하고,
정적 캘린더로 주요 경제이벤트 발표 일정을 제공한다.
"""

import os
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

IMPACT_HIGH = 'H'
IMPACT_MEDIUM = 'M'
IMPACT_LOW = 'L'

KR_INDICATORS = [
    {'name': '기준금리', 'code': '722Y001', 'frequency': 'irregular',
     'impact': IMPACT_HIGH, 'source': '한국은행'},
    {'name': 'CPI', 'code': '901Y009', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '통계청'},
    {'name': 'GDP 성장률', 'code': '200Y002', 'frequency': 'quarterly',
     'impact': IMPACT_HIGH, 'source': '한국은행'},
    {'name': '고용률', 'code': '901Y055', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '통계청'},
    {'name': '무역수지', 'code': '403Y003', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '관세청'},
    {'name': '산업생산지수', 'code': '901Y033', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '통계청'},
    {'name': '소매판매지수', 'code': '901Y061', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '통계청'},
    {'name': '경상수지', 'code': '301Y013', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '한국은행'},
    {'name': 'BSI', 'code': '512Y014', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
    {'name': 'CSI', 'code': '511Y002', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
    {'name': 'PPI', 'code': '404Y014', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
]

# 금통위 일정 (연 8회)
BOK_RATE_DECISION_MONTHS = [1, 2, 4, 5, 7, 8, 10, 11]

DEFAULT_LOOKAHEAD_DAYS = 7
MAX_LOOKAHEAD_DAYS = 90

# 월별 정적 발표일 매핑 (일반적인 발표일 패턴)
STATIC_RELEASE_DAYS = {
    '무역수지': 1,         # 매월 1일 (속보치)
    'CPI': 3,              # 매월 초 (보통 1-5일)
    'PMI': 1,              # 매월 1일
    '고용률': 15,           # 매월 중순
    'PPI': 15,             # 매월 중순
    '경상수지': 10,         # 매월 중순 (전전월)
    '산업생산지수': 28,     # 매월 말
    '소매판매지수': 28,     # 매월 말
    'BSI': 28,             # 매월 말
    'CSI': 28,             # 매월 말
}

# GDP 발표 월 (분기별)
GDP_RELEASE_MONTHS = [1, 4, 7, 10]  # 분기 종료 후 약 25일
GDP_RELEASE_DAY = 25

# 금통위 발표일 (보통 둘째주 목요일)
BOK_RATE_WEEK = 2  # 둘째주
BOK_RATE_WEEKDAY = 3  # 목요일 (0=월, 3=목)


# ═══════════════════════════════════════════════════════════
# 함수
# ═══════════════════════════════════════════════════════════

def fetch_indicator_value(indicator_code: str, period: str = 'latest',
                          api_key: str = None) -> dict:
    """ECOS API로 경제지표 최근값 조회.

    Args:
        indicator_code: ECOS 통계코드 (예: '722Y001')
        period: 조회 기간 ('latest' 또는 'YYYYMM')
        api_key: ECOS API 키 (None이면 환경변수에서 읽음)

    Returns:
        {'code': str, 'value': float|None, 'date': str, 'error': str|None}
    """
    key = api_key or os.environ.get('ECOS_API_KEY')
    if not key:
        return {'code': indicator_code, 'value': None,
                'date': '', 'error': 'ECOS_API_KEY not set'}

    # ECOS API 호출 (실제 환경에서)
    try:
        import requests
        url = (f'https://ecos.bok.or.kr/api/StatisticSearch/'
               f'{key}/json/kr/1/1/{indicator_code}/M/'
               f'{period}/{period}')
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if 'StatisticSearch' in data:
            row = data['StatisticSearch']['row'][0]
            return {
                'code': indicator_code,
                'value': float(row.get('DATA_VALUE', 0)),
                'date': row.get('TIME', ''),
                'error': None,
            }
        return {'code': indicator_code, 'value': None,
                'date': '', 'error': 'No data returned'}
    except Exception as e:
        return {'code': indicator_code, 'value': None,
                'date': '', 'error': str(e)}


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> int:
    """월의 n번째 특정 요일의 날짜 반환.

    Args:
        year, month: 대상 년월
        weekday: 0=월 ~ 6=일
        n: 몇 번째 (1=첫째, 2=둘째, ...)

    Returns:
        해당 날짜 (int)
    """
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()
    # 첫 번째 해당 요일까지의 차이
    diff = (weekday - first_weekday) % 7
    day = 1 + diff + (n - 1) * 7
    return day


def build_static_calendar(year: int, month: int) -> list:
    """정적 경제 캘린더 생성.

    대부분의 경제지표 발표일은 정형화되어 있어 정적 매핑 사용.

    Args:
        year: 대상 연도
        month: 대상 월

    Returns:
        list of dict: [{'date': 'YYYY-MM-DD', 'name': str, 'impact': str, ...}]
    """
    events = []

    for indicator in KR_INDICATORS:
        name = indicator['name']
        impact = indicator['impact']
        source = indicator['source']
        freq = indicator['frequency']

        # 금통위 (irregular — BOK_RATE_DECISION_MONTHS에 있는 월만)
        if name == '기준금리':
            if month in BOK_RATE_DECISION_MONTHS:
                day = _nth_weekday_of_month(year, month, BOK_RATE_WEEKDAY, BOK_RATE_WEEK)
                events.append({
                    'date': f'{year:04d}-{month:02d}-{day:02d}',
                    'name': '금통위 기준금리 결정',
                    'impact': impact,
                    'source': source,
                    'frequency': freq,
                    'code': indicator['code'],
                })
            continue

        # GDP (quarterly — 특정 월만)
        if name == 'GDP 성장률':
            if month in GDP_RELEASE_MONTHS:
                events.append({
                    'date': f'{year:04d}-{month:02d}-{GDP_RELEASE_DAY:02d}',
                    'name': 'GDP 성장률 (속보치)',
                    'impact': impact,
                    'source': source,
                    'frequency': freq,
                    'code': indicator['code'],
                })
            continue

        # 월간 지표 (정적 발표일)
        if freq == 'monthly' and name in STATIC_RELEASE_DAYS:
            day = STATIC_RELEASE_DAYS[name]
            # 날짜 유효성 검증 (28일이 최대 안전 날짜)
            try:
                dt = datetime(year, month, min(day, 28))
                events.append({
                    'date': dt.strftime('%Y-%m-%d'),
                    'name': name,
                    'impact': impact,
                    'source': source,
                    'frequency': freq,
                    'code': indicator['code'],
                })
            except ValueError:
                pass

    # 날짜순 정렬
    events.sort(key=lambda x: x['date'])
    return events


def get_upcoming_events(days_ahead: int = DEFAULT_LOOKAHEAD_DAYS,
                        impact_filter: list = None,
                        base_date: datetime = None) -> list:
    """향후 N일 경제 이벤트 목록 반환.

    Args:
        days_ahead: 향후 조회 일수 (기본 7, 최대 90)
        impact_filter: 임팩트 필터 (예: ['H', 'M']). None이면 전체.
        base_date: 기준일 (기본 오늘)

    Returns:
        list of dict: 기간 내 경제 이벤트 목록
    """
    days_ahead = min(days_ahead, MAX_LOOKAHEAD_DAYS)
    base = base_date or datetime.now()
    end = base + timedelta(days=days_ahead)

    events = []
    # 기준월과 종료월 사이의 모든 월을 커버
    current = datetime(base.year, base.month, 1)
    while current <= end:
        month_events = build_static_calendar(current.year, current.month)
        for ev in month_events:
            ev_date = datetime.strptime(ev['date'], '%Y-%m-%d')
            if base <= ev_date <= end:
                if impact_filter is None or ev['impact'] in impact_filter:
                    events.append(ev)
        # 다음 월
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    events.sort(key=lambda x: x['date'])
    return events


def classify_impact(indicator_name: str) -> str:
    """경제지표명 → 임팩트 레벨 분류.

    Args:
        indicator_name: 경제지표명 (예: 'CPI', '기준금리')

    Returns:
        'H' | 'M' | 'L' | 'unknown'
    """
    for ind in KR_INDICATORS:
        if ind['name'] == indicator_name:
            return ind['impact']
    return 'unknown'
