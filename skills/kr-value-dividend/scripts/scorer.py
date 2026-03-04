"""
kr-value-dividend: 4-컴포넌트 스코어링.
Value(40%) + Growth(35%) + Sustainability(20%) + Quality(5%) = 100%.
"""

# ── 가중치 ────────────────────────────────────────────────
WEIGHTS = {
    'value': 0.40,
    'growth': 0.35,
    'sustainability': 0.20,
    'quality': 0.05,
}

# ── 등급 ──────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Excellent',      'min': 85, 'max': 100, 'action': '즉시 매수 고려'},
    {'name': 'Good',           'min': 70, 'max': 84,  'action': '매수 후보'},
    {'name': 'Average',        'min': 55, 'max': 69,  'action': '관찰'},
    {'name': 'Below Average',  'min': 0,  'max': 54,  'action': '패스'},
]

# ── Value Score 임계값 ────────────────────────────────────
PER_THRESHOLDS = [
    (8,  100),
    (10,  80),
    (12,  60),
    (15,  40),
]

PBR_THRESHOLDS = [
    (0.5, 100),
    (0.8,  80),
    (1.0,  60),
    (1.5,  40),
]

VALUE_PER_WEIGHT = 0.6
VALUE_PBR_WEIGHT = 0.4

# ── Growth Score 임계값 ───────────────────────────────────
DIVIDEND_CAGR_THRESHOLDS = [
    (15, 100),
    (10,  80),
    (5,   60),
    (1,   40),
    (0,   20),
]

REVENUE_TREND_BONUS = 10
EPS_TREND_BONUS = 10
GROWTH_MAX = 100

# ── Sustainability Score 임계값 ──────────────────────────
PAYOUT_THRESHOLDS = [
    (30, 100),
    (50,  80),
    (70,  60),
    (80,  40),
]

DE_RATIO_THRESHOLDS = [
    (50,  100),
    (100,  80),
    (150,  60),
]

SUSTAINABILITY_PAYOUT_WEIGHT = 0.6
SUSTAINABILITY_DE_WEIGHT = 0.4


def _score_from_thresholds(value: float, thresholds: list, default: int = 20) -> int:
    """임계값 테이블에서 점수 산출. thresholds: [(threshold, score), ...]"""
    for threshold, score in thresholds:
        if value <= threshold:
            return score
    return default


def _score_from_thresholds_gte(value: float, thresholds: list, default: int = 20) -> int:
    """임계값 테이블에서 점수 산출 (이상 기준). thresholds: [(threshold, score), ...]"""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return default


def calc_value_score(per: float, pbr: float) -> dict:
    """Value Score 계산 (PER + PBR 복합).

    Args:
        per: PER (양수)
        pbr: PBR (양수)
    Returns:
        {'score': int, 'per_score': int, 'pbr_score': int}
    """
    per_score = _score_from_thresholds(per, PER_THRESHOLDS)
    pbr_score = _score_from_thresholds(pbr, PBR_THRESHOLDS)
    score = round(per_score * VALUE_PER_WEIGHT + pbr_score * VALUE_PBR_WEIGHT)
    return {'score': score, 'per_score': per_score, 'pbr_score': pbr_score}


def calc_growth_score(dividend_cagr: float,
                      revenue_trend_positive: bool = False,
                      eps_trend_positive: bool = False) -> dict:
    """Growth Score 계산.

    Args:
        dividend_cagr: 3년 배당 CAGR (%)
        revenue_trend_positive: 매출 3년 양의 추세
        eps_trend_positive: EPS 3년 양의 추세
    Returns:
        {'score': int, 'base_score': int, 'bonuses': dict}
    """
    base = _score_from_thresholds_gte(dividend_cagr, DIVIDEND_CAGR_THRESHOLDS)
    bonuses = {}
    if revenue_trend_positive:
        bonuses['revenue_trend'] = REVENUE_TREND_BONUS
    if eps_trend_positive:
        bonuses['eps_trend'] = EPS_TREND_BONUS

    total = min(base + sum(bonuses.values()), GROWTH_MAX)
    return {'score': total, 'base_score': base, 'bonuses': bonuses}


def calc_sustainability_score(payout_ratio: float, de_ratio: float) -> dict:
    """Sustainability Score 계산.

    Args:
        payout_ratio: 배당성향 (%)
        de_ratio: 부채비율 (%)
    Returns:
        {'score': int, 'payout_score': int, 'de_score': int}
    """
    payout_score = _score_from_thresholds(payout_ratio, PAYOUT_THRESHOLDS)
    de_score = _score_from_thresholds(de_ratio, DE_RATIO_THRESHOLDS)
    score = round(payout_score * SUSTAINABILITY_PAYOUT_WEIGHT + de_score * SUSTAINABILITY_DE_WEIGHT)
    return {'score': score, 'payout_score': payout_score, 'de_score': de_score}


def calc_quality_score(roe: float, opm: float) -> dict:
    """Quality Score 계산.

    Args:
        roe: ROE (%)
        opm: 영업이익률 (%)
    Returns:
        {'score': int, 'roe_score': int, 'opm_score': int}
    """
    # ROE 스코어링
    if roe >= 20:
        roe_score = 100
    elif roe >= 15:
        roe_score = 80
    elif roe >= 10:
        roe_score = 60
    elif roe >= 5:
        roe_score = 40
    else:
        roe_score = 20

    # 영업이익률 스코어링
    if opm >= 20:
        opm_score = 100
    elif opm >= 15:
        opm_score = 80
    elif opm >= 10:
        opm_score = 60
    elif opm >= 5:
        opm_score = 40
    else:
        opm_score = 20

    score = round(roe_score * 0.6 + opm_score * 0.4)
    return {'score': score, 'roe_score': roe_score, 'opm_score': opm_score}


def calc_total_score(value_score: int, growth_score: int,
                     sustainability_score: int, quality_score: int) -> dict:
    """4-컴포넌트 종합 스코어 계산.

    Returns:
        {'total_score': int, 'rating': str, 'action': str, 'components': dict}
    """
    total = round(
        value_score * WEIGHTS['value'] +
        growth_score * WEIGHTS['growth'] +
        sustainability_score * WEIGHTS['sustainability'] +
        quality_score * WEIGHTS['quality']
    )
    total = max(0, min(100, total))

    rating = 'Below Average'
    action = '패스'
    for band in RATING_BANDS:
        if band['min'] <= total <= band['max']:
            rating = band['name']
            action = band['action']
            break

    return {
        'total_score': total,
        'rating': rating,
        'action': action,
        'components': {
            'value': value_score,
            'growth': growth_score,
            'sustainability': sustainability_score,
            'quality': quality_score,
        },
        'weights': WEIGHTS,
    }
