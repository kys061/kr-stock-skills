"""
kr-macro-regime: 주식-채권 관계 계산기.
KOSPI / 국고채 비율 + 60일 롤링 상관계수.
"""


def calc_correlation(series_a: list[float], series_b: list[float],
                     window: int = 60) -> float:
    """두 시계열의 롤링 상관계수.

    Args:
        series_a, series_b: 가격/수익률 시계열 (동일 길이)
        window: 상관 계산 윈도우
    Returns:
        상관계수 (-1 ~ +1)
    """
    n = min(len(series_a), len(series_b), window)
    if n < 3:
        return 0.0

    a = series_a[-n:]
    b = series_b[-n:]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    var_a = sum((x - mean_a) ** 2 for x in a) / n
    var_b = sum((x - mean_b) ** 2 for x in b) / n

    denom = (var_a * var_b) ** 0.5
    if denom == 0:
        return 0.0
    return cov / denom


def classify_correlation(corr: float) -> str:
    """상관계수 → 분류.

    | 상관 | 분류 |
    |------|------|
    | > 0.3 | positive (양의 상관) |
    | < -0.3 | negative (음의 상관) |
    | -0.3~0.3 | weak (약한 상관) |
    """
    if corr > 0.3:
        return 'positive'
    elif corr < -0.3:
        return 'negative'
    return 'weak'


def regime_signal(corr_type: str) -> str:
    """상관 분류 → 레짐 시그널."""
    mapping = {
        'positive': 'Inflationary',
        'negative': 'Transitional',  # 정상적 역상관 = 중립
        'weak': 'Transitional',
    }
    return mapping.get(corr_type, 'Transitional')


class EquityBondCalculator:
    """주식-채권 관계 분석."""

    def calculate(self, kospi_values: list[float],
                  bond_prices: list[float]) -> dict:
        """KOSPI-국고채 비율 + 상관관계 분석.

        Args:
            kospi_values: KOSPI 지수 시계열
            bond_prices: 국고채 가격 시계열
        Returns:
            {'correlation', 'corr_type', 'regime_signal'}
        """
        if not kospi_values or not bond_prices:
            return {
                'correlation': 0.0,
                'corr_type': 'weak',
                'regime_signal': 'Transitional',
            }

        corr = calc_correlation(kospi_values, bond_prices)
        corr_type = classify_correlation(corr)

        return {
            'correlation': round(corr, 4),
            'corr_type': corr_type,
            'regime_signal': regime_signal(corr_type),
        }
