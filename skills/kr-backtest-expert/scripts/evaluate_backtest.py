"""kr-backtest-expert: 5차원 백테스트 평가 엔진.

Usage:
    python evaluate_backtest.py --input backtest_results.json
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime

# ─── Dimension 1: Sample Size (20점) ───

SAMPLE_SIZE_SCORING = [
    (200, 20),
    (100, 15),
    (30, 8),
    (0, 0),
]

# ─── Dimension 2: Expectancy (20점) ───

EXPECTANCY_THRESHOLDS = [
    (1.5, 20),
    (0.5, 10),
    (0.0, 5),
    (-999, 0),
]

# ─── Dimension 3: Risk Management (20점) ───
# Drawdown Component (0-12) + Profit Factor Component (0-8)

MAX_DRAWDOWN_CATASTROPHIC = 50
DRAWDOWN_SAFE = 20
PROFIT_FACTOR_MAX = 3.0
PROFIT_FACTOR_MIN = 1.0

# ─── Dimension 4: Robustness (20점) ───

MIN_YEARS_TESTED = 5
MAX_YEARS_FULL = 10
MAX_PARAMS_NO_PENALTY = 4
PARAMS_MEDIUM_PENALTY = 6
PARAMS_HEAVY_PENALTY = 7
PARAMS_SEVERE_PENALTY = 8

# ─── Dimension 5: Execution Realism (20점) ───
# 슬리피지 테스트 완료 → 20, 미완료 → 0

# ─── 판정 ───

VERDICT_THRESHOLDS = {
    'DEPLOY': 70,
    'REFINE': 40,
    'ABANDON': 0,
}

# ─── 한국 비용 모델 ───

KR_COST_MODEL = {
    'brokerage_fee': 0.00015,
    'sell_tax': 0.0023,
    'dividend_tax': 0.154,
    'capital_gains_tax': 0.22,
    'slippage_default': 0.001,
    'slippage_stress': 0.002,
}

KR_PRICE_LIMIT = 0.30

# ─── Red Flags ───

RED_FLAGS = [
    {'id': 'small_sample', 'severity': 'HIGH',
     'check': lambda d: d.get('total_trades', 0) < 30},
    {'id': 'no_slippage_test', 'severity': 'HIGH',
     'check': lambda d: not d.get('slippage_tested', False)},
    {'id': 'excessive_drawdown', 'severity': 'HIGH',
     'check': lambda d: d.get('max_drawdown_pct', 0) > 50},
    {'id': 'negative_expectancy', 'severity': 'HIGH',
     'check': lambda d: d.get('expectancy_pct', 0) < 0},
    {'id': 'over_optimized', 'severity': 'MEDIUM',
     'check': lambda d: d.get('num_parameters', 0) >= 7},
    {'id': 'short_test_period', 'severity': 'MEDIUM',
     'check': lambda d: d.get('years_tested', 0) < 5},
    {'id': 'too_good', 'severity': 'MEDIUM',
     'check': lambda d: (d.get('win_rate', 0) > 90
                         and d.get('max_drawdown_pct', 100) < 5)},
    {'id': 'price_limit_untested', 'severity': 'MEDIUM',
     'check': lambda d: not d.get('price_limit_tested', False)},
    {'id': 'tax_unaccounted', 'severity': 'MEDIUM',
     'check': lambda d: not d.get('tax_included', False)},
]


def validate_inputs(data: dict) -> list:
    """입력 데이터 검증.

    Args:
        data: 백테스트 결과 dict

    Returns:
        오류 메시지 리스트 (빈 리스트 = 유효)
    """
    errors = []
    required = ['total_trades', 'win_rate', 'avg_win_pct', 'avg_loss_pct',
                 'max_drawdown_pct']
    for key in required:
        if key not in data:
            errors.append(f'필수 필드 누락: {key}')
    return errors


def calc_expectancy(win_rate: float, avg_win: float,
                    avg_loss: float) -> float:
    """기대값 계산.

    Args:
        win_rate: 승률 (0-100)
        avg_win: 평균 수익률 (%)
        avg_loss: 평균 손실률 (%, 양수값)

    Returns:
        기대값 (%)
    """
    wr = win_rate / 100.0
    lr = 1.0 - wr
    return wr * avg_win - lr * abs(avg_loss)


def calc_profit_factor(win_rate: float, avg_win: float,
                       avg_loss: float) -> float:
    """Profit Factor 계산.

    Args:
        win_rate: 승률 (0-100)
        avg_win: 평균 수익률 (%)
        avg_loss: 평균 손실률 (%, 양수값)

    Returns:
        Profit Factor
    """
    gross_profit = (win_rate / 100.0) * avg_win
    gross_loss = (1.0 - win_rate / 100.0) * abs(avg_loss)
    if gross_loss <= 0:
        return 0.0
    return gross_profit / gross_loss


def score_sample_size(total_trades: int) -> int:
    """Dimension 1: Sample Size 스코어링."""
    for threshold, score in SAMPLE_SIZE_SCORING:
        if total_trades >= threshold:
            return score
    return 0


def score_expectancy(expectancy_pct: float) -> int:
    """Dimension 2: Expectancy 스코어링."""
    if expectancy_pct >= 1.5:
        return 20
    elif expectancy_pct >= 0.5:
        return int(10 + (expectancy_pct - 0.5) / 1.0 * 8)
    elif expectancy_pct >= 0.0:
        return int(5 + (expectancy_pct / 0.5) * 5)
    return 0


def score_risk_management(max_dd_pct: float, profit_factor: float) -> int:
    """Dimension 3: Risk Management 스코어링.

    Drawdown (0-12) + Profit Factor (0-8) = 0-20.
    """
    # Drawdown component (0-12)
    if max_dd_pct >= MAX_DRAWDOWN_CATASTROPHIC:
        dd_score = 0
    elif max_dd_pct <= DRAWDOWN_SAFE:
        dd_score = 12
    else:
        ratio = (max_dd_pct - DRAWDOWN_SAFE) / (
            MAX_DRAWDOWN_CATASTROPHIC - DRAWDOWN_SAFE)
        dd_score = int(12 * (1 - ratio))

    # Profit Factor component (0-8)
    if profit_factor < PROFIT_FACTOR_MIN:
        pf_score = 0
    elif profit_factor >= PROFIT_FACTOR_MAX:
        pf_score = 8
    else:
        ratio = (profit_factor - PROFIT_FACTOR_MIN) / (
            PROFIT_FACTOR_MAX - PROFIT_FACTOR_MIN)
        pf_score = int(8 * ratio)

    return dd_score + pf_score


def score_robustness(years_tested: int, num_parameters: int) -> int:
    """Dimension 4: Robustness 스코어링.

    Years (0-15) + Parameters (0-5) = 0-20.
    """
    # Years component (0-15)
    if years_tested < MIN_YEARS_TESTED:
        years_score = 0
    elif years_tested >= MAX_YEARS_FULL:
        years_score = 15
    else:
        ratio = (years_tested - MIN_YEARS_TESTED) / (
            MAX_YEARS_FULL - MIN_YEARS_TESTED)
        years_score = int(15 * ratio)

    # Parameters component (0-5)
    if num_parameters <= MAX_PARAMS_NO_PENALTY:
        params_score = 5
    elif num_parameters <= PARAMS_MEDIUM_PENALTY:
        params_score = 3
    elif num_parameters <= PARAMS_HEAVY_PENALTY:
        params_score = 1
    else:
        params_score = 0

    return years_score + params_score


def score_execution_realism(slippage_tested: bool) -> int:
    """Dimension 5: Execution Realism 스코어링."""
    return 20 if slippage_tested else 0


def detect_red_flags(data: dict) -> list:
    """Red Flag 감지.

    Args:
        data: 백테스트 결과 dict

    Returns:
        발견된 Red Flag 리스트
    """
    flags = []
    for flag in RED_FLAGS:
        if flag['check'](data):
            flags.append({
                'id': flag['id'],
                'severity': flag['severity'],
            })
    return flags


def get_verdict(score: int) -> str:
    """종합 점수 → 판정."""
    if score >= VERDICT_THRESHOLDS['DEPLOY']:
        return 'DEPLOY'
    elif score >= VERDICT_THRESHOLDS['REFINE']:
        return 'REFINE'
    return 'ABANDON'


def evaluate(data: dict) -> dict:
    """백테스트 결과 종합 평가.

    Args:
        data: 백테스트 결과 dict

    Returns:
        평가 결과 dict
    """
    errors = validate_inputs(data)
    if errors:
        return {'valid': False, 'errors': errors}

    total_trades = data.get('total_trades', 0)
    win_rate = data.get('win_rate', 0)
    avg_win = data.get('avg_win_pct', 0)
    avg_loss = data.get('avg_loss_pct', 0)
    max_dd = data.get('max_drawdown_pct', 0)
    years = data.get('years_tested', 0)
    params = data.get('num_parameters', 0)
    slippage = data.get('slippage_tested', False)

    expectancy = calc_expectancy(win_rate, avg_win, avg_loss)
    profit_factor = calc_profit_factor(win_rate, avg_win, avg_loss)

    d1 = score_sample_size(total_trades)
    d2 = score_expectancy(expectancy)
    d3 = score_risk_management(max_dd, profit_factor)
    d4 = score_robustness(years, params)
    d5 = score_execution_realism(slippage)

    composite = d1 + d2 + d3 + d4 + d5
    verdict = get_verdict(composite)
    red_flags = detect_red_flags(data)

    return {
        'valid': True,
        'composite_score': composite,
        'verdict': verdict,
        'dimensions': {
            'sample_size': d1,
            'expectancy': d2,
            'risk_management': d3,
            'robustness': d4,
            'execution_realism': d5,
        },
        'derived': {
            'expectancy_pct': round(expectancy, 3),
            'profit_factor': round(profit_factor, 3),
        },
        'red_flags': red_flags,
        'red_flag_count': len(red_flags),
        'evaluated_at': datetime.now().isoformat(),
    }


def kr_cost_calculator(trades: int, avg_trade_value: float,
                       avg_hold_days: int = 10) -> dict:
    """한국 거래 비용 계산.

    Args:
        trades: 거래 횟수
        avg_trade_value: 평균 거래 금액
        avg_hold_days: 평균 보유일

    Returns:
        비용 내역 dict
    """
    buy_cost = avg_trade_value * KR_COST_MODEL['brokerage_fee']
    sell_cost = avg_trade_value * (KR_COST_MODEL['brokerage_fee']
                                   + KR_COST_MODEL['sell_tax'])
    slippage = avg_trade_value * KR_COST_MODEL['slippage_default'] * 2
    per_trade_cost = buy_cost + sell_cost + slippage
    total_cost = per_trade_cost * trades

    return {
        'per_trade_cost': round(per_trade_cost),
        'per_trade_pct': round(per_trade_cost / avg_trade_value * 100, 3),
        'total_cost': round(total_cost),
        'total_trades': trades,
        'cost_model': KR_COST_MODEL,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 백테스트 평가 엔진')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = evaluate(data)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'[Backtest] 결과 → {args.output}')
    else:
        print(f'[Backtest] Score={result.get("composite_score", "?")} '
              f'Verdict={result.get("verdict", "?")}')


if __name__ == '__main__':
    main()
