"""kr-portfolio-manager: 한국 포트폴리오 분석 엔진.

Usage:
    python portfolio_analyzer.py --holdings portfolio.json
"""

import argparse
import json
import os

# ─── 자산 배분 분석 차원 ───

ALLOCATION_DIMENSIONS = [
    'asset_class',
    'sector',
    'market_cap',
    'market',
]

# ─── 분산 투자 지표 ───

DIVERSIFICATION = {
    'optimal_positions': (15, 30),
    'under_diversified': 10,
    'over_diversified': 50,
    'max_single_position': 0.15,
    'max_sector': 0.35,
    'correlation_redundancy': 0.8,
}

# ─── 리밸런싱 기준 ───

REBALANCING = {
    'major_drift': 0.10,
    'moderate_drift': 0.05,
    'excess_cash': 0.10,
}

# ─── 한국 세제 모델 ───

KR_TAX_MODEL = {
    'dividend_tax': 0.154,
    'financial_income_threshold': 20_000_000,
    'capital_gains_tax': 0.22,
    'capital_gains_threshold': 1_000_000_000,
    'transaction_tax': 0.0023,
    'isa_tax_free': 2_000_000,
}

# ─── 액션 추천 기준 ───

POSITION_ACTIONS = ['HOLD', 'ADD', 'TRIM', 'SELL']

REBALANCING_PRIORITY = [
    'IMMEDIATE',
    'HIGH',
    'MEDIUM',
    'LOW',
]

# ─── KRX 업종 분류 ───

KRX_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학', '바이오/제약',
    '금융/은행', '유통/소비재', '건설/부동산', 'IT/소프트웨어',
    '통신', '에너지/유틸리티', '엔터테인먼트', '방산', '2차전지',
    '원전',
]

# ─── 시가총액 분류 기준 (KRX) ───

MARKET_CAP_TIERS = {
    'large': 1_000_000_000_000,    # 1조원 이상
    'mid': 300_000_000_000,        # 3,000억 이상
    'small': 0,                     # 그 외
}


def classify_market_cap(market_cap: float) -> str:
    """시가총액 등급 분류.

    Args:
        market_cap: 시가총액 (원)

    Returns:
        'large', 'mid', 'small'
    """
    if market_cap >= MARKET_CAP_TIERS['large']:
        return 'large'
    elif market_cap >= MARKET_CAP_TIERS['mid']:
        return 'mid'
    else:
        return 'small'


def calc_position_weight(position_value: float,
                         total_value: float) -> float:
    """포지션 비중 계산.

    Args:
        position_value: 포지션 가치
        total_value: 전체 포트폴리오 가치

    Returns:
        비중 (0-1)
    """
    if total_value <= 0:
        return 0.0
    return round(position_value / total_value, 4)


def analyze_allocation(holdings: list) -> dict:
    """자산 배분 분석.

    Args:
        holdings: [{'symbol', 'name', 'value', 'sector', 'market',
                    'market_cap', 'asset_class'}, ...]

    Returns:
        각 차원별 배분 결과
    """
    total_value = sum(h.get('value', 0) for h in holdings)
    if total_value <= 0:
        return {dim: {} for dim in ALLOCATION_DIMENSIONS}

    result = {}
    for dim in ALLOCATION_DIMENSIONS:
        breakdown = {}
        for h in holdings:
            key = h.get(dim, 'unknown')
            if dim == 'market_cap' and isinstance(key, (int, float)):
                key = classify_market_cap(key)
            breakdown[key] = breakdown.get(key, 0) + h.get('value', 0)

        result[dim] = {
            k: {
                'value': v,
                'weight': calc_position_weight(v, total_value),
            }
            for k, v in breakdown.items()
        }

    return result


def analyze_diversification(holdings: list) -> dict:
    """분산투자 분석.

    Args:
        holdings: 포지션 리스트

    Returns:
        분산투자 분석 결과
    """
    total_value = sum(h.get('value', 0) for h in holdings)
    position_count = len(holdings)

    # 종목 수 판정
    opt_min, opt_max = DIVERSIFICATION['optimal_positions']
    if position_count < DIVERSIFICATION['under_diversified']:
        diversification_status = 'under_diversified'
    elif position_count > DIVERSIFICATION['over_diversified']:
        diversification_status = 'over_diversified'
    elif opt_min <= position_count <= opt_max:
        diversification_status = 'optimal'
    else:
        diversification_status = 'acceptable'

    # 집중도 분석
    concentration_issues = []
    if total_value > 0:
        for h in holdings:
            weight = h.get('value', 0) / total_value
            if weight > DIVERSIFICATION['max_single_position']:
                concentration_issues.append({
                    'type': 'position_concentration',
                    'symbol': h.get('symbol', ''),
                    'name': h.get('name', ''),
                    'weight': round(weight, 4),
                    'limit': DIVERSIFICATION['max_single_position'],
                })

        # 섹터 집중도
        sector_weights = {}
        for h in holdings:
            sector = h.get('sector', 'unknown')
            sector_weights[sector] = sector_weights.get(sector, 0) + h.get('value', 0)

        for sector, value in sector_weights.items():
            weight = value / total_value
            if weight > DIVERSIFICATION['max_sector']:
                concentration_issues.append({
                    'type': 'sector_concentration',
                    'sector': sector,
                    'weight': round(weight, 4),
                    'limit': DIVERSIFICATION['max_sector'],
                })

    return {
        'position_count': position_count,
        'diversification_status': diversification_status,
        'optimal_range': DIVERSIFICATION['optimal_positions'],
        'concentration_issues': concentration_issues,
        'total_value': total_value,
    }


def calc_dividend_tax(dividend_amount: float,
                      use_isa: bool = False) -> dict:
    """배당소득 세금 계산.

    Args:
        dividend_amount: 배당 총액
        use_isa: ISA 계좌 사용 여부

    Returns:
        세금 내역
    """
    if use_isa:
        tax_free = min(dividend_amount, KR_TAX_MODEL['isa_tax_free'])
        taxable = max(dividend_amount - tax_free, 0)
        tax = taxable * 0.099  # ISA 분리과세 9.9%
        return {
            'gross': round(dividend_amount),
            'tax_free': round(tax_free),
            'taxable': round(taxable),
            'tax': round(tax),
            'net': round(dividend_amount - tax),
            'effective_rate': round(tax / dividend_amount, 4) if dividend_amount > 0 else 0,
            'account_type': 'ISA',
        }

    tax = dividend_amount * KR_TAX_MODEL['dividend_tax']
    comprehensive = dividend_amount > KR_TAX_MODEL['financial_income_threshold']

    return {
        'gross': round(dividend_amount),
        'tax': round(tax),
        'net': round(dividend_amount - tax),
        'effective_rate': KR_TAX_MODEL['dividend_tax'],
        'comprehensive_taxation': comprehensive,
        'account_type': 'general',
    }


def calc_transaction_cost(trade_value: float,
                          is_sell: bool = False) -> dict:
    """거래 비용 계산.

    Args:
        trade_value: 거래 금액
        is_sell: 매도 여부

    Returns:
        비용 내역
    """
    brokerage = trade_value * 0.00015  # 0.015%
    sell_tax = trade_value * KR_TAX_MODEL['transaction_tax'] if is_sell else 0

    return {
        'trade_value': round(trade_value),
        'brokerage': round(brokerage),
        'sell_tax': round(sell_tax),
        'total': round(brokerage + sell_tax),
        'total_pct': round((brokerage + sell_tax) / trade_value * 100, 3) if trade_value else 0,
    }


def check_large_shareholder(holdings: list) -> list:
    """대주주 해당 여부 확인.

    Args:
        holdings: 포지션 리스트

    Returns:
        대주주 해당 종목 리스트
    """
    threshold = KR_TAX_MODEL['capital_gains_threshold']
    warnings = []

    for h in holdings:
        if h.get('value', 0) >= threshold:
            warnings.append({
                'symbol': h.get('symbol', ''),
                'name': h.get('name', ''),
                'value': h.get('value', 0),
                'threshold': threshold,
                'tax_rate': KR_TAX_MODEL['capital_gains_tax'],
            })

    return warnings


def determine_action(position: dict, target_weight: float,
                     current_weight: float) -> dict:
    """포지션 액션 결정.

    Args:
        position: 포지션 정보
        target_weight: 목표 비중
        current_weight: 현재 비중

    Returns:
        {'action', 'priority', 'drift', 'reason'}
    """
    drift = current_weight - target_weight
    abs_drift = abs(drift)

    if abs_drift >= REBALANCING['major_drift']:
        priority = 'IMMEDIATE'
    elif abs_drift >= REBALANCING['moderate_drift']:
        priority = 'HIGH'
    elif abs_drift > 0.02:
        priority = 'MEDIUM'
    else:
        priority = 'LOW'

    if abs_drift <= 0.02:
        action = 'HOLD'
        reason = '목표 범위 내'
    elif drift > 0:
        action = 'TRIM'
        reason = f'과다 편중 {abs_drift:.1%}'
    else:
        action = 'ADD'
        reason = f'목표 미달 {abs_drift:.1%}'

    return {
        'action': action,
        'priority': priority,
        'drift': round(drift, 4),
        'reason': reason,
        'symbol': position.get('symbol', ''),
        'name': position.get('name', ''),
    }


def analyze_portfolio(holdings: list) -> dict:
    """포트폴리오 종합 분석.

    Args:
        holdings: 포지션 리스트

    Returns:
        종합 분석 결과
    """
    if not holdings:
        return {
            'valid': False,
            'error': 'No holdings provided',
        }

    allocation = analyze_allocation(holdings)
    diversification = analyze_diversification(holdings)
    large_shareholder = check_large_shareholder(holdings)

    total_value = diversification['total_value']

    # 현금 비중 확인
    cash_value = sum(
        h.get('value', 0) for h in holdings
        if h.get('asset_class') == 'cash'
    )
    cash_ratio = cash_value / total_value if total_value > 0 else 0
    excess_cash = cash_ratio > REBALANCING['excess_cash']

    return {
        'valid': True,
        'total_value': total_value,
        'position_count': diversification['position_count'],
        'allocation': allocation,
        'diversification': diversification,
        'large_shareholder_warnings': large_shareholder,
        'cash_ratio': round(cash_ratio, 4),
        'excess_cash': excess_cash,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 포트폴리오 분석')
    parser.add_argument('--holdings', required=True)
    args = parser.parse_args()

    with open(args.holdings, 'r', encoding='utf-8') as f:
        holdings = json.load(f)

    result = analyze_portfolio(holdings)

    if not result['valid']:
        print(f'[Error] {result["error"]}')
        return

    print(f'[Portfolio] 총 가치: {result["total_value"]:,.0f}원')
    print(f'  종목 수: {result["position_count"]}')
    print(f'  현금 비중: {result["cash_ratio"]:.1%}')
    div = result['diversification']
    print(f'  분산투자: {div["diversification_status"]}')
    if div['concentration_issues']:
        print(f'  ⚠ 집중도 이슈: {len(div["concentration_issues"])}건')


if __name__ == '__main__':
    main()
