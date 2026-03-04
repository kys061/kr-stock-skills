"""상관 분석기: Pearson 상관계수 + 롤링 안정성."""

import math

# ── 상관 등급 ────────────────────────────────────────────────
CORRELATION_GRADES = [
    (0.90, '매우 강함', 100),
    (0.70, '강함',     75),
    (0.50, '보통',     50),
]
CORRELATION_DEFAULT_SCORE = 20
CORRELATION_MIN = 0.70           # 최소 상관계수 필터
ROLLING_WINDOW = 90              # 롤링 상관 윈도우
STABILITY_THRESHOLD = 0.15      # 안정성 경고 임계값
STABILITY_BONUS = 10            # 안정적 상관 보너스
STABILITY_PENALTY = -15         # 불안정 상관 페널티


def calc_correlation(prices_a: list, prices_b: list) -> float:
    """Pearson 상관계수 계산.

    Args:
        prices_a: 종목 A 종가 리스트
        prices_b: 종목 B 종가 리스트 (동일 길이)
    Returns:
        상관계수 (-1 ~ +1)
    """
    n = min(len(prices_a), len(prices_b))
    if n < 30:
        return 0.0

    a = prices_a[-n:]
    b = prices_b[-n:]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / n)
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / n)

    if std_a == 0 or std_b == 0:
        return 0.0

    return cov / (std_a * std_b)


def calc_rolling_correlation(prices_a: list, prices_b: list,
                             window: int = ROLLING_WINDOW) -> list:
    """롤링 상관계수 계산.

    Args:
        prices_a, prices_b: 동일 길이 종가 리스트
        window: 롤링 윈도우 (기본 90일)
    Returns:
        [(index, correlation), ...]
    """
    n = min(len(prices_a), len(prices_b))
    if n < window:
        return []

    results = []
    for i in range(window, n + 1):
        corr = calc_correlation(prices_a[i - window:i], prices_b[i - window:i])
        results.append((i, round(corr, 4)))
    return results


def check_stability(rolling_correlations: list) -> dict:
    """상관 안정성 검사.

    Args:
        rolling_correlations: calc_rolling_correlation() 결과
    Returns:
        {'is_stable': bool, 'recent': float, 'historical': float, 'diff': float}
    """
    if len(rolling_correlations) < 2:
        return {'is_stable': True, 'recent': 0, 'historical': 0, 'diff': 0}

    correlations = [c for _, c in rolling_correlations]
    recent = correlations[-1]
    historical = sum(correlations) / len(correlations)
    diff = recent - historical

    return {
        'is_stable': diff >= -STABILITY_THRESHOLD,
        'recent': round(recent, 4),
        'historical': round(historical, 4),
        'diff': round(diff, 4),
    }


def score_correlation(correlation: float, stability: dict = None) -> dict:
    """상관 점수 계산.

    Args:
        correlation: Pearson 상관계수
        stability: check_stability() 결과
    Returns:
        {'score': int, 'correlation': float, 'grade': str, 'adjustment': int}
    """
    grade = '약함'
    base = CORRELATION_DEFAULT_SCORE

    for threshold, g, s in CORRELATION_GRADES:
        if correlation >= threshold:
            grade = g
            base = s
            break

    adjustment = 0
    if stability:
        if stability.get('is_stable', True):
            adjustment = STABILITY_BONUS
        else:
            adjustment = STABILITY_PENALTY

    score = max(0, min(100, base + adjustment))
    return {
        'score': score,
        'correlation': round(correlation, 4),
        'grade': grade,
        'adjustment': adjustment,
    }
