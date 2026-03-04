"""kr-options-advisor: KOSPI200 옵션 전략 시뮬레이터.

Usage:
    python strategy_simulator.py --strategy bull_call_spread --spot 350 --dte 30
"""

import argparse
from black_scholes import (
    STRATEGIES, KOSPI200_MULTIPLIER, VKOSPI_DEFAULT, KR_RISK_FREE_RATE,
    IV_CRUSH_MODEL, GREEKS_TARGETS,
    bs_price, calc_greeks, dte_to_years, premium_to_krw,
    classify_moneyness,
)


def build_strategy_legs(strategy_name: str, spot: float,
                        dte: int, vol: float = None,
                        width: float = 5.0) -> list:
    """전략의 각 레그 생성.

    Args:
        strategy_name: 전략 이름
        spot: 기초자산 가격
        dte: 잔존일수
        vol: 변동성
        width: 스프레드 폭 (포인트)

    Returns:
        [{'type': 'call'/'put', 'strike': float, 'action': 'buy'/'sell',
          'premium': float, 'greeks': dict}, ...]
    """
    if vol is None:
        vol = VKOSPI_DEFAULT

    t = dte_to_years(dte)
    atm = round(spot)
    otm_call = atm + width
    otm_put = atm - width
    deep_otm_call = atm + width * 2
    deep_otm_put = atm - width * 2

    def _leg(opt_type, strike, action):
        price = bs_price(spot, strike, t, vol, opt_type)
        greeks = calc_greeks(spot, strike, t, vol, opt_type)
        return {
            'type': opt_type,
            'strike': strike,
            'action': action,
            'premium': price,
            'greeks': greeks,
        }

    builders = {
        'covered_call': [
            _leg('call', otm_call, 'sell'),
        ],
        'cash_secured_put': [
            _leg('put', otm_put, 'sell'),
        ],
        'poor_mans_covered_call': [
            _leg('call', otm_put, 'buy'),
            _leg('call', otm_call, 'sell'),
        ],
        'protective_put': [
            _leg('put', otm_put, 'buy'),
        ],
        'collar': [
            _leg('put', otm_put, 'buy'),
            _leg('call', otm_call, 'sell'),
        ],
        'bull_call_spread': [
            _leg('call', atm, 'buy'),
            _leg('call', otm_call, 'sell'),
        ],
        'bull_put_spread': [
            _leg('put', otm_put, 'sell'),
            _leg('put', deep_otm_put, 'buy'),
        ],
        'bear_call_spread': [
            _leg('call', otm_call, 'sell'),
            _leg('call', deep_otm_call, 'buy'),
        ],
        'bear_put_spread': [
            _leg('put', atm, 'buy'),
            _leg('put', otm_put, 'sell'),
        ],
        'long_straddle': [
            _leg('call', atm, 'buy'),
            _leg('put', atm, 'buy'),
        ],
        'long_strangle': [
            _leg('call', otm_call, 'buy'),
            _leg('put', otm_put, 'buy'),
        ],
        'short_straddle': [
            _leg('call', atm, 'sell'),
            _leg('put', atm, 'sell'),
        ],
        'short_strangle': [
            _leg('call', otm_call, 'sell'),
            _leg('put', otm_put, 'sell'),
        ],
        'iron_condor': [
            _leg('put', deep_otm_put, 'buy'),
            _leg('put', otm_put, 'sell'),
            _leg('call', otm_call, 'sell'),
            _leg('call', deep_otm_call, 'buy'),
        ],
        'iron_butterfly': [
            _leg('put', otm_put, 'buy'),
            _leg('put', atm, 'sell'),
            _leg('call', atm, 'sell'),
            _leg('call', otm_call, 'buy'),
        ],
        'calendar_spread': [
            _leg('call', atm, 'sell'),
            _leg('call', atm, 'buy'),  # 장기 (dte 더 길지만 동일 행사가)
        ],
        'diagonal_spread': [
            _leg('call', atm, 'sell'),
            _leg('call', otm_put, 'buy'),  # 장기 ITM
        ],
        'ratio_spread': [
            _leg('call', atm, 'buy'),
            _leg('call', otm_call, 'sell'),
            _leg('call', otm_call, 'sell'),
        ],
    }

    return builders.get(strategy_name, [])


def calc_strategy_cost(legs: list) -> dict:
    """전략 순비용 계산.

    Args:
        legs: 레그 리스트

    Returns:
        {'net_premium', 'net_premium_krw', 'is_debit'}
    """
    net = 0.0
    for leg in legs:
        if leg['action'] == 'buy':
            net -= leg['premium']
        else:
            net += leg['premium']

    return {
        'net_premium': round(net, 4),
        'net_premium_krw': premium_to_krw(abs(net)),
        'is_debit': net < 0,
    }


def calc_strategy_greeks(legs: list) -> dict:
    """전략 합산 그릭스.

    Args:
        legs: 레그 리스트

    Returns:
        합산 그릭스 dict
    """
    totals = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}

    for leg in legs:
        sign = 1 if leg['action'] == 'buy' else -1
        for greek in totals:
            totals[greek] += sign * leg['greeks'].get(greek, 0)

    return {k: round(v, 4) for k, v in totals.items()}


def calc_expiry_payoff(legs: list, spot_at_expiry: float,
                       net_premium: float) -> float:
    """만기 시 손익 계산.

    Args:
        legs: 레그 리스트
        spot_at_expiry: 만기 시 기초자산 가격
        net_premium: 순프리미엄 (음수=지불, 양수=수취)

    Returns:
        만기 손익 (포인트)
    """
    payoff = net_premium

    for leg in legs:
        if leg['type'] == 'call':
            intrinsic = max(spot_at_expiry - leg['strike'], 0)
        else:
            intrinsic = max(leg['strike'] - spot_at_expiry, 0)

        if leg['action'] == 'buy':
            payoff += intrinsic
        else:
            payoff -= intrinsic

    return round(payoff, 4)


def calc_breakeven_points(legs: list, net_premium: float,
                          spot: float, search_range: float = 50.0,
                          step: float = 0.1) -> list:
    """손익분기점 계산.

    Args:
        legs: 레그 리스트
        net_premium: 순프리미엄
        spot: 현재 기초자산 가격
        search_range: 탐색 범위
        step: 탐색 간격

    Returns:
        손익분기점 리스트
    """
    breakevens = []
    low = spot - search_range
    high = spot + search_range
    prev_payoff = None
    s = low

    while s <= high:
        payoff = calc_expiry_payoff(legs, s, net_premium)
        if prev_payoff is not None:
            if prev_payoff * payoff < 0:
                breakevens.append(round(s, 2))
            elif prev_payoff != 0 and payoff == 0:
                breakevens.append(round(s, 2))
        prev_payoff = payoff
        s += step

    return breakevens


def calc_max_profit_loss(legs: list, net_premium: float,
                         spot: float, search_range: float = 50.0,
                         step: float = 0.1) -> dict:
    """최대 이익/손실 계산.

    Args:
        legs: 레그 리스트
        net_premium: 순프리미엄
        spot: 현재 기초자산 가격

    Returns:
        {'max_profit', 'max_loss', 'max_profit_at', 'max_loss_at'}
    """
    max_profit = float('-inf')
    max_loss = float('inf')
    max_profit_at = spot
    max_loss_at = spot

    s = spot - search_range
    while s <= spot + search_range:
        payoff = calc_expiry_payoff(legs, s, net_premium)
        if payoff > max_profit:
            max_profit = payoff
            max_profit_at = s
        if payoff < max_loss:
            max_loss = payoff
            max_loss_at = s
        s += step

    return {
        'max_profit': round(max_profit, 4),
        'max_loss': round(max_loss, 4),
        'max_profit_at': round(max_profit_at, 2),
        'max_loss_at': round(max_loss_at, 2),
        'max_profit_krw': premium_to_krw(max(max_profit, 0)),
        'max_loss_krw': premium_to_krw(abs(min(max_loss, 0))),
    }


def simulate_iv_crush(legs: list, spot: float, dte: int,
                      current_iv: float) -> dict:
    """IV Crush 시뮬레이션.

    Args:
        legs: 레그 리스트
        spot: 기초자산 가격
        dte: 잔존일수
        current_iv: 현재 IV

    Returns:
        {'pre_value', 'post_value', 'pnl', 'pnl_krw'}
    """
    pre_iv = current_iv * IV_CRUSH_MODEL['pre_earnings_iv_premium']
    post_iv = pre_iv * IV_CRUSH_MODEL['post_earnings_iv_drop']
    t = dte_to_years(dte)

    pre_value = 0.0
    post_value = 0.0

    for leg in legs:
        sign = 1 if leg['action'] == 'buy' else -1
        pre_price = bs_price(spot, leg['strike'], t, pre_iv, leg['type'])
        post_price = bs_price(spot, leg['strike'], t, post_iv, leg['type'])
        pre_value += sign * pre_price
        post_value += sign * post_price

    pnl = post_value - pre_value

    return {
        'pre_iv': round(pre_iv, 4),
        'post_iv': round(post_iv, 4),
        'pre_value': round(pre_value, 4),
        'post_value': round(post_value, 4),
        'pnl': round(pnl, 4),
        'pnl_krw': premium_to_krw(pnl),
    }


def check_greeks_warnings(strategy_greeks: dict) -> list:
    """그릭스 경고 확인.

    Args:
        strategy_greeks: 전략 합산 그릭스

    Returns:
        경고 메시지 리스트
    """
    warnings = []
    delta_range = GREEKS_TARGETS['delta']
    if not (delta_range[0] <= strategy_greeks['delta'] <= delta_range[1]):
        warnings.append(
            f'델타 중립 범위 이탈: {strategy_greeks["delta"]:.4f} '
            f'(목표: {delta_range[0]}~{delta_range[1]})')

    if abs(strategy_greeks.get('vega', 0)) > GREEKS_TARGETS['vega_warning']:
        warnings.append(
            f'베가 위험 수준: {strategy_greeks["vega"]:.4f} '
            f'(경고: >{GREEKS_TARGETS["vega_warning"]})')

    return warnings


def simulate_strategy(strategy_name: str, spot: float,
                      dte: int, vol: float = None,
                      width: float = 5.0) -> dict:
    """전략 전체 시뮬레이션.

    Args:
        strategy_name: 전략 이름
        spot: 기초자산 가격
        dte: 잔존일수
        vol: 변동성
        width: 스프레드 폭

    Returns:
        시뮬레이션 결과 dict
    """
    if strategy_name not in STRATEGIES:
        return {'valid': False, 'error': f'Unknown strategy: {strategy_name}'}

    if vol is None:
        vol = VKOSPI_DEFAULT

    legs = build_strategy_legs(strategy_name, spot, dte, vol, width)
    if not legs:
        return {'valid': False, 'error': 'Failed to build strategy legs'}

    cost = calc_strategy_cost(legs)
    greeks = calc_strategy_greeks(legs)
    breakevens = calc_breakeven_points(legs, cost['net_premium'], spot)
    max_pl = calc_max_profit_loss(legs, cost['net_premium'], spot)
    warnings = check_greeks_warnings(greeks)

    strategy_info = STRATEGIES[strategy_name]

    return {
        'valid': True,
        'strategy': strategy_name,
        'category': strategy_info['category'],
        'expected_legs': strategy_info['legs'],
        'actual_legs': len(legs),
        'spot': spot,
        'dte': dte,
        'volatility': vol,
        'legs': [{
            'type': l['type'],
            'strike': l['strike'],
            'action': l['action'],
            'premium': l['premium'],
            'premium_krw': premium_to_krw(l['premium']),
        } for l in legs],
        'cost': cost,
        'greeks': greeks,
        'breakevens': breakevens,
        'max_profit': max_pl['max_profit'],
        'max_loss': max_pl['max_loss'],
        'max_profit_krw': max_pl['max_profit_krw'],
        'max_loss_krw': max_pl['max_loss_krw'],
        'risk_reward_ratio': round(
            abs(max_pl['max_profit'] / max_pl['max_loss']), 2
        ) if max_pl['max_loss'] != 0 else 0,
        'warnings': warnings,
    }


def get_strategies_by_category(category: str) -> list:
    """카테고리별 전략 조회."""
    return [name for name, info in STRATEGIES.items()
            if info['category'] == category]


def get_strategy_categories() -> list:
    """전략 카테고리 목록."""
    return list(set(info['category'] for info in STRATEGIES.values()))


def main():
    parser = argparse.ArgumentParser(description='KOSPI200 옵션 전략 시뮬레이터')
    parser.add_argument('--strategy', required=True,
                        choices=list(STRATEGIES.keys()))
    parser.add_argument('--spot', type=float, required=True)
    parser.add_argument('--dte', type=int, default=30)
    parser.add_argument('--vol', type=float, default=VKOSPI_DEFAULT)
    parser.add_argument('--width', type=float, default=5.0)
    args = parser.parse_args()

    result = simulate_strategy(args.strategy, args.spot, args.dte,
                               args.vol, args.width)

    if not result['valid']:
        print(f'[Error] {result["error"]}')
        return

    print(f'[Strategy] {result["strategy"]} ({result["category"]})')
    print(f'  KOSPI200: {result["spot"]}')
    print(f'  DTE: {result["dte"]}일')
    print(f'  Vol: {result["volatility"]:.1%}')
    print(f'\n  Legs:')
    for leg in result['legs']:
        action = '매수' if leg['action'] == 'buy' else '매도'
        print(f'    {action} {leg["type"].upper()} {leg["strike"]} '
              f'@ {leg["premium"]:.4f}pt ({leg["premium_krw"]:,}원)')
    print(f'\n  순비용: {result["cost"]["net_premium"]:.4f}pt '
          f'({"지불" if result["cost"]["is_debit"] else "수취"})')
    print(f'  최대이익: {result["max_profit"]:.4f}pt '
          f'({result["max_profit_krw"]:,}원)')
    print(f'  최대손실: {result["max_loss"]:.4f}pt '
          f'({result["max_loss_krw"]:,}원)')
    print(f'  손익비: {result["risk_reward_ratio"]}')
    if result['breakevens']:
        print(f'  손익분기: {result["breakevens"]}')
    if result['warnings']:
        print(f'\n  ⚠ 경고:')
        for w in result['warnings']:
            print(f'    - {w}')


if __name__ == '__main__':
    main()
