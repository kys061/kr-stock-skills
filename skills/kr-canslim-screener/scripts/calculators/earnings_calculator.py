"""C 컴포넌트: 분기 EPS 성장률 (Current Earnings)."""

# ── 임계값 ────────────────────────────────────────────────
C_THRESHOLDS = [
    {'eps_growth': 50, 'rev_growth': 25, 'score': 100},
    {'eps_growth': 30, 'rev_growth': 0,  'score': 80},
    {'eps_growth': 18, 'rev_growth': 0,  'score': 60},
    {'eps_growth': 10, 'rev_growth': 0,  'score': 40},
]
C_DEFAULT = 20


def calc_quarterly_growth(current_eps: float, prev_year_eps: float,
                          current_rev: float = 0, prev_year_rev: float = 0) -> dict:
    """분기 EPS 성장률 계산 (YoY).

    Args:
        current_eps: 당분기 EPS
        prev_year_eps: 전년 동기 EPS
        current_rev: 당분기 매출 (선택)
        prev_year_rev: 전년 동기 매출 (선택)
    Returns:
        {'score': int, 'eps_growth': float, 'rev_growth': float}
    """
    if prev_year_eps <= 0:
        # 전년 적자 → 흑자전환
        if current_eps > 0:
            return {'score': 80, 'eps_growth': None, 'rev_growth': 0}
        return {'score': C_DEFAULT, 'eps_growth': None, 'rev_growth': 0}

    eps_growth = ((current_eps - prev_year_eps) / prev_year_eps) * 100
    rev_growth = 0
    if prev_year_rev > 0 and current_rev > 0:
        rev_growth = ((current_rev - prev_year_rev) / prev_year_rev) * 100

    for t in C_THRESHOLDS:
        if eps_growth >= t['eps_growth']:
            if t['rev_growth'] > 0 and rev_growth < t['rev_growth']:
                continue
            return {'score': t['score'], 'eps_growth': round(eps_growth, 1), 'rev_growth': round(rev_growth, 1)}

    return {'score': C_DEFAULT, 'eps_growth': round(eps_growth, 1), 'rev_growth': round(rev_growth, 1)}
