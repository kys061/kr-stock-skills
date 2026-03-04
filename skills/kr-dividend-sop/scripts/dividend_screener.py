"""kr-dividend-sop: Step 1 스크리닝 + Step 2 진입 판단.

5-Step SOP의 스크리닝과 진입 점수 계산을 담당한다.
"""

# ─── SOP 단계 정의 ───

SOP_STEPS = [
    'SCREEN',
    'ENTRY',
    'HOLD',
    'COLLECT',
    'EXIT',
]

# ─── Step 1: 스크리닝 필수 조건 ───

SCREENING_CRITERIA = {
    'min_yield': 2.5,
    'min_consecutive_years': 3,
    'no_cut_years': 3,
    'max_payout_ratio': 0.80,
    'min_market_cap': 500_000_000_000,
    'max_debt_ratio': 1.50,
    'min_current_ratio': 1.0,
    'min_roe': 0.05,
    'revenue_trend_years': 3,
    'eps_trend_years': 3,
}

# ─── Step 2: 진입 점수 체계 ───

ENTRY_SCORING = {
    'valuation': {
        'weight': 0.40,
        'per_sweet_spot': (5, 12),
        'pbr_sweet_spot': (0.3, 1.0),
    },
    'dividend_quality': {
        'weight': 0.30,
        'yield_excellent': 4.0,
        'yield_good': 3.0,
        'growth_bonus': 0.10,
    },
    'financial_health': {
        'weight': 0.20,
        'roe_excellent': 0.15,
        'roe_good': 0.10,
    },
    'timing': {
        'weight': 0.10,
        'rsi_oversold': 40,
        'near_ex_date_penalty': True,
    },
}

ENTRY_GRADES = {
    'STRONG_BUY': 85,
    'BUY': 70,
    'HOLD': 55,
    'PASS': 0,
}


def check_screening_criteria(stock_data: dict) -> dict:
    """Step 1: 스크리닝 기준 통과 여부 확인.

    Args:
        stock_data: {
            'dividend_yield': float,
            'consecutive_years': int,
            'no_cut_years': int,
            'payout_ratio': float,
            'market_cap': int,
            'debt_ratio': float,
            'current_ratio': float,
            'roe': float,
            'revenue_trend': bool,
            'eps_trend': bool,
        }

    Returns:
        {'passed': bool, 'failed_reasons': list, 'passed_count': int, 'total_count': int}
    """
    failed = []
    criteria = SCREENING_CRITERIA

    checks = [
        ('min_yield', stock_data.get('dividend_yield', 0) >= criteria['min_yield'],
         f"배당수익률 {stock_data.get('dividend_yield', 0):.1f}% < {criteria['min_yield']}%"),
        ('min_consecutive_years', stock_data.get('consecutive_years', 0) >= criteria['min_consecutive_years'],
         f"연속배당 {stock_data.get('consecutive_years', 0)}년 < {criteria['min_consecutive_years']}년"),
        ('no_cut_years', stock_data.get('no_cut_years', 0) >= criteria['no_cut_years'],
         f"무감배 {stock_data.get('no_cut_years', 0)}년 < {criteria['no_cut_years']}년"),
        ('max_payout_ratio', stock_data.get('payout_ratio', 1.0) <= criteria['max_payout_ratio'],
         f"배당성향 {stock_data.get('payout_ratio', 1.0):.0%} > {criteria['max_payout_ratio']:.0%}"),
        ('min_market_cap', stock_data.get('market_cap', 0) >= criteria['min_market_cap'],
         f"시가총액 미달"),
        ('max_debt_ratio', stock_data.get('debt_ratio', 999) <= criteria['max_debt_ratio'],
         f"부채비율 {stock_data.get('debt_ratio', 999):.0%} > {criteria['max_debt_ratio']:.0%}"),
        ('min_current_ratio', stock_data.get('current_ratio', 0) >= criteria['min_current_ratio'],
         f"유동비율 {stock_data.get('current_ratio', 0):.2f} < {criteria['min_current_ratio']}"),
        ('min_roe', stock_data.get('roe', 0) >= criteria['min_roe'],
         f"ROE {stock_data.get('roe', 0):.1%} < {criteria['min_roe']:.1%}"),
        ('revenue_trend', stock_data.get('revenue_trend', False),
         "매출 3년 양의 추세 미충족"),
        ('eps_trend', stock_data.get('eps_trend', False),
         "EPS 3년 양의 추세 미충족"),
    ]

    for name, passed, reason in checks:
        if not passed:
            failed.append(reason)

    total = len(checks)
    passed_count = total - len(failed)

    return {
        'passed': len(failed) == 0,
        'failed_reasons': failed,
        'passed_count': passed_count,
        'total_count': total,
    }


def _calc_valuation_score(per: float, pbr: float) -> float:
    """밸류에이션 점수 (0-100)."""
    per_low, per_high = ENTRY_SCORING['valuation']['per_sweet_spot']
    pbr_low, pbr_high = ENTRY_SCORING['valuation']['pbr_sweet_spot']

    # PER 점수
    if per <= 0:
        per_score = 0
    elif per_low <= per <= per_high:
        per_score = 100
    elif per < per_low:
        per_score = max(50, 100 - (per_low - per) * 10)
    else:
        per_score = max(0, 100 - (per - per_high) * 5)

    # PBR 점수
    if pbr <= 0:
        pbr_score = 0
    elif pbr_low <= pbr <= pbr_high:
        pbr_score = 100
    elif pbr < pbr_low:
        pbr_score = max(60, 100 - (pbr_low - pbr) * 50)
    else:
        pbr_score = max(0, 100 - (pbr - pbr_high) * 30)

    return (per_score + pbr_score) / 2


def _calc_dividend_quality_score(dividend_yield: float,
                                  is_growing: bool = False) -> float:
    """배당 품질 점수 (0-100)."""
    excellent = ENTRY_SCORING['dividend_quality']['yield_excellent']
    good = ENTRY_SCORING['dividend_quality']['yield_good']
    bonus = ENTRY_SCORING['dividend_quality']['growth_bonus']

    if dividend_yield >= excellent:
        score = 100
    elif dividend_yield >= good:
        score = 80 + (dividend_yield - good) / (excellent - good) * 20
    elif dividend_yield >= 2.0:
        score = 50 + (dividend_yield - 2.0) / (good - 2.0) * 30
    else:
        score = max(0, dividend_yield / 2.0 * 50)

    if is_growing:
        score = min(100, score * (1 + bonus))

    return score


def _calc_financial_health_score(roe: float) -> float:
    """재무 건전성 점수 (0-100)."""
    excellent = ENTRY_SCORING['financial_health']['roe_excellent']
    good_val = ENTRY_SCORING['financial_health']['roe_good']

    if roe >= excellent:
        return 100
    elif roe >= good_val:
        return 80 + (roe - good_val) / (excellent - good_val) * 20
    elif roe >= 0.05:
        return 50 + (roe - 0.05) / (good_val - 0.05) * 30
    else:
        return max(0, roe / 0.05 * 50)


def _calc_timing_score(rsi: float = None,
                        days_to_ex_date: int = None) -> float:
    """타이밍 점수 (0-100)."""
    oversold = ENTRY_SCORING['timing']['rsi_oversold']

    if rsi is None:
        rsi_score = 50
    elif rsi <= 30:
        rsi_score = 100
    elif rsi <= oversold:
        rsi_score = 70 + (oversold - rsi) / (oversold - 30) * 30
    elif rsi <= 50:
        rsi_score = 50 + (50 - rsi) / (50 - oversold) * 20
    else:
        rsi_score = max(0, 50 - (rsi - 50))

    if (ENTRY_SCORING['timing']['near_ex_date_penalty']
            and days_to_ex_date is not None
            and 0 < days_to_ex_date <= 30):
        penalty = (30 - days_to_ex_date) / 30 * 20
        rsi_score = max(0, rsi_score - penalty)

    return rsi_score


def calc_entry_score(stock_data: dict) -> dict:
    """Step 2: 진입 점수 계산.

    Args:
        stock_data: {
            'per': float, 'pbr': float,
            'dividend_yield': float, 'is_growing': bool,
            'roe': float,
            'rsi': float (optional), 'days_to_ex_date': int (optional),
        }

    Returns:
        {'score': float, 'grade': str, 'components': dict}
    """
    val_score = _calc_valuation_score(
        stock_data.get('per', 0),
        stock_data.get('pbr', 0),
    )
    div_score = _calc_dividend_quality_score(
        stock_data.get('dividend_yield', 0),
        stock_data.get('is_growing', False),
    )
    fin_score = _calc_financial_health_score(
        stock_data.get('roe', 0),
    )
    tim_score = _calc_timing_score(
        stock_data.get('rsi'),
        stock_data.get('days_to_ex_date'),
    )

    weights = ENTRY_SCORING
    total = (
        val_score * weights['valuation']['weight']
        + div_score * weights['dividend_quality']['weight']
        + fin_score * weights['financial_health']['weight']
        + tim_score * weights['timing']['weight']
    )

    grade = 'PASS'
    for g, threshold in sorted(ENTRY_GRADES.items(),
                                key=lambda x: x[1], reverse=True):
        if total >= threshold:
            grade = g
            break

    return {
        'score': round(total, 1),
        'grade': grade,
        'components': {
            'valuation': round(val_score, 1),
            'dividend_quality': round(div_score, 1),
            'financial_health': round(fin_score, 1),
            'timing': round(tim_score, 1),
        },
    }
