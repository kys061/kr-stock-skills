"""kr-growth-outlook: Earnings growth path projector."""


# --- Consensus EPS growth benchmarks ---

CONSENSUS_EPS_BENCHMARKS = {
    'hyper': {'min': 50, 'score': 95},
    'strong': {'min': 25, 'score': 80},
    'moderate': {'min': 10, 'score': 65},
    'low': {'min': 5, 'score': 50},
    'flat': {'min': 0, 'score': 40},
    'decline': {'min': -10, 'score': 25},
    'severe': {'min': -999, 'score': 10},
}

# --- Operating margin trajectory ---

MARGIN_TRAJECTORY_SCORES = {
    'expanding_fast': {'min': 3, 'score': 90},
    'expanding': {'min': 1, 'score': 75},
    'stable': {'min': -1, 'score': 55},
    'contracting': {'min': -3, 'score': 35},
    'contracting_fast': {'min': -999, 'score': 15},
}

# --- ROIC benchmarks ---

ROIC_BENCHMARKS = {
    'excellent': {'min': 20, 'score': 90},
    'good': {'min': 12, 'score': 75},
    'average': {'min': 8, 'score': 55},
    'poor': {'min': 0, 'score': 30},
    'negative': {'min': -999, 'score': 10},
}

# --- Revenue quality ---

REVENUE_QUALITY_SCORES = {
    'recurring_high': 80,
    'recurring_medium': 55,
    'recurring_low': 30,
    'geographic_global': 80,
    'geographic_regional': 50,
    'geographic_domestic': 20,
}

# --- Earnings component weights ---

EARNINGS_WEIGHTS = {
    'consensus_growth': 0.40,
    'margin_trajectory': 0.25,
    'reinvestment_efficiency': 0.20,
    'revenue_quality': 0.15,
}
# Sum: 0.40+0.25+0.20+0.15 = 1.00


def score_consensus_growth(eps_growth_yoy):
    """Consensus EPS growth rate -> 0-100 score."""
    if eps_growth_yoy is None:
        return 50.0
    for level in ('hyper', 'strong', 'moderate', 'low', 'flat', 'decline', 'severe'):
        if eps_growth_yoy >= CONSENSUS_EPS_BENCHMARKS[level]['min']:
            return float(CONSENSUS_EPS_BENCHMARKS[level]['score'])
    return 10.0


def score_margin_trajectory(opm_change_yoy):
    """OPM change (YoY %p) -> 0-100 score."""
    if opm_change_yoy is None:
        return 50.0
    for level in ('expanding_fast', 'expanding', 'stable',
                  'contracting', 'contracting_fast'):
        if opm_change_yoy >= MARGIN_TRAJECTORY_SCORES[level]['min']:
            return float(MARGIN_TRAJECTORY_SCORES[level]['score'])
    return 15.0


def _score_reinvestment(roic):
    """ROIC -> reinvestment efficiency score."""
    if roic is None:
        return 50.0
    for level in ('excellent', 'good', 'average', 'poor', 'negative'):
        if roic >= ROIC_BENCHMARKS[level]['min']:
            return float(ROIC_BENCHMARKS[level]['score'])
    return 10.0


def _score_revenue_quality(recurring_ratio=None, geographic=None):
    """Revenue quality composite score."""
    scores = []
    if recurring_ratio is not None:
        if recurring_ratio >= 70:
            scores.append(REVENUE_QUALITY_SCORES['recurring_high'])
        elif recurring_ratio >= 40:
            scores.append(REVENUE_QUALITY_SCORES['recurring_medium'])
        else:
            scores.append(REVENUE_QUALITY_SCORES['recurring_low'])

    if geographic is not None:
        key = f'geographic_{geographic}'
        scores.append(REVENUE_QUALITY_SCORES.get(key, 50))

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def analyze_earnings_path(earnings_data):
    """Earnings path comprehensive analysis.

    Args:
        earnings_data: {eps_growth_yoy, opm_change, roic,
                        recurring_ratio, geographic, ...}

    Returns:
        {'consensus_score', 'margin_score', 'reinvestment_score',
         'quality_score', 'score'}
    """
    consensus = score_consensus_growth(earnings_data.get('eps_growth_yoy'))
    margin = score_margin_trajectory(earnings_data.get('opm_change'))
    reinvest = _score_reinvestment(earnings_data.get('roic'))
    quality = _score_revenue_quality(
        earnings_data.get('recurring_ratio'),
        earnings_data.get('geographic'),
    )

    total = (consensus * EARNINGS_WEIGHTS['consensus_growth']
             + margin * EARNINGS_WEIGHTS['margin_trajectory']
             + reinvest * EARNINGS_WEIGHTS['reinvestment_efficiency']
             + quality * EARNINGS_WEIGHTS['revenue_quality'])

    return {
        'consensus_score': round(consensus, 1),
        'margin_score': round(margin, 1),
        'reinvestment_score': round(reinvest, 1),
        'quality_score': round(quality, 1),
        'score': round(total, 1),
    }
