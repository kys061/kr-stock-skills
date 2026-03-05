"""kr-growth-outlook: TAM/SAM 시장규모 분석."""


# --- TAM CAGR 스코어링 ---

TAM_CAGR_BENCHMARKS = {
    'explosive': {'min': 15, 'score': 90},
    'high': {'min': 10, 'score': 75},
    'moderate': {'min': 7, 'score': 60},
    'low': {'min': 3, 'score': 45},
    'stagnant': {'min': 0, 'score': 30},
    'decline': {'min': -999, 'score': 15},
}

# --- 시장점유율 트렌드 ---

MS_TREND_BENCHMARKS = {
    'gaining_fast': {'delta': 2.0, 'score': 90},
    'gaining': {'delta': 0.5, 'score': 75},
    'stable': {'delta': -0.5, 'score': 50},
    'losing': {'delta': -2.0, 'score': 30},
    'losing_fast': {'delta': -999, 'score': 10},
}

# --- SAM 침투율 (비선형: 5-15% 최적) ---

SAM_PENETRATION_BENCHMARKS = {
    'dominant': {'min': 30, 'score': 70},
    'strong': {'min': 15, 'score': 85},
    'growing': {'min': 5, 'score': 90},
    'emerging': {'min': 1, 'score': 80},
    'nascent': {'min': 0, 'score': 60},
}

# --- 14개 섹터 정적 TAM DB ---

SECTOR_GROWTH_RATINGS = {
    'semiconductor': {'tam_2026': 680e9, 'cagr_26_30': 0.12, 'kr_ms': 0.20, 'grade': 'S'},
    'automotive': {'tam_2026': 3.5e12, 'cagr_26_30': 0.04, 'kr_ms': 0.08, 'grade': 'B'},
    'shipbuilding': {'tam_2026': 150e9, 'cagr_26_30': 0.08, 'kr_ms': 0.40, 'grade': 'A'},
    'defense': {'tam_2026': 2.2e12, 'cagr_26_30': 0.07, 'kr_ms': 0.03, 'grade': 'A'},
    'bio_health': {'tam_2026': 1.8e12, 'cagr_26_30': 0.09, 'kr_ms': 0.02, 'grade': 'A'},
    'battery': {'tam_2026': 180e9, 'cagr_26_30': 0.15, 'kr_ms': 0.25, 'grade': 'A'},
    'power_equipment': {'tam_2026': 250e9, 'cagr_26_30': 0.10, 'kr_ms': 0.05, 'grade': 'A'},
    'chemical': {'tam_2026': 500e9, 'cagr_26_30': 0.03, 'kr_ms': 0.05, 'grade': 'C'},
    'steel': {'tam_2026': 1.4e12, 'cagr_26_30': 0.02, 'kr_ms': 0.03, 'grade': 'C'},
    'construction': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.90, 'grade': 'D'},
    'financial': {'tam_2026': None, 'cagr_26_30': 0.03, 'kr_ms': 0.95, 'grade': 'C'},
    'telecom': {'tam_2026': None, 'cagr_26_30': 0.02, 'kr_ms': 0.99, 'grade': 'D'},
    'utility': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.99, 'grade': 'D'},
    'entertainment': {'tam_2026': 350e9, 'cagr_26_30': 0.08, 'kr_ms': 0.05, 'grade': 'B'},
}


def score_tam_cagr(cagr_percent):
    """TAM CAGR -> 0-100 score."""
    if cagr_percent is None:
        return 50.0
    for level in ('explosive', 'high', 'moderate', 'low', 'stagnant', 'decline'):
        if cagr_percent >= TAM_CAGR_BENCHMARKS[level]['min']:
            return float(TAM_CAGR_BENCHMARKS[level]['score'])
    return 15.0


def score_market_share_trend(current_ms, prev_ms):
    """Market share change (YoY %p) -> 0-100 score."""
    if current_ms is None or prev_ms is None:
        return 50.0
    delta = current_ms - prev_ms
    for level in ('gaining_fast', 'gaining', 'stable', 'losing', 'losing_fast'):
        if delta >= MS_TREND_BENCHMARKS[level]['delta']:
            return float(MS_TREND_BENCHMARKS[level]['score'])
    return 10.0


def score_sam_penetration(sam_share_percent):
    """SAM penetration -> 0-100 score (non-linear: 5-15% is optimal)."""
    if sam_share_percent is None:
        return 50.0
    for level in ('dominant', 'strong', 'growing', 'emerging', 'nascent'):
        if sam_share_percent >= SAM_PENETRATION_BENCHMARKS[level]['min']:
            return float(SAM_PENETRATION_BENCHMARKS[level]['score'])
    return 60.0


def get_sector_tam_data(sector_name):
    """Get static TAM data for a sector."""
    return SECTOR_GROWTH_RATINGS.get(sector_name)


def analyze_tam(sector, market_share=None, prev_market_share=None):
    """TAM/SAM comprehensive analysis.

    Returns: {'cagr_score', 'ms_trend_score', 'penetration_score', 'score'}
    """
    tam_data = get_sector_tam_data(sector)

    if tam_data:
        cagr_pct = tam_data['cagr_26_30'] * 100
        cagr_score = score_tam_cagr(cagr_pct)
        ms = market_share if market_share is not None else tam_data.get('kr_ms', 0) * 100
    else:
        cagr_score = 50.0
        ms = market_share if market_share is not None else None

    ms_trend_score = score_market_share_trend(
        market_share, prev_market_share
    ) if market_share is not None and prev_market_share is not None else 50.0

    penetration_score = score_sam_penetration(ms) if ms is not None else 50.0

    # Weighted: CAGR 40% + MS Trend 30% + Penetration 30%
    total = cagr_score * 0.40 + ms_trend_score * 0.30 + penetration_score * 0.30

    return {
        'cagr_score': round(cagr_score, 1),
        'ms_trend_score': round(ms_trend_score, 1),
        'penetration_score': round(penetration_score, 1),
        'score': round(total, 1),
    }
