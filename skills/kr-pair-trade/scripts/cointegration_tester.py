"""공적분 테스트기: ADF (Augmented Dickey-Fuller) + Half-Life.

statsmodels 없을 경우 간소화 AR(1) 기반 대안 제공.
"""

import math

# ── ADF 등급 ──────────────────────────────────────────────────
ADF_GRADES = [
    (0.01, '★★★ 매우 강함', 100),
    (0.05, '★★ 보통',       70),
]
ADF_DEFAULT_SCORE = 20           # p > 0.05: 공적분 없음
ADF_PVALUE_THRESHOLD = 0.05     # 최소 통과 기준

# ── Half-Life 등급 ────────────────────────────────────────────
HALFLIFE_SCORES = [
    (30, 100),   # < 30일: 빠른 회귀
    (60, 70),    # 30-60일: 보통
]
HALFLIFE_DEFAULT = 40            # > 60일: 느림
HALFLIFE_BONUS_FAST = 10        # < 20일 추가 보너스


def calc_spread(prices_a: list, prices_b: list, beta: float = 1.0) -> list:
    """스프레드 계산: Spread = A - (beta * B).

    Args:
        prices_a: 종목 A 종가
        prices_b: 종목 B 종가
        beta: 헤지비율 (OLS 기울기)
    Returns:
        스프레드 리스트
    """
    n = min(len(prices_a), len(prices_b))
    return [prices_a[i] - beta * prices_b[i] for i in range(n)]


def calc_beta(prices_a: list, prices_b: list) -> float:
    """OLS 회귀 기울기 (헤지비율) 계산.

    Args:
        prices_a, prices_b: 종가 리스트
    Returns:
        beta (float)
    """
    n = min(len(prices_a), len(prices_b))
    if n < 30:
        return 1.0

    a = prices_a[-n:]
    b = prices_b[-n:]

    mean_b = sum(b) / n
    mean_a = sum(a) / n

    num = sum((b[i] - mean_b) * (a[i] - mean_a) for i in range(n))
    den = sum((b[i] - mean_b) ** 2 for i in range(n))

    if den == 0:
        return 1.0

    return num / den


def run_adf_test(spread: list) -> dict:
    """ADF 공적분 테스트 실행.

    statsmodels 사용 가능하면 adfuller(), 없으면 간소화 AR(1) 검정.

    Args:
        spread: 스프레드 리스트 (calc_spread() 결과)
    Returns:
        {'p_value': float, 'test_stat': float, 'is_cointegrated': bool, 'method': str}
    """
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(spread, maxlag=1, regression='c', autolag=None)
        return {
            'p_value': round(result[1], 6),
            'test_stat': round(result[0], 4),
            'is_cointegrated': result[1] < ADF_PVALUE_THRESHOLD,
            'method': 'adfuller',
        }
    except ImportError:
        return _simple_adf(spread)


def _simple_adf(spread: list) -> dict:
    """간소화 AR(1) 기반 정상성 검정 (statsmodels 대안)."""
    if len(spread) < 30:
        return {'p_value': 1.0, 'test_stat': 0, 'is_cointegrated': False, 'method': 'simple'}

    # AR(1): spread[t] = alpha + theta * spread[t-1] + error
    # theta < 1 이면 평균 회귀 가능성
    n = len(spread) - 1
    y = spread[1:]
    x = spread[:-1]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))

    if den == 0:
        return {'p_value': 1.0, 'test_stat': 0, 'is_cointegrated': False, 'method': 'simple'}

    theta = num / den

    # 잔차 표준오차
    residuals = [y[i] - (theta * x[i] + (mean_y - theta * mean_x)) for i in range(n)]
    se_residuals = math.sqrt(sum(r ** 2 for r in residuals) / max(n - 2, 1))

    se_theta = se_residuals / math.sqrt(den) if den > 0 else 1.0
    t_stat = (theta - 1) / se_theta if se_theta > 0 else 0

    # 근사 p-value (ADF critical values: -3.43 @ 1%, -2.86 @ 5%)
    if t_stat < -3.43:
        p_value = 0.005
    elif t_stat < -2.86:
        p_value = 0.03
    elif t_stat < -2.57:
        p_value = 0.08
    else:
        p_value = 0.50

    return {
        'p_value': round(p_value, 6),
        'test_stat': round(t_stat, 4),
        'is_cointegrated': p_value < ADF_PVALUE_THRESHOLD,
        'method': 'simple',
    }


def calc_half_life(spread: list) -> float:
    """Half-Life 계산: 평균 회귀까지 예상 거래일.

    HL = -ln(2) / ln(theta)  where theta = AR(1) coefficient.
    """
    if len(spread) < 30:
        return 999.0

    n = len(spread) - 1
    y = spread[1:]
    x = spread[:-1]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))

    if den == 0:
        return 999.0

    theta = num / den

    if theta <= 0 or theta >= 1:
        return 999.0

    return round(-math.log(2) / math.log(theta), 1)


def score_cointegration(p_value: float, half_life: float = 0) -> dict:
    """공적분 점수 계산.

    Args:
        p_value: ADF 테스트 p-value
        half_life: Half-Life (거래일)
    Returns:
        {'score': int, 'p_value': float, 'grade': str, 'half_life': float}
    """
    grade = '없음'
    base = ADF_DEFAULT_SCORE

    for threshold, g, s in ADF_GRADES:
        if p_value < threshold:
            grade = g
            base = s
            break

    # Half-Life 보정
    hl_adj = 0
    if half_life > 0 and half_life < 999:
        if half_life < 20:
            hl_adj = HALFLIFE_BONUS_FAST
        elif half_life < 30:
            hl_adj = 5

    score = max(0, min(100, base + hl_adj))
    return {
        'score': score,
        'p_value': round(p_value, 6),
        'grade': grade,
        'half_life': half_life,
    }
