"""kr-growth-outlook: Moat (competitive advantage) scorer."""


# --- 5-type Moat weights ---

MOAT_TYPES = {
    'cost_advantage': {'weight': 0.20, 'label': '원가 우위'},
    'switching_cost': {'weight': 0.20, 'label': '전환 비용'},
    'network_effect': {'weight': 0.15, 'label': '네트워크 효과'},
    'intangible_assets': {'weight': 0.25, 'label': '무형자산'},
    'efficient_scale': {'weight': 0.20, 'label': '효율적 규모'},
}
# Sum: 0.20+0.20+0.15+0.25+0.20 = 1.00

# --- Moat strength thresholds ---

MOAT_STRENGTH = {
    'wide': {'min': 75, 'description': '넓은 해자 (10년+ 방어 가능)'},
    'narrow': {'min': 50, 'description': '좁은 해자 (5-10년 방어)'},
    'none': {'min': 0, 'description': '해자 없음 (경쟁 심화 위험)'},
}


def score_moat_type(moat_data):
    """Score 5 moat types with weighted average.

    Args:
        moat_data: dict of {type_name: score (0-100)}

    Returns:
        {'type_scores': {...}, 'weighted_score': float}
    """
    type_scores = {}
    weighted_sum = 0
    total_weight = 0

    for moat_type, config in MOAT_TYPES.items():
        score = moat_data.get(moat_type)
        if score is not None:
            score = max(0, min(100, float(score)))
            type_scores[moat_type] = score
            weighted_sum += score * config['weight']
            total_weight += config['weight']
        else:
            type_scores[moat_type] = 50.0
            weighted_sum += 50.0 * config['weight']
            total_weight += config['weight']

    weighted_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

    return {
        'type_scores': type_scores,
        'weighted_score': weighted_score,
    }


def classify_moat_strength(score):
    """Classify moat strength: 'wide', 'narrow', 'none'."""
    if score >= MOAT_STRENGTH['wide']['min']:
        return 'wide'
    elif score >= MOAT_STRENGTH['narrow']['min']:
        return 'narrow'
    return 'none'


def analyze_competitive_moat(moat_indicators):
    """Comprehensive moat analysis.

    Args:
        moat_indicators: dict of {moat_type: score (0-100)}

    Returns:
        {'score', 'strength', 'type_scores', 'top_moats'}
    """
    result = score_moat_type(moat_indicators)
    score = result['weighted_score']
    strength = classify_moat_strength(score)

    # Identify top moats (score >= 70)
    top_moats = [
        {'type': t, 'score': s, 'label': MOAT_TYPES[t]['label']}
        for t, s in result['type_scores'].items()
        if s >= 70
    ]
    top_moats.sort(key=lambda x: x['score'], reverse=True)

    return {
        'score': score,
        'strength': strength,
        'type_scores': result['type_scores'],
        'top_moats': top_moats,
    }
