"""
kr-dividend-pullback: 4-컴포넌트 스코어링.
Dividend Growth(40%) + Financial Quality(30%) + Technical Setup(20%) + Valuation(10%) = 100%.
"""

# ── 가중치 ────────────────────────────────────────────────
WEIGHTS = {
    'dividend_growth': 0.40,
    'financial_quality': 0.30,
    'technical_setup': 0.20,
    'valuation': 0.10,
}

# ── 등급 ──────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Strong Buy',  'min': 85, 'max': 100, 'action': '즉시 매수 (RSI 극단적 과매도)'},
    {'name': 'Buy',         'min': 70, 'max': 84,  'action': '매수 (RSI 과매도 구간)'},
    {'name': 'Watch',       'min': 55, 'max': 69,  'action': '관찰 (추가 하락 대기)'},
    {'name': 'Pass',        'min': 0,  'max': 54,  'action': '패스'},
]

# ── Dividend Growth 임계값 ────────────────────────────────
CAGR_THRESHOLDS = [
    (20, 100),
    (15,  85),
    (10,  70),
    (8,   55),
]

CONSECUTIVE_BONUS = {
    5: 10,   # 5년 연속 증가 → +10
    7: 15,   # 7년 연속 → +15
    10: 20,  # 10년 연속 → +20
}

# ── Financial Quality 임계값 ──────────────────────────────
ROE_THRESHOLDS = [
    (20, 100),
    (15,  80),
    (10,  60),
    (5,   40),
]

OPM_THRESHOLDS = [
    (20, 100),
    (15,  80),
    (10,  60),
    (5,   40),
]

DE_THRESHOLDS = [
    (50,  100),
    (100,  80),
    (150,  60),
]

# ── Valuation 임계값 ─────────────────────────────────────
PER_THRESHOLDS = [
    (10, 100),
    (15,  80),
    (20,  60),
    (25,  40),
]

PBR_THRESHOLDS = [
    (0.8, 100),
    (1.0,  80),
    (1.5,  60),
    (2.0,  40),
]


def _score_gte(value: float, thresholds: list, default: int = 20) -> int:
    """이상 기준 점수."""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return default


def _score_lte(value: float, thresholds: list, default: int = 20) -> int:
    """이하 기준 점수."""
    for threshold, score in thresholds:
        if value <= threshold:
            return score
    return default


def calc_dividend_growth_score(cagr: float, consecutive_years: int = 0) -> dict:
    """Dividend Growth 컴포넌트.

    Args:
        cagr: 3년 배당 CAGR (%)
        consecutive_years: 연속 배당 증가 년수
    """
    base = _score_gte(cagr, CAGR_THRESHOLDS)
    bonus = 0
    for years, pts in sorted(CONSECUTIVE_BONUS.items(), reverse=True):
        if consecutive_years >= years:
            bonus = pts
            break
    score = min(100, base + bonus)
    return {'score': score, 'base': base, 'bonus': bonus}


def calc_financial_quality_score(roe: float, opm: float, de_ratio: float) -> dict:
    """Financial Quality 컴포넌트.

    ROE(40%) + OPM(30%) + D/E(30%)
    """
    roe_score = _score_gte(roe, ROE_THRESHOLDS)
    opm_score = _score_gte(opm, OPM_THRESHOLDS)
    de_score = _score_lte(de_ratio, DE_THRESHOLDS)
    score = round(roe_score * 0.4 + opm_score * 0.3 + de_score * 0.3)
    return {'score': score, 'roe_score': roe_score, 'opm_score': opm_score, 'de_score': de_score}


def calc_technical_setup_score(rsi: float) -> dict:
    """Technical Setup 컴포넌트 (RSI 수준).

    낮을수록 높은 점수.
    """
    if rsi > 40:
        score = 0
    elif rsi < 30:
        score = 90
    elif rsi < 35:
        score = 80
    else:
        score = 70
    return {'score': score, 'rsi': rsi}


def calc_valuation_score(per: float, pbr: float) -> dict:
    """Valuation 컴포넌트.

    PER(60%) + PBR(40%)
    """
    per_score = _score_lte(per, PER_THRESHOLDS)
    pbr_score = _score_lte(pbr, PBR_THRESHOLDS)
    score = round(per_score * 0.6 + pbr_score * 0.4)
    return {'score': score, 'per_score': per_score, 'pbr_score': pbr_score}


def calc_total_score(dg_score: int, fq_score: int,
                     ts_score: int, val_score: int) -> dict:
    """4-컴포넌트 종합 스코어.

    Returns:
        {'total_score': int, 'rating': str, 'action': str, 'components': dict}
    """
    total = round(
        dg_score * WEIGHTS['dividend_growth'] +
        fq_score * WEIGHTS['financial_quality'] +
        ts_score * WEIGHTS['technical_setup'] +
        val_score * WEIGHTS['valuation']
    )
    total = max(0, min(100, total))

    rating = 'Pass'
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
            'dividend_growth': dg_score,
            'financial_quality': fq_score,
            'technical_setup': ts_score,
            'valuation': val_score,
        },
        'weights': WEIGHTS,
    }
