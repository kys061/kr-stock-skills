"""kr-growth-outlook: Policy/regulatory tailwind analyzer."""


# --- Policy support levels ---

POLICY_SCORE_MAP = {
    'strong_tailwind': 90,
    'moderate_tailwind': 70,
    'neutral': 50,
    'moderate_headwind': 30,
    'strong_headwind': 10,
}

# --- Regulatory environment ---

REGULATORY_SCORES = {
    'deregulating': 85,
    'stable_favorable': 70,
    'neutral': 50,
    'tightening': 30,
    'hostile': 10,
}

# --- Global alignment ---

ESG_SCORES = {'aligned': 80, 'transitioning': 55, 'lagging': 25}
TRADE_SCORES = {'beneficiary': 80, 'neutral': 50, 'tariff_risk': 20}
TECH_STD_SCORES = {'setter': 90, 'adopter': 60, 'excluded': 20}

# --- Policy component weights ---

POLICY_WEIGHTS = {
    'government_support': 0.40,
    'regulatory_environment': 0.30,
    'global_alignment': 0.30,
}
# Sum: 0.40+0.30+0.30 = 1.00

# --- Sector default policy levels ---

SECTOR_POLICY_DEFAULTS = {
    'semiconductor': 'strong_tailwind',
    'defense': 'strong_tailwind',
    'power_equipment': 'strong_tailwind',
    'bio_health': 'moderate_tailwind',
    'shipbuilding': 'moderate_tailwind',
    'financial': 'moderate_tailwind',
    'entertainment': 'moderate_tailwind',
    'automotive': 'neutral',
    'battery': 'neutral',
    'chemical': 'neutral',
    'telecom': 'neutral',
    'utility': 'neutral',
    'steel': 'moderate_headwind',
    'construction': 'moderate_headwind',
}


def score_government_support(support_level):
    """Government support level -> 0-100 score."""
    if support_level is None:
        return 50.0
    return float(POLICY_SCORE_MAP.get(str(support_level).lower(), 50))


def analyze_policy(policy_data):
    """Policy/regulatory comprehensive analysis.

    Args:
        policy_data: {support_level, regulatory, esg, trade, tech_standards, sector}

    Returns:
        {'support_score', 'regulatory_score', 'global_score', 'score'}
    """
    # Government support
    support_level = policy_data.get('support_level')
    if support_level is None:
        sector = policy_data.get('sector')
        support_level = SECTOR_POLICY_DEFAULTS.get(sector, 'neutral')
    support_score = score_government_support(support_level)

    # Regulatory environment
    reg = policy_data.get('regulatory', 'neutral')
    regulatory_score = float(REGULATORY_SCORES.get(str(reg).lower(), 50))

    # Global alignment (ESG + Trade + Tech Standards)
    global_scores = []
    esg = policy_data.get('esg')
    if esg:
        global_scores.append(float(ESG_SCORES.get(str(esg).lower(), 55)))
    trade = policy_data.get('trade')
    if trade:
        global_scores.append(float(TRADE_SCORES.get(str(trade).lower(), 50)))
    tech = policy_data.get('tech_standards')
    if tech:
        global_scores.append(float(TECH_STD_SCORES.get(str(tech).lower(), 60)))
    global_score = round(sum(global_scores) / len(global_scores), 1) if global_scores else 50.0

    total = (support_score * POLICY_WEIGHTS['government_support']
             + regulatory_score * POLICY_WEIGHTS['regulatory_environment']
             + global_score * POLICY_WEIGHTS['global_alignment'])

    return {
        'support_score': round(support_score, 1),
        'regulatory_score': round(regulatory_score, 1),
        'global_score': round(global_score, 1),
        'score': round(total, 1),
    }
