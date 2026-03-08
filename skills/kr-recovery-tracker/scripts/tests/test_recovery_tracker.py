"""Tests for kr-recovery-tracker recovery_tracker.py

Test coverage:
  TestCalculateRsi (5): basic, all_gains, all_losses, insufficient_data, empty
  TestCalculateRecovery (5): normal, full_recovery, no_recovery, negative, none_input
  TestClassifyStage (6): panic, rebound, stabilization, trend, full, fallback_ratio
  TestCheckStage3Conditions (4): all_met, none_met, partial, missing_values
  TestClassifySignal (5): vix_green, vix_red, usdkrw_orange, recovery_low, recovery_high
  TestLoadRecoveryStages (2): existing, missing
  TestBuildRecoveryAnalysis (3): normal, auto_detect, all_errors
  TestFormatChange (2): positive, none
  Total: 32 tests
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from recovery_tracker import (
    calculate_rsi,
    calculate_recovery,
    classify_stage,
    check_stage3_conditions,
    classify_signal,
    load_recovery_stages,
    build_recovery_analysis,
    format_change,
    SIGNAL_EMOJI,
    SIGNAL_THRESHOLDS,
    YFINANCE_TICKERS,
)


# ---------------------------------------------------------------------------
# TestCalculateRsi
# ---------------------------------------------------------------------------

class TestCalculateRsi:
    """T-01 ~ T-05: RSI calculation tests."""

    def test_basic_rsi(self):
        """T-01: RSI with mixed gains/losses returns value in 0-100."""
        closes = [100 + i * 0.5 + ((-1) ** i) * 2 for i in range(20)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_all_gains(self):
        """T-02: Pure uptrend gives RSI = 100."""
        closes = [100 + i for i in range(20)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi == 100.0

    def test_all_losses(self):
        """T-03: Pure downtrend gives RSI near 0."""
        closes = [200 - i for i in range(20)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi is not None
        assert rsi < 5

    def test_insufficient_data(self):
        """T-04: Less than period+1 data points returns None."""
        closes = [100, 101, 102]
        rsi = calculate_rsi(closes, period=14)
        assert rsi is None

    def test_empty_list(self):
        """T-05: Empty list returns None."""
        assert calculate_rsi([], period=14) is None
        assert calculate_rsi(None, period=14) is None


# ---------------------------------------------------------------------------
# TestCalculateRecovery
# ---------------------------------------------------------------------------

class TestCalculateRecovery:
    """T-06 ~ T-10: Recovery calculation tests."""

    def test_normal_recovery(self):
        """T-06: Normal partial recovery."""
        result = calculate_recovery(6244, 5094, 5585)
        assert result is not None
        assert result['total_drop'] == 1150
        assert result['recovery_amount'] == 491
        assert 42 <= result['recovery_ratio'] <= 43  # ~42.7%
        assert result['drop_pct'] < 0  # negative
        assert result['rebound_pct'] > 0
        assert result['remaining_loss_pct'] < 0

    def test_full_recovery(self):
        """T-07: Full recovery (current == pre_crisis)."""
        result = calculate_recovery(6244, 5094, 6244)
        assert result['recovery_ratio'] == 100.0
        assert result['remaining_loss_pct'] == 0.0

    def test_no_recovery(self):
        """T-08: No recovery (current == bottom)."""
        result = calculate_recovery(6244, 5094, 5094)
        assert result['recovery_ratio'] == 0.0
        assert result['recovery_amount'] == 0

    def test_negative_overshoot(self):
        """T-09: Current below bottom (further decline)."""
        result = calculate_recovery(6244, 5094, 4900)
        assert result['recovery_ratio'] < 0

    def test_none_input(self):
        """T-10: None inputs return None."""
        assert calculate_recovery(None, 5094, 5585) is None
        assert calculate_recovery(6244, None, 5585) is None
        assert calculate_recovery(6244, 5094, None) is None


# ---------------------------------------------------------------------------
# TestClassifyStage
# ---------------------------------------------------------------------------

class TestClassifyStage:
    """T-11 ~ T-16: Stage classification tests."""

    def test_panic(self):
        """T-11: VIX 40 → Stage 1 (패닉)."""
        stage, name = classify_stage(40, 5)
        assert stage == 1
        assert name == '패닉'

    def test_rebound(self):
        """T-12: VIX 29 → Stage 2 (기술적 반등)."""
        stage, name = classify_stage(29, 40)
        assert stage == 2
        assert name == '기술적 반등'

    def test_stabilization(self):
        """T-13: VIX 22 → Stage 3 (안정화)."""
        stage, name = classify_stage(22, 60)
        assert stage == 3
        assert name == '안정화'

    def test_trend_recovery(self):
        """T-14: VIX 17 → Stage 4 (추세 회복)."""
        stage, name = classify_stage(17, 80)
        assert stage == 4
        assert name == '추세 회복'

    def test_full_recovery(self):
        """T-15: VIX 12 → Stage 5 (완전 회복)."""
        stage, name = classify_stage(12, 98)
        assert stage == 5
        assert name == '완전 회복'

    def test_fallback_to_ratio(self):
        """T-16: VIX 999 doesn't match any VIX range → fallback to recovery ratio 70 → Stage 3."""
        stage, name = classify_stage(999, 70)
        # VIX 999 exceeds all VIX ranges → falls back to recovery ratio
        assert stage == 3
        assert name == '안정화'


# ---------------------------------------------------------------------------
# TestCheckStage3Conditions
# ---------------------------------------------------------------------------

class TestCheckStage3Conditions:
    """T-17 ~ T-20: Stage 3 conditions check tests."""

    def _conditions(self):
        return {
            'conditions': [
                {'id': 'vix', 'name': 'VIX', 'operator': '<', 'threshold': 25},
                {'id': 'usdkrw_pct', 'name': 'USD/KRW', 'operator': '<', 'threshold': 3},
                {'id': 'cnn_fg', 'name': 'CNN F&G', 'operator': '>', 'threshold': 35},
                {'id': 'recovery_ratio', 'name': 'KOSPI 회복률', 'operator': '>', 'threshold': 60},
                {'id': 'daily_volatility', 'name': '일간 변동성', 'operator': '<', 'threshold': 3},
            ],
            'min_conditions_met': 4,
        }

    def test_all_met(self):
        """T-17: All conditions met → stage3_reached True."""
        values = {
            'vix': 20, 'usdkrw_pct': 1, 'cnn_fg': 50,
            'recovery_ratio': 70, 'daily_volatility': 1,
        }
        result = check_stage3_conditions(self._conditions(), values)
        assert result['met_count'] == 5
        assert result['stage3_reached'] is True

    def test_none_met(self):
        """T-18: No conditions met → stage3_reached False."""
        values = {
            'vix': 35, 'usdkrw_pct': 10, 'cnn_fg': 10,
            'recovery_ratio': 30, 'daily_volatility': 5,
        }
        result = check_stage3_conditions(self._conditions(), values)
        assert result['met_count'] == 0
        assert result['stage3_reached'] is False

    def test_partial_met(self):
        """T-19: 3 out of 5 met, need 4 → stage3_reached False."""
        values = {
            'vix': 20, 'usdkrw_pct': 1, 'cnn_fg': 50,
            'recovery_ratio': 30, 'daily_volatility': 5,
        }
        result = check_stage3_conditions(self._conditions(), values)
        assert result['met_count'] == 3
        assert result['stage3_reached'] is False

    def test_missing_values(self):
        """T-20: Missing values treated as not met."""
        values = {'vix': 20}  # Only VIX provided
        result = check_stage3_conditions(self._conditions(), values)
        assert result['met_count'] == 1


# ---------------------------------------------------------------------------
# TestClassifySignal
# ---------------------------------------------------------------------------

class TestClassifySignal:
    """T-21 ~ T-25: Signal classification tests."""

    def test_vix_green(self):
        """T-21: VIX 15 → green."""
        assert classify_signal('VIX', 15) == 'green'

    def test_vix_red(self):
        """T-22: VIX 45 → red."""
        assert classify_signal('VIX', 45) == 'red'

    def test_usdkrw_orange(self):
        """T-23: USD/KRW 1460 → orange (between 1450-1500)."""
        assert classify_signal('USDKRW', 1460) == 'orange'

    def test_recovery_low(self):
        """T-24: Recovery 15% → red."""
        assert classify_signal('RECOVERY', 15) == 'red'

    def test_recovery_high(self):
        """T-25: Recovery 85% → green."""
        assert classify_signal('RECOVERY', 85) == 'green'


# ---------------------------------------------------------------------------
# TestLoadRecoveryStages
# ---------------------------------------------------------------------------

class TestLoadRecoveryStages:
    """T-26 ~ T-27: Recovery stages loading tests."""

    def test_load_existing(self):
        """T-26: Load actual recovery_stages.json from references/."""
        stages = load_recovery_stages()
        assert isinstance(stages, dict)
        assert 'stages' in stages
        assert len(stages['stages']) == 5
        assert stages['stages'][0]['name'] == '패닉'

    def test_load_missing(self, tmp_path, monkeypatch):
        """T-27: Missing file returns default stages."""
        import recovery_tracker as mod
        monkeypatch.setattr(mod, '_STAGES_PATH', str(tmp_path / 'nonexistent.json'))
        result = mod.load_recovery_stages()
        assert 'stages' in result
        assert len(result['stages']) == 5


# ---------------------------------------------------------------------------
# TestBuildRecoveryAnalysis
# ---------------------------------------------------------------------------

class TestBuildRecoveryAnalysis:
    """T-28 ~ T-30: Recovery analysis builder tests."""

    def test_normal_analysis(self):
        """T-28: Normal analysis with all data."""
        data = {
            'KOSPI': {
                'current': 5585, 'prev': 5584, 'change_pct': 0.02,
                'period_high': 6244, 'period_low': 5094,
                'rsi': 52.69, 'recent_5d': [5700, 5792, 5094, 5584, 5585],
            },
            'VIX': {
                'current': 29.49, 'prev': 23.77, 'change_pct': 24.1,
                'period_high': 52, 'period_low': 12,
                'recent_5d': [28, 23, 24, 35, 29.49],
            },
            'EWY': {
                'current': 126.73, 'prev': 125.74, 'change_pct': 0.79,
                'period_high': 147, 'period_low': 110,
                'recent_5d': [140, 130, 120, 125, 126.73],
            },
            'USDKRW': {
                'current': 1484.59, 'prev': 1479, 'change_pct': 0.38,
                'period_high': 1500, 'period_low': 1350,
                'recent_5d': [1450, 1470, 1500, 1479, 1484.59],
            },
        }
        result = build_recovery_analysis(data, pre_crisis=6244, bottom=5094)
        assert result['stage'] == 2
        assert result['stage_name'] == '기술적 반등'
        assert result['recovery']['recovery_ratio'] > 40
        assert result['rsi'] == 52.69

    def test_auto_detect(self):
        """T-29: Auto-detect pre_crisis and bottom from period high/low."""
        data = {
            'KOSPI': {
                'current': 5585, 'prev': 5584, 'change_pct': 0.02,
                'period_high': 6244, 'period_low': 5094,
                'rsi': 52.69, 'recent_5d': [5585],
            },
            'VIX': {
                'current': 22, 'prev': 23, 'change_pct': -4.3,
                'period_high': 35, 'period_low': 12,
                'recent_5d': [22],
            },
            'EWY': {'current': 126, 'prev': 125, 'change_pct': 0.8,
                    'period_high': 147, 'period_low': 110, 'recent_5d': [126]},
            'USDKRW': {'current': 1400, 'prev': 1395, 'change_pct': 0.4,
                       'period_high': 1500, 'period_low': 1350, 'recent_5d': [1400]},
        }
        result = build_recovery_analysis(data)  # No pre_crisis/bottom
        assert result['recovery'] is not None
        assert result['recovery']['pre_crisis'] == 6244
        assert result['recovery']['bottom'] == 5094

    def test_all_errors(self):
        """T-30: All indicators error → still returns structure."""
        data = {
            'KOSPI': {'error': 'timeout'},
            'VIX': {'error': 'timeout'},
            'EWY': {'error': 'timeout'},
            'USDKRW': {'error': 'timeout'},
        }
        result = build_recovery_analysis(data)
        assert result['stage'] is not None
        assert result['recovery'] is None


# ---------------------------------------------------------------------------
# TestFormatChange
# ---------------------------------------------------------------------------

class TestFormatChange:
    """T-31 ~ T-32: Format helper tests."""

    def test_positive(self):
        """T-31: Positive change formats with + sign."""
        assert format_change(2.5) == "+2.50%"

    def test_none(self):
        """T-32: None returns dash."""
        assert format_change(None) == "-"
