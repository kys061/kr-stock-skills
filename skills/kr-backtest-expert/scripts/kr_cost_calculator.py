"""kr-backtest-expert: 한국 거래 비용 계산기.

Usage:
    python kr_cost_calculator.py --trades 100 --avg-value 10000000
"""

import argparse
from evaluate_backtest import KR_COST_MODEL, KR_PRICE_LIMIT


def calculate_round_trip(trade_value: float,
                         slippage: float = None) -> dict:
    """왕복 거래 비용 계산.

    Args:
        trade_value: 거래 금액
        slippage: 슬리피지 (None이면 기본값 사용)

    Returns:
        비용 내역 dict
    """
    if slippage is None:
        slippage = KR_COST_MODEL['slippage_default']

    buy_brokerage = trade_value * KR_COST_MODEL['brokerage_fee']
    sell_brokerage = trade_value * KR_COST_MODEL['brokerage_fee']
    sell_tax = trade_value * KR_COST_MODEL['sell_tax']
    buy_slippage = trade_value * slippage
    sell_slippage = trade_value * slippage

    total = (buy_brokerage + sell_brokerage + sell_tax
             + buy_slippage + sell_slippage)

    return {
        'buy_brokerage': round(buy_brokerage),
        'sell_brokerage': round(sell_brokerage),
        'sell_tax': round(sell_tax),
        'buy_slippage': round(buy_slippage),
        'sell_slippage': round(sell_slippage),
        'total': round(total),
        'total_pct': round(total / trade_value * 100, 3) if trade_value else 0,
    }


def calculate_dividend_tax(dividend_amount: float) -> dict:
    """배당 세금 계산.

    Args:
        dividend_amount: 배당금

    Returns:
        세금 내역 dict
    """
    tax = dividend_amount * KR_COST_MODEL['dividend_tax']
    net = dividend_amount - tax

    return {
        'gross_dividend': round(dividend_amount),
        'tax': round(tax),
        'net_dividend': round(net),
        'tax_rate': KR_COST_MODEL['dividend_tax'],
    }


def main():
    parser = argparse.ArgumentParser(description='한국 거래 비용 계산기')
    parser.add_argument('--trades', type=int, default=100)
    parser.add_argument('--avg-value', type=float, default=10_000_000)
    args = parser.parse_args()

    single = calculate_round_trip(args.avg_value)
    print(f'[Cost] 1회 왕복: {single["total"]:,}원 '
          f'({single["total_pct"]}%)')
    print(f'[Cost] {args.trades}회 총: '
          f'{single["total"] * args.trades:,}원')


if __name__ == '__main__':
    main()
