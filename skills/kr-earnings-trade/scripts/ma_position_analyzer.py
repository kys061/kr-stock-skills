"""kr-earnings-trade: Factor 4,5 — MA200/MA50 포지션 분석.

현재가의 이동평균 대비 위치를 측정하고 점수화한다.
"""

# ─── 상수 ───
MA200_SCORE_TABLE = [
    (20, 100), (10, 85), (5, 70), (0, 55), (-5, 35), (-999, 15),
]

MA50_SCORE_TABLE = [
    (10, 100), (5, 80), (0, 60), (-5, 35), (-999, 15),
]

MA200_PERIOD = 200
MA50_PERIOD = 50


def calc_sma(prices: list, period: int) -> float:
    """단순이동평균 계산.

    Args:
        prices: close 가격 리스트
        period: SMA 기간

    Returns:
        SMA 값 (데이터 부족 시 0.0)
    """
    if len(prices) < period:
        return 0.0
    return sum(prices[-period:]) / period


def calc_ma_distance(current_price: float, ma_value: float) -> float:
    """현재가의 MA 대비 거리 (백분율).

    Args:
        current_price: 현재가
        ma_value: 이동평균 값

    Returns:
        거리 % (예: 10.0 = MA 위 10%)
    """
    if ma_value <= 0:
        return 0.0
    return (current_price / ma_value - 1) * 100


def score_ma200(distance_pct: float) -> dict:
    """MA200 거리 → 점수.

    Args:
        distance_pct: MA200 대비 거리 %

    Returns:
        {'score': int, 'distance_pct': float}
    """
    score = MA200_SCORE_TABLE[-1][1]
    for threshold, s in MA200_SCORE_TABLE:
        if distance_pct >= threshold:
            score = s
            break
    return {'score': score, 'distance_pct': round(distance_pct, 2)}


def score_ma50(distance_pct: float) -> dict:
    """MA50 거리 → 점수.

    Args:
        distance_pct: MA50 대비 거리 %

    Returns:
        {'score': int, 'distance_pct': float}
    """
    score = MA50_SCORE_TABLE[-1][1]
    for threshold, s in MA50_SCORE_TABLE:
        if distance_pct >= threshold:
            score = s
            break
    return {'score': score, 'distance_pct': round(distance_pct, 2)}
