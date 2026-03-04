"""kr-portfolio-manager: 리밸런싱 추천 엔진."""

from portfolio_analyzer import (
    REBALANCING, REBALANCING_PRIORITY, POSITION_ACTIONS,
    KR_TAX_MODEL, calc_position_weight, determine_action,
    calc_transaction_cost,
)


def build_target_allocation(holdings: list,
                            target_weights: dict = None) -> dict:
    """목표 배분 생성.

    Args:
        holdings: 포지션 리스트
        target_weights: {symbol: weight} 목표 비중 (없으면 균등)

    Returns:
        {symbol: target_weight}
    """
    if target_weights:
        return target_weights

    # 균등 배분 (현금 제외)
    non_cash = [h for h in holdings if h.get('asset_class') != 'cash']
    if not non_cash:
        return {}

    equal_weight = round(1.0 / len(non_cash), 4)
    return {h.get('symbol', ''): equal_weight for h in non_cash}


def generate_rebalancing_actions(holdings: list,
                                 target_weights: dict = None) -> dict:
    """리밸런싱 액션 생성.

    Args:
        holdings: 포지션 리스트
        target_weights: {symbol: weight} 목표 비중

    Returns:
        리밸런싱 계획
    """
    targets = build_target_allocation(holdings, target_weights)
    total_value = sum(h.get('value', 0) for h in holdings)

    if total_value <= 0:
        return {'valid': False, 'error': 'Total value is zero'}

    actions = []
    total_trade_value = 0

    for h in holdings:
        symbol = h.get('symbol', '')
        current_weight = calc_position_weight(h.get('value', 0), total_value)
        target_weight = targets.get(symbol, 0)

        action = determine_action(h, target_weight, current_weight)

        # 거래 금액 계산
        drift_value = abs(action['drift']) * total_value
        total_trade_value += drift_value

        action['current_weight'] = current_weight
        action['target_weight'] = target_weight
        action['trade_value'] = round(drift_value)
        actions.append(action)

    # 우선순위 정렬
    priority_order = {p: i for i, p in enumerate(REBALANCING_PRIORITY)}
    actions.sort(key=lambda a: priority_order.get(a['priority'], 99))

    # 거래 비용 추정
    estimated_cost = calc_total_rebalancing_cost(actions)

    return {
        'valid': True,
        'actions': actions,
        'total_trade_value': round(total_trade_value),
        'estimated_cost': estimated_cost,
        'action_count': len([a for a in actions if a['action'] != 'HOLD']),
    }


def calc_total_rebalancing_cost(actions: list) -> dict:
    """리밸런싱 총 비용 추정.

    Args:
        actions: 액션 리스트

    Returns:
        비용 내역
    """
    total_brokerage = 0
    total_sell_tax = 0
    total_trades = 0

    for a in actions:
        if a['action'] == 'HOLD':
            continue
        trade_value = a.get('trade_value', 0)
        is_sell = a['action'] in ('TRIM', 'SELL')
        cost = calc_transaction_cost(trade_value, is_sell)
        total_brokerage += cost['brokerage']
        total_sell_tax += cost['sell_tax']
        total_trades += 1

    return {
        'total_brokerage': round(total_brokerage),
        'total_sell_tax': round(total_sell_tax),
        'total_cost': round(total_brokerage + total_sell_tax),
        'total_trades': total_trades,
    }


def apply_tax_optimization(actions: list,
                           annual_dividend: float = 0) -> list:
    """세금 최적화 적용.

    Args:
        actions: 액션 리스트
        annual_dividend: 연간 배당 총액

    Returns:
        세금 관련 경고/제안 리스트
    """
    suggestions = []

    # 금융소득종합과세 경고
    if annual_dividend > KR_TAX_MODEL['financial_income_threshold']:
        suggestions.append({
            'type': 'comprehensive_tax_warning',
            'message': f'금융소득종합과세 기준 초과: '
                       f'{annual_dividend:,.0f}원 > '
                       f'{KR_TAX_MODEL["financial_income_threshold"]:,.0f}원',
            'priority': 'HIGH',
        })

    # 대량 매도 시 거래세 경고
    sell_value = sum(
        a.get('trade_value', 0) for a in actions
        if a['action'] in ('TRIM', 'SELL'))
    if sell_value > 0:
        tax = sell_value * KR_TAX_MODEL['transaction_tax']
        suggestions.append({
            'type': 'transaction_tax_impact',
            'message': f'매도 거래세 예상: {tax:,.0f}원 '
                       f'(매도 {sell_value:,.0f}원 × '
                       f'{KR_TAX_MODEL["transaction_tax"]:.2%})',
            'priority': 'MEDIUM',
        })

    # ISA 활용 제안
    if annual_dividend > 0 and annual_dividend <= KR_TAX_MODEL['isa_tax_free'] * 2:
        suggestions.append({
            'type': 'isa_suggestion',
            'message': f'ISA 활용 시 {min(annual_dividend, KR_TAX_MODEL["isa_tax_free"]):,.0f}원 '
                       f'비과세 가능',
            'priority': 'LOW',
        })

    return suggestions


def generate_rebalancing_report(result: dict) -> str:
    """리밸런싱 Markdown 리포트 생성.

    Args:
        result: generate_rebalancing_actions() 결과

    Returns:
        Markdown 문자열
    """
    if not result.get('valid'):
        return f'# 리밸런싱 오류\n\n{result.get("error", "Unknown error")}'

    lines = ['# 포트폴리오 리밸런싱 계획']
    lines.append(f'\n## 요약')
    lines.append(f'- 조정 필요 종목: {result["action_count"]}개')
    lines.append(f'- 총 거래 금액: {result["total_trade_value"]:,}원')
    lines.append(f'- 예상 비용: {result["estimated_cost"]["total_cost"]:,}원')

    lines.append(f'\n## 액션 리스트')
    lines.append(f'| 종목 | 액션 | 현재 | 목표 | 편차 | 우선순위 |')
    lines.append(f'|------|------|------|------|------|----------|')

    for a in result['actions']:
        lines.append(
            f'| {a["name"]} ({a["symbol"]}) | {a["action"]} | '
            f'{a["current_weight"]:.1%} | {a["target_weight"]:.1%} | '
            f'{a["drift"]:+.1%} | {a["priority"]} |')

    cost = result['estimated_cost']
    lines.append(f'\n## 비용 추정')
    lines.append(f'- 중개수수료: {cost["total_brokerage"]:,}원')
    lines.append(f'- 거래세: {cost["total_sell_tax"]:,}원')
    lines.append(f'- **합계**: {cost["total_cost"]:,}원')

    lines.append(f'\n---\n*Generated by kr-portfolio-manager*')
    return '\n'.join(lines)
