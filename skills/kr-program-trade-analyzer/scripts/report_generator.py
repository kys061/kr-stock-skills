"""kr-program-trade-analyzer: 프로그램 매매 리포트 생성."""

from .program_trade_analyzer import PROGRAM_FLOW_SIGNALS
from .basis_analyzer import BASIS_STATES
from .expiry_effect_analyzer import PROGRAM_IMPACT_GRADES, EXPIRY_TYPES


def _format_amount(amount):
    """금액 포맷."""
    if amount is None or amount == 0:
        return '-'
    abs_val = abs(amount)
    sign = '+' if amount > 0 else '-'
    if abs_val >= 1_000_000_000_000:
        return f'{sign}{abs_val / 1_000_000_000_000:.1f}조'
    elif abs_val >= 100_000_000:
        return f'{sign}{abs_val / 100_000_000:.0f}억'
    return f'{sign}{abs_val:,.0f}'


def generate_program_trade_report(program, basis, expiry, impact=None):
    """프로그램 매매 종합 리포트 생성.

    Args:
        program: analyze_program_trades() 결과.
        basis: analyze_basis() 결과.
        expiry: analyze_expiry_effect() 결과 또는 get_next_expiry() 결과.
        impact: calc_program_impact_score() 결과 (optional).

    Returns:
        str: 마크다운 형식 리포트.
    """
    signal = program.get('signal', 'NEUTRAL')
    signal_label = PROGRAM_FLOW_SIGNALS.get(signal, {}).get('label', '중립')

    arb = program.get('arbitrage', {})
    non_arb = program.get('non_arbitrage', {})

    lines = [
        '# 프로그램 매매 분석 리포트',
        '',
        f'## 시그널: {signal} ({signal_label})',
        '',
        '## 프로그램 매매',
        f'- **차익거래**: {_format_amount(arb.get("net", 0))} ({arb.get("classification", "neutral")})',
        f'- **비차익거래**: {_format_amount(non_arb.get("net", 0))} ({non_arb.get("classification", "neutral")})',
        f'- **합계**: {_format_amount(program.get("total", 0))}',
    ]

    consecutive = program.get('consecutive_sell', 0)
    if consecutive >= 5:
        lines.append(f'- **⚠️ 비차익 연속 매도**: {consecutive}일')

    # 베이시스
    state = basis.get('state', 'FAIR')
    state_info = BASIS_STATES.get(state, {})
    lines.extend([
        '',
        '## 선물 베이시스',
        f'- **상태**: {state} ({state_info.get("label", "")})',
        f'- **베이시스**: {basis.get("basis", 0):.2f} ({basis.get("basis_pct", 0):.3%})',
        f'- **이론가 대비 괴리**: {basis.get("deviation", 0):.3%}',
        f'- **의미**: {state_info.get("implication", "")}',
    ])

    # 만기일
    expiry_type = expiry.get('type', 'MONTHLY')
    type_info = EXPIRY_TYPES.get(expiry_type, {})
    lines.extend([
        '',
        '## 만기일 효과',
        f'- **다음 만기**: {expiry.get("date", "N/A")} ({type_info.get("label", expiry_type)})',
        f'- **잔존일**: {expiry.get("days_until", "N/A")}일',
        f'- **근접도**: {expiry.get("proximity", "far")}',
        f'- **변동성 프리미엄**: {expiry.get("volatility_premium", 1.0):.0%}',
    ])

    patterns = expiry.get('patterns', [])
    if patterns:
        lines.append(f'- **활성 패턴**: {", ".join(patterns)}')

    # 종합 스코어
    if impact:
        grade = impact.get('grade', 'NEUTRAL')
        grade_label = PROGRAM_IMPACT_GRADES.get(grade, {}).get('label', '중립')
        lines.extend([
            '',
            f'## 종합 등급: {grade}',
            f'**{grade_label}**',
            f'**종합 점수**: {impact.get("score", 0):.1f}/100',
            '',
            '| 컴포넌트 | 점수 | 가중치 |',
            '|---------|:----:|:------:|',
        ])
        for key, comp in impact.get('components', {}).items():
            lines.append(f'| {key} | {comp["score"]:.1f} | {comp["weight"]:.0%} |')

    return '\n'.join(lines)
