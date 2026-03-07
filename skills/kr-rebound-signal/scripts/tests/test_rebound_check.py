"""Tests for rebound_check.py - 14 bounce signal judgment functions."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rebound_check import (
    check_vix_reversal,
    check_ewy_rebound,
    check_sp_futures_positive,
    check_cnn_fg_extreme_fear,
    check_put_call_ratio,
    check_usdkrw_decline,
    check_kospi_rsi,
    check_hy_spread_contraction,
    check_credit_balance_drop,
    check_insider_cluster,
    calculate_rsi,
    overall_judgment,
    format_change,
)


class TestCheckVixReversal:
    def test_sharp_drop_exactly_10(self):
        result, change = check_vix_reversal(27.0, 30.0)
        assert result is True  # -10% exactly

    def test_massive_drop(self):
        result, change = check_vix_reversal(20.0, 40.0)
        assert result is True  # -50%

    def test_moderate_drop(self):
        result, change = check_vix_reversal(28.0, 30.0)
        assert result is False  # -6.67%

    def test_increase(self):
        result, change = check_vix_reversal(35.0, 30.0)
        assert result is False

    def test_zero_prev(self):
        assert check_vix_reversal(30.0, 0) is None

    def test_change_pct_returned(self):
        result, change = check_vix_reversal(25.0, 50.0)
        assert change == -50.0


class TestCheckEwyRebound:
    def test_strong_rebound(self):
        assert check_ewy_rebound(2.5) is True

    def test_exactly_one_percent(self):
        assert check_ewy_rebound(1.0) is True

    def test_weak_rebound(self):
        assert check_ewy_rebound(0.5) is False

    def test_negative(self):
        assert check_ewy_rebound(-1.0) is False

    def test_zero(self):
        assert check_ewy_rebound(0.0) is False


class TestCheckSpFuturesPositive:
    def test_positive(self):
        assert check_sp_futures_positive(0.5) is True

    def test_zero(self):
        assert check_sp_futures_positive(0) is False

    def test_negative(self):
        assert check_sp_futures_positive(-0.3) is False

    def test_tiny_positive(self):
        assert check_sp_futures_positive(0.01) is True


class TestCheckCnnFgExtremeFear:
    def test_extreme_fear(self):
        assert check_cnn_fg_extreme_fear(15) is True

    def test_exactly_20(self):
        assert check_cnn_fg_extreme_fear(20) is False

    def test_greed(self):
        assert check_cnn_fg_extreme_fear(65) is False

    def test_zero(self):
        assert check_cnn_fg_extreme_fear(0) is True

    def test_just_below_20(self):
        assert check_cnn_fg_extreme_fear(19) is True


class TestCheckPutCallRatio:
    def test_above_one(self):
        assert check_put_call_ratio(1.2) is True

    def test_exactly_one(self):
        assert check_put_call_ratio(1.0) is False

    def test_below_one(self):
        assert check_put_call_ratio(0.8) is False

    def test_extreme(self):
        assert check_put_call_ratio(1.5) is True


class TestCheckUsdkrwDecline:
    def test_decline(self):
        assert check_usdkrw_decline(-0.5) is True

    def test_increase(self):
        assert check_usdkrw_decline(0.3) is False

    def test_flat(self):
        assert check_usdkrw_decline(0) is False

    def test_large_decline(self):
        assert check_usdkrw_decline(-2.0) is True


class TestCheckKospiRsi:
    def test_oversold(self):
        assert check_kospi_rsi(25.0) is True

    def test_exactly_30(self):
        assert check_kospi_rsi(30.0) is False

    def test_normal(self):
        assert check_kospi_rsi(50.0) is False

    def test_extreme_oversold(self):
        assert check_kospi_rsi(10.0) is True


class TestCheckHySpreadContraction:
    def test_contraction(self):
        assert check_hy_spread_contraction(4.5, 5.0) is True

    def test_expansion(self):
        assert check_hy_spread_contraction(5.5, 5.0) is False

    def test_flat(self):
        assert check_hy_spread_contraction(5.0, 5.0) is False

    def test_large_contraction(self):
        assert check_hy_spread_contraction(3.0, 6.0) is True


class TestCheckCreditBalanceDrop:
    def test_large_drop(self):
        result, drop = check_credit_balance_drop(60, 100)
        assert result is True
        assert drop == 40.0

    def test_small_drop(self):
        result, drop = check_credit_balance_drop(80, 100)
        assert result is False
        assert drop == 20.0

    def test_exactly_30(self):
        result, drop = check_credit_balance_drop(70, 100)
        assert result is True
        assert drop == 30.0

    def test_zero_peak(self):
        assert check_credit_balance_drop(50, 0) is None

    def test_no_drop(self):
        result, drop = check_credit_balance_drop(100, 100)
        assert result is False
        assert drop == 0.0


class TestCheckInsiderCluster:
    def test_above_threshold(self):
        assert check_insider_cluster(15) is True

    def test_exactly_threshold(self):
        assert check_insider_cluster(10) is True

    def test_below_threshold(self):
        assert check_insider_cluster(5) is False

    def test_zero(self):
        assert check_insider_cluster(0) is False

    def test_custom_threshold(self):
        assert check_insider_cluster(8, threshold=5) is True


class TestCalculateRsi:
    def test_uptrend(self):
        closes = [100 + i * 2 for i in range(20)]
        rsi = calculate_rsi(closes)
        assert rsi is not None
        assert rsi > 70

    def test_downtrend(self):
        closes = [200 - i * 2 for i in range(20)]
        rsi = calculate_rsi(closes)
        assert rsi is not None
        assert rsi < 30

    def test_insufficient_data(self):
        closes = [100, 101, 102]
        assert calculate_rsi(closes) is None

    def test_flat_prices(self):
        closes = [100] * 20
        rsi = calculate_rsi(closes)
        assert rsi == 100.0

    def test_minimum_data(self):
        closes = [100 + i for i in range(16)]  # exactly period + 1
        rsi = calculate_rsi(closes, period=14)
        assert rsi is not None
        assert 0 <= rsi <= 100


class TestOverallJudgment:
    def test_historic_rebound(self):
        assert overall_judgment(7) == "역사적 반등 가능성"
        assert overall_judgment(10) == "역사적 반등 가능성"
        assert overall_judgment(14) == "역사적 반등 가능성"

    def test_aggressive_buy(self):
        assert overall_judgment(5) == "적극 매수 고려"
        assert overall_judgment(6) == "적극 매수 고려"

    def test_scale_in(self):
        assert overall_judgment(3) == "분할 매수 고려"
        assert overall_judgment(4) == "분할 매수 고려"

    def test_wait(self):
        assert overall_judgment(0) == "관망 유지"
        assert overall_judgment(1) == "관망 유지"
        assert overall_judgment(2) == "관망 유지"


class TestFormatChange:
    def test_positive(self):
        assert format_change(1.5) == "+1.50%"

    def test_negative(self):
        assert format_change(-2.3) == "-2.30%"

    def test_zero(self):
        assert format_change(0) == "+0.00%"

    def test_none(self):
        assert format_change(None) == "-"
