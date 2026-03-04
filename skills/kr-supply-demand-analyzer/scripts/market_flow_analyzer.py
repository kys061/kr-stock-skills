"""kr-supply-demand-analyzer: 시장 레벨 수급 분석."""


# ─── 시장 수급 분석 ───

MARKET_FLOW_CONFIG = {
    'markets': ['KOSPI', 'KOSDAQ'],
    'investor_groups': ['foreign', 'institution', 'individual'],
    'consecutive_thresholds': {
        'strong': 10,   # 10일 연속 → 강력
        'moderate': 5,  # 5일 연속 → 보통
        'mild': 3,      # 3일 연속 → 약한
    },
    'amount_thresholds': {
        'foreign': {
            'strong': 500_000_000_000,   # 5000억/일
            'moderate': 100_000_000_000, # 1000억/일
            'mild': 50_000_000_000,      # 500억/일
        },
        'institution': {
            'strong': 300_000_000_000,   # 3000억/일
            'moderate': 100_000_000_000, # 1000억/일
            'mild': 30_000_000_000,      # 300억/일
        },
    },
}

# ─── 시장 수급 시그널 (7단계) ───

MARKET_FLOW_SIGNALS = {
    'STRONG_BUY': {'min_score': 85, 'label': '강력 유입'},
    'BUY': {'min_score': 70, 'label': '유입'},
    'MILD_BUY': {'min_score': 55, 'label': '약한 유입'},
    'NEUTRAL': {'min_score': 45, 'label': '중립'},
    'MILD_SELL': {'min_score': 30, 'label': '약한 유출'},
    'SELL': {'min_score': 15, 'label': '유출'},
    'STRONG_SELL': {'min_score': 0, 'label': '강력 유출'},
}

# ─── 투자자 심리 지수 ───

SENTIMENT_WEIGHTS = {
    'foreign': 0.45,      # 외국인 (코스피 방향 결정)
    'institution': 0.35,  # 기관
    'individual_inverse': 0.20,  # 개인 역지표
}


def _classify_amount(net_amount, investor_type):
    """순매수 금액 기반 강도 분류.

    Args:
        net_amount: 순매수 금액 (원).
        investor_type: 'foreign' 또는 'institution'.

    Returns:
        str: 'strong_buy', 'buy', 'mild_buy', 'neutral',
             'mild_sell', 'sell', 'strong_sell'
    """
    thresholds = MARKET_FLOW_CONFIG['amount_thresholds'].get(investor_type)
    if thresholds is None:
        return 'neutral'

    abs_amount = abs(net_amount) if net_amount else 0
    is_buy = (net_amount or 0) > 0

    if abs_amount >= thresholds['strong']:
        return 'strong_buy' if is_buy else 'strong_sell'
    elif abs_amount >= thresholds['moderate']:
        return 'buy' if is_buy else 'sell'
    elif abs_amount >= thresholds['mild']:
        return 'mild_buy' if is_buy else 'mild_sell'
    return 'neutral'


def _amount_to_score(net_amount, investor_type):
    """순매수 금액 → 0-100 점수 변환."""
    classification = _classify_amount(net_amount, investor_type)
    score_map = {
        'strong_buy': 95,
        'buy': 80,
        'mild_buy': 65,
        'neutral': 50,
        'mild_sell': 35,
        'sell': 20,
        'strong_sell': 5,
    }
    return score_map.get(classification, 50)


def calc_consecutive_days(daily_flows, investor_type):
    """투자자별 연속 매수/매도 일수 계산.

    Args:
        daily_flows: dict {date_str: {foreign: net, institution: net, individual: net}}
                     날짜 내림차순 (최근 → 과거).
        investor_type: 'foreign', 'institution', 'individual'.

    Returns:
        dict: {buy_days, sell_days, direction, strength}
    """
    if not daily_flows:
        return {'buy_days': 0, 'sell_days': 0, 'direction': 'neutral', 'strength': 'none'}

    sorted_dates = sorted(daily_flows.keys(), reverse=True)
    buy_days = 0
    sell_days = 0

    # 최근부터 연속 매수/매도 일수 계산
    first_net = daily_flows[sorted_dates[0]].get(investor_type, 0)
    if first_net > 0:
        for d in sorted_dates:
            if daily_flows[d].get(investor_type, 0) > 0:
                buy_days += 1
            else:
                break
    elif first_net < 0:
        for d in sorted_dates:
            if daily_flows[d].get(investor_type, 0) < 0:
                sell_days += 1
            else:
                break

    # 강도 분류
    max_days = max(buy_days, sell_days)
    thresholds = MARKET_FLOW_CONFIG['consecutive_thresholds']
    if max_days >= thresholds['strong']:
        strength = 'strong'
    elif max_days >= thresholds['moderate']:
        strength = 'moderate'
    elif max_days >= thresholds['mild']:
        strength = 'mild'
    else:
        strength = 'none'

    direction = 'buy' if buy_days > 0 else ('sell' if sell_days > 0 else 'neutral')

    return {
        'buy_days': buy_days,
        'sell_days': sell_days,
        'direction': direction,
        'strength': strength,
    }


def _consecutive_to_score(consecutive_data):
    """연속 매수/매도 → 0-100 점수."""
    direction = consecutive_data['direction']
    strength = consecutive_data['strength']

    strength_scores = {
        'strong': 40,
        'moderate': 25,
        'mild': 10,
        'none': 0,
    }
    bonus = strength_scores.get(strength, 0)

    if direction == 'buy':
        return min(50 + bonus, 100)
    elif direction == 'sell':
        return max(50 - bonus, 0)
    return 50


def calc_investor_sentiment(foreign_score, inst_score, individual_score):
    """투자자 심리 지수 계산.

    Args:
        foreign_score: 외국인 수급 점수 (0-100).
        inst_score: 기관 수급 점수 (0-100).
        individual_score: 개인 수급 점수 (0-100).

    Returns:
        float: 0-100 심리 지수.
    """
    # 개인은 역지표: 개인 매수(높은 점수) = 부정적 → 역전
    individual_inverse = 100 - individual_score

    sentiment = (
        foreign_score * SENTIMENT_WEIGHTS['foreign']
        + inst_score * SENTIMENT_WEIGHTS['institution']
        + individual_inverse * SENTIMENT_WEIGHTS['individual_inverse']
    )
    return round(max(0, min(100, sentiment)), 1)


def _classify_signal(score):
    """점수 → 7단계 시그널 분류."""
    for signal, cfg in MARKET_FLOW_SIGNALS.items():
        if score >= cfg['min_score']:
            return signal
    return 'STRONG_SELL'


def analyze_market_flow(investor_data, market='KOSPI'):
    """시장 레벨 수급 분석.

    Args:
        investor_data: dict {date_str: {foreign: net, institution: net, individual: net}}
        market: 'KOSPI' 또는 'KOSDAQ'.

    Returns:
        dict: {foreign_score, institution_score, individual_score,
               consecutive_days, signal, sentiment_score}
    """
    if not investor_data:
        return {
            'market': market,
            'foreign_score': 50,
            'institution_score': 50,
            'individual_score': 50,
            'consecutive_days': {
                'foreign': {'buy_days': 0, 'sell_days': 0, 'direction': 'neutral', 'strength': 'none'},
                'institution': {'buy_days': 0, 'sell_days': 0, 'direction': 'neutral', 'strength': 'none'},
            },
            'signal': 'NEUTRAL',
            'sentiment_score': 50.0,
        }

    # 최근 날짜의 순매수 금액
    sorted_dates = sorted(investor_data.keys(), reverse=True)
    latest = investor_data[sorted_dates[0]]

    foreign_net = latest.get('foreign', 0)
    inst_net = latest.get('institution', 0)
    individual_net = latest.get('individual', 0)

    # 금액 기반 점수
    foreign_amount_score = _amount_to_score(foreign_net, 'foreign')
    inst_amount_score = _amount_to_score(inst_net, 'institution')
    # 개인은 thresholds가 없으므로 net 기반 단순 계산
    individual_amount_score = 50
    if individual_net > 100_000_000_000:
        individual_amount_score = 80
    elif individual_net > 50_000_000_000:
        individual_amount_score = 65
    elif individual_net < -100_000_000_000:
        individual_amount_score = 20
    elif individual_net < -50_000_000_000:
        individual_amount_score = 35

    # 연속 매수/매도 일수
    foreign_consec = calc_consecutive_days(investor_data, 'foreign')
    inst_consec = calc_consecutive_days(investor_data, 'institution')

    # 연속성 점수 반영 (금액 70% + 연속성 30%)
    foreign_consec_score = _consecutive_to_score(foreign_consec)
    inst_consec_score = _consecutive_to_score(inst_consec)

    foreign_score = round(foreign_amount_score * 0.7 + foreign_consec_score * 0.3, 1)
    inst_score = round(inst_amount_score * 0.7 + inst_consec_score * 0.3, 1)
    individual_score = round(individual_amount_score, 1)

    # 심리 지수
    sentiment = calc_investor_sentiment(foreign_score, inst_score, individual_score)

    # 시그널 (외국인 가중)
    combined = foreign_score * 0.55 + inst_score * 0.45
    signal = _classify_signal(combined)

    return {
        'market': market,
        'foreign_score': foreign_score,
        'institution_score': inst_score,
        'individual_score': individual_score,
        'consecutive_days': {
            'foreign': foreign_consec,
            'institution': inst_consec,
        },
        'signal': signal,
        'sentiment_score': sentiment,
    }
