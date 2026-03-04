"""L 컴포넌트: RS Rank (Leadership / Relative Strength)."""

# ── 임계값 ────────────────────────────────────────────────
L_THRESHOLDS = [
    (90, 100),
    (80,  80),
    (70,  60),
    (50,  40),
]
L_DEFAULT = 20

# ── Minervini RS 가중치 ────────────────────────────────────
RS_WEIGHTS = {
    '3m': 0.40,   # 최근 3개월 40%
    '6m': 0.20,   # 6개월 20%
    '9m': 0.20,   # 9개월 20%
    '12m': 0.20,  # 12개월 20%
}


def calc_rs_rank(stock_returns: dict, all_stock_returns: list = None) -> dict:
    """RS Rank 계산 (Minervini 가중치).

    Args:
        stock_returns: {'3m': float, '6m': float, '9m': float, '12m': float}
            각 기간 수익률 (%)
        all_stock_returns: [weighted_return, ...] 전종목 가중 수익률 리스트
            백분위 순위 계산용
    Returns:
        {'score': int, 'rs_rank': float, 'weighted_return': float}
    """
    weighted = (
        stock_returns.get('3m', 0) * RS_WEIGHTS['3m'] +
        stock_returns.get('6m', 0) * RS_WEIGHTS['6m'] +
        stock_returns.get('9m', 0) * RS_WEIGHTS['9m'] +
        stock_returns.get('12m', 0) * RS_WEIGHTS['12m']
    )

    # 백분위 계산
    rs_rank = 50  # 기본값
    if all_stock_returns and len(all_stock_returns) > 0:
        below_count = sum(1 for r in all_stock_returns if r < weighted)
        rs_rank = (below_count / len(all_stock_returns)) * 100

    score = L_DEFAULT
    for threshold, s in L_THRESHOLDS:
        if rs_rank >= threshold:
            score = s
            break

    return {
        'score': score,
        'rs_rank': round(rs_rank, 1),
        'weighted_return': round(weighted, 2),
    }


def calc_period_returns(prices: list, index_prices: list = None) -> dict:
    """기간별 수익률 계산.

    Args:
        prices: 일봉 종가 (최근 260일, 최신이 마지막)
        index_prices: KOSPI 지수 종가 (동일 기간)
    Returns:
        {'3m': float, '6m': float, '9m': float, '12m': float}
    """
    if len(prices) < 260:
        return {'3m': 0, '6m': 0, '9m': 0, '12m': 0}

    current = prices[-1]
    if current <= 0:
        return {'3m': 0, '6m': 0, '9m': 0, '12m': 0}

    periods = {
        '3m': 63,    # ~3개월
        '6m': 126,   # ~6개월
        '9m': 189,   # ~9개월
        '12m': 252,  # ~12개월
    }

    returns = {}
    for label, days in periods.items():
        idx = max(0, len(prices) - 1 - days)
        past = prices[idx]
        if past > 0:
            stock_ret = ((current - past) / past) * 100
            # 지수 대비 상대 수익률
            if index_prices and len(index_prices) > idx:
                idx_current = index_prices[-1]
                idx_past = index_prices[idx]
                if idx_past > 0 and idx_current > 0:
                    idx_ret = ((idx_current - idx_past) / idx_past) * 100
                    stock_ret -= idx_ret
            returns[label] = stock_ret
        else:
            returns[label] = 0

    return returns
