"""
kr-macro-regime: 금리 곡선 계산기.
국고채 10년 - 3년 스프레드.
"""


def calc_spread(yield_10y: float, yield_3y: float) -> float:
    """10Y - 3Y 스프레드 (bp 단위)."""
    return (yield_10y - yield_3y) * 100  # bp


def classify_spread(spread_bp: float) -> str:
    """스프레드 → 상태 분류.

    | 스프레드 | 상태 |
    |---------|------|
    | < 0bp | inverted (역전) |
    | 0-30bp | flat (평탄) |
    | 30-100bp | normal (정상) |
    | > 100bp | steep (스티프) |
    """
    if spread_bp < 0:
        return 'inverted'
    elif spread_bp < 30:
        return 'flat'
    elif spread_bp <= 100:
        return 'normal'
    return 'steep'


def regime_signal(state: str) -> str:
    """상태 → 레짐 시그널."""
    mapping = {
        'inverted': 'Contraction',
        'flat': 'Transitional',
        'normal': 'Transitional',   # 중립
        'steep': 'Broadening',
    }
    return mapping.get(state, 'Transitional')


class YieldCurveCalculator:
    """한국 국채 금리 곡선 분석."""

    def calculate(self, yields_10y: list[float],
                  yields_3y: list[float]) -> dict:
        """국고채 10Y-3Y 스프레드 분석.

        Args:
            yields_10y: 10년 국고채 수익률 시계열 (%)
            yields_3y: 3년 국고채 수익률 시계열 (%)
        Returns:
            {'current_spread_bp', 'state', 'regime_signal'}
        """
        if not yields_10y or not yields_3y:
            return {
                'current_spread_bp': 0.0,
                'state': 'normal',
                'regime_signal': 'Transitional',
            }

        spread = calc_spread(yields_10y[-1], yields_3y[-1])
        state = classify_spread(spread)

        return {
            'current_spread_bp': round(spread, 1),
            'state': state,
            'regime_signal': regime_signal(state),
        }
