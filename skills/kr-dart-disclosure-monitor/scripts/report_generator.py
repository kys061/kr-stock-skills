"""kr-dart-disclosure-monitor: 공시 리포트 생성."""

from .disclosure_classifier import DISCLOSURE_TYPES
from .event_impact_scorer import EVENT_IMPACT_LEVELS, DISCLOSURE_RISK_GRADES
from .stake_change_tracker import STAKE_SIGNALS


def generate_disclosure_report(classifications, impacts=None, stake_changes=None,
                                risk_score=None):
    """공시 종합 리포트 생성.

    Args:
        classifications: classify_batch() 결과.
        impacts: list of score_event_impact() 결과 (optional).
        stake_changes: track_stake_changes() 결과 (optional).
        risk_score: calc_disclosure_risk_score() 결과 (optional).

    Returns:
        str: 마크다운 형식 리포트.
    """
    lines = [
        '# DART 공시 분석 리포트',
        '',
    ]

    # 공시 유형별 요약
    type_counts = {}
    for c in classifications:
        dtype = c.get('type', 'OTHER')
        type_counts[dtype] = type_counts.get(dtype, 0) + 1

    lines.extend([
        f'## 공시 현황 (총 {len(classifications)}건)',
        '',
        '| 유형 | 건수 | 비율 |',
        '|------|:----:|:----:|',
    ])
    total = len(classifications) or 1
    for dtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        label = DISCLOSURE_TYPES.get(dtype, {}).get('label', dtype)
        lines.append(f'| {label} ({dtype}) | {count} | {count/total:.0%} |')

    # 주요 이벤트 (레벨 3+)
    if impacts:
        high_impacts = [i for i in impacts if i.get('level', 1) >= 3]
        if high_impacts:
            lines.extend([
                '',
                '## 주요 이벤트',
            ])
            for imp in sorted(high_impacts, key=lambda x: -x.get('level', 0)):
                level = imp.get('level', 1)
                label = imp.get('label', 'Info')
                korean = imp.get('korean', '')
                action = imp.get('action', '')
                lines.append(f'- **[{level}] {label}** ({korean}): {action}')

    # 지분 변동
    if stake_changes:
        signal = stake_changes.get('signal', 'NEUTRAL')
        signal_info = STAKE_SIGNALS.get(signal, STAKE_SIGNALS['NEUTRAL'])
        significant = stake_changes.get('significant_changes', [])

        lines.extend([
            '',
            f'## 지분 변동: {signal} ({signal_info["label"]})',
        ])
        if significant:
            lines.append(f'- **유의미 변동**: {len(significant)}건')
            for s in significant[:5]:
                holder = s.get('holder', 'N/A')
                change = s.get('change_pct', 0)
                lines.append(f'  - {holder}: {change:+.2%}p')

    # 리스크 스코어
    if risk_score:
        grade = risk_score.get('grade', 'NORMAL')
        grade_label = DISCLOSURE_RISK_GRADES.get(grade, {}).get('label', '정상')
        lines.extend([
            '',
            f'## 리스크 등급: {grade} ({grade_label})',
            f'**리스크 점수**: {risk_score.get("score", 0):.1f}/100',
            '',
            '| 컴포넌트 | 점수 | 가중치 |',
            '|---------|:----:|:------:|',
        ])
        for key, comp in risk_score.get('components', {}).items():
            lines.append(f'| {key} | {comp["score"]:.1f} | {comp["weight"]:.0%} |')

    return '\n'.join(lines)
