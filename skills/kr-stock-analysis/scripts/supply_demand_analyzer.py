"""kr-stock-analysis: 수급 분석 엔진 (KR 고유)."""


# ─── 수급 분석 ───

SUPPLY_DEMAND_ANALYSIS = {
    'investor_types': [
        'foreign',          # 외국인
        'institution',      # 기관 합계
        'individual',       # 개인
    ],
    'periods': [1, 5, 20, 60],  # 일, 주, 월, 분기
    'signals': {
        'strong_buy': {'foreign': 'buy', 'institution': 'buy'},
        'buy': {'foreign': 'buy', 'institution': 'neutral'},
        'neutral': {},
        'sell': {'foreign': 'sell', 'institution': 'sell'},
        'strong_sell': {'foreign': 'sell', 'institution': 'sell', 'individual': 'buy'},
    },
}

# ─── 수급 강도 기준 ───

FLOW_THRESHOLDS = {
    'strong_buy': 1_000_000_000,    # 10억 이상 순매수
    'buy': 100_000_000,             # 1억 이상 순매수
    'neutral_band': 100_000_000,    # ±1억 중립
    'sell': -100_000_000,           # 1억 이상 순매도
    'strong_sell': -1_000_000_000,  # 10억 이상 순매도
}


def _classify_flow(net_amount):
    """개별 투자자 순매수/매도 분류."""
    if net_amount is None:
        return 'neutral'
    if net_amount >= FLOW_THRESHOLDS['strong_buy']:
        return 'strong_buy'
    elif net_amount >= FLOW_THRESHOLDS['buy']:
        return 'buy'
    elif net_amount > FLOW_THRESHOLDS['sell']:
        return 'neutral'
    elif net_amount > FLOW_THRESHOLDS['strong_sell']:
        return 'sell'
    else:
        return 'strong_sell'


def classify_supply_signal(foreign_net, inst_net, individual_net=None):
    """수급 시그널 분류.

    Args:
        foreign_net: 외국인 순매수 금액 (원).
        inst_net: 기관 순매수 금액 (원).
        individual_net: 개인 순매수 금액 (원, optional).

    Returns:
        str: 'STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL'
    """
    f_flow = _classify_flow(foreign_net)
    i_flow = _classify_flow(inst_net)
    p_flow = _classify_flow(individual_net) if individual_net is not None else 'neutral'

    # STRONG_SELL: 외국인+기관 매도 + 개인 매수 (개인 물량 받기)
    if f_flow in ('sell', 'strong_sell') and i_flow in ('sell', 'strong_sell'):
        if p_flow in ('buy', 'strong_buy'):
            return 'STRONG_SELL'
        return 'SELL'

    # STRONG_BUY: 외국인+기관 동시 매수
    if f_flow in ('buy', 'strong_buy') and i_flow in ('buy', 'strong_buy'):
        return 'STRONG_BUY'

    # BUY: 외국인 매수 (기관 중립)
    if f_flow in ('buy', 'strong_buy') and i_flow == 'neutral':
        return 'BUY'

    # SELL: 외국인 매도 (기관 중립)
    if f_flow in ('sell', 'strong_sell') and i_flow == 'neutral':
        return 'SELL'

    return 'NEUTRAL'


def _score_investor_flow(flow_data, periods):
    """투자자별 수급 점수."""
    scores = []
    # 기간별 가중치: 최근이 더 중요
    period_weights = {1: 0.35, 5: 0.30, 20: 0.20, 60: 0.15}

    for period in periods:
        net = flow_data.get(period, 0)
        weight = period_weights.get(period, 0.1)
        flow_class = _classify_flow(net)

        if flow_class == 'strong_buy':
            scores.append(90 * weight)
        elif flow_class == 'buy':
            scores.append(70 * weight)
        elif flow_class == 'neutral':
            scores.append(50 * weight)
        elif flow_class == 'sell':
            scores.append(30 * weight)
        else:  # strong_sell
            scores.append(10 * weight)

    return round(sum(scores), 1) if scores else 50.0


def analyze_supply_demand(investor_data, periods=None):
    """종합 수급 분석.

    Args:
        investor_data: dict with structure:
            {
                'foreign': {1: net_amount, 5: net_amount, 20: ..., 60: ...},
                'institution': {1: ..., 5: ..., 20: ..., 60: ...},
                'individual': {1: ..., 5: ..., 20: ..., 60: ...},
            }
        periods: list of periods to analyze (default: [1, 5, 20, 60])

    Returns:
        dict: {foreign, institution, individual, signal, score}
    """
    if periods is None:
        periods = SUPPLY_DEMAND_ANALYSIS['periods']

    foreign = investor_data.get('foreign', {})
    institution = investor_data.get('institution', {})
    individual = investor_data.get('individual', {})

    # 투자자별 수급 점수
    foreign_score = _score_investor_flow(foreign, periods)
    inst_score = _score_investor_flow(institution, periods)
    individual_score = _score_investor_flow(individual, periods)

    # 최근(1일) 기준 시그널 분류
    signal = classify_supply_signal(
        foreign.get(1, 0),
        institution.get(1, 0),
        individual.get(1, 0),
    )

    # 수급 종합: 외국인 45% + 기관 35% + 개인 역방향 20%
    # 개인은 역지표 (개인 매수 = 부정적)
    individual_inverse = 100 - individual_score
    total = (foreign_score * 0.45 + inst_score * 0.35
             + individual_inverse * 0.20)

    return {
        'foreign': {
            'flows': foreign,
            'score': foreign_score,
        },
        'institution': {
            'flows': institution,
            'score': inst_score,
        },
        'individual': {
            'flows': individual,
            'score': individual_score,
        },
        'signal': signal,
        'score': round(total, 1),
    }
