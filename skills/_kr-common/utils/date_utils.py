"""날짜 유틸리티 - 영업일 계산, 날짜 형식 변환."""

from datetime import datetime, timedelta


def today() -> str:
    """오늘 날짜 'YYYY-MM-DD'."""
    return datetime.now().strftime('%Y-%m-%d')


def to_krx_format(date_str: str) -> str:
    """'YYYY-MM-DD' → 'YYYYMMDD'. 이미 YYYYMMDD 형식이면 그대로 반환."""
    if date_str and '-' in date_str:
        return date_str.replace('-', '')
    return date_str


def from_krx_format(date_str: str) -> str:
    """'YYYYMMDD' → 'YYYY-MM-DD'. 이미 YYYY-MM-DD 형식이면 그대로 반환."""
    if date_str and '-' not in date_str and len(date_str) == 8:
        return f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
    return date_str


def parse_date(date_str: str) -> datetime:
    """날짜 문자열을 datetime으로 변환. YYYY-MM-DD, YYYYMMDD 모두 지원."""
    date_str = date_str.strip()
    if '-' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%d')
    return datetime.strptime(date_str, '%Y%m%d')


def get_recent_trading_day(date_str: str = None) -> str:
    """가장 최근 영업일 반환. 주말이면 직전 금요일.

    Args:
        date_str: 기준 날짜 (None이면 오늘)

    Returns:
        'YYYY-MM-DD' 형식 영업일
    """
    if date_str:
        dt = parse_date(date_str)
    else:
        dt = datetime.now()

    # 주말이면 금요일로
    while dt.weekday() >= 5:  # 5=토, 6=일
        dt -= timedelta(days=1)

    return dt.strftime('%Y-%m-%d')


def get_n_days_ago(n: int, from_date: str = None) -> str:
    """n 영업일 전 날짜.

    Args:
        n: 영업일 수
        from_date: 기준 날짜 (None이면 오늘)

    Returns:
        'YYYY-MM-DD' 형식
    """
    if from_date:
        dt = parse_date(from_date)
    else:
        dt = datetime.now()

    count = 0
    while count < n:
        dt -= timedelta(days=1)
        if dt.weekday() < 5:  # 평일
            count += 1

    return dt.strftime('%Y-%m-%d')


def date_range(start: str, end: str) -> list:
    """시작일~종료일 사이의 영업일 목록.

    Args:
        start: 시작일 'YYYY-MM-DD'
        end: 종료일 'YYYY-MM-DD'

    Returns:
        영업일 목록 ['YYYY-MM-DD', ...]
    """
    start_dt = parse_date(start)
    end_dt = parse_date(end)

    result = []
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:
            result.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return result


def ensure_date_format(date_str: str) -> str:
    """날짜를 YYYY-MM-DD 형식으로 정규화."""
    if not date_str:
        return today()
    return from_krx_format(to_krx_format(date_str.strip()))
