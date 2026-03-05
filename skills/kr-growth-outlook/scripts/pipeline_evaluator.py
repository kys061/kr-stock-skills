"""kr-growth-outlook: Technology/Product pipeline evaluator."""


# --- New Product levels ---

NEW_PRODUCT_SCORES = {
    'breakthrough': 90,
    'major': 75,
    'incremental': 55,
    'maintenance': 35,
    'none': 15,
}

# --- R&D Investment benchmarks ---

RD_INVESTMENT_BENCHMARKS = {
    'leader': {'min': 15, 'score': 90},
    'high': {'min': 10, 'score': 75},
    'moderate': {'min': 5, 'score': 60},
    'low': {'min': 2, 'score': 45},
    'minimal': {'min': 0, 'score': 30},
}

# --- Tech position levels ---

TECH_POSITION_SCORES = {
    'leader': 90,
    'fast_follower': 70,
    'follower': 50,
    'laggard': 25,
}

# --- Pipeline component weights ---

PIPELINE_WEIGHTS = {
    'new_products': 0.35,
    'rd_capability': 0.30,
    'tech_position': 0.35,
}
# Sum: 0.35+0.30+0.35 = 1.00


def score_new_products(product_level):
    """New product level -> 0-100 score."""
    if product_level is None:
        return 50.0
    return float(NEW_PRODUCT_SCORES.get(str(product_level).lower(), 50))


def score_rd_capability(rd_to_revenue, patent_growth=None, rd_personnel=None):
    """R&D capability composite score."""
    scores = []

    # R&D to revenue ratio
    if rd_to_revenue is not None:
        for level in ('leader', 'high', 'moderate', 'low', 'minimal'):
            if rd_to_revenue >= RD_INVESTMENT_BENCHMARKS[level]['min']:
                scores.append(RD_INVESTMENT_BENCHMARKS[level]['score'])
                break

    # Patent growth bonus
    if patent_growth is not None:
        if patent_growth >= 20:
            scores.append(85)
        elif patent_growth >= 10:
            scores.append(70)
        elif patent_growth >= 0:
            scores.append(50)
        else:
            scores.append(30)

    # R&D personnel ratio bonus
    if rd_personnel is not None:
        if rd_personnel >= 15:
            scores.append(85)
        elif rd_personnel >= 8:
            scores.append(70)
        elif rd_personnel >= 3:
            scores.append(50)
        else:
            scores.append(30)

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def analyze_pipeline(product_data):
    """Pipeline comprehensive analysis.

    Args:
        product_data: {new_products: str, rd_to_revenue: float,
                       tech_position: str, patent_growth: float, ...}

    Returns:
        {'new_product_score', 'rd_score', 'tech_score', 'score'}
    """
    np_score = score_new_products(product_data.get('new_products'))
    rd_score = score_rd_capability(
        product_data.get('rd_to_revenue'),
        product_data.get('patent_growth'),
        product_data.get('rd_personnel'),
    )
    tech_score = float(TECH_POSITION_SCORES.get(
        str(product_data.get('tech_position', '')).lower(), 50
    ))

    total = (np_score * PIPELINE_WEIGHTS['new_products']
             + rd_score * PIPELINE_WEIGHTS['rd_capability']
             + tech_score * PIPELINE_WEIGHTS['tech_position'])

    return {
        'new_product_score': round(np_score, 1),
        'rd_score': round(rd_score, 1),
        'tech_score': round(tech_score, 1),
        'score': round(total, 1),
    }
