"""kr-earnings-trade: Factor 2 — 사전 추세 분석.

실적 발표 전 20일 수익률을 측정하고 점수화한다.
"""

# ─── 상수 ───
TREND_SCORE_TABLE = [
    (15, 100), (10, 85), (5, 70), (0, 50), (-5, 30), (-999, 15),
]

TREND_LOOKBACK = 20  # 20일 사전 추세


def calc_pre_earnings_trend(prices: list, earnings_idx: int,
                             lookback: int = TREND_LOOKBACK) -> float:
    """실적 전 N일 수익률 계산.

    Args:
        prices: 가격 리스트 (close 필드)
        earnings_idx: 실적일 인덱스
        lookback: 추세 측정 기간

    Returns:
        수익률 (백분율, 예: 5.0 = 5%)
    """
    if not prices or earnings_idx < lookback:
        return 0.0

    try:
        start_price = prices[earnings_idx - lookback]['close']
        end_price = prices[earnings_idx - 1]['close']  # 실적 전일
        if start_price <= 0:
            return 0.0
        return (end_price / start_price - 1) * 100
    except (KeyError, IndexError, ZeroDivisionError):
        return 0.0


def score_trend(trend_pct: float) -> dict:
    """사전 추세 → 점수.

    Args:
        trend_pct: 20일 수익률 (백분율)

    Returns:
        {'score': int, 'trend_pct': float}
    """
    score = TREND_SCORE_TABLE[-1][1]  # default: 15
    for threshold, s in TREND_SCORE_TABLE:
        if trend_pct >= threshold:
            score = s
            break

    return {'score': score, 'trend_pct': round(trend_pct, 2)}
