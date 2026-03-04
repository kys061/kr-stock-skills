"""
kr-macro-regime: 사이즈 팩터 계산기.
KOSDAQ / KOSPI 비율 추세.
"""


def calc_ratio(kosdaq: float, kospi: float) -> float:
    """KOSDAQ / KOSPI 비율."""
    if kospi <= 0:
        return 0.0
    return kosdaq / kospi


def calc_trend(ratios: list[float], threshold: float = 0.02) -> str:
    """비율 시계열 → 추세.

    Args:
        ratios: KOSDAQ/KOSPI 비율 시계열
        threshold: 변화 임계값
    Returns:
        'rising' | 'falling' | 'stable'
    """
    if len(ratios) < 2:
        return 'stable'

    recent_len = min(6, len(ratios))
    long_len = min(12, len(ratios))

    sma_6m = sum(ratios[-recent_len:]) / recent_len
    sma_12m = sum(ratios[-long_len:]) / long_len

    if sma_12m <= 0:
        return 'stable'

    diff = (sma_6m - sma_12m) / sma_12m
    if diff > threshold:
        return 'rising'
    elif diff < -threshold:
        return 'falling'
    return 'stable'


def regime_signal(trend: str) -> str:
    """추세 → 레짐 시그널."""
    mapping = {
        'rising': 'Broadening',
        'falling': 'Concentration',
        'stable': 'Transitional',
    }
    return mapping.get(trend, 'Transitional')


class SizeFactorCalculator:
    """KOSDAQ/KOSPI 사이즈 팩터 분석."""

    def calculate(self, kospi_values: list[float],
                  kosdaq_values: list[float]) -> dict:
        """KOSDAQ/KOSPI 비율 추세 분석.

        Args:
            kospi_values: KOSPI 지수 시계열
            kosdaq_values: KOSDAQ 지수 시계열
        Returns:
            {'current_ratio', 'trend', 'regime_signal'}
        """
        if not kospi_values or not kosdaq_values:
            return {
                'current_ratio': 0.0,
                'trend': 'stable',
                'regime_signal': 'Transitional',
            }

        min_len = min(len(kospi_values), len(kosdaq_values))
        ratios = [
            calc_ratio(kosdaq_values[i], kospi_values[i])
            for i in range(min_len)
        ]

        current = ratios[-1] if ratios else 0.0
        trend_ = calc_trend(ratios)

        return {
            'current_ratio': round(current, 4),
            'trend': trend_,
            'regime_signal': regime_signal(trend_),
        }
