"""kr-stock-analysis: 펀더멘털 분석 엔진."""


# ─── 펀더멘털 지표 ───

FUNDAMENTAL_METRICS = {
    'valuation': {
        'per': {'label': 'PER', 'source': 'PyKRX'},
        'pbr': {'label': 'PBR', 'source': 'PyKRX'},
        'psr': {'label': 'PSR', 'source': 'calculated'},
        'ev_ebitda': {'label': 'EV/EBITDA', 'source': 'DART'},
    },
    'profitability': {
        'roe': {'label': 'ROE', 'source': 'DART'},
        'roa': {'label': 'ROA', 'source': 'DART'},
        'operating_margin': {'label': '영업이익률', 'source': 'DART'},
        'net_margin': {'label': '순이익률', 'source': 'DART'},
    },
    'growth': {
        'revenue_growth_3y': {'label': '매출 3년 CAGR', 'source': 'DART'},
        'earnings_growth_3y': {'label': '순이익 3년 CAGR', 'source': 'DART'},
        'dividend_growth_3y': {'label': '배당 3년 CAGR', 'source': 'DART'},
    },
    'financial_health': {
        'debt_ratio': {'label': '부채비율', 'source': 'DART'},
        'current_ratio': {'label': '유동비율', 'source': 'DART'},
        'interest_coverage': {'label': '이자보상비율', 'source': 'DART'},
    },
}

# ─── 밸류에이션 기준 (업종 중립) ───

VALUATION_BENCHMARKS = {
    'per': {'cheap': 10, 'fair': 15, 'expensive': 25},
    'pbr': {'cheap': 0.7, 'fair': 1.0, 'expensive': 2.0},
    'psr': {'cheap': 0.5, 'fair': 1.5, 'expensive': 5.0},
    'ev_ebitda': {'cheap': 6, 'fair': 10, 'expensive': 15},
}

PROFITABILITY_BENCHMARKS = {
    'roe': {'poor': 5, 'average': 10, 'excellent': 20},
    'roa': {'poor': 2, 'average': 5, 'excellent': 10},
    'operating_margin': {'poor': 5, 'average': 10, 'excellent': 20},
    'net_margin': {'poor': 3, 'average': 7, 'excellent': 15},
}

GROWTH_BENCHMARKS = {
    'revenue_growth_3y': {'low': 5, 'moderate': 10, 'high': 20},
    'earnings_growth_3y': {'low': 5, 'moderate': 15, 'high': 30},
    'dividend_growth_3y': {'low': 3, 'moderate': 7, 'high': 15},
}

HEALTH_BENCHMARKS = {
    'debt_ratio': {'safe': 100, 'caution': 200, 'danger': 400},
    'current_ratio': {'danger': 0.8, 'caution': 1.0, 'safe': 1.5},
    'interest_coverage': {'danger': 1.5, 'caution': 3.0, 'safe': 5.0},
}


def _score_valuation(data):
    """밸류에이션 점수 (0-100). 저PER/PBR이 높은 점수."""
    scores = []
    for metric, benchmarks in VALUATION_BENCHMARKS.items():
        val = data.get(metric)
        if val is None or val <= 0:
            continue
        if val <= benchmarks['cheap']:
            scores.append(90)
        elif val <= benchmarks['fair']:
            ratio = (val - benchmarks['cheap']) / (benchmarks['fair'] - benchmarks['cheap'])
            scores.append(90 - ratio * 30)
        elif val <= benchmarks['expensive']:
            ratio = (val - benchmarks['fair']) / (benchmarks['expensive'] - benchmarks['fair'])
            scores.append(60 - ratio * 30)
        else:
            scores.append(max(10, 30 - (val - benchmarks['expensive']) * 2))
    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_profitability(data):
    """수익성 점수 (0-100). 높은 ROE/마진이 높은 점수."""
    scores = []
    for metric, benchmarks in PROFITABILITY_BENCHMARKS.items():
        val = data.get(metric)
        if val is None:
            continue
        if val >= benchmarks['excellent']:
            scores.append(90)
        elif val >= benchmarks['average']:
            ratio = (val - benchmarks['average']) / (benchmarks['excellent'] - benchmarks['average'])
            scores.append(60 + ratio * 30)
        elif val >= benchmarks['poor']:
            ratio = (val - benchmarks['poor']) / (benchmarks['average'] - benchmarks['poor'])
            scores.append(30 + ratio * 30)
        else:
            scores.append(max(10, 30 - (benchmarks['poor'] - val) * 3))
    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_growth(data):
    """성장성 점수 (0-100). 높은 CAGR이 높은 점수."""
    scores = []
    for metric, benchmarks in GROWTH_BENCHMARKS.items():
        val = data.get(metric)
        if val is None:
            continue
        if val >= benchmarks['high']:
            scores.append(min(100, 80 + (val - benchmarks['high'])))
        elif val >= benchmarks['moderate']:
            ratio = (val - benchmarks['moderate']) / (benchmarks['high'] - benchmarks['moderate'])
            scores.append(60 + ratio * 20)
        elif val >= benchmarks['low']:
            ratio = (val - benchmarks['low']) / (benchmarks['moderate'] - benchmarks['low'])
            scores.append(40 + ratio * 20)
        elif val >= 0:
            scores.append(max(20, 40 - (benchmarks['low'] - val) * 3))
        else:
            scores.append(max(5, 20 + val))
    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_financial_health(data):
    """재무건전성 점수 (0-100)."""
    scores = []

    # 부채비율: 낮을수록 좋음
    debt = data.get('debt_ratio')
    if debt is not None:
        b = HEALTH_BENCHMARKS['debt_ratio']
        if debt <= b['safe']:
            scores.append(90)
        elif debt <= b['caution']:
            ratio = (debt - b['safe']) / (b['caution'] - b['safe'])
            scores.append(90 - ratio * 30)
        elif debt <= b['danger']:
            ratio = (debt - b['caution']) / (b['danger'] - b['caution'])
            scores.append(60 - ratio * 30)
        else:
            scores.append(max(10, 30 - (debt - b['danger']) * 0.05))

    # 유동비율: 높을수록 좋음
    current = data.get('current_ratio')
    if current is not None:
        b = HEALTH_BENCHMARKS['current_ratio']
        if current >= b['safe']:
            scores.append(90)
        elif current >= b['caution']:
            ratio = (current - b['caution']) / (b['safe'] - b['caution'])
            scores.append(60 + ratio * 30)
        elif current >= b['danger']:
            ratio = (current - b['danger']) / (b['caution'] - b['danger'])
            scores.append(30 + ratio * 30)
        else:
            scores.append(max(10, 30 * (current / b['danger'])))

    # 이자보상비율: 높을수록 좋음
    interest = data.get('interest_coverage')
    if interest is not None:
        b = HEALTH_BENCHMARKS['interest_coverage']
        if interest >= b['safe']:
            scores.append(90)
        elif interest >= b['caution']:
            ratio = (interest - b['caution']) / (b['safe'] - b['caution'])
            scores.append(60 + ratio * 30)
        elif interest >= b['danger']:
            ratio = (interest - b['danger']) / (b['caution'] - b['danger'])
            scores.append(30 + ratio * 30)
        else:
            scores.append(max(5, 30 * max(0, interest) / b['danger']))

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def analyze_fundamentals(stock_data):
    """종합 펀더멘털 분석.

    Args:
        stock_data: dict with keys matching FUNDAMENTAL_METRICS
            valuation: {per, pbr, psr, ev_ebitda}
            profitability: {roe, roa, operating_margin, net_margin}
            growth: {revenue_growth_3y, earnings_growth_3y, dividend_growth_3y}
            financial_health: {debt_ratio, current_ratio, interest_coverage}

    Returns:
        dict: {valuation, profitability, growth, health, score}
    """
    valuation = stock_data.get('valuation', {})
    profitability = stock_data.get('profitability', {})
    growth = stock_data.get('growth', {})
    health = stock_data.get('financial_health', {})

    val_score = _score_valuation(valuation)
    prof_score = _score_profitability(profitability)
    growth_score = _score_growth(growth)
    health_score = _score_financial_health(health)

    # 펀더멘털 종합: 수익성 30% + 성장성 25% + 재무건전성 25% + 밸류에이션 20%
    total = (prof_score * 0.30 + growth_score * 0.25
             + health_score * 0.25 + val_score * 0.20)

    return {
        'valuation': {'data': valuation, 'score': val_score},
        'profitability': {'data': profitability, 'score': prof_score},
        'growth': {'data': growth, 'score': growth_score},
        'health': {'data': health, 'score': health_score},
        'score': round(total, 1),
    }
