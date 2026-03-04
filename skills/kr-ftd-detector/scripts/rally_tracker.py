"""
kr-ftd-detector: 랠리 시도 추적기 + 상태 머신.
KOSPI/KOSDAQ 각각에 독립적 상태 머신을 운영.
"""

from enum import Enum


class RallyState(Enum):
    NO_SIGNAL = 'no_signal'
    CORRECTION = 'correction'
    RALLY_ATTEMPT = 'rally_attempt'
    FTD_WINDOW = 'ftd_window'
    FTD_CONFIRMED = 'ftd_confirmed'
    RALLY_FAILED = 'rally_failed'
    FTD_INVALIDATED = 'ftd_invalidated'


class RallyTracker:
    """KOSPI/KOSDAQ 랠리 시도 추적기.

    하나의 지수에 대해 상태 머신을 운영.
    KOSPI + KOSDAQ 이중 추적 시 인스턴스 2개 생성.
    """

    CORRECTION_THRESHOLD = -0.03    # -3% 조정 기준
    MIN_CORRECTION_DAYS = 3         # 최소 조정 일수

    def __init__(self, index_name: str = 'KOSPI'):
        self.index_name = index_name
        self.state = RallyState.NO_SIGNAL
        self.swing_low = None           # 조정 저점
        self.swing_low_date = None
        self.rally_day = 0              # 랠리 Day 카운트
        self.correction_start = None    # 조정 시작 가격
        self.correction_days = 0        # 조정 일수
        self.ftd_close = None           # FTD 일 종가
        self.ftd_date = None
        self._history = []              # 상태 전이 히스토리

    def update(self, date: str, close: float, prev_close: float,
               volume: int = 0, prev_volume: int = 0) -> RallyState:
        """일별 데이터로 상태 머신 업데이트.

        Args:
            date: 날짜 문자열
            close: 당일 종가
            prev_close: 전일 종가
            volume: 당일 거래량
            prev_volume: 전일 거래량
        Returns:
            업데이트 후 상태
        """
        daily_return = (close - prev_close) / prev_close if prev_close > 0 else 0

        if self.state == RallyState.NO_SIGNAL:
            self._handle_no_signal(date, close, daily_return)
        elif self.state == RallyState.CORRECTION:
            self._handle_correction(date, close, daily_return)
        elif self.state == RallyState.RALLY_ATTEMPT:
            self._handle_rally_attempt(date, close, daily_return, volume, prev_volume)
        elif self.state == RallyState.FTD_WINDOW:
            self._handle_ftd_window(date, close, daily_return, volume, prev_volume)
        elif self.state == RallyState.FTD_CONFIRMED:
            self._handle_ftd_confirmed(date, close)
        elif self.state in (RallyState.RALLY_FAILED, RallyState.FTD_INVALIDATED):
            # 실패/무효화 후 다시 조정 감시
            self._transition(RallyState.CORRECTION, date)
            self._handle_correction(date, close, daily_return)

        return self.state

    def _handle_no_signal(self, date: str, close: float, daily_return: float):
        """NO_SIGNAL: 조정 시작 감지."""
        if self.correction_start is None:
            self.correction_start = close

        pct_from_start = (close - self.correction_start) / self.correction_start
        if daily_return < 0:
            self.correction_days += 1
        else:
            self.correction_days = 0
            self.correction_start = close

        if (pct_from_start <= self.CORRECTION_THRESHOLD and
                self.correction_days >= self.MIN_CORRECTION_DAYS):
            self.swing_low = close
            self.swing_low_date = date
            self._transition(RallyState.CORRECTION, date)

    def _handle_correction(self, date: str, close: float, daily_return: float):
        """CORRECTION: 스윙 로우 갱신 + 랠리 시작 감지."""
        if close < (self.swing_low or float('inf')):
            self.swing_low = close
            self.swing_low_date = date

        if daily_return > 0 and self.swing_low is not None:
            self.rally_day = 1
            self._transition(RallyState.RALLY_ATTEMPT, date)

    def _handle_rally_attempt(self, date: str, close: float, daily_return: float,
                               volume: int, prev_volume: int):
        """RALLY_ATTEMPT (Day 1-3): 스윙 로우 이탈 감시."""
        if close < self.swing_low:
            self._transition(RallyState.RALLY_FAILED, date)
            return

        self.rally_day += 1

        if self.rally_day >= 4:
            self._transition(RallyState.FTD_WINDOW, date)

    def _handle_ftd_window(self, date: str, close: float, daily_return: float,
                            volume: int, prev_volume: int):
        """FTD_WINDOW (Day 4-10): FTD 자격 판정."""
        if close < self.swing_low:
            self._transition(RallyState.RALLY_FAILED, date)
            return

        self.rally_day += 1

        if self.rally_day > 10:
            self._transition(RallyState.RALLY_FAILED, date)
            return

        # FTD 자격 조건: +1.5% AND 거래량 증가
        if daily_return >= 0.015 and volume > prev_volume:
            self.ftd_close = close
            self.ftd_date = date
            self._transition(RallyState.FTD_CONFIRMED, date)

    def _handle_ftd_confirmed(self, date: str, close: float):
        """FTD_CONFIRMED: FTD 무효화 감시."""
        if self.ftd_close is not None and close < self.ftd_close:
            self._transition(RallyState.FTD_INVALIDATED, date)

    def _transition(self, new_state: RallyState, date: str):
        """상태 전이 + 히스토리 기록."""
        old_state = self.state
        self.state = new_state
        self._history.append({
            'date': date,
            'from': old_state.value,
            'to': new_state.value,
        })

    def get_state(self) -> dict:
        """현재 상태 + 메타데이터."""
        return {
            'index_name': self.index_name,
            'state': self.state.value,
            'swing_low': self.swing_low,
            'swing_low_date': self.swing_low_date,
            'rally_day': self.rally_day,
            'ftd_close': self.ftd_close,
            'ftd_date': self.ftd_date,
            'history': self._history[-5:],  # 최근 5개 전이만
        }

    def reset(self):
        """상태 초기화."""
        self.state = RallyState.NO_SIGNAL
        self.swing_low = None
        self.swing_low_date = None
        self.rally_day = 0
        self.correction_start = None
        self.correction_days = 0
        self.ftd_close = None
        self.ftd_date = None
        self._history = []
