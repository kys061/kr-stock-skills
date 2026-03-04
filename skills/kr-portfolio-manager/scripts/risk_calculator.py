"""kr-portfolio-manager: 리스크 메트릭스 계산."""

import math
from portfolio_analyzer import DIVERSIFICATION, KR_TAX_MODEL


def calc_portfolio_variance(weights: list, returns_matrix: list) -> float:
    """포트폴리오 분산 계산 (단순화).

    Args:
        weights: 비중 리스트
        returns_matrix: [[수익률, ...], ...] 종목별 수익률 시계열

    Returns:
        포트폴리오 분산
    """
    if not weights or not returns_matrix:
        return 0.0

    n = len(weights)
    if n != len(returns_matrix):
        return 0.0

    # 각 종목의 평균 수익률
    means = []
    for returns in returns_matrix:
        if returns:
            means.append(sum(returns) / len(returns))
        else:
            means.append(0)

    # 공분산 행렬 (단순 계산)
    periods = min(len(r) for r in returns_matrix) if returns_matrix else 0
    if periods < 2:
        return 0.0

    variance = 0.0
    for i in range(n):
        for j in range(n):
            cov = 0.0
            for t in range(periods):
                cov += ((returns_matrix[i][t] - means[i])
                        * (returns_matrix[j][t] - means[j]))
            cov /= (periods - 1)
            variance += weights[i] * weights[j] * cov

    return round(variance, 8)


def calc_portfolio_volatility(weights: list,
                              returns_matrix: list) -> float:
    """포트폴리오 변동성 (연율)."""
    var = calc_portfolio_variance(weights, returns_matrix)
    if var <= 0:
        return 0.0
    return round(math.sqrt(var) * math.sqrt(252), 4)


def calc_sharpe_ratio(portfolio_return: float,
                      portfolio_vol: float,
                      risk_free: float = 0.035) -> float:
    """샤프 비율.

    Args:
        portfolio_return: 포트폴리오 연간 수익률
        portfolio_vol: 포트폴리오 연간 변동성
        risk_free: 무위험 이자율 (BOK 기준금리)

    Returns:
        샤프 비율
    """
    if portfolio_vol <= 0:
        return 0.0
    return round((portfolio_return - risk_free) / portfolio_vol, 4)


def calc_max_drawdown(equity_curve: list) -> dict:
    """최대 낙폭 계산.

    Args:
        equity_curve: 평가 금액 시계열

    Returns:
        {'max_drawdown_pct', 'peak', 'trough', 'peak_idx', 'trough_idx'}
    """
    if not equity_curve or len(equity_curve) < 2:
        return {
            'max_drawdown_pct': 0.0,
            'peak': 0, 'trough': 0,
            'peak_idx': 0, 'trough_idx': 0,
        }

    peak = equity_curve[0]
    peak_idx = 0
    max_dd = 0.0
    dd_peak = peak
    dd_peak_idx = 0
    dd_trough = peak
    dd_trough_idx = 0

    for i, value in enumerate(equity_curve):
        if value > peak:
            peak = value
            peak_idx = i
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            dd_peak = peak
            dd_peak_idx = peak_idx
            dd_trough = value
            dd_trough_idx = i

    return {
        'max_drawdown_pct': round(max_dd * 100, 2),
        'peak': dd_peak,
        'trough': dd_trough,
        'peak_idx': dd_peak_idx,
        'trough_idx': dd_trough_idx,
    }


def calc_correlation(returns_a: list, returns_b: list) -> float:
    """두 수익률 시계열의 상관계수.

    Args:
        returns_a: 종목A 수익률 시계열
        returns_b: 종목B 수익률 시계열

    Returns:
        피어슨 상관계수
    """
    n = min(len(returns_a), len(returns_b))
    if n < 2:
        return 0.0

    a = returns_a[:n]
    b = returns_b[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / (n - 1)
    var_a = sum((x - mean_a) ** 2 for x in a) / (n - 1)
    var_b = sum((x - mean_b) ** 2 for x in b) / (n - 1)

    if var_a <= 0 or var_b <= 0:
        return 0.0

    return round(cov / (math.sqrt(var_a) * math.sqrt(var_b)), 4)


def detect_correlation_redundancy(holdings: list,
                                  returns_data: dict) -> list:
    """상관관계 중복 종목 탐지.

    Args:
        holdings: 포지션 리스트
        returns_data: {symbol: [수익률 시계열], ...}

    Returns:
        중복 쌍 리스트
    """
    threshold = DIVERSIFICATION['correlation_redundancy']
    redundancies = []
    symbols = [h.get('symbol') for h in holdings if h.get('symbol') in returns_data]

    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            corr = calc_correlation(
                returns_data[symbols[i]],
                returns_data[symbols[j]]
            )
            if abs(corr) >= threshold:
                redundancies.append({
                    'pair': (symbols[i], symbols[j]),
                    'correlation': corr,
                    'threshold': threshold,
                })

    return redundancies


def calc_risk_metrics(holdings: list, equity_curve: list = None,
                      returns_data: dict = None,
                      annual_return: float = None) -> dict:
    """리스크 메트릭스 종합 계산.

    Args:
        holdings: 포지션 리스트
        equity_curve: 평가 금액 시계열 (옵션)
        returns_data: {symbol: [수익률 시계열]} (옵션)
        annual_return: 연간 수익률 (옵션)

    Returns:
        리스크 메트릭스 dict
    """
    total_value = sum(h.get('value', 0) for h in holdings)
    weights = []
    for h in holdings:
        w = h.get('value', 0) / total_value if total_value > 0 else 0
        weights.append(w)

    result = {
        'total_value': total_value,
        'position_count': len(holdings),
    }

    # 변동성 (returns_data 있을 경우)
    if returns_data:
        matrix = [returns_data.get(h.get('symbol', ''), []) for h in holdings]
        vol = calc_portfolio_volatility(weights, matrix)
        result['volatility'] = vol

        # 샤프 비율
        if annual_return is not None:
            result['sharpe_ratio'] = calc_sharpe_ratio(annual_return, vol)

        # 상관관계 중복
        redundancies = detect_correlation_redundancy(holdings, returns_data)
        result['correlation_redundancies'] = redundancies

    # MDD
    if equity_curve:
        result['max_drawdown'] = calc_max_drawdown(equity_curve)

    # 집중도 리스크
    max_weight = max(weights) if weights else 0
    result['max_position_weight'] = round(max_weight, 4)
    result['concentration_risk'] = max_weight > DIVERSIFICATION['max_single_position']

    return result
