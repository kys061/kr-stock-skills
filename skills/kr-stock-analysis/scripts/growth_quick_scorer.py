"""kr-stock-analysis: Growth Quick Score (lightweight, no WebSearch)."""


# --- Growth Quick components ---

GROWTH_QUICK_COMPONENTS = {
    'consensus_eps_growth': {'weight': 0.40, 'source': 'FnGuide'},
    'rd_investment': {'weight': 0.20, 'source': 'DART'},
    'sector_tam_cagr': {'weight': 0.20, 'source': 'sector_tam_database'},
    'policy_score': {'weight': 0.20, 'source': 'korea_policy_roadmap'},
}
# Sum: 0.40+0.20+0.20+0.20 = 1.00

# --- Consensus EPS growth benchmarks ---

CONSENSUS_EPS_BENCHMARKS = {
    'hyper': {'min': 50, 'score': 95},
    'strong': {'min': 25, 'score': 80},
    'moderate': {'min': 10, 'score': 65},
    'low': {'min': 5, 'score': 50},
    'flat': {'min': 0, 'score': 40},
    'decline': {'min': -10, 'score': 25},
    'severe': {'min': -20, 'score': 10},
}

# --- R&D investment benchmarks ---

RD_INVESTMENT_BENCHMARKS = {
    'leader': {'min': 15, 'score': 90},
    'high': {'min': 10, 'score': 75},
    'moderate': {'min': 5, 'score': 60},
    'low': {'min': 2, 'score': 45},
    'minimal': {'min': 0, 'score': 30},
}

# --- Sector TAM CAGR benchmarks ---

SECTOR_TAM_BENCHMARKS = {
    'explosive': {'min': 15, 'score': 90},
    'high': {'min': 10, 'score': 75},
    'moderate': {'min': 7, 'score': 60},
    'low': {'min': 3, 'score': 45},
    'stagnant': {'min': 0, 'score': 30},
}

# --- Policy score map ---

POLICY_QUICK_SCORES = {
    'strong_tailwind': 90,
    'moderate_tailwind': 70,
    'neutral': 50,
    'moderate_headwind': 30,
    'strong_headwind': 10,
}

# --- Sector defaults ---

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

SECTOR_TAM_CAGR = {
    'semiconductor': 12, 'automotive': 4, 'shipbuilding': 8,
    'defense': 7, 'bio_health': 9, 'battery': 15,
    'power_equipment': 10, 'chemical': 3, 'steel': 2,
    'construction': 1, 'financial': 3, 'telecom': 2,
    'utility': 1, 'entertainment': 8,
}

# --- Growth Quick grades ---

GROWTH_QUICK_GRADES = {
    'HIGH_GROWTH': 70,
    'GROWTH': 55,
    'MODERATE': 40,
    'LOW': 0,
}


def score_quick_consensus(eps_growth):
    """Consensus EPS growth rate -> Quick Score."""
    if eps_growth is None:
        return 50.0
    for level in ('hyper', 'strong', 'moderate', 'low', 'flat', 'decline', 'severe'):
        if eps_growth >= CONSENSUS_EPS_BENCHMARKS[level]['min']:
            return float(CONSENSUS_EPS_BENCHMARKS[level]['score'])
    return 10.0


def score_quick_rd(rd_ratio, rd_trend=None):
    """R&D investment ratio -> Quick Score."""
    if rd_ratio is None:
        return 50.0
    base = 50.0
    for level in ('leader', 'high', 'moderate', 'low', 'minimal'):
        if rd_ratio >= RD_INVESTMENT_BENCHMARKS[level]['min']:
            base = float(RD_INVESTMENT_BENCHMARKS[level]['score'])
            break
    if rd_trend == 'increasing':
        base = min(100, base + 5)
    elif rd_trend == 'decreasing':
        base = max(0, base - 5)
    return base


def calc_growth_quick_score(consensus_eps=None, rd_ratio=None,
                            sector=None, policy_level=None):
    """Calculate lightweight Growth Quick Score (no WebSearch).

    Args:
        consensus_eps: float, YoY EPS growth %.
        rd_ratio: float, R&D to revenue %.
        sector: str, sector name for TAM/policy lookup.
        policy_level: str, override policy level.

    Returns:
        {'score', 'grade', 'components'}
    """
    components = {}
    weighted_sum = 0
    total_weight = 0

    # 1. Consensus EPS (40%)
    eps_score = score_quick_consensus(consensus_eps)
    components['consensus_eps_growth'] = {'score': eps_score, 'weight': 0.40}
    weighted_sum += eps_score * 0.40
    total_weight += 0.40

    # 2. R&D investment (20%)
    rd_score = score_quick_rd(rd_ratio)
    components['rd_investment'] = {'score': rd_score, 'weight': 0.20}
    weighted_sum += rd_score * 0.20
    total_weight += 0.20

    # 3. Sector TAM CAGR (20%)
    tam_cagr = SECTOR_TAM_CAGR.get(sector) if sector else None
    if tam_cagr is not None:
        tam_score = 50.0
        for level in ('explosive', 'high', 'moderate', 'low', 'stagnant'):
            if tam_cagr >= SECTOR_TAM_BENCHMARKS[level]['min']:
                tam_score = float(SECTOR_TAM_BENCHMARKS[level]['score'])
                break
    else:
        tam_score = 50.0
    components['sector_tam_cagr'] = {'score': tam_score, 'weight': 0.20}
    weighted_sum += tam_score * 0.20
    total_weight += 0.20

    # 4. Policy score (20%)
    if policy_level is None and sector:
        policy_level = SECTOR_POLICY_DEFAULTS.get(sector, 'neutral')
    p_score = float(POLICY_QUICK_SCORES.get(
        str(policy_level).lower() if policy_level else 'neutral', 50))
    components['policy_score'] = {'score': p_score, 'weight': 0.20}
    weighted_sum += p_score * 0.20
    total_weight += 0.20

    score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

    grade = 'LOW'
    for g in ('HIGH_GROWTH', 'GROWTH', 'MODERATE', 'LOW'):
        if score >= GROWTH_QUICK_GRADES[g]:
            grade = g
            break

    return {
        'score': score,
        'grade': grade,
        'components': components,
    }
