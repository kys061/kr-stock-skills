"""kr-weekly-strategy: 주간 리포트 생성."""


def generate_weekly_report(plan):
    """주간 전략 리포트 생성.

    Args:
        plan: dict from generate_weekly_plan().

    Returns:
        str: 포맷팅된 주간 리포트.
    """
    lines = []
    lines.append('=' * 55)
    lines.append(' KR 주간 전략 리포트')
    lines.append('=' * 55)
    lines.append('')

    # 1. 시장 요약
    lines.append('## 시장 환경')
    for s in plan.get('summary', []):
        lines.append(f'  {s}')
    lines.append('')

    # 2. 이번 주 액션
    lines.append('## 이번 주 액션 플랜')
    for action in plan.get('action', []):
        lines.append(f'  - {action}')
    lines.append('')

    # 3. 시나리오
    lines.append('## 시나리오 계획')
    scenarios = plan.get('scenarios', {})
    for scenario_type in ('base', 'bull', 'bear'):
        s = scenarios.get(scenario_type, {})
        prob = s.get('probability', 0)
        desc = s.get('description', '')
        lines.append(f'  [{scenario_type.upper()}] ({prob}%) {desc}')
        for action in s.get('actions', []):
            lines.append(f'    - {action}')
    lines.append('')

    # 4. 섹터 전략
    lines.append('## 섹터 전략')
    sector_info = plan.get('sectors', {})
    top = sector_info.get('top', [])
    for sector, alloc in top:
        lines.append(f'  {sector:<12s} {alloc:>5.1f}%')
    changes = sector_info.get('changes', {})
    if changes:
        lines.append('')
        lines.append('  변경:')
        for sector, ch in changes.items():
            lines.append(f'    {sector}: {ch["from"]:.1f}% → {ch["to"]:.1f}% ({ch["change"]:+.1f}%)')
    lines.append('')

    # 5. 리스크 관리
    lines.append('## 리스크 관리')
    risks = plan.get('risks', [])
    for r in risks:
        priority_mark = '🔴' if r['priority'] == 'high' else '🟡'
        lines.append(f'  {priority_mark} {r["description"]}')
    lines.append('')

    # 6. 운용 가이드
    lines.append('## 겸업 투자자 가이드')
    guide = plan.get('guide', {})
    lines.append(f'  체크 빈도: {guide.get("frequency", "주 2회")}')
    lines.append('  할 일:')
    for a in guide.get('actions', []):
        lines.append(f'    - {a}')
    lines.append('  주의:')
    for w in guide.get('warnings', []):
        lines.append(f'    - {w}')
    lines.append('')

    return '\n'.join(lines)
