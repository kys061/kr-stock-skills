"""S 컴포넌트: 상승일/하락일 거래량 비율 (Supply/Demand)."""

# ── 임계값 ────────────────────────────────────────────────
S_THRESHOLDS = [
    (2.0, 100),
    (1.5,  80),
    (1.0,  60),
    (0.7,  40),
]
S_DEFAULT = 20

VOLUME_WINDOW = 60  # 60일 윈도우


def calc_volume_ratio(prices: list, volumes: list) -> dict:
    """상승일/하락일 거래량 비율 계산.

    Args:
        prices: 최근 60일 종가 리스트
        volumes: 최근 60일 거래량 리스트
    Returns:
        {'score': int, 'up_down_ratio': float, 'up_volume': float, 'down_volume': float}
    """
    if len(prices) < 2 or len(volumes) < 2:
        return {'score': S_DEFAULT, 'up_down_ratio': 0, 'up_volume': 0, 'down_volume': 0}

    n = min(len(prices), len(volumes), VOLUME_WINDOW)
    up_volume = 0
    down_volume = 0

    for i in range(1, n):
        if prices[i] > prices[i - 1]:
            up_volume += volumes[i]
        elif prices[i] < prices[i - 1]:
            down_volume += volumes[i]

    if down_volume == 0:
        ratio = 2.0 if up_volume > 0 else 0
    else:
        ratio = up_volume / down_volume

    score = S_DEFAULT
    for threshold, s in S_THRESHOLDS:
        if ratio >= threshold:
            score = s
            break

    return {
        'score': score,
        'up_down_ratio': round(ratio, 2),
        'up_volume': up_volume,
        'down_volume': down_volume,
    }
