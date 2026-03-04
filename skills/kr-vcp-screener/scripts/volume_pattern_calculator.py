"""Volume Pattern (Dry-Up Ratio) 계산기.

Dry-Up Ratio = 수축 기간 평균 거래량 / 이전 상승 기간 평균 거래량
"""

# ── Dry-Up Ratio 스코어 테이블 ──────────────────────────────
DRYUP_SCORES = [
    (0.30, 90),   # < 0.30
    (0.50, 75),   # 0.30-0.50
    (0.70, 60),   # 0.50-0.70
    (1.00, 40),   # 0.70-1.00
]
DRYUP_DEFAULT = 20        # > 1.00


def calc_dryup_ratio(contraction_volumes: list,
                     advance_volumes: list) -> dict:
    """Dry-Up Ratio 계산.

    Args:
        contraction_volumes: 수축 기간 일별 거래량
        advance_volumes: 이전 상승 기간 일별 거래량
    Returns:
        {'ratio': float, 'score': int}
    """
    if not contraction_volumes or not advance_volumes:
        return {'ratio': 0, 'score': DRYUP_DEFAULT}

    avg_contraction = sum(contraction_volumes) / len(contraction_volumes)
    avg_advance = sum(advance_volumes) / len(advance_volumes)

    if avg_advance <= 0:
        return {'ratio': 0, 'score': DRYUP_DEFAULT}

    ratio = avg_contraction / avg_advance

    score = DRYUP_DEFAULT
    for threshold, s in DRYUP_SCORES:
        if ratio < threshold:
            score = s
            break
    else:
        # ratio >= 1.00 이면 default
        if ratio < 1.00:
            score = 40

    return {
        'ratio': round(ratio, 3),
        'score': score,
    }


def calc_pivot_proximity(current_price: float, pivot_price: float) -> dict:
    """피봇 포인트 근접도 계산.

    Args:
        current_price: 현재가
        pivot_price: 피봇 가격 (마지막 수축 고가)
    Returns:
        {'score': int, 'pct_from_pivot': float, 'position': str}
    """
    if pivot_price <= 0 or current_price <= 0:
        return {'score': 20, 'pct_from_pivot': 0, 'position': 'unknown'}

    pct = ((current_price - pivot_price) / pivot_price) * 100

    if pct >= 0 and pct <= 3:
        return {'score': 100, 'pct_from_pivot': round(pct, 1), 'position': 'breakout'}
    elif pct < 0 and pct >= -3:
        return {'score': 85, 'pct_from_pivot': round(pct, 1), 'position': 'near_pivot'}
    elif pct < -3 and pct >= -5:
        return {'score': 75, 'pct_from_pivot': round(pct, 1), 'position': 'watch'}
    elif pct < -5 and pct >= -10:
        return {'score': 50, 'pct_from_pivot': round(pct, 1), 'position': 'forming'}
    elif pct < -10 and pct >= -20:
        return {'score': 30, 'pct_from_pivot': round(pct, 1), 'position': 'early'}
    elif pct > 3:
        return {'score': 20, 'pct_from_pivot': round(pct, 1), 'position': 'extended'}
    else:
        return {'score': 20, 'pct_from_pivot': round(pct, 1), 'position': 'no_chase'}
