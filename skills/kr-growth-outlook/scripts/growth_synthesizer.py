"""kr-growth-outlook: 6-component growth score synthesizer."""


# --- 6-component weights ---

GROWTH_COMPONENTS = {
    'tam_sam': {'weight': 0.25, 'label': 'TAM/SAM 시장규모'},
    'competitive_moat': {'weight': 0.20, 'label': '경쟁우위/해자'},
    'pipeline': {'weight': 0.15, 'label': '기술/제품 파이프라인'},
    'earnings_path': {'weight': 0.20, 'label': '실적 성장 경로'},
    'policy_tailwind': {'weight': 0.10, 'label': '정책/규제 순풍'},
    'management': {'weight': 0.10, 'label': '경영진/거버넌스'},
}
# Sum: 0.25+0.20+0.15+0.20+0.10+0.10 = 1.00

# --- Time horizon multipliers ---

TIME_HORIZON_MULTIPLIER = {
    'short_1_3y': {
        'tam_sam': 0.8, 'competitive_moat': 0.9, 'pipeline': 1.3,
        'earnings_path': 1.3, 'policy_tailwind': 0.9, 'management': 0.8,
    },
    'mid_4_7y': {
        'tam_sam': 1.0, 'competitive_moat': 1.2, 'pipeline': 1.1,
        'earnings_path': 1.0, 'policy_tailwind': 1.0, 'management': 0.7,
    },
    'long_10y': {
        'tam_sam': 1.3, 'competitive_moat': 1.3, 'pipeline': 0.7,
        'earnings_path': 0.7, 'policy_tailwind': 1.5, 'management': 1.5,
    },
}

# --- Growth grades ---

GROWTH_GRADES = {
    'S': {'min': 85, 'label': 'Hyper Growth', 'implication': '10년 10배+ 잠재력'},
    'A': {'min': 70, 'label': 'Strong Growth', 'implication': '10년 5배+ 잠재력'},
    'B': {'min': 55, 'label': 'Moderate Growth', 'implication': '10년 2-3배 잠재력'},
    'C': {'min': 40, 'label': 'Slow Growth', 'implication': '시장 수익률 수준'},
    'D': {'min': 0, 'label': 'No Growth / Decline', 'implication': '구조적 하락 리스크'},
}

# --- Composite horizon weights ---

COMPOSITE_HORIZON_WEIGHTS = {
    'short_1_3y': 0.40,
    'mid_4_7y': 0.35,
    'long_10y': 0.25,
}
# Sum: 0.40+0.35+0.25 = 1.00


def _apply_horizon_multiplier(base_scores, horizon):
    """Apply time-horizon multipliers to base component scores.

    Returns: dict with adjusted weights (re-normalized to sum 1.0)
    """
    multipliers = TIME_HORIZON_MULTIPLIER.get(horizon, {})
    adjusted = {}
    total = 0

    for comp, config in GROWTH_COMPONENTS.items():
        mult = multipliers.get(comp, 1.0)
        adjusted_weight = config['weight'] * mult
        adjusted[comp] = adjusted_weight
        total += adjusted_weight

    # Re-normalize
    if total > 0:
        for comp in adjusted:
            adjusted[comp] = adjusted[comp] / total

    return adjusted


def _get_growth_grade(score):
    """Score -> growth grade (S/A/B/C/D)."""
    for grade in ('S', 'A', 'B', 'C', 'D'):
        if score >= GROWTH_GRADES[grade]['min']:
            return grade
    return 'D'


def calc_growth_score(component_scores, horizon='short_1_3y'):
    """Calculate growth score for a single time horizon.

    Args:
        component_scores: {tam_sam: score, competitive_moat: score, ...}
        horizon: 'short_1_3y' | 'mid_4_7y' | 'long_10y'

    Returns:
        {'score', 'grade', 'components', 'horizon'}
    """
    adjusted_weights = _apply_horizon_multiplier(component_scores, horizon)
    weighted_sum = 0
    total_weight = 0
    components_detail = {}

    for comp, config in GROWTH_COMPONENTS.items():
        score = component_scores.get(comp)
        if score is not None:
            score = max(0, min(100, float(score)))
            weight = adjusted_weights.get(comp, config['weight'])
            weighted_sum += score * weight
            total_weight += weight
            components_detail[comp] = {
                'score': score,
                'weight': round(weight, 3),
                'label': config['label'],
            }
        else:
            weight = adjusted_weights.get(comp, config['weight'])
            weighted_sum += 50.0 * weight
            total_weight += weight
            components_detail[comp] = {
                'score': 50.0,
                'weight': round(weight, 3),
                'label': config['label'],
            }

    final_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0
    grade = _get_growth_grade(final_score)

    return {
        'score': final_score,
        'grade': grade,
        'components': components_detail,
        'horizon': horizon,
    }


def analyze_growth_outlook(analysis_data):
    """Full 3-horizon growth outlook analysis.

    Args:
        analysis_data: {tam_sam, competitive_moat, pipeline,
                        earnings_path, policy_tailwind, management}
            Each value is a score (0-100) from respective analyzers.

    Returns:
        {'short', 'mid', 'long', 'composite', 'grade', 'components'}
    """
    short = calc_growth_score(analysis_data, 'short_1_3y')
    mid = calc_growth_score(analysis_data, 'mid_4_7y')
    long = calc_growth_score(analysis_data, 'long_10y')

    # Composite: short 40% + mid 35% + long 25%
    composite_score = round(
        short['score'] * COMPOSITE_HORIZON_WEIGHTS['short_1_3y']
        + mid['score'] * COMPOSITE_HORIZON_WEIGHTS['mid_4_7y']
        + long['score'] * COMPOSITE_HORIZON_WEIGHTS['long_10y'],
        1
    )
    composite_grade = _get_growth_grade(composite_score)

    return {
        'short': short,
        'mid': mid,
        'long': long,
        'composite': composite_score,
        'grade': composite_grade,
        'grade_detail': GROWTH_GRADES.get(composite_grade, {}),
        'components': analysis_data,
    }
