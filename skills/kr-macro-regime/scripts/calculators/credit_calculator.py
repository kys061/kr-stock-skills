"""
kr-macro-regime: 신용 환경 계산기.
회사채 BBB- vs AA- 스프레드.
"""


def calc_credit_spread(bbb_yield: float, aa_yield: float) -> float:
    """BBB- - AA- 스프레드 (bp 단위)."""
    return (bbb_yield - aa_yield) * 100


def calc_trend(spreads: list[float], threshold: float = 10.0) -> str:
    """스프레드 추세 판정.

    Args:
        spreads: 스프레드 bp 시계열
        threshold: 변화 임계값 (bp)
    Returns:
        'widening' | 'tightening' | 'stable'
    """
    if len(spreads) < 2:
        return 'stable'

    # 6M vs 12M
    recent_len = min(6, len(spreads))
    long_len = min(12, len(spreads))

    sma_6m = sum(spreads[-recent_len:]) / recent_len
    sma_12m = sum(spreads[-long_len:]) / long_len

    diff = sma_6m - sma_12m
    if diff > threshold:
        return 'widening'
    elif diff < -threshold:
        return 'tightening'
    return 'stable'


def regime_signal(trend: str) -> str:
    """추세 → 레짐 시그널."""
    mapping = {
        'widening': 'Contraction',
        'tightening': 'Broadening',
        'stable': 'Transitional',
    }
    return mapping.get(trend, 'Transitional')


class CreditCalculator:
    """한국 신용 환경 분석."""

    def calculate(self, bbb_yields: list[float],
                  aa_yields: list[float]) -> dict:
        """BBB- vs AA- 스프레드 분석.

        Args:
            bbb_yields: BBB- 수익률 시계열 (%)
            aa_yields: AA- 수익률 시계열 (%)
        Returns:
            {'current_spread_bp', 'trend', 'regime_signal'}
        """
        if not bbb_yields or not aa_yields:
            return {
                'current_spread_bp': 0.0,
                'trend': 'stable',
                'regime_signal': 'Transitional',
            }

        min_len = min(len(bbb_yields), len(aa_yields))
        spreads = [
            calc_credit_spread(bbb_yields[i], aa_yields[i])
            for i in range(min_len)
        ]

        current = spreads[-1] if spreads else 0.0
        trend_ = calc_trend(spreads)

        return {
            'current_spread_bp': round(current, 1),
            'trend': trend_,
            'regime_signal': regime_signal(trend_),
        }
