"""kr-credit-monitor: 신용잔고 리포트 생성."""

from .credit_balance_analyzer import LEVERAGE_CYCLE_PHASES, DEPOSIT_CREDIT_RATIO
from .forced_liquidation_risk import CREDIT_RISK_GRADES


def _format_amount(amount):
    """금액 포맷 (한글 단위)."""
    if amount is None or amount == 0:
        return '-'
    abs_val = abs(amount)
    if abs_val >= 1_000_000_000_000:
        return f'{abs_val / 1_000_000_000_000:.1f}조'
    elif abs_val >= 100_000_000:
        return f'{abs_val / 100_000_000:.0f}억'
    return f'{abs_val:,.0f}'


def generate_credit_report(balance_analysis, liquidation_risk=None, risk_score=None,
                           deposit_ratio=None):
    """신용잔고 종합 리포트 생성.

    Args:
        balance_analysis: analyze_credit_balance() 결과.
        liquidation_risk: estimate_forced_liquidation() 결과 (optional).
        risk_score: calc_credit_risk_score() 결과 (optional).
        deposit_ratio: calc_deposit_credit_ratio() 결과 (optional).

    Returns:
        str: 마크다운 형식 리포트.
    """
    total = balance_analysis.get('total', 0)
    mr = balance_analysis.get('market_ratio', 0)
    mr_level = balance_analysis.get('market_ratio_level', 'safe')
    growth = balance_analysis.get('growth', {})
    percentile = balance_analysis.get('percentile', 50)
    cycle = balance_analysis.get('cycle_phase', 'TROUGH')
    cycle_label = LEVERAGE_CYCLE_PHASES.get(cycle, {}).get('label', cycle)

    lines = [
        '# 신용잔고 분석 리포트',
        '',
        f'## 레버리지 사이클: {cycle} ({cycle_label})',
        '',
        '## 신용잔고 현황',
        f'- **총 신용잔고**: {_format_amount(total)}',
        f'- **시총 대비 비율**: {mr:.2%} ({mr_level})',
        f'- **3년 퍼센타일**: {percentile:.1f}%',
    ]

    # 성장률
    if growth:
        yoy = growth.get('yoy', 0)
        mom = growth.get('mom', 0)
        lines.extend([
            f'- **YoY 성장률**: {yoy:+.1%} ({growth.get("yoy_level", "normal")})',
            f'- **MoM 성장률**: {mom:+.1%} ({growth.get("mom_level", "normal")})',
        ])

    # 예탁금 비율
    if deposit_ratio:
        lines.extend([
            '',
            '## 예탁금 대비',
            f'- **비율**: {deposit_ratio.get("ratio", 0):.1%} ({deposit_ratio.get("label", "")})',
        ])

    # 반대매매 시나리오
    if liquidation_risk:
        trigger = liquidation_risk.get('trigger_price_drop', 0)
        lines.extend([
            '',
            '## 반대매매 리스크',
            f'- **담보부족 발동 하락률**: {trigger:.1%}',
            '',
            '| 시나리오 | 반대매매 발동 | 영향 금액 | 시장 영향 |',
            '|---------|:----------:|----------|:--------:|',
        ])
        for sc in liquidation_risk.get('scenarios', []):
            triggered = '✅' if sc.get('triggers_margin_call') else '❌'
            affected = _format_amount(sc.get('affected_amount', 0))
            impact = sc.get('impact_level', 'negligible')
            lines.append(f'| {sc["label"]} | {triggered} | {affected} | {impact} |')

    # 리스크 스코어
    if risk_score:
        grade = risk_score.get('grade', 'NORMAL')
        grade_label = CREDIT_RISK_GRADES.get(grade, {}).get('label', '보통')
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
