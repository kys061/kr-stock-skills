"""kr-backtest-expert 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from evaluate_backtest import (
    SAMPLE_SIZE_SCORING, EXPECTANCY_THRESHOLDS,
    MAX_DRAWDOWN_CATASTROPHIC, DRAWDOWN_SAFE,
    PROFIT_FACTOR_MAX, PROFIT_FACTOR_MIN,
    MIN_YEARS_TESTED, MAX_YEARS_FULL,
    MAX_PARAMS_NO_PENALTY, PARAMS_SEVERE_PENALTY,
    VERDICT_THRESHOLDS, KR_COST_MODEL, KR_PRICE_LIMIT,
    validate_inputs, calc_expectancy, calc_profit_factor,
    score_sample_size, score_expectancy, score_risk_management,
    score_robustness, score_execution_realism,
    detect_red_flags, get_verdict, evaluate,
    kr_cost_calculator,
)
from kr_cost_calculator import (
    calculate_round_trip, calculate_dividend_tax,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_sample_size_scoring(self):
        assert SAMPLE_SIZE_SCORING[0] == (200, 20)
        assert SAMPLE_SIZE_SCORING[-1] == (0, 0)

    def test_verdict_thresholds(self):
        assert VERDICT_THRESHOLDS['DEPLOY'] == 70
        assert VERDICT_THRESHOLDS['REFINE'] == 40
        assert VERDICT_THRESHOLDS['ABANDON'] == 0

    def test_kr_cost_model(self):
        assert KR_COST_MODEL['brokerage_fee'] == 0.00015
        assert KR_COST_MODEL['sell_tax'] == 0.0023
        assert KR_COST_MODEL['dividend_tax'] == 0.154
        assert KR_COST_MODEL['slippage_default'] == 0.001

    def test_kr_price_limit(self):
        assert KR_PRICE_LIMIT == 0.30

    def test_drawdown_thresholds(self):
        assert MAX_DRAWDOWN_CATASTROPHIC == 50
        assert DRAWDOWN_SAFE == 20

    def test_robustness_thresholds(self):
        assert MIN_YEARS_TESTED == 5
        assert MAX_YEARS_FULL == 10
        assert MAX_PARAMS_NO_PENALTY == 4
        assert PARAMS_SEVERE_PENALTY == 8


# ─── 입력 검증 ───

class TestValidateInputs:

    def test_valid_input(self):
        data = {
            'total_trades': 100,
            'win_rate': 55,
            'avg_win_pct': 5.0,
            'avg_loss_pct': 3.0,
            'max_drawdown_pct': 15,
        }
        assert validate_inputs(data) == []

    def test_missing_field(self):
        data = {'total_trades': 100}
        errors = validate_inputs(data)
        assert len(errors) > 0


# ─── 기대값 & PF ───

class TestCalculations:

    def test_positive_expectancy(self):
        exp = calc_expectancy(60, 5.0, 3.0)
        assert exp > 0

    def test_negative_expectancy(self):
        exp = calc_expectancy(30, 3.0, 5.0)
        assert exp < 0

    def test_profit_factor_positive(self):
        pf = calc_profit_factor(60, 5.0, 3.0)
        assert pf > 1.0

    def test_profit_factor_zero_loss(self):
        pf = calc_profit_factor(100, 5.0, 0)
        assert pf == 0.0


# ─── Dimension 1: Sample Size ───

class TestScoreSampleSize:

    def test_200_trades(self):
        assert score_sample_size(200) == 20

    def test_100_trades(self):
        assert score_sample_size(100) == 15

    def test_30_trades(self):
        assert score_sample_size(30) == 8

    def test_below_30(self):
        assert score_sample_size(10) == 0


# ─── Dimension 2: Expectancy ───

class TestScoreExpectancy:

    def test_high_expectancy(self):
        assert score_expectancy(2.0) == 20

    def test_medium_expectancy(self):
        score = score_expectancy(1.0)
        assert 10 <= score <= 18

    def test_zero_expectancy(self):
        assert score_expectancy(0.0) == 5

    def test_negative(self):
        assert score_expectancy(-1.0) == 0


# ─── Dimension 3: Risk Management ───

class TestScoreRiskManagement:

    def test_safe_and_high_pf(self):
        score = score_risk_management(15, 3.0)
        assert score == 20

    def test_catastrophic_dd(self):
        score = score_risk_management(55, 2.0)
        assert score < 10

    def test_low_pf(self):
        score = score_risk_management(15, 0.8)
        assert score == 12  # DD safe, PF below min


# ─── Dimension 4: Robustness ───

class TestScoreRobustness:

    def test_full_marks(self):
        score = score_robustness(10, 3)
        assert score == 20

    def test_short_period(self):
        score = score_robustness(3, 3)
        assert score == 5  # 0 years + 5 params

    def test_too_many_params(self):
        score = score_robustness(10, 10)
        assert score == 15  # 15 years + 0 params


# ─── Dimension 5: Execution Realism ───

class TestScoreExecution:

    def test_slippage_tested(self):
        assert score_execution_realism(True) == 20

    def test_not_tested(self):
        assert score_execution_realism(False) == 0


# ─── Red Flags ───

class TestDetectRedFlags:

    def test_small_sample(self):
        flags = detect_red_flags({'total_trades': 10})
        ids = [f['id'] for f in flags]
        assert 'small_sample' in ids

    def test_no_slippage(self):
        flags = detect_red_flags({'slippage_tested': False})
        ids = [f['id'] for f in flags]
        assert 'no_slippage_test' in ids

    def test_price_limit_untested(self):
        flags = detect_red_flags({'price_limit_tested': False})
        ids = [f['id'] for f in flags]
        assert 'price_limit_untested' in ids

    def test_tax_unaccounted(self):
        flags = detect_red_flags({'tax_included': False})
        ids = [f['id'] for f in flags]
        assert 'tax_unaccounted' in ids


# ─── 판정 ───

class TestGetVerdict:

    def test_deploy(self):
        assert get_verdict(75) == 'DEPLOY'

    def test_refine(self):
        assert get_verdict(55) == 'REFINE'

    def test_abandon(self):
        assert get_verdict(30) == 'ABANDON'


# ─── 통합 평가 ───

class TestEvaluate:

    def test_full_evaluation(self):
        data = {
            'total_trades': 250,
            'win_rate': 55,
            'avg_win_pct': 5.0,
            'avg_loss_pct': 3.0,
            'max_drawdown_pct': 15,
            'years_tested': 10,
            'num_parameters': 3,
            'slippage_tested': True,
            'price_limit_tested': True,
            'tax_included': True,
        }
        result = evaluate(data)
        assert result['valid'] is True
        assert result['composite_score'] >= 70
        assert result['verdict'] == 'DEPLOY'

    def test_poor_evaluation(self):
        data = {
            'total_trades': 10,
            'win_rate': 30,
            'avg_win_pct': 2.0,
            'avg_loss_pct': 5.0,
            'max_drawdown_pct': 60,
            'years_tested': 2,
            'num_parameters': 10,
            'slippage_tested': False,
        }
        result = evaluate(data)
        assert result['verdict'] == 'ABANDON'
        assert result['red_flag_count'] >= 3

    def test_invalid_input(self):
        result = evaluate({})
        assert result['valid'] is False


# ─── 한국 비용 계산기 ───

class TestKRCostCalculator:

    def test_round_trip_basic(self):
        result = kr_cost_calculator(100, 10_000_000)
        assert result['per_trade_cost'] > 0
        assert result['total_cost'] > 0
        assert result['total_trades'] == 100

    def test_calculate_round_trip(self):
        result = calculate_round_trip(10_000_000)
        assert result['sell_tax'] > result['buy_brokerage']
        assert result['total_pct'] > 0

    def test_dividend_tax(self):
        result = calculate_dividend_tax(1_000_000)
        assert result['tax_rate'] == 0.154
        assert result['net_dividend'] == round(1_000_000 * (1 - 0.154))
