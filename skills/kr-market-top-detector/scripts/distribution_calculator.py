"""
kr-market-top-detector: 분배일(Distribution Day) 계산기.
O'Neil 방법론: 25 거래일 내 분배일 누적.
KOSPI + KOSDAQ 이중 추적.
"""


DISTRIBUTION_THRESHOLD = -0.002   # -0.2%
WINDOW = 25                       # 25 거래일

# 분배일 수 → 점수 매핑
SCORE_MAP = {
    0: 0,
    1: 10,
    2: 20,
    3: 30,
    4: 50,
    5: 70,
    6: 85,
    7: 95,
}


def is_distribution_day(close: float, prev_close: float,
                        volume: int, prev_volume: int) -> bool:
    """개별 일자가 분배일인지 판정.

    조건: 종가 전일 대비 -0.2% 이상 하락 AND 거래량 >= 전일
    """
    if prev_close <= 0:
        return False
    daily_return = (close - prev_close) / prev_close
    return daily_return <= DISTRIBUTION_THRESHOLD and volume >= prev_volume


def count_distribution_days(closes: list, volumes: list,
                            window: int = WINDOW) -> int:
    """최근 window 거래일 내 분배일 횟수.

    Args:
        closes: 종가 리스트 (오래된 → 최신, 최소 window+1개)
        volumes: 거래량 리스트 (동일 길이)
        window: 윈도우 크기
    Returns:
        분배일 횟수
    """
    if len(closes) < 2 or len(volumes) < 2:
        return 0

    count = 0
    start = max(1, len(closes) - window)
    for i in range(start, len(closes)):
        if is_distribution_day(closes[i], closes[i - 1],
                               volumes[i], volumes[i - 1]):
            count += 1
    return count


def score_single_index(dist_count: int) -> float:
    """단일 지수 분배일 수 → 점수 (0-100)."""
    if dist_count <= 0:
        return 0.0
    if dist_count >= 7:
        return 100.0
    return float(SCORE_MAP.get(dist_count, 0))


def score_dual_index(kospi_count: int, kosdaq_count: int) -> float:
    """KOSPI + KOSDAQ 이중 추적 → 복합 점수 (0-100).

    최종 = max 점수 × 0.7 + min 점수 × 0.3
    """
    s_kospi = score_single_index(kospi_count)
    s_kosdaq = score_single_index(kosdaq_count)

    high = max(s_kospi, s_kosdaq)
    low = min(s_kospi, s_kosdaq)
    return high * 0.7 + low * 0.3


class DistributionDayCalculator:
    """분배일 계산 + 스코어링."""

    def __init__(self, window: int = WINDOW):
        self.window = window

    def count(self, closes: list, volumes: list) -> int:
        """분배일 카운팅."""
        return count_distribution_days(closes, volumes, self.window)

    def score(self, kospi_count: int, kosdaq_count: int) -> float:
        """이중 지수 점수."""
        return score_dual_index(kospi_count, kosdaq_count)
