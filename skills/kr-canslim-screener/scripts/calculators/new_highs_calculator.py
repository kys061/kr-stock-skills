"""N 컴포넌트: 52주 신고가 근접도 + 브레이크아웃 (New Highs)."""

# ── 임계값 ────────────────────────────────────────────────
N_THRESHOLDS = [
    {'pct_from_high': 5,  'breakout': True,  'score': 100},
    {'pct_from_high': 10, 'breakout': True,  'score': 80},
    {'pct_from_high': 15, 'breakout': False, 'score': 60},
    {'pct_from_high': 25, 'breakout': False, 'score': 40},
]
N_DEFAULT = 20

BREAKOUT_VOLUME_MULTIPLIER = 1.5  # 50일 평균 × 1.5


def calc_52w_proximity(current_price: float, high_52w: float,
                       current_volume: float = 0, avg_volume_50d: float = 0) -> dict:
    """52주 고가 근접도 + 브레이크아웃 판정.

    Args:
        current_price: 현재가
        high_52w: 52주 고가
        current_volume: 당일 거래량
        avg_volume_50d: 50일 평균 거래량
    Returns:
        {'score': int, 'pct_from_high': float, 'is_breakout': bool}
    """
    if high_52w <= 0:
        return {'score': N_DEFAULT, 'pct_from_high': 100, 'is_breakout': False}

    pct_from_high = ((high_52w - current_price) / high_52w) * 100
    is_breakout = (avg_volume_50d > 0 and
                   current_volume >= avg_volume_50d * BREAKOUT_VOLUME_MULTIPLIER)

    for t in N_THRESHOLDS:
        if pct_from_high <= t['pct_from_high']:
            if t['breakout'] and not is_breakout:
                # 브레이크아웃 필요하지만 미충족 → 한 단계 낮은 점수
                return {'score': max(t['score'] - 20, N_DEFAULT),
                        'pct_from_high': round(pct_from_high, 1),
                        'is_breakout': is_breakout}
            return {'score': t['score'],
                    'pct_from_high': round(pct_from_high, 1),
                    'is_breakout': is_breakout}

    return {'score': N_DEFAULT, 'pct_from_high': round(pct_from_high, 1), 'is_breakout': is_breakout}
