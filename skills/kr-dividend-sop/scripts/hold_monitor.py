"""kr-dividend-sop: Step 3 보유 + Step 4 수령 + Step 5 EXIT.

보유 모니터링, 배당 수령 관리, 매도 판단 트리거를 담당한다.
"""

from datetime import datetime, timedelta

# ─── Step 3: 보유 모니터링 체크리스트 ───

HOLD_CHECKLIST = [
    'dividend_maintained',
    'payout_ratio_safe',
    'debt_ratio_safe',
    'earnings_positive',
    'no_governance_issue',
    'market_cap_maintained',
]

HOLD_STATUS = ['HEALTHY', 'CAUTION', 'WARNING', 'EXIT_SIGNAL']

# ─── Step 4: 한국 배당 캘린더 ───

KR_DIVIDEND_CALENDAR = {
    'record_date_major': '12-31',
    'record_date_mid': '06-30',
    'ex_date_offset': -2,
    'payment_lag_days': (30, 60),
    'interim_dividend_months': [3, 6, 9],
}

EX_DATE_STRATEGY = {
    'hold_through': True,
    'min_holding_days_before_ex': 2,
    'reinvest_after_payment': True,
}

# ─── Step 5: EXIT 트리거 ───

EXIT_TRIGGERS = {
    'dividend_cut': {
        'severity': 'HIGH',
        'action': 'REVIEW',
    },
    'dividend_suspension': {
        'severity': 'CRITICAL',
        'action': 'EXIT',
    },
    'payout_exceed': {
        'severity': 'MEDIUM',
        'threshold': 1.00,
        'action': 'WARN',
    },
    'earnings_loss': {
        'severity': 'HIGH',
        'consecutive_quarters': 2,
        'action': 'REVIEW',
    },
    'debt_spike': {
        'severity': 'MEDIUM',
        'threshold': 2.00,
        'action': 'WARN',
    },
    'price_crash': {
        'severity': 'HIGH',
        'threshold': -0.30,
        'action': 'REVIEW',
    },
}


def check_hold_status(holdings: list) -> list:
    """Step 3: 보유 종목 상태 점검.

    Args:
        holdings: [
            {
                'ticker': str,
                'name': str,
                'dividend_maintained': bool,
                'payout_ratio': float,
                'debt_ratio': float,
                'operating_profit': float,
                'governance_issue': bool,
                'price_change_pct': float,
            },
            ...
        ]

    Returns:
        [{'ticker': str, 'name': str, 'status': str, 'issues': list}, ...]
    """
    results = []
    for h in holdings:
        issues = []

        if not h.get('dividend_maintained', True):
            issues.append('배당 감소/중단 감지')
        if h.get('payout_ratio', 0) > 0.80:
            issues.append(f"배당성향 {h['payout_ratio']:.0%} > 80%")
        if h.get('debt_ratio', 0) > 1.50:
            issues.append(f"부채비율 {h['debt_ratio']:.0%} > 150%")
        if h.get('operating_profit', 1) <= 0:
            issues.append('영업적자 전환')
        if h.get('governance_issue', False):
            issues.append('지배구조 이슈 발생')
        if h.get('price_change_pct', 0) <= -0.30:
            issues.append(f"주가 {h['price_change_pct']:.0%} 급락")

        issue_count = len(issues)
        has_critical = (not h.get('dividend_maintained', True)
                        or h.get('operating_profit', 1) <= 0)

        if issue_count == 0:
            status = 'HEALTHY'
        elif has_critical:
            status = 'EXIT_SIGNAL'
        elif issue_count >= 2:
            status = 'WARNING'
        else:
            status = 'CAUTION'

        results.append({
            'ticker': h.get('ticker', ''),
            'name': h.get('name', ''),
            'status': status,
            'issues': issues,
        })

    return results


def calc_ex_date(record_date_str: str) -> str:
    """배당 기준일로부터 배당락일 계산.

    한국: 기준일 2영업일 전 (주말/공휴일 미고려 간소화 버전).

    Args:
        record_date_str: 'YYYY-MM-DD' 형식 기준일

    Returns:
        'YYYY-MM-DD' 형식 배당락일
    """
    record_date = datetime.strptime(record_date_str, '%Y-%m-%d')
    offset = abs(KR_DIVIDEND_CALENDAR['ex_date_offset'])
    business_days = 0
    current = record_date

    while business_days < offset:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            business_days += 1

    return current.strftime('%Y-%m-%d')


def check_exit_triggers(stock_data: dict) -> dict:
    """Step 5: EXIT 트리거 확인.

    Args:
        stock_data: {
            'current_dps': float,      # 현재 주당배당금
            'prev_dps': float,         # 전년 주당배당금
            'payout_ratio': float,
            'operating_profit_quarters': list,  # 최근 분기 영업이익 리스트
            'debt_ratio': float,
            'price_change_pct': float,  # 최근 N일 주가 변동률
        }

    Returns:
        {'triggered': bool, 'triggers': list}
    """
    triggers_found = []

    current_dps = stock_data.get('current_dps', 0)
    prev_dps = stock_data.get('prev_dps', 0)

    # T1: 감배
    if prev_dps > 0 and current_dps < prev_dps:
        triggers_found.append({
            'id': 'dividend_cut',
            'severity': EXIT_TRIGGERS['dividend_cut']['severity'],
            'action': EXIT_TRIGGERS['dividend_cut']['action'],
            'detail': f"DPS {prev_dps} → {current_dps} (감배)",
        })

    # T2: 무배당
    if current_dps == 0 and prev_dps > 0:
        triggers_found.append({
            'id': 'dividend_suspension',
            'severity': EXIT_TRIGGERS['dividend_suspension']['severity'],
            'action': EXIT_TRIGGERS['dividend_suspension']['action'],
            'detail': '무배당 전환',
        })

    # T3: 배당성향 초과
    payout = stock_data.get('payout_ratio', 0)
    threshold = EXIT_TRIGGERS['payout_exceed']['threshold']
    if payout > threshold:
        triggers_found.append({
            'id': 'payout_exceed',
            'severity': EXIT_TRIGGERS['payout_exceed']['severity'],
            'action': EXIT_TRIGGERS['payout_exceed']['action'],
            'detail': f"배당성향 {payout:.0%} > {threshold:.0%}",
        })

    # T4: 연속 영업적자
    op_quarters = stock_data.get('operating_profit_quarters', [])
    consec = EXIT_TRIGGERS['earnings_loss']['consecutive_quarters']
    if len(op_quarters) >= consec:
        recent = op_quarters[-consec:]
        if all(q <= 0 for q in recent):
            triggers_found.append({
                'id': 'earnings_loss',
                'severity': EXIT_TRIGGERS['earnings_loss']['severity'],
                'action': EXIT_TRIGGERS['earnings_loss']['action'],
                'detail': f"{consec}분기 연속 영업적자",
            })

    # T5: 부채비율 급등
    debt = stock_data.get('debt_ratio', 0)
    debt_threshold = EXIT_TRIGGERS['debt_spike']['threshold']
    if debt > debt_threshold:
        triggers_found.append({
            'id': 'debt_spike',
            'severity': EXIT_TRIGGERS['debt_spike']['severity'],
            'action': EXIT_TRIGGERS['debt_spike']['action'],
            'detail': f"부채비율 {debt:.0%} > {debt_threshold:.0%}",
        })

    # T6: 주가 급락
    price_chg = stock_data.get('price_change_pct', 0)
    crash_threshold = EXIT_TRIGGERS['price_crash']['threshold']
    if price_chg <= crash_threshold:
        triggers_found.append({
            'id': 'price_crash',
            'severity': EXIT_TRIGGERS['price_crash']['severity'],
            'action': EXIT_TRIGGERS['price_crash']['action'],
            'detail': f"주가 {price_chg:.0%} 급락",
        })

    return {
        'triggered': len(triggers_found) > 0,
        'triggers': triggers_found,
    }


def generate_dividend_calendar(holdings: list,
                                year: int = None) -> list:
    """배당 일정 캘린더 생성.

    Args:
        holdings: [{'ticker': str, 'name': str, 'record_date': str, 'dps': float}, ...]
        year: 기준 연도 (기본: 현재 연도)

    Returns:
        [{'ticker': str, 'name': str, 'record_date': str,
          'ex_date': str, 'payment_start': str, 'payment_end': str, 'dps': float}, ...]
    """
    if year is None:
        year = datetime.now().year

    calendar = []
    lag_min, lag_max = KR_DIVIDEND_CALENDAR['payment_lag_days']

    for h in holdings:
        record_str = h.get('record_date', f"{year}-12-31")
        ex_date = calc_ex_date(record_str)
        record_dt = datetime.strptime(record_str, '%Y-%m-%d')
        pay_start = (record_dt + timedelta(days=lag_min)).strftime('%Y-%m-%d')
        pay_end = (record_dt + timedelta(days=lag_max)).strftime('%Y-%m-%d')

        calendar.append({
            'ticker': h.get('ticker', ''),
            'name': h.get('name', ''),
            'record_date': record_str,
            'ex_date': ex_date,
            'payment_start': pay_start,
            'payment_end': pay_end,
            'dps': h.get('dps', 0),
        })

    calendar.sort(key=lambda x: x['ex_date'])
    return calendar
