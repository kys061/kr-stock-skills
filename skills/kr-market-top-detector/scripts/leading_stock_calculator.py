"""
kr-market-top-detector: 선도주 건전성 계산기.
한국 선도주 8종목의 건전성을 측정.
"""


KR_LEADING_STOCKS = [
    {'ticker': '005930', 'name': '삼성전자', 'theme': 'AI/반도체'},
    {'ticker': '000660', 'name': 'SK하이닉스', 'theme': '반도체'},
    {'ticker': '373220', 'name': 'LG에너지솔루션', 'theme': '2차전지'},
    {'ticker': '207940', 'name': '삼성바이오로직스', 'theme': '바이오'},
    {'ticker': '005380', 'name': '현대차', 'theme': '자동차'},
    {'ticker': '068270', 'name': '셀트리온', 'theme': '바이오시밀러'},
    {'ticker': '035420', 'name': 'NAVER', 'theme': '플랫폼'},
    {'ticker': '012450', 'name': '한화에어로스페이스', 'theme': '방산'},
]


def calc_pct_below_50ma(stock_data: list[dict]) -> float:
    """50MA 아래 종목 비율.

    Args:
        stock_data: [{'close': float, 'ma50': float}, ...]
    Returns:
        0.0~1.0 비율
    """
    if not stock_data:
        return 0.0
    below = sum(1 for s in stock_data
                if s.get('close', 0) < s.get('ma50', float('inf')))
    return below / len(stock_data)


def calc_avg_drawdown(stock_data: list[dict]) -> float:
    """52주 고점 대비 평균 하락률.

    Args:
        stock_data: [{'close': float, 'high_52w': float}, ...]
    Returns:
        음수 비율 (예: -0.12 = -12%)
    """
    if not stock_data:
        return 0.0
    drawdowns = []
    for s in stock_data:
        high = s.get('high_52w', 0)
        close = s.get('close', 0)
        if high > 0:
            drawdowns.append((close - high) / high)
    return sum(drawdowns) / len(drawdowns) if drawdowns else 0.0


def calc_declining_count(stock_data: list[dict]) -> int:
    """주간 수익률 음수 종목 수.

    Args:
        stock_data: [{'weekly_return': float}, ...]
    Returns:
        음수 종목 수
    """
    return sum(1 for s in stock_data if s.get('weekly_return', 0) < 0)


def score_leading_stocks(pct_below_50ma: float, avg_drawdown: float,
                         declining_count: int, total: int = 8) -> float:
    """선도주 건전성 → 점수 (0-100).

    50MA 아래 비율 60% + 평균 하락률 30% + 하락 종목 수 10%
    """
    # 50MA 아래 비율 점수 (0~1 → 0~100)
    ma_score = min(pct_below_50ma * 100 / 0.88, 100.0)  # 88%+ → 100

    # 평균 하락률 점수 (0% → 0, -25% → 100)
    dd = abs(avg_drawdown)
    dd_score = min(dd / 0.25 * 100, 100.0)

    # 하락 종목 수 점수
    if total > 0:
        decline_score = (declining_count / total) * 100
    else:
        decline_score = 0.0

    return ma_score * 0.6 + dd_score * 0.3 + decline_score * 0.1


class LeadingStockCalculator:
    """선도주 건전성 종합 계산."""

    def calculate(self, stock_data: list[dict]) -> dict:
        """건전성 지표 계산.

        Args:
            stock_data: [{'close', 'ma50', 'high_52w', 'weekly_return'}, ...]
        Returns:
            {'pct_below_50ma', 'avg_drawdown', 'declining_count', 'total'}
        """
        return {
            'pct_below_50ma': calc_pct_below_50ma(stock_data),
            'avg_drawdown': calc_avg_drawdown(stock_data),
            'declining_count': calc_declining_count(stock_data),
            'total': len(stock_data),
        }

    def score(self, health: dict) -> float:
        """건전성 지표 → 점수(0-100)."""
        return score_leading_stocks(
            health.get('pct_below_50ma', 0),
            health.get('avg_drawdown', 0),
            health.get('declining_count', 0),
            health.get('total', 8),
        )
