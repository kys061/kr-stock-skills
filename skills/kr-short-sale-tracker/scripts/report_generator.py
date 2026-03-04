"""kr-short-sale-tracker: 공매도 리포트 생성."""

from .short_ratio_analyzer import SHORT_BALANCE_LEVELS, SHORT_TRADE_LEVELS
from .short_cover_detector import SHORT_COVER_SIGNALS, SHORT_RISK_GRADES


def generate_short_sale_report(ratio_analysis, cover_signals, risk_score=None):
    """공매도 종합 리포트 생성.

    Args:
        ratio_analysis: analyze_short_ratio() 결과.
        cover_signals: detect_short_cover() 결과.
        risk_score: calc_short_risk_score() 결과 (optional).

    Returns:
        str: 마크다운 형식 리포트.
    """
    balance_ratio = ratio_analysis.get('balance_ratio', 0)
    trade_ratio = ratio_analysis.get('trade_ratio', 0)
    balance_level = ratio_analysis.get('balance_level', 'minimal')
    trade_level = ratio_analysis.get('trade_level', 'low')
    percentile = ratio_analysis.get('percentile', 50)

    signal = cover_signals.get('signal', 'NEUTRAL')
    signal_label = SHORT_COVER_SIGNALS.get(signal, {}).get('label', '중립')
    consec = cover_signals.get('consecutive_decrease', 0)
    dtc = cover_signals.get('days_to_cover', 0)
    dtc_level = cover_signals.get('dtc_level', 'low')
    squeeze = cover_signals.get('squeeze_probability', 0)

    lines = [
        '# 공매도 분석 리포트',
        '',
        f'## 숏커버 시그널: {signal} ({signal_label})',
        '',
        '## 공매도 비율',
        f'- **잔고비율**: {balance_ratio:.2%} ({balance_level})',
        f'- **거래비율**: {trade_ratio:.2%} ({trade_level})',
        f'- **퍼센타일**: {percentile:.1f}% (1년 기준)',
    ]

    # 이동평균
    ma = ratio_analysis.get('ma_ratios', {})
    if ma:
        lines.append('- **이동평균**:')
        for key, val in ma.items():
            lines.append(f'  - {key}: {val:.4%}')

    lines.extend([
        '',
        '## 숏커버 분석',
        f'- **연속 잔고 감소**: {consec}일 ({cover_signals.get("decrease_strength", "none")})',
    ])

    if cover_signals.get('sharp_decrease'):
        lines.append(f'- **급감 발생**: {cover_signals.get("sharp_decrease_pct", 0):.1%}')

    lines.extend([
        f'- **Days-to-Cover**: {dtc:.1f}일 ({dtc_level})',
        f'- **숏스퀴즈 확률**: {squeeze:.0%}',
    ])

    if risk_score:
        grade = risk_score.get('grade', 'MODERATE')
        grade_label = SHORT_RISK_GRADES.get(grade, {}).get('label', '보통')
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
