"""kr-earnings-calendar: DART 실적 공시 조회 모듈.

DART API를 통해 실적 관련 공시를 조회하고,
시총 필터링 + 공시시간 분류를 수행한다.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'common'))

# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

DART_REPORT_CODES = {
    'annual': 'A001',        # 사업보고서 (4Q 확정)
    'semi_annual': 'A002',   # 반기보고서 (2Q 확정)
    'quarterly': 'A003',     # 분기보고서 (1Q/3Q 확정)
    'preliminary': 'D002',   # 영업(잠정)실적
    'revenue_change': 'D001',  # 매출액/손익구조 변경
}

CONFIRMED_CODES = {'A001', 'A002', 'A003'}
PRELIMINARY_CODES = {'D001', 'D002'}

MARKET_CAP_MIN = 1_000_000_000_000   # 1조원 (시총 필터)
LOOKBACK_DAYS = 7                     # 기본 과거 조회 기간
LOOKAHEAD_DAYS = 14                   # 기본 향후 조회 기간

# 월별 실적 시즌 매핑
EARNINGS_SEASON_MAP = {
    1: {'quarter': '4Q', 'type': 'preliminary'},
    2: {'quarter': '4Q', 'type': 'preliminary'},
    3: {'quarter': '4Q', 'type': 'confirmed'},
    4: {'quarter': '1Q', 'type': 'preliminary'},
    5: {'quarter': '1Q', 'type': 'confirmed'},
    7: {'quarter': '2Q', 'type': 'preliminary'},
    8: {'quarter': '2Q', 'type': 'confirmed'},
    10: {'quarter': '3Q', 'type': 'preliminary'},
    11: {'quarter': '3Q', 'type': 'confirmed'},
}

# 공시시간 분류 경계
MARKET_OPEN_HOUR = 8     # 08:00
MARKET_CLOSE_HOUR = 15   # 15:00
MARKET_CLOSE_MINUTE = 30 # 15:30


# ═══════════════════════════════════════════════════════════
# 함수
# ═══════════════════════════════════════════════════════════

def fetch_recent_disclosures(days_back: int = LOOKBACK_DAYS,
                              days_ahead: int = LOOKAHEAD_DAYS,
                              report_codes: list = None,
                              client=None) -> list:
    """DART 공시 목록 조회 (기간/유형 필터링).

    Args:
        days_back: 과거 몇 일 조회
        days_ahead: 향후 몇 일 조회
        report_codes: DART 공시 코드 목록 (None이면 전체 실적 관련)
        client: KRClient 인스턴스

    Returns:
        list of dict: 공시 목록
    """
    if client is None:
        return []

    if report_codes is None:
        report_codes = list(DART_REPORT_CODES.values())

    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

    try:
        disclosures = client.get_dart_disclosures(
            start_date=start_date,
            end_date=end_date,
            report_codes=report_codes,
        )
        return disclosures if disclosures else []
    except Exception:
        return []


def filter_earnings_disclosures(disclosures: list,
                                 min_market_cap: int = MARKET_CAP_MIN,
                                 client=None) -> list:
    """시총 필터 + 실적 관련 공시만 추출.

    Args:
        disclosures: 원본 공시 목록
        min_market_cap: 최소 시총 (원)
        client: KRClient 인스턴스 (시총 조회용)

    Returns:
        시총 기준 충족하는 실적 공시 목록
    """
    if not disclosures:
        return []

    filtered = []
    for disc in disclosures:
        report_code = disc.get('report_code', '')

        # 실적 관련 공시만
        all_codes = set(DART_REPORT_CODES.values())
        if report_code not in all_codes:
            continue

        # 시총 필터 (client 없으면 스킵)
        if client and min_market_cap > 0:
            ticker = disc.get('ticker', '')
            if ticker:
                try:
                    info = client.get_stock_info(ticker)
                    market_cap = info.get('market_cap', 0)
                    if market_cap < min_market_cap:
                        continue
                    disc['market_cap'] = market_cap
                    disc['name'] = info.get('name', '')
                except Exception:
                    continue

        # 유형 분류
        disc['is_confirmed'] = report_code in CONFIRMED_CODES
        disc['is_preliminary'] = report_code in PRELIMINARY_CODES
        disc['report_type'] = _classify_report_type(report_code)

        filtered.append(disc)

    return filtered


def classify_disclosure_timing(disclosure: dict) -> str:
    """공시 시간 → 장전/장중/장후 분류.

    Args:
        disclosure: 공시 dict (disclosure_time 또는 time 필드 필요)

    Returns:
        'before_open' | 'during_market' | 'after_close' | 'unknown'
    """
    time_str = disclosure.get('disclosure_time', disclosure.get('time', ''))
    if not time_str:
        return 'unknown'

    try:
        # HH:MM 또는 HH:MM:SS 형식
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        if hour < MARKET_OPEN_HOUR:
            return 'before_open'
        elif hour > MARKET_CLOSE_HOUR or (hour == MARKET_CLOSE_HOUR and minute >= MARKET_CLOSE_MINUTE):
            return 'after_close'
        else:
            return 'during_market'
    except (ValueError, IndexError):
        return 'unknown'


def get_current_earnings_season(month: int = None) -> dict:
    """현재 월 → 실적 시즌 (분기/유형) 매핑.

    Args:
        month: 대상 월 (None이면 현재 월)

    Returns:
        {'quarter': str, 'type': str} 또는 {'quarter': None, 'type': 'off_season'}
    """
    if month is None:
        month = datetime.now().month

    if month in EARNINGS_SEASON_MAP:
        return EARNINGS_SEASON_MAP[month]

    return {'quarter': None, 'type': 'off_season'}


def _classify_report_type(report_code: str) -> str:
    """DART 코드 → 보고서 유형명 변환."""
    code_to_name = {
        'A001': '사업보고서',
        'A002': '반기보고서',
        'A003': '분기보고서',
        'D001': '매출액/손익구조변경',
        'D002': '영업(잠정)실적',
    }
    return code_to_name.get(report_code, report_code)
