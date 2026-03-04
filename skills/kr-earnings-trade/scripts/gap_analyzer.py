"""kr-earnings-trade: Factor 1 — 갭 크기 분석.

실적 발표 후 갭 크기를 측정하고 점수화한다.
한국 ±30% 가격제한폭 감안.
"""

# ─── 상수 ───
GAP_SCORE_TABLE = [
    (10, 100), (7, 85), (5, 70), (3, 55), (1, 35), (0, 15),
]

KR_PRICE_LIMIT = 0.30  # ±30%


def calc_gap(prices: list, earnings_idx: int, timing: str = 'after_close') -> float:
    """실적 발표 갭 계산.

    Args:
        prices: OHLCV 리스트 [{'open': ..., 'close': ...}, ...]
        earnings_idx: 실적 발표일 인덱스
        timing: 'before_open' | 'during_market' | 'after_close'

    Returns:
        갭 비율 (예: 0.05 = 5%)
    """
    if not prices or earnings_idx < 0:
        return 0.0

    try:
        if timing == 'before_open':
            # 장전: open[D] / close[D-1] - 1
            if earnings_idx < 1:
                return 0.0
            gap = prices[earnings_idx]['open'] / prices[earnings_idx - 1]['close'] - 1
        elif timing == 'during_market':
            # 장중: close[D] / open[D] - 1
            gap = prices[earnings_idx]['close'] / prices[earnings_idx]['open'] - 1
        else:
            # 장후 (기본): open[D+1] / close[D] - 1
            if earnings_idx + 1 >= len(prices):
                return 0.0
            gap = prices[earnings_idx + 1]['open'] / prices[earnings_idx]['close'] - 1
        return gap
    except (KeyError, ZeroDivisionError, IndexError):
        return 0.0


def score_gap(gap_pct: float) -> dict:
    """갭 크기 → 점수.

    Args:
        gap_pct: 갭 비율 (백분율, 예: 5.0 = 5%)

    Returns:
        {'score': int, 'gap_pct': float, 'abs_gap': float}
    """
    abs_gap = abs(gap_pct)
    score = GAP_SCORE_TABLE[-1][1]  # default: 15
    for threshold, s in GAP_SCORE_TABLE:
        if abs_gap >= threshold:
            score = s
            break

    return {
        'score': score,
        'gap_pct': round(gap_pct, 2),
        'abs_gap': round(abs_gap, 2),
    }
