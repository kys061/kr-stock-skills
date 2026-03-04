"""kr-earnings-trade: Factor 3 — 거래량 추세 분석.

20일/60일 평균 거래량 비율로 기관 참여도를 측정한다.
"""

# ─── 상수 ───
VOLUME_SCORE_TABLE = [
    (2.0, 100), (1.5, 80), (1.2, 60), (1.0, 40), (0, 20),
]

VOLUME_SHORT_WINDOW = 20
VOLUME_LONG_WINDOW = 60


def calc_volume_ratio(volumes: list, idx: int,
                       short_window: int = VOLUME_SHORT_WINDOW,
                       long_window: int = VOLUME_LONG_WINDOW) -> float:
    """거래량 비율 (short/long 평균) 계산.

    Args:
        volumes: 거래량 리스트
        idx: 기준 인덱스
        short_window: 단기 평균 기간
        long_window: 장기 평균 기간

    Returns:
        거래량 비율 (예: 1.5 = 1.5x)
    """
    if not volumes or idx < long_window:
        return 1.0

    try:
        short_start = max(0, idx - short_window)
        short_avg = sum(volumes[short_start:idx]) / short_window

        long_start = max(0, idx - long_window)
        long_avg = sum(volumes[long_start:idx]) / long_window

        if long_avg <= 0:
            return 1.0
        return short_avg / long_avg
    except (ZeroDivisionError, IndexError):
        return 1.0


def score_volume(ratio: float) -> dict:
    """거래량 비율 → 점수.

    Args:
        ratio: 20d/60d 비율

    Returns:
        {'score': int, 'ratio': float}
    """
    score = VOLUME_SCORE_TABLE[-1][1]  # default: 20
    for threshold, s in VOLUME_SCORE_TABLE:
        if ratio >= threshold:
            score = s
            break

    return {'score': score, 'ratio': round(ratio, 2)}
