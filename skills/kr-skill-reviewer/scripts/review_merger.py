"""kr-skill-reviewer: Auto + LLM 리뷰 병합."""


# ─── 병합 가중치 ───

MERGE_WEIGHTS = {
    'auto': 0.50,
    'llm': 0.50,
}

# ─── 등급 기준 ───

REVIEW_GRADES = {
    'PRODUCTION_READY': 90,
    'USABLE': 80,
    'NOTABLE_GAPS': 70,
    'HIGH_RISK': 0,
}


def _get_grade(score):
    """점수 → 등급 변환."""
    if score >= REVIEW_GRADES['PRODUCTION_READY']:
        return 'PRODUCTION_READY'
    elif score >= REVIEW_GRADES['USABLE']:
        return 'USABLE'
    elif score >= REVIEW_GRADES['NOTABLE_GAPS']:
        return 'NOTABLE_GAPS'
    else:
        return 'HIGH_RISK'


def merge_reviews(auto_result, llm_result=None, weights=None):
    """Auto + LLM 리뷰 병합.

    Args:
        auto_result: dict from run_auto_review().
        llm_result: dict with 'score' and optional 'findings' (None if LLM unavailable).
        weights: dict with 'auto' and 'llm' weights (default: 50/50).

    Returns:
        dict: {final_score, grade, auto_score, llm_score, improvements}
    """
    if weights is None:
        weights = MERGE_WEIGHTS

    auto_score = auto_result.get('score', 0)

    if llm_result and 'score' in llm_result:
        llm_score = llm_result['score']
        final_score = (auto_score * weights['auto']
                       + llm_score * weights['llm'])
    else:
        # LLM 미사용 시 Auto만으로 결정
        llm_score = None
        final_score = auto_score

    final_score = round(final_score, 1)
    grade = _get_grade(final_score)

    # 개선 사항 통합
    improvements = []
    auto_findings = auto_result.get('findings', [])
    for f in auto_findings:
        improvements.append({'source': 'auto', 'finding': f})

    if llm_result:
        llm_findings = llm_result.get('findings', [])
        for f in llm_findings:
            improvements.append({'source': 'llm', 'finding': f})

    return {
        'final_score': final_score,
        'grade': grade,
        'auto_score': auto_score,
        'llm_score': llm_score,
        'improvements': improvements,
    }
