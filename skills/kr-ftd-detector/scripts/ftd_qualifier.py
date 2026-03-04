"""
kr-ftd-detector: FTD 자격 판정 + 품질 점수 계산.
5-컴포넌트 가중치 시스템.
"""

# ── 품질 점수 가중치 ──────────────────────────────────

QUALITY_WEIGHTS = {
    'volume_surge': 0.25,
    'day_number': 0.15,
    'gain_size': 0.20,
    'breadth_confirmation': 0.20,
    'foreign_flow': 0.20,
}

# ── 노출 가이드 ──────────────────────────────────────

EXPOSURE_LEVELS = [
    {'name': 'Strong FTD',   'min': 80, 'max': 100, 'exposure': '75-100%'},
    {'name': 'Moderate FTD', 'min': 60, 'max': 79,  'exposure': '50-75%'},
    {'name': 'Weak FTD',     'min': 40, 'max': 59,  'exposure': '25-50%'},
    {'name': 'No FTD',       'min': 0,  'max': 39,  'exposure': '0-25%'},
]

# ── FTD 자격 상수 ─────────────────────────────────────

FTD_MIN_GAIN = 0.015       # +1.5%
FTD_WINDOW_START = 4
FTD_WINDOW_END = 10


def score_volume_surge(volume_ratio: float) -> float:
    """Component 1: 거래량 급증 점수 (0-100).

    Args:
        volume_ratio: FTD일 거래량 / 전일 거래량
    """
    if volume_ratio < 1.0:
        return 0.0
    elif volume_ratio < 1.2:
        return 30.0
    elif volume_ratio < 1.5:
        return 50.0
    elif volume_ratio < 2.0:
        return 70.0
    else:
        return min(90.0 + (volume_ratio - 2.0) * 10.0, 100.0)


def score_day_number(day: int) -> float:
    """Component 2: FTD 발생일 점수 (0-100).

    Args:
        day: 랠리 시작 후 일수 (4-10)
    """
    day_scores = {
        4: 100.0,
        5: 90.0,
        6: 80.0,
        7: 65.0,
        8: 50.0,
        9: 35.0,
        10: 20.0,
    }
    return day_scores.get(day, 0.0)


def score_gain_size(gain: float) -> float:
    """Component 3: 상승폭 점수 (0-100).

    Args:
        gain: FTD일 상승률 (0.015 = 1.5%)
    """
    if gain < FTD_MIN_GAIN:
        return 0.0
    elif gain < 0.020:
        return 40.0
    elif gain < 0.025:
        return 60.0
    elif gain < 0.035:
        return 80.0
    else:
        return 100.0


def score_breadth_confirmation(breadth_change: float) -> float:
    """Component 4: 시장폭 확인 점수 (0-100).

    Args:
        breadth_change: 200MA 위 종목 비율 변화 (%p, 0.05 = +5%p 개선)
    """
    if breadth_change >= 0.05:
        return 90.0
    elif breadth_change >= 0.02:
        return 60.0
    elif breadth_change >= -0.02:
        return 30.0
    else:
        return 10.0


def score_foreign_flow(foreign_net_today: float, foreign_net_yesterday: float,
                        was_selling: bool) -> float:
    """Component 5: 외국인 순매수 전환 점수 (0-100).

    Args:
        foreign_net_today: FTD 당일 외국인 순매수 금액 (양수=순매수)
        foreign_net_yesterday: 전일 외국인 순매수 금액
        was_selling: 직전 5일간 외국인 순매도 상태였는지
    """
    if foreign_net_today > 0 and foreign_net_yesterday > 0 and was_selling:
        return 95.0  # 2일 연속 순매수 전환 (이전 순매도에서)
    elif foreign_net_today > 0 and was_selling:
        return 70.0  # 당일만 순매수 전환
    elif foreign_net_today > 0:
        return 50.0  # 순매수이지만 이전에도 순매수 (전환 아님)
    elif foreign_net_today <= 0 and was_selling:
        return 10.0  # 순매도 지속
    else:
        return 30.0  # 중립


def get_exposure_level(quality_score: float) -> dict:
    """품질 점수 → 노출 수준 매핑.

    Args:
        quality_score: 0-100
    Returns:
        {'name': str, 'exposure': str}
    """
    clamped = max(0, min(quality_score, 100))
    for level in EXPOSURE_LEVELS:
        if level['min'] <= clamped <= level['max']:
            return {'name': level['name'], 'exposure': level['exposure']}
    return {'name': 'No FTD', 'exposure': '0-25%'}


class FTDQualifier:
    """FTD 자격 판정 + 품질 점수 계산기."""

    def qualify(self, rally_day: int, daily_return: float,
                volume_ratio: float,
                breadth_change: float = 0.0,
                foreign_net_today: float = 0.0,
                foreign_net_yesterday: float = 0.0,
                was_selling: bool = False) -> dict:
        """FTD 자격 판정 + 품질 점수 계산.

        Args:
            rally_day: 랠리 Day (4-10이 유효)
            daily_return: 당일 수익률 (0.02 = +2%)
            volume_ratio: 당일/전일 거래량 비율
            breadth_change: 시장폭 변화 (%p)
            foreign_net_today: 외국인 당일 순매수
            foreign_net_yesterday: 외국인 전일 순매수
            was_selling: 외국인 이전 순매도 상태
        Returns:
            {
                'is_ftd': bool,
                'quality_score': float (0-100),
                'components': dict,
                'exposure': dict,
            }
        """
        # FTD 자격 기본 조건
        is_ftd = (
            FTD_WINDOW_START <= rally_day <= FTD_WINDOW_END
            and daily_return >= FTD_MIN_GAIN
            and volume_ratio > 1.0
        )

        if not is_ftd:
            return {
                'is_ftd': False,
                'quality_score': 0.0,
                'components': {},
                'exposure': get_exposure_level(0),
            }

        # 5-컴포넌트 품질 점수
        components = {
            'volume_surge': score_volume_surge(volume_ratio),
            'day_number': score_day_number(rally_day),
            'gain_size': score_gain_size(daily_return),
            'breadth_confirmation': score_breadth_confirmation(breadth_change),
            'foreign_flow': score_foreign_flow(
                foreign_net_today, foreign_net_yesterday, was_selling),
        }

        quality_score = sum(
            components[k] * QUALITY_WEIGHTS[k] for k in QUALITY_WEIGHTS
        )
        quality_score = max(0.0, min(quality_score, 100.0))

        return {
            'is_ftd': True,
            'quality_score': quality_score,
            'components': components,
            'exposure': get_exposure_level(quality_score),
        }
