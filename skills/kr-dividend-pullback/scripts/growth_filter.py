"""
kr-dividend-pullback: 배당 성장 필터 + RSI 타이밍 필터.
Phase 1 배당 성장 → Phase 2 RSI 타이밍.
"""

# ── Phase 1: 배당 성장 필터 임계값 ────────────────────────
MIN_YIELD = 2.0                 # 배당수익률 최소 2.0%
MIN_DIVIDEND_CAGR = 8.0         # 3년 배당 CAGR 최소 8%
MIN_CONSECUTIVE_YEARS = 4       # 4년 연속 무삭감
MIN_MARKET_CAP = 300_000_000_000  # 시가총액 최소 3,000억원
MAX_DE_RATIO = 150.0            # 부채비율 최대 150%
MIN_CURRENT_RATIO = 1.0         # 유동비율 최소 1.0
MAX_PAYOUT_RATIO = 80.0         # 배당성향 최대 80%

# ── Phase 2: RSI 타이밍 ──────────────────────────────────
RSI_THRESHOLD = 40              # RSI 진입 임계값
RSI_PERIOD = 14                 # RSI 계산 기간

# ── RSI 점수 테이블 ──────────────────────────────────────
RSI_SCORE_TABLE = [
    (30, 90),   # RSI < 30: 극단적 과매도
    (35, 80),   # RSI 30-35: 강한 과매도
    (40, 70),   # RSI 35-40: 초기 풀백
]


def filter_growth(stock: dict) -> bool:
    """Phase 1: 배당 성장 필터.

    Args:
        stock: {
            'div_yield': float,
            'dividend_cagr': float,
            'dividend_history': list[float],  # 4년 [Y-4, Y-3, Y-2, Y-1]
            'market_cap': float,
            'revenue_trend_positive': bool,
            'eps_trend_positive': bool,
            'de_ratio': float,
            'current_ratio': float,
            'payout_ratio': float,
        }
    """
    if stock.get('div_yield', 0) < MIN_YIELD:
        return False
    if stock.get('dividend_cagr', 0) < MIN_DIVIDEND_CAGR:
        return False
    if stock.get('market_cap', 0) < MIN_MARKET_CAP:
        return False

    # 4년 연속 무삭감
    div_hist = stock.get('dividend_history', [])
    if len(div_hist) < MIN_CONSECUTIVE_YEARS:
        return False
    for d in div_hist:
        if d <= 0:
            return False
    for i in range(1, len(div_hist)):
        if div_hist[i] < div_hist[i - 1]:
            return False

    # 매출/EPS 성장
    if not stock.get('revenue_trend_positive', False):
        return False
    if not stock.get('eps_trend_positive', False):
        return False

    # 재무 건전성
    if stock.get('de_ratio', 200) >= MAX_DE_RATIO:
        return False
    if stock.get('current_ratio', 0) < MIN_CURRENT_RATIO:
        return False
    if stock.get('payout_ratio', 100) >= MAX_PAYOUT_RATIO:
        return False

    return True


def filter_rsi(rsi_value: float) -> bool:
    """Phase 2: RSI 타이밍 필터.

    Args:
        rsi_value: RSI(14) 값
    Returns:
        True if RSI ≤ 40 (진입 대상)
    """
    return rsi_value <= RSI_THRESHOLD


def score_rsi(rsi_value: float) -> int:
    """RSI 점수 (Technical Setup 컴포넌트).

    낮을수록 높은 점수.
    """
    if rsi_value > RSI_THRESHOLD:
        return 0
    for threshold, score in RSI_SCORE_TABLE:
        if rsi_value < threshold:
            return score
    return 70  # RSI 35-40 기본값


def calc_dividend_cagr(dividends: list) -> float:
    """배당 CAGR 계산.

    Args:
        dividends: [Y-N, ..., Y-1] 배당금 리스트
    Returns:
        CAGR (%)
    """
    if len(dividends) < 2 or dividends[0] <= 0 or dividends[-1] <= 0:
        return 0.0
    years = len(dividends) - 1
    return ((dividends[-1] / dividends[0]) ** (1 / years) - 1) * 100
