"""
kr-market-top-detector: 외국인 이탈 강도 계산기.
한국 시장 특화 — Component 7.
"""


def calc_consecutive_sell_days(daily_net: list[float]) -> int:
    """최근부터 외국인 연속 순매도 일수.

    Args:
        daily_net: 외국인 일별 순매수 금액 (최신이 마지막)
    Returns:
        연속 순매도 일수 (0 이상)
    """
    if not daily_net:
        return 0
    count = 0
    for val in reversed(daily_net):
        if val < 0:
            count += 1
        else:
            break
    return count


def calc_sell_intensity(daily_net: list[float],
                        recent: int = 5, avg_window: int = 20) -> float:
    """매도 강도: 최근 5일 순매도 / 20일 평균 절대값.

    Args:
        daily_net: 외국인 일별 순매수 금액
        recent: 최근 일수
        avg_window: 평균 산출 기간
    Returns:
        강도 배수 (양수 = 매도 강도 높음)
    """
    if len(daily_net) < recent:
        return 0.0

    recent_sum = sum(daily_net[-recent:])
    avg_window_data = daily_net[-avg_window:] if len(daily_net) >= avg_window \
        else daily_net
    avg_abs = sum(abs(v) for v in avg_window_data) / len(avg_window_data) \
        if avg_window_data else 1.0

    if avg_abs == 0:
        return 0.0
    # 순매도면 음수, 절대값 대비 비율
    return -recent_sum / (avg_abs * recent)


def score_foreign_flow(consecutive_sell: int,
                       sell_intensity: float) -> float:
    """외국인 이탈 → 점수 (0-100).

    | 조건 | 점수 |
    |------|:----:|
    | 연속 순매수 5일+ | 0-10 |
    | 중립 | 10-30 |
    | 연속 순매도 3-5일 | 30-50 |
    | 연속 순매도 5-10일 + 강도 1.5x+ | 50-75 |
    | 연속 순매도 10일+ + 강도 2x+ | 75-100 |
    """
    # 순매수 상태
    if consecutive_sell == 0:
        return 5.0
    if consecutive_sell < 0:
        return 0.0  # 방어적 처리

    # 연속 순매도 일수 기반 기본 점수
    if consecutive_sell <= 2:
        base = 15.0 + consecutive_sell * 5  # 15-25
    elif consecutive_sell <= 5:
        base = 30.0 + (consecutive_sell - 3) * 10  # 30-50
    elif consecutive_sell <= 10:
        base = 50.0 + (consecutive_sell - 5) * 5  # 50-75
    else:
        base = min(100.0, 75.0 + (consecutive_sell - 10) * 5)  # 75-100

    # 강도 보정 (1.5x 이상이면 점수 증가)
    if sell_intensity >= 2.0 and consecutive_sell >= 5:
        base = min(100.0, base * 1.2)
    elif sell_intensity >= 1.5 and consecutive_sell >= 3:
        base = min(100.0, base * 1.1)

    return min(100.0, base)


class ForeignFlowCalculator:
    """외국인 이탈 강도 종합 계산."""

    def calculate(self, daily_net: list[float]) -> dict:
        """투자자별 매매동향 → 이탈 지표.

        Args:
            daily_net: 외국인 일별 순매수 금액 (오래된→최신)
        Returns:
            {'consecutive_sell_days', 'sell_intensity', 'signal'}
        """
        consec = calc_consecutive_sell_days(daily_net)
        intensity = calc_sell_intensity(daily_net)

        if consec >= 10 and intensity >= 2.0:
            signal = 'strong_outflow'
        elif consec >= 5 and intensity >= 1.0:
            signal = 'moderate_outflow'
        elif consec >= 3:
            signal = 'mild_outflow'
        elif consec == 0 and len(daily_net) > 0 and daily_net[-1] > 0:
            signal = 'inflow'
        else:
            signal = 'neutral'

        return {
            'consecutive_sell_days': consec,
            'sell_intensity': round(intensity, 2),
            'signal': signal,
        }

    def score(self, flow: dict) -> float:
        """이탈 지표 → 점수(0-100)."""
        return score_foreign_flow(
            flow.get('consecutive_sell_days', 0),
            flow.get('sell_intensity', 0.0),
        )
