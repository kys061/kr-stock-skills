"""
kr-macro-regime: 시장 집중도 계산기.
KOSPI 상위 10종목 시총 비중 추세.
"""


def calc_top10_ratio(market_caps: list[float]) -> float:
    """상위 10종목 비중 계산.

    Args:
        market_caps: 전종목 시가총액 리스트 (내림차순 정렬)
    Returns:
        상위 10종목 비율 (0-1)
    """
    if not market_caps or len(market_caps) < 10:
        return 0.0
    total = sum(market_caps)
    if total <= 0:
        return 0.0
    top10 = sum(market_caps[:10])
    return top10 / total


def calc_trend(sma_6m: float, sma_12m: float,
               threshold: float = 0.02) -> str:
    """6M/12M SMA 크로스오버 추세 판정.

    Args:
        sma_6m: 6개월 SMA 값
        sma_12m: 12개월 SMA 값
        threshold: 변화 임계값
    Returns:
        'concentrating' | 'broadening' | 'stable'
    """
    if sma_12m <= 0:
        return 'stable'
    diff = (sma_6m - sma_12m) / sma_12m
    if diff > threshold:
        return 'concentrating'
    elif diff < -threshold:
        return 'broadening'
    return 'stable'


def regime_signal(trend: str) -> str:
    """추세 → 레짐 시그널 매핑."""
    mapping = {
        'concentrating': 'Concentration',
        'broadening': 'Broadening',
        'stable': 'Transitional',
    }
    return mapping.get(trend, 'Transitional')


class ConcentrationCalculator:
    """시장 집중도 분석."""

    def calculate(self, top10_ratios: list[float]) -> dict:
        """비중 시계열 → 추세 분석.

        Args:
            top10_ratios: 상위 10종목 비중 시계열 (오래된→최신)
        Returns:
            {'current_ratio', 'sma_6m', 'sma_12m', 'trend', 'regime_signal'}
        """
        if not top10_ratios:
            return {
                'current_ratio': 0.0,
                'sma_6m': 0.0,
                'sma_12m': 0.0,
                'trend': 'stable',
                'regime_signal': 'Transitional',
            }

        current = top10_ratios[-1]

        # SMA 계산 (월간 데이터 가정: 6M=6개, 12M=12개)
        sma_6m = (sum(top10_ratios[-6:]) / min(6, len(top10_ratios))
                  if len(top10_ratios) >= 1 else current)
        sma_12m = (sum(top10_ratios[-12:]) / min(12, len(top10_ratios))
                   if len(top10_ratios) >= 1 else current)

        trend_ = calc_trend(sma_6m, sma_12m)

        return {
            'current_ratio': round(current, 4),
            'sma_6m': round(sma_6m, 4),
            'sma_12m': round(sma_12m, 4),
            'trend': trend_,
            'regime_signal': regime_signal(trend_),
        }
