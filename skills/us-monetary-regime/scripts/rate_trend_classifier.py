"""us-monetary-regime: 금리 트렌드 5단계 분류."""


# --- Rate Regimes ---

RATE_REGIMES = {
    'aggressive_hike': {'range': (0, 20), 'label': '급격한 인상기'},
    'gradual_hike': {'range': (20, 40), 'label': '점진적 인상기'},
    'hold': {'range': (40, 60), 'label': '동결기'},
    'gradual_cut': {'range': (60, 80), 'label': '점진적 인하기'},
    'aggressive_cut': {'range': (80, 100), 'label': '급격한 인하기'},
}

CHANGE_THRESHOLDS = {
    'aggressive': 50,  # bp
    'gradual': 25,     # bp
}

# --- Yield Curve Weights (sum = 1.00) ---

YIELD_CURVE_WEIGHTS = {
    'level': 0.50,
    'direction': 0.30,
    'market_expectation': 0.20,
}

INVERSION_THRESHOLD = 0  # bp, 2y-10y


def _score_rate_level(current_ffr, ffr_12m_ago):
    """현재 금리 수준과 12개월 전 대비 변화로 점수 산출."""
    diff = current_ffr - ffr_12m_ago  # 양수=인상, 음수=인하

    if diff <= -1.0:
        return 90  # 1%p+ 인하
    elif diff <= -0.5:
        return 75
    elif diff <= -0.25:
        return 65
    elif diff < 0.25:
        return 50  # 거의 변화 없음
    elif diff < 0.5:
        return 35
    elif diff < 1.0:
        return 25
    else:
        return 10  # 1%p+ 인상


def _score_direction(last_change_bp, ffr_6m_ago, current_ffr):
    """금리 방향성 점수."""
    # 최근 변경 기반
    if last_change_bp <= -50:
        change_score = 90
    elif last_change_bp <= -25:
        change_score = 70
    elif last_change_bp == 0:
        change_score = 50
    elif last_change_bp >= 50:
        change_score = 10
    else:  # +25
        change_score = 30

    # 6개월 추세 보조
    trend = current_ffr - ffr_6m_ago
    if trend < -0.25:
        trend_adj = 10
    elif trend > 0.25:
        trend_adj = -10
    else:
        trend_adj = 0

    return max(0, min(100, change_score + trend_adj))


def _score_market_expectation(cut_prob, hike_prob):
    """시장 기대 점수."""
    # cut_prob 높을수록 인하 기대 → 높은 점수
    net = cut_prob - hike_prob  # -1 ~ +1
    return max(0, min(100, 50 + net * 50))


def _classify_regime(score):
    """점수 -> 레짐 분류."""
    for regime, info in RATE_REGIMES.items():
        low, high = info['range']
        if low <= score < high:
            return regime
    if score >= 80:
        return 'aggressive_cut'
    return 'aggressive_hike'


def _get_direction(score):
    """점수 -> 방향."""
    if score < 40:
        return 'rising'
    elif score > 60:
        return 'falling'
    return 'stable'


def _get_yield_curve_signal(spread_bp):
    """2y-10y 스프레드 -> 시그널."""
    if spread_bp < -50:
        return 'deeply_inverted'
    elif spread_bp < INVERSION_THRESHOLD:
        return 'inverted'
    elif spread_bp < 50:
        return 'flat'
    elif spread_bp < 150:
        return 'normal'
    return 'steep'


def classify_rate_trend(current_ffr=5.50, ffr_6m_ago=5.50,
                        ffr_12m_ago=5.50, last_change_bp=0,
                        next_meeting_cut_prob=0.0,
                        next_meeting_hike_prob=0.0,
                        yield_curve_2y10y=0.0):
    """금리 트렌드 분류.

    Args:
        current_ffr: float, 현재 FFR (%).
        ffr_6m_ago: float, 6개월 전 FFR (%).
        ffr_12m_ago: float, 12개월 전 FFR (%).
        last_change_bp: int, 마지막 변경 폭 (bp). +인상, -인하.
        next_meeting_cut_prob: float, 다음 회의 인하 확률 (0~1).
        next_meeting_hike_prob: float, 다음 회의 인상 확률 (0~1).
        yield_curve_2y10y: float, 2y-10y 스프레드 (bp).

    Returns:
        dict: {rate_regime, rate_score, regime_label, direction,
               direction_confidence, yield_curve_signal, components}
    """
    # 각 컴포넌트
    level_score = _score_rate_level(current_ffr, ffr_12m_ago)
    direction_score = _score_direction(last_change_bp, ffr_6m_ago, current_ffr)
    expectation_score = _score_market_expectation(
        next_meeting_cut_prob, next_meeting_hike_prob
    )

    # 가중 합산
    weighted = (
        level_score * YIELD_CURVE_WEIGHTS['level'] +
        direction_score * YIELD_CURVE_WEIGHTS['direction'] +
        expectation_score * YIELD_CURVE_WEIGHTS['market_expectation']
    )
    rate_score = round(max(0, min(100, weighted)), 1)

    # 분류
    regime = _classify_regime(rate_score)
    direction = _get_direction(rate_score)
    yield_signal = _get_yield_curve_signal(yield_curve_2y10y)

    # 방향 확신도
    confidence = abs(rate_score - 50) / 50
    confidence = round(min(1.0, confidence), 2)

    return {
        'rate_regime': regime,
        'rate_score': rate_score,
        'regime_label': RATE_REGIMES[regime]['label'],
        'direction': direction,
        'direction_confidence': confidence,
        'yield_curve_signal': yield_signal,
        'components': {
            'level': {
                'score': level_score,
                'weight': YIELD_CURVE_WEIGHTS['level'],
            },
            'direction': {
                'score': direction_score,
                'weight': YIELD_CURVE_WEIGHTS['direction'],
            },
            'market_expectation': {
                'score': expectation_score,
                'weight': YIELD_CURVE_WEIGHTS['market_expectation'],
            },
        },
    }
