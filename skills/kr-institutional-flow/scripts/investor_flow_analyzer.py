"""kr-institutional-flow: 투자자별 매매동향 분석.

PyKRX 12분류 데이터를 3분류(외국인/기관/개인)로 축약하고,
연속 순매수/순매도 일수와 시그널 점수를 계산한다.
"""

# ─── 투자자 그룹 매핑 ───
INVESTOR_GROUPS = {
    'foreign': ['외국인'],
    'institutional': ['금융투자', '보험', '투신', '사모', '은행', '연기금'],
    'retail': ['개인'],
    'other': ['기타법인', '기타외국인', '기타금융', '국가'],
}

# ─── 외국인 수급 시그널 상수 ───
FOREIGN_CONSECUTIVE_STRONG = 10
FOREIGN_CONSECUTIVE_MODERATE = 5
FOREIGN_CONSECUTIVE_MILD = 3
FOREIGN_STRONG_AMOUNT = 5_000_000_000      # 50억원/일
FOREIGN_MODERATE_AMOUNT = 1_000_000_000    # 10억원/일

# ─── 기관 수급 시그널 상수 ───
INST_CONSECUTIVE_STRONG = 10
INST_CONSECUTIVE_MODERATE = 5
INST_CONSECUTIVE_MILD = 3
INST_STRONG_AMOUNT = 10_000_000_000        # 100억원/일
INST_MODERATE_AMOUNT = 3_000_000_000       # 30억원/일

# ─── 분석 기간 ───
ANALYSIS_WINDOW = 20
TREND_WINDOW = 60


def aggregate_by_group(daily_data: list, group: str) -> list:
    """12분류 일별 데이터를 특정 그룹의 순매수 리스트로 축약.

    Args:
        daily_data: [{date, investors: {name: net_buy, ...}}, ...]
        group: 'foreign' | 'institutional' | 'retail'

    Returns:
        일별 순매수 금액 리스트 [net_buy_day1, net_buy_day2, ...]
    """
    if group not in INVESTOR_GROUPS:
        return []

    members = INVESTOR_GROUPS[group]
    result = []
    for day in daily_data:
        investors = day.get('investors', {})
        net = sum(investors.get(m, 0) for m in members)
        result.append(net)
    return result


def calc_consecutive_days(net_buys: list) -> dict:
    """가장 최근부터 연속 순매수/순매도 일수 계산.

    Args:
        net_buys: 일별 순매수 리스트 (최근이 마지막)

    Returns:
        {
            'direction': 'buy' | 'sell' | 'neutral',
            'days': int,
            'avg_amount': float
        }
    """
    if not net_buys:
        return {'direction': 'neutral', 'days': 0, 'avg_amount': 0}

    reversed_buys = list(reversed(net_buys))
    first = reversed_buys[0]

    if first > 0:
        direction = 'buy'
    elif first < 0:
        direction = 'sell'
    else:
        return {'direction': 'neutral', 'days': 0, 'avg_amount': 0}

    count = 0
    total = 0
    for val in reversed_buys:
        if (direction == 'buy' and val > 0) or \
           (direction == 'sell' and val < 0):
            count += 1
            total += abs(val)
        else:
            break

    avg_amount = total / count if count > 0 else 0
    return {
        'direction': direction,
        'days': count,
        'avg_amount': avg_amount,
    }


def score_foreign_flow(consecutive_data: dict) -> dict:
    """외국인 수급 시그널 점수 (7등급).

    Args:
        consecutive_data: calc_consecutive_days 결과

    Returns:
        {'score': int, 'signal': str, 'days': int, 'avg_amount': float}
    """
    direction = consecutive_data['direction']
    days = consecutive_data['days']
    avg = consecutive_data['avg_amount']

    if direction == 'buy':
        if days >= FOREIGN_CONSECUTIVE_STRONG and avg >= FOREIGN_STRONG_AMOUNT:
            return _signal_result(100, 'Strong Buy', consecutive_data)
        elif days >= FOREIGN_CONSECUTIVE_MODERATE and avg >= FOREIGN_MODERATE_AMOUNT:
            return _signal_result(80, 'Buy', consecutive_data)
        elif days >= FOREIGN_CONSECUTIVE_MILD:
            return _signal_result(60, 'Mild Buy', consecutive_data)
        else:
            return _signal_result(40, 'Neutral', consecutive_data)
    elif direction == 'sell':
        if days >= FOREIGN_CONSECUTIVE_STRONG and avg >= FOREIGN_STRONG_AMOUNT:
            return _signal_result(0, 'Strong Sell', consecutive_data)
        elif days >= FOREIGN_CONSECUTIVE_MODERATE and avg >= FOREIGN_MODERATE_AMOUNT:
            return _signal_result(15, 'Sell', consecutive_data)
        elif days >= FOREIGN_CONSECUTIVE_MILD:
            return _signal_result(30, 'Mild Sell', consecutive_data)
        else:
            return _signal_result(40, 'Neutral', consecutive_data)
    else:
        return _signal_result(40, 'Neutral', consecutive_data)


def score_institutional_flow(consecutive_data: dict) -> dict:
    """기관 수급 시그널 점수 (7등급).

    Args:
        consecutive_data: calc_consecutive_days 결과

    Returns:
        {'score': int, 'signal': str, 'days': int, 'avg_amount': float}
    """
    direction = consecutive_data['direction']
    days = consecutive_data['days']
    avg = consecutive_data['avg_amount']

    if direction == 'buy':
        if days >= INST_CONSECUTIVE_STRONG and avg >= INST_STRONG_AMOUNT:
            return _signal_result(100, 'Strong Buy', consecutive_data)
        elif days >= INST_CONSECUTIVE_MODERATE and avg >= INST_MODERATE_AMOUNT:
            return _signal_result(80, 'Buy', consecutive_data)
        elif days >= INST_CONSECUTIVE_MILD:
            return _signal_result(60, 'Mild Buy', consecutive_data)
        else:
            return _signal_result(40, 'Neutral', consecutive_data)
    elif direction == 'sell':
        if days >= INST_CONSECUTIVE_STRONG and avg >= INST_STRONG_AMOUNT:
            return _signal_result(0, 'Strong Sell', consecutive_data)
        elif days >= INST_CONSECUTIVE_MODERATE and avg >= INST_MODERATE_AMOUNT:
            return _signal_result(15, 'Sell', consecutive_data)
        elif days >= INST_CONSECUTIVE_MILD:
            return _signal_result(30, 'Mild Sell', consecutive_data)
        else:
            return _signal_result(40, 'Neutral', consecutive_data)
    else:
        return _signal_result(40, 'Neutral', consecutive_data)


def _signal_result(score: int, signal: str, data: dict) -> dict:
    return {
        'score': score,
        'signal': signal,
        'days': data['days'],
        'avg_amount': data['avg_amount'],
    }
