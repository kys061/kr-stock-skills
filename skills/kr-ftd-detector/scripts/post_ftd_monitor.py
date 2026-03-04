"""
kr-ftd-detector: FTD 이후 건전성 모니터링.
FTD 무효화 조건 체크.
"""


class PostFTDMonitor:
    """FTD 이후 건전성 모니터링."""

    MAX_DISTRIBUTION_DAYS = 3   # 25일 내 분배일 허용 한도
    DISTRIBUTION_THRESHOLD = -0.002  # -0.2%

    def __init__(self, ftd_close: float, swing_low: float):
        """
        Args:
            ftd_close: FTD 일 종가
            swing_low: 랠리 시작 스윙 로우
        """
        self.ftd_close = ftd_close
        self.swing_low = swing_low
        self.distribution_days = 0
        self.days_since_ftd = 0
        self.is_valid = True
        self.invalidation_reason = None

    def check(self, close: float, prev_close: float,
              volume: int = 0, prev_volume: int = 0) -> dict:
        """일별 FTD 건전성 체크.

        Args:
            close: 당일 종가
            prev_close: 전일 종가
            volume: 당일 거래량
            prev_volume: 전일 거래량
        Returns:
            {
                'is_valid': bool,
                'invalidation_reason': str or None,
                'distribution_days': int,
                'days_since_ftd': int,
                'health': str,  # 'healthy' | 'warning' | 'critical'
            }
        """
        if not self.is_valid:
            return self._result()

        self.days_since_ftd += 1
        daily_return = (close - prev_close) / prev_close if prev_close > 0 else 0

        # 무효화 1: FTD 일 종가 하회
        if close < self.ftd_close:
            self.is_valid = False
            self.invalidation_reason = 'ftd_close_broken'
            return self._result()

        # 무효화 2: 스윙 로우 이탈
        if close < self.swing_low:
            self.is_valid = False
            self.invalidation_reason = 'swing_low_broken'
            return self._result()

        # 분배일 카운팅 (25거래일 윈도우)
        if daily_return <= self.DISTRIBUTION_THRESHOLD and volume > prev_volume:
            self.distribution_days += 1

        # 무효화 3: 분배일 과다
        if self.distribution_days >= self.MAX_DISTRIBUTION_DAYS:
            self.is_valid = False
            self.invalidation_reason = 'excessive_distribution'
            return self._result()

        return self._result()

    def _result(self) -> dict:
        """현재 상태 반환."""
        if not self.is_valid:
            health = 'critical'
        elif self.distribution_days >= 2:
            health = 'warning'
        else:
            health = 'healthy'

        return {
            'is_valid': self.is_valid,
            'invalidation_reason': self.invalidation_reason,
            'distribution_days': self.distribution_days,
            'days_since_ftd': self.days_since_ftd,
            'health': health,
        }
