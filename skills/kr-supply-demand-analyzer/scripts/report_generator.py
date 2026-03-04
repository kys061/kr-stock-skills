"""kr-supply-demand-analyzer: 수급 종합 리포트 생성."""

from .market_flow_analyzer import MARKET_FLOW_SIGNALS
from .sector_flow_mapper import SECTOR_FLOW_CONFIG
from .liquidity_tracker import LIQUIDITY_GRADES


# ─── 수급 종합 스코어 ───

SUPPLY_DEMAND_COMPOSITE_WEIGHTS = {
    'market_flow': {'weight': 0.30, 'label': '시장 순매수 강도'},
    'sector_rotation': {'weight': 0.25, 'label': '섹터 로테이션 건전성'},
    'liquidity': {'weight': 0.25, 'label': '유동성 충분도'},
    'investor_sentiment': {'weight': 0.20, 'label': '투자자 심리'},
}
# 가중치 합계: 0.30 + 0.25 + 0.25 + 0.20 = 1.00

SUPPLY_DEMAND_GRADES = {
    'STRONG_INFLOW': {'min_score': 80, 'label': '강력 자금 유입'},
    'INFLOW': {'min_score': 65, 'label': '자금 유입'},
    'BALANCED': {'min_score': 45, 'label': '균형'},
    'OUTFLOW': {'min_score': 30, 'label': '자금 유출'},
    'STRONG_OUTFLOW': {'min_score': 0, 'label': '강력 자금 유출'},
}


def _classify_grade(score):
    """종합 점수 → 등급."""
    for grade, cfg in SUPPLY_DEMAND_GRADES.items():
        if score >= cfg['min_score']:
            return grade
    return 'STRONG_OUTFLOW'


def calc_composite_score(market_flow_score, sector_score, liquidity_score,
                         sentiment_score):
    """수급 종합 스코어 계산.

    Args:
        market_flow_score: 시장 수급 점수 (0-100).
        sector_score: 섹터 로테이션 점수 (0-100).
        liquidity_score: 유동성 점수 (0-100).
        sentiment_score: 투자자 심리 점수 (0-100).

    Returns:
        dict: {score, grade, label, components}
    """
    weights = SUPPLY_DEMAND_COMPOSITE_WEIGHTS
    total = (
        market_flow_score * weights['market_flow']['weight']
        + sector_score * weights['sector_rotation']['weight']
        + liquidity_score * weights['liquidity']['weight']
        + sentiment_score * weights['investor_sentiment']['weight']
    )
    total = round(max(0, min(100, total)), 1)

    grade = _classify_grade(total)
    label = SUPPLY_DEMAND_GRADES[grade]['label']

    return {
        'score': total,
        'grade': grade,
        'label': label,
        'components': {
            'market_flow': {
                'score': market_flow_score,
                'weight': weights['market_flow']['weight'],
                'weighted': round(market_flow_score * weights['market_flow']['weight'], 1),
            },
            'sector_rotation': {
                'score': sector_score,
                'weight': weights['sector_rotation']['weight'],
                'weighted': round(sector_score * weights['sector_rotation']['weight'], 1),
            },
            'liquidity': {
                'score': liquidity_score,
                'weight': weights['liquidity']['weight'],
                'weighted': round(liquidity_score * weights['liquidity']['weight'], 1),
            },
            'investor_sentiment': {
                'score': sentiment_score,
                'weight': weights['investor_sentiment']['weight'],
                'weighted': round(sentiment_score * weights['investor_sentiment']['weight'], 1),
            },
        },
    }


def _format_amount(amount):
    """금액을 한글 단위로 포맷."""
    if amount is None:
        return '-'
    abs_val = abs(amount)
    sign = '+' if amount > 0 else '-' if amount < 0 else ''
    if abs_val >= 1_000_000_000_000:
        return f'{sign}{abs_val / 1_000_000_000_000:.1f}조'
    elif abs_val >= 100_000_000:
        return f'{sign}{abs_val / 100_000_000:.0f}억'
    return f'{sign}{abs_val:,.0f}'


def generate_supply_demand_report(market_flow, sector_flow, liquidity):
    """수급 종합 리포트 생성.

    Args:
        market_flow: analyze_market_flow() 결과.
        sector_flow: map_sector_flows() 결과.
        liquidity: analyze_liquidity() 결과.

    Returns:
        str: 마크다운 형식 리포트.
    """
    # 종합 스코어 계산
    # market_flow 점수: 외국인/기관 합산 점수의 평균
    market_score = (
        market_flow.get('foreign_score', 50) * 0.55
        + market_flow.get('institution_score', 50) * 0.45
    )
    sector_score = sector_flow.get('sector_score', 60.0)
    liquidity_score = liquidity.get('score', 50.0)
    sentiment_score = market_flow.get('sentiment_score', 50.0)

    composite = calc_composite_score(
        market_score, sector_score, liquidity_score, sentiment_score,
    )

    # 시그널 라벨
    signal = market_flow.get('signal', 'NEUTRAL')
    signal_label = MARKET_FLOW_SIGNALS.get(signal, {}).get('label', '중립')

    # 유동성 등급 라벨
    liq_grade = liquidity.get('grade', 'NORMAL')
    liq_label = LIQUIDITY_GRADES.get(liq_grade, {}).get('label', '보통')

    # HHI 경고
    hhi = sector_flow.get('hhi', 0)
    hhi_warning = ''
    if hhi >= SECTOR_FLOW_CONFIG['hhi_critical']:
        hhi_warning = ' ⚠️ 위험'
    elif hhi >= SECTOR_FLOW_CONFIG['hhi_warning']:
        hhi_warning = ' ⚠ 경고'

    lines = [
        f'# 수급 종합 리포트 ({market_flow.get("market", "KOSPI")})',
        '',
        f'## 종합 등급: {composite["grade"]} ({composite["label"]})',
        f'**종합 점수**: {composite["score"]}/100',
        '',
        '## 컴포넌트 점수',
        '| 컴포넌트 | 점수 | 가중치 | 기여 |',
        '|---------|:----:|:------:|:----:|',
    ]

    for key, comp in composite['components'].items():
        label = SUPPLY_DEMAND_COMPOSITE_WEIGHTS[key]['label']
        lines.append(
            f'| {label} | {comp["score"]:.1f} | {comp["weight"]:.0%} | {comp["weighted"]:.1f} |'
        )

    lines.extend([
        '',
        '## 시장 수급',
        f'- **시그널**: {signal} ({signal_label})',
        f'- **외국인 점수**: {market_flow.get("foreign_score", 50):.1f}',
        f'- **기관 점수**: {market_flow.get("institution_score", 50):.1f}',
        f'- **심리 지수**: {sentiment_score:.1f}',
    ])

    # 연속 매수/매도
    consec = market_flow.get('consecutive_days', {})
    for inv in ['foreign', 'institution']:
        cd = consec.get(inv, {})
        if cd.get('direction') == 'buy' and cd.get('buy_days', 0) > 0:
            lines.append(f'- **{inv} 연속 매수**: {cd["buy_days"]}일 ({cd.get("strength", "")})')
        elif cd.get('direction') == 'sell' and cd.get('sell_days', 0) > 0:
            lines.append(f'- **{inv} 연속 매도**: {cd["sell_days"]}일 ({cd.get("strength", "")})')

    lines.extend([
        '',
        '## 섹터 자금 흐름',
        f'- **HHI 집중도**: {hhi:.4f}{hhi_warning}',
        f'- **섹터 건전성 점수**: {sector_score:.1f}',
    ])

    # 히트맵
    heatmap = sector_flow.get('heatmap', {})
    inflow_sectors = [s for s, h in heatmap.items() if h == 'inflow']
    outflow_sectors = [s for s, h in heatmap.items() if h == 'outflow']
    if inflow_sectors:
        lines.append(f'- **유입 섹터**: {", ".join(inflow_sectors)}')
    if outflow_sectors:
        lines.append(f'- **유출 섹터**: {", ".join(outflow_sectors)}')

    lines.extend([
        '',
        '## 유동성',
        f'- **등급**: {liq_grade} ({liq_label})',
        f'- **유동성 점수**: {liquidity_score:.1f}',
    ])

    vol_ratio = liquidity.get('volume_ratio', {})
    if vol_ratio:
        lines.append(f'- **거래대금 비율 (5일)**: {vol_ratio.get("5d_ratio", 1.0):.2f}x')
        lines.append(f'- **거래대금 비율 (20일)**: {vol_ratio.get("20d_ratio", 1.0):.2f}x')

    turnover = liquidity.get('turnover', 0)
    if turnover:
        lines.append(f'- **회전율**: {turnover:.2f}%')

    concentration = liquidity.get('concentration', 0)
    if concentration:
        lines.append(f'- **상위10 집중도**: {concentration:.1%}')

    return '\n'.join(lines)
