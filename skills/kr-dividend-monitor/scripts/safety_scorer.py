"""kr-dividend-monitor: 배당 안전성 스코어링.

4개 컴포넌트로 배당 안전성을 0-100점으로 평가한다.
"""

# ─── 배당 안전성 점수 체계 ───

SAFETY_SCORING = {
    'payout_ratio': {
        'weight': 0.30,
        'safe': 0.50,
        'caution': 0.70,
        'warning': 0.90,
        'danger': 1.00,
    },
    'earnings_stability': {
        'weight': 0.25,
        'positive_years': 5,
        'min_years': 3,
    },
    'dividend_history': {
        'weight': 0.25,
        'excellent_years': 10,
        'good_years': 5,
        'min_years': 3,
    },
    'debt_health': {
        'weight': 0.20,
        'safe_ratio': 0.80,
        'caution_ratio': 1.20,
        'warning_ratio': 1.50,
        'danger_ratio': 2.00,
    },
}

# ─── 안전성 등급 ───

SAFETY_GRADES = {
    'SAFE': 80,
    'MODERATE': 60,
    'AT_RISK': 40,
    'DANGEROUS': 0,
}


def calc_payout_score(payout_ratio: float) -> float:
    """배당성향 점수 (0-100)."""
    s = SAFETY_SCORING['payout_ratio']

    if payout_ratio <= 0:
        return 0  # 적자 or 무배당
    elif payout_ratio <= s['safe']:
        return 100
    elif payout_ratio <= s['caution']:
        return 70 + (s['caution'] - payout_ratio) / (s['caution'] - s['safe']) * 30
    elif payout_ratio <= s['warning']:
        return 40 + (s['warning'] - payout_ratio) / (s['warning'] - s['caution']) * 30
    elif payout_ratio <= s['danger']:
        return (s['danger'] - payout_ratio) / (s['danger'] - s['warning']) * 40
    else:
        return 0


def calc_earnings_stability_score(positive_years: int) -> float:
    """실적 안정성 점수 (0-100)."""
    s = SAFETY_SCORING['earnings_stability']

    if positive_years >= s['positive_years']:
        return 100
    elif positive_years >= s['min_years']:
        return 50 + (positive_years - s['min_years']) / (s['positive_years'] - s['min_years']) * 50
    elif positive_years > 0:
        return positive_years / s['min_years'] * 50
    else:
        return 0


def calc_dividend_history_score(consecutive_years: int) -> float:
    """배당 이력 점수 (0-100)."""
    s = SAFETY_SCORING['dividend_history']

    if consecutive_years >= s['excellent_years']:
        return 100
    elif consecutive_years >= s['good_years']:
        return 70 + (consecutive_years - s['good_years']) / (s['excellent_years'] - s['good_years']) * 30
    elif consecutive_years >= s['min_years']:
        return 40 + (consecutive_years - s['min_years']) / (s['good_years'] - s['min_years']) * 30
    elif consecutive_years > 0:
        return consecutive_years / s['min_years'] * 40
    else:
        return 0


def calc_debt_health_score(debt_ratio: float) -> float:
    """부채 건전성 점수 (0-100)."""
    s = SAFETY_SCORING['debt_health']

    if debt_ratio <= s['safe_ratio']:
        return 100
    elif debt_ratio <= s['caution_ratio']:
        return 60 + (s['caution_ratio'] - debt_ratio) / (s['caution_ratio'] - s['safe_ratio']) * 40
    elif debt_ratio <= s['warning_ratio']:
        return 30 + (s['warning_ratio'] - debt_ratio) / (s['warning_ratio'] - s['caution_ratio']) * 30
    elif debt_ratio <= s['danger_ratio']:
        return (s['danger_ratio'] - debt_ratio) / (s['danger_ratio'] - s['warning_ratio']) * 30
    else:
        return 0


def calc_safety_score(stock_data: dict) -> dict:
    """배당 안전성 종합 점수 계산.

    Args:
        stock_data: {
            'payout_ratio': float,
            'positive_earnings_years': int,
            'consecutive_dividend_years': int,
            'debt_ratio': float,
        }

    Returns:
        {'score': float, 'grade': str, 'components': dict}
    """
    payout_s = calc_payout_score(stock_data.get('payout_ratio', 0))
    earnings_s = calc_earnings_stability_score(
        stock_data.get('positive_earnings_years', 0))
    dividend_s = calc_dividend_history_score(
        stock_data.get('consecutive_dividend_years', 0))
    debt_s = calc_debt_health_score(stock_data.get('debt_ratio', 0))

    weights = SAFETY_SCORING
    total = (
        payout_s * weights['payout_ratio']['weight']
        + earnings_s * weights['earnings_stability']['weight']
        + dividend_s * weights['dividend_history']['weight']
        + debt_s * weights['debt_health']['weight']
    )

    grade = 'DANGEROUS'
    for g, threshold in sorted(SAFETY_GRADES.items(),
                                key=lambda x: x[1], reverse=True):
        if total >= threshold:
            grade = g
            break

    return {
        'score': round(total, 1),
        'grade': grade,
        'components': {
            'payout_ratio': round(payout_s, 1),
            'earnings_stability': round(earnings_s, 1),
            'dividend_history': round(dividend_s, 1),
            'debt_health': round(debt_s, 1),
        },
    }
