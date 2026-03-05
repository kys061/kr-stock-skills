"""us-monetary-regime: 글로벌 유동성 추적."""


# --- Liquidity Weights (sum = 1.00) ---

LIQUIDITY_WEIGHTS = {
    'fed_bs': 0.30,
    'm2': 0.30,
    'dxy': 0.25,
    'rrp': 0.15,
}

# --- Liquidity Levels ---

LIQUIDITY_LEVELS = {
    'severe_contraction': (0, 20),
    'contraction': (20, 40),
    'stable': (40, 60),
    'expansion': (60, 80),
    'severe_expansion': (80, 100),
}

# --- Fed Balance Sheet Scoring ---

FED_BS_SCORING = {
    'shrinking_fast': 15,   # MoM < -1%
    'shrinking': 30,        # MoM -0.5% ~ -1%
    'stable': 50,           # MoM +-0.5%
    'growing': 70,          # MoM +0.5% ~ +1%
    'growing_fast': 85,     # MoM > +1%
}

# --- M2 Growth Scoring ---

M2_SCORING = {
    'contracting': 20,      # YoY < -2%
    'flat': 40,             # YoY -2% ~ +2%
    'moderate_growth': 60,  # YoY +2% ~ +6%
    'strong_growth': 80,    # YoY > +6%
}

# --- DXY Scoring (inverse: strong dollar = tight liquidity) ---

DXY_SCORING = {
    'strong_rise': 20,      # 3M > +5%
    'mild_rise': 35,        # 3M +1% ~ +5%
    'stable': 50,           # 3M +-1%
    'mild_fall': 65,        # 3M -1% ~ -5%
    'strong_fall': 80,      # 3M < -5%
}


def _score_fed_bs(change_pct):
    """Fed B/S MoM 변화율 -> 점수."""
    if change_pct < -1.0:
        return FED_BS_SCORING['shrinking_fast']
    elif change_pct < -0.5:
        return FED_BS_SCORING['shrinking']
    elif change_pct <= 0.5:
        return FED_BS_SCORING['stable']
    elif change_pct <= 1.0:
        return FED_BS_SCORING['growing']
    return FED_BS_SCORING['growing_fast']


def _score_m2(growth_yoy):
    """M2 YoY 증가율 -> 점수."""
    if growth_yoy < -2.0:
        return M2_SCORING['contracting']
    elif growth_yoy <= 2.0:
        return M2_SCORING['flat']
    elif growth_yoy <= 6.0:
        return M2_SCORING['moderate_growth']
    return M2_SCORING['strong_growth']


def _score_dxy(change_3m):
    """DXY 3개월 변화율 -> 점수 (역관계)."""
    if change_3m > 5.0:
        return DXY_SCORING['strong_rise']
    elif change_3m > 1.0:
        return DXY_SCORING['mild_rise']
    elif change_3m >= -1.0:
        return DXY_SCORING['stable']
    elif change_3m >= -5.0:
        return DXY_SCORING['mild_fall']
    return DXY_SCORING['strong_fall']


def _score_rrp(change_pct):
    """RRP 잔고 변화율 -> 점수.

    RRP 감소 = 유동성 시장 유입 → 높은 점수.
    RRP 증가 = 유동성 시장 이탈 → 낮은 점수.
    """
    if change_pct < -20:
        return 80  # 급격한 RRP 감소 → 유동성 확대
    elif change_pct < -5:
        return 65
    elif change_pct <= 5:
        return 50
    elif change_pct <= 20:
        return 35
    return 20  # 급격한 RRP 증가 → 유동성 축소


def _classify_level(score):
    """점수 -> 유동성 레벨."""
    for level, (low, high) in LIQUIDITY_LEVELS.items():
        if low <= score < high:
            return level
    if score >= 80:
        return 'severe_expansion'
    return 'severe_contraction'


def _get_trend(score):
    """점수 -> 유동성 추세."""
    if score < 40:
        return 'contracting'
    elif score > 60:
        return 'expanding'
    return 'stable'


def track_liquidity(fed_bs_change_pct=0.0, m2_growth_yoy=0.0,
                    dxy_change_3m=0.0, rrp_change_pct=0.0):
    """글로벌 유동성 추적.

    Args:
        fed_bs_change_pct: float, Fed B/S MoM 변화율 (%).
        m2_growth_yoy: float, M2 YoY 증가율 (%).
        dxy_change_3m: float, DXY 3개월 변화율 (%).
        rrp_change_pct: float, RRP 잔고 MoM 변화율 (%).

    Returns:
        dict: {liquidity_score, liquidity_level, liquidity_trend, components}
    """
    bs_score = _score_fed_bs(fed_bs_change_pct)
    m2_score = _score_m2(m2_growth_yoy)
    dxy_score = _score_dxy(dxy_change_3m)
    rrp_score = _score_rrp(rrp_change_pct)

    weighted = (
        bs_score * LIQUIDITY_WEIGHTS['fed_bs'] +
        m2_score * LIQUIDITY_WEIGHTS['m2'] +
        dxy_score * LIQUIDITY_WEIGHTS['dxy'] +
        rrp_score * LIQUIDITY_WEIGHTS['rrp']
    )
    liquidity_score = round(max(0, min(100, weighted)), 1)

    return {
        'liquidity_score': liquidity_score,
        'liquidity_level': _classify_level(liquidity_score),
        'liquidity_trend': _get_trend(liquidity_score),
        'components': {
            'fed_bs': {
                'raw': fed_bs_change_pct,
                'score': bs_score,
                'weight': LIQUIDITY_WEIGHTS['fed_bs'],
            },
            'm2': {
                'raw': m2_growth_yoy,
                'score': m2_score,
                'weight': LIQUIDITY_WEIGHTS['m2'],
            },
            'dxy': {
                'raw': dxy_change_3m,
                'score': dxy_score,
                'weight': LIQUIDITY_WEIGHTS['dxy'],
            },
            'rrp': {
                'raw': rrp_change_pct,
                'score': rrp_score,
                'weight': LIQUIDITY_WEIGHTS['rrp'],
            },
        },
    }
