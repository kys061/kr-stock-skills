"""A 컴포넌트: 3년 연간 EPS CAGR + 안정성 (Annual Growth)."""

# ── 임계값 ────────────────────────────────────────────────
A_CAGR_THRESHOLDS = [
    (40, 90),
    (30, 70),
    (25, 50),
    (15, 35),
]
A_DEFAULT = 20

STABILITY_BONUS = 10      # 3년 모두 EPS 증가
DECLINE_PENALTY = -10     # 1년이라도 EPS 감소


def calc_annual_cagr(eps_history: list) -> dict:
    """3년 연간 EPS CAGR + 안정성 보너스.

    Args:
        eps_history: [Y-3, Y-2, Y-1] 연간 EPS
    Returns:
        {'score': int, 'cagr': float, 'stability_adj': int}
    """
    if len(eps_history) < 3 or eps_history[0] <= 0 or eps_history[-1] <= 0:
        return {'score': A_DEFAULT, 'cagr': 0.0, 'stability_adj': 0}

    years = len(eps_history) - 1
    cagr = ((eps_history[-1] / eps_history[0]) ** (1 / years) - 1) * 100

    # 기본 점수
    base_score = A_DEFAULT
    for threshold, score in A_CAGR_THRESHOLDS:
        if cagr >= threshold:
            base_score = score
            break

    # 안정성 조정
    stability_adj = 0
    all_increasing = all(eps_history[i] > eps_history[i - 1] for i in range(1, len(eps_history)))
    any_declining = any(eps_history[i] < eps_history[i - 1] for i in range(1, len(eps_history)))

    if all_increasing:
        stability_adj = STABILITY_BONUS
    elif any_declining:
        stability_adj = DECLINE_PENALTY

    score = max(0, min(100, base_score + stability_adj))
    return {'score': score, 'cagr': round(cagr, 1), 'stability_adj': stability_adj}
