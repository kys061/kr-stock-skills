"""kr-weekly-strategy: 섹터 전략 생성."""


# ─── 한국 14개 섹터 ───

KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학',
    '바이오/제약', '금융/은행', '유통/소비', '건설/부동산',
    'IT/소프트웨어', '통신', '에너지/유틸리티', '엔터테인먼트',
    '방산', '2차전지',
]

# ─── 전략 제약 ───

WEEKLY_CONSTRAINTS = {
    'max_sector_change_pct': 0.15,
    'max_cash_change_pct': 0.15,
    'blog_length_lines': (150, 250),
    'continuity_required': True,
}


def calc_sector_scores(sector_data):
    """섹터별 점수 계산.

    Args:
        sector_data: dict with sector names as keys:
            {
                '반도체': {
                    'momentum': float (-100~100),
                    'foreign_flow': float (순매수 억원),
                    'earnings_revision': float (-100~100),
                    'theme_score': float (0-100),
                },
                ...
            }

    Returns:
        dict: {sector: {score, rank, signals}, ...}
    """
    scores = {}
    for sector in KR_SECTORS:
        data = sector_data.get(sector, {})
        momentum = data.get('momentum', 0)
        foreign = data.get('foreign_flow', 0)
        revision = data.get('earnings_revision', 0)
        theme = data.get('theme_score', 50)

        # 점수 계산: 모멘텀 30% + 외국인 수급 25% + 실적 수정 25% + 테마 20%
        m_score = max(0, min(100, momentum + 50))  # -100~100 → 0~100
        f_score = max(0, min(100, 50 + foreign / 10))  # 수급 정규화
        r_score = max(0, min(100, revision + 50))
        t_score = max(0, min(100, theme))

        total = (m_score * 0.30 + f_score * 0.25
                 + r_score * 0.25 + t_score * 0.20)

        signals = []
        if m_score >= 70:
            signals.append('강한 모멘텀')
        if f_score >= 70:
            signals.append('외국인 매수')
        if r_score >= 70:
            signals.append('실적 상향')
        if m_score <= 30:
            signals.append('약한 모멘텀')
        if f_score <= 30:
            signals.append('외국인 매도')

        scores[sector] = {
            'score': round(total, 1),
            'signals': signals,
        }

    # 순위 부여
    sorted_sectors = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
    for rank, (sector, data) in enumerate(sorted_sectors, 1):
        data['rank'] = rank

    return scores


def recommend_sector_allocation(scores, prev_allocation=None):
    """섹터 비중 추천.

    Args:
        scores: dict from calc_sector_scores().
        prev_allocation: dict of previous sector allocations (optional).

    Returns:
        dict: {allocations, changes, constrained}
    """
    if prev_allocation is None:
        prev_allocation = {}

    # 상위 5개 섹터에 비중 배분
    sorted_sectors = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
    top_sectors = sorted_sectors[:5]
    total_score = sum(s['score'] for _, s in top_sectors)

    allocations = {}
    for sector, data in top_sectors:
        if total_score > 0:
            alloc = round(data['score'] / total_score * 100, 1)
        else:
            alloc = 20.0
        allocations[sector] = alloc

    # 나머지 섹터 0%
    for sector in KR_SECTORS:
        if sector not in allocations:
            allocations[sector] = 0.0

    # 제약 적용
    constrained = []
    if WEEKLY_CONSTRAINTS['continuity_required'] and prev_allocation:
        allocations, constrained = apply_rotation_constraints(
            allocations, prev_allocation,
            WEEKLY_CONSTRAINTS['max_sector_change_pct'],
        )

    # 변경 내역
    changes = {}
    for sector in KR_SECTORS:
        new = allocations.get(sector, 0)
        old = prev_allocation.get(sector, 0)
        if abs(new - old) > 0.1:
            changes[sector] = {'from': old, 'to': new, 'change': round(new - old, 1)}

    return {
        'allocations': allocations,
        'changes': changes,
        'constrained': constrained,
    }


def apply_rotation_constraints(new_alloc, prev_alloc, max_change):
    """섹터 로테이션 제약 적용.

    Args:
        new_alloc: dict of new allocations.
        prev_alloc: dict of previous allocations.
        max_change: float, 최대 변경 비율 (0.15 = 15%).

    Returns:
        tuple: (constrained_alloc, constrained_sectors)
    """
    constrained = []
    result = dict(new_alloc)
    max_change_pct = max_change * 100

    for sector in KR_SECTORS:
        new = result.get(sector, 0)
        old = prev_alloc.get(sector, 0)
        diff = new - old

        if abs(diff) > max_change_pct:
            if diff > 0:
                result[sector] = round(old + max_change_pct, 1)
            else:
                result[sector] = round(max(0, old - max_change_pct), 1)
            constrained.append(sector)

    # 총합 100%로 정규화
    total = sum(result.values())
    if total > 0 and abs(total - 100) > 0.5:
        factor = 100 / total
        for sector in result:
            result[sector] = round(result[sector] * factor, 1)

    return result, constrained
