"""kr-skill-reviewer: 리뷰 리포트 생성."""


def generate_review_report(merged_result, skill_name=None):
    """리뷰 리포트 생성.

    Args:
        merged_result: dict from merge_reviews().
        skill_name: str, 리뷰 대상 스킬명 (optional).

    Returns:
        str: 포맷팅된 리포트.
    """
    lines = []
    lines.append('=' * 55)
    title = f' {skill_name} 스킬 리뷰 리포트' if skill_name else ' 스킬 리뷰 리포트'
    lines.append(title)
    lines.append('=' * 55)
    lines.append('')

    score = merged_result['final_score']
    grade = merged_result['grade']
    lines.append(f'## 최종 등급: {grade} ({score:.1f}/100)')
    lines.append('')

    # Auto / LLM 점수
    lines.append('## 축별 점수')
    lines.append(f'  Auto Axis: {merged_result["auto_score"]:.1f}')
    llm = merged_result.get('llm_score')
    if llm is not None:
        lines.append(f'  LLM Axis:  {llm:.1f}')
    else:
        lines.append('  LLM Axis:  미사용')
    lines.append('')

    # 개선 사항
    improvements = merged_result.get('improvements', [])
    if improvements:
        lines.append('## 개선 사항')
        for i, imp in enumerate(improvements, 1):
            source = imp.get('source', '?')
            finding = imp.get('finding', '')
            lines.append(f'  {i}. [{source}] {finding}')
        lines.append('')

    # 등급 설명
    grade_desc = {
        'PRODUCTION_READY': '프로덕션 배포 가능. 높은 품질.',
        'USABLE': '사용 가능하나 일부 개선 필요.',
        'NOTABLE_GAPS': '주목할 갭 존재. 개선 후 사용 권장.',
        'HIGH_RISK': '고위험. 드래프트 취급. 대폭 개선 필요.',
    }
    lines.append(f'## 판정: {grade_desc.get(grade, "")}')
    lines.append('')

    return '\n'.join(lines)
