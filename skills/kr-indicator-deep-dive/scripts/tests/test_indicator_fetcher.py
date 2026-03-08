"""Tests for kr-indicator-deep-dive indicator_fetcher.py

Test coverage:
  TestCalculateRsi (5): basic, all_gains, all_losses, insufficient_data, empty
  TestClassifyZone (5): vix_zones(4), usdkrw, kospi_rsi, ewy_none
  TestClassifySignal (5): vix_signals(4), usdkrw, kospi_rsi_extreme
  TestHistoricalReturns (3): found, not_found, unknown_indicator
  TestBuildIndicatorAnalysis (5): normal, kospi_rsi, error, no_rsi, zone_none
  TestBuildDashboard (3): mixed_signals, all_errors, empty
  TestLoadHistoricalExtremes (2): exists, missing
  TestFormatChange (2): positive, none
  Total: 30 tests
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from indicator_fetcher import (
    calculate_rsi,
    classify_zone,
    classify_signal,
    get_historical_returns,
    build_indicator_analysis,
    build_dashboard,
    load_historical_extremes,
    format_change,
    INDICATOR_ZONES,
    HISTORICAL_RETURNS,
    SIGNAL_EMOJI,
    SIGNAL_LABEL_KR,
)


# ---------------------------------------------------------------------------
# TestCalculateRsi
# ---------------------------------------------------------------------------

class TestCalculateRsi:
    """T-01 ~ T-05: RSI calculation tests."""

    def test_basic_rsi(self):
        """T-01: RSI with mixed gains/losses returns value in 0-100."""
        # 20 days of alternating up/down with slight upward bias
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
        assert rsi < 5  # Should be very close to 0

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
# TestClassifyZone
# ---------------------------------------------------------------------------

class TestClassifyZone:
    """T-06 ~ T-10: Zone classification tests."""

    def test_vix_low(self):
        """T-06: VIX 12 → 하위 25% (안정)."""
        assert classify_zone('VIX', 12) == '하위 25% (안정)'

    def test_vix_normal(self):
        """T-07: VIX 17 → 25~50% (보통)."""
        assert classify_zone('VIX', 17) == '25~50% (보통)'

    def test_vix_elevated(self):
        """T-08: VIX 22 → 50~75% (경계)."""
        assert classify_zone('VIX', 22) == '50~75% (경계)'

    def test_vix_high(self):
        """T-09: VIX 35 → 상위 25% (공포)."""
        assert classify_zone('VIX', 35) == '상위 25% (공포)'

    def test_usdkrw_extreme(self):
        """T-10: USD/KRW 1450 → 위험 (극약세)."""
        assert classify_zone('USDKRW', 1450) == '위험 (극약세)'

    def test_kospi_rsi_oversold(self):
        """T-10b: KOSPI RSI 15 → 극단적 과매도."""
        assert classify_zone('KOSPI_RSI', 15) == '극단적 과매도'

    def test_ewy_no_zones(self):
        """T-10c: EWY has no zone definitions → None."""
        assert classify_zone('EWY', 120) is None


# ---------------------------------------------------------------------------
# TestClassifySignal
# ---------------------------------------------------------------------------

class TestClassifySignal:
    """T-11 ~ T-15: Signal classification tests."""

    def test_vix_green(self):
        """T-11: VIX 12 → green."""
        assert classify_signal('VIX', 12) == 'green'

    def test_vix_yellow(self):
        """T-12: VIX 20 → yellow."""
        assert classify_signal('VIX', 20) == 'yellow'

    def test_vix_orange(self):
        """T-13: VIX 30 → orange."""
        assert classify_signal('VIX', 30) == 'orange'

    def test_vix_red(self):
        """T-14: VIX 45 → red."""
        assert classify_signal('VIX', 45) == 'red'

    def test_usdkrw_red(self):
        """T-15: USD/KRW 1500 → red."""
        assert classify_signal('USDKRW', 1500) == 'red'

    def test_kospi_rsi_extreme_oversold(self):
        """T-15b: KOSPI RSI 14 → red (극단적 과매도)."""
        assert classify_signal('KOSPI_RSI', 14) == 'red'


# ---------------------------------------------------------------------------
# TestHistoricalReturns
# ---------------------------------------------------------------------------

class TestHistoricalReturns:
    """T-16 ~ T-18: Historical return lookup tests."""

    def test_vix_fear_zone(self):
        """T-16: VIX fear zone has 1w/1m/3m returns."""
        returns = get_historical_returns('VIX', '상위 25% (공포)')
        assert returns is not None
        assert '1w' in returns
        assert '1m' in returns
        assert '3m' in returns
        assert returns['3m']['avg'] == 5.4

    def test_unknown_zone(self):
        """T-17: Unknown zone returns None."""
        returns = get_historical_returns('VIX', '존재하지 않는 구간')
        assert returns is None

    def test_unknown_indicator(self):
        """T-18: Unknown indicator returns None."""
        returns = get_historical_returns('UNKNOWN', '아무거나')
        assert returns is None


# ---------------------------------------------------------------------------
# TestBuildIndicatorAnalysis
# ---------------------------------------------------------------------------

class TestBuildIndicatorAnalysis:
    """T-19 ~ T-23: Analysis builder tests."""

    def test_vix_analysis(self):
        """T-19: VIX analysis builds correctly with zone/signal."""
        data = {
            'current': 29.49, 'prev': 23.77, 'change_pct': 24.1,
            'recent_5d': [28.0, 23.57, 23.77, 35.0, 29.49],
            'week52_high': 52.33, 'week52_low': 12.5,
        }
        result = build_indicator_analysis('VIX', data)
        assert result['current'] == 29.49
        assert result['zone'] == '상위 25% (공포)'
        assert result['signal'] == 'orange'
        assert result['signal_emoji'] == '🟠'
        assert result['historical_returns'] is not None

    def test_kospi_with_rsi(self):
        """T-20: KOSPI analysis uses RSI for zone classification."""
        data = {
            'current': 5584.87, 'prev': 5600.0, 'change_pct': -0.27,
            'rsi': 14.88,
            'recent_5d': [5700, 5650, 5600, 5590, 5584.87],
            'week52_high': 6200, 'week52_low': 4800,
        }
        result = build_indicator_analysis('KOSPI', data)
        assert result['rsi'] == 14.88
        assert result['zone'] == '극단적 과매도'
        assert result['signal'] == 'red'

    def test_error_data(self):
        """T-21: Error data passes through."""
        data = {'error': 'Connection timeout'}
        result = build_indicator_analysis('VIX', data)
        assert 'error' in result
        assert result['error'] == 'Connection timeout'

    def test_kospi_no_rsi(self):
        """T-22: KOSPI without RSI data has None zone/signal."""
        data = {
            'current': 5584.87, 'prev': 5600.0, 'change_pct': -0.27,
            'recent_5d': [5584.87],
            'week52_high': 6200, 'week52_low': 4800,
        }
        result = build_indicator_analysis('KOSPI', data)
        assert result['zone'] is None
        assert result['signal'] is None

    def test_extremes_passed_through(self):
        """T-23: Historical extremes are included in analysis."""
        data = {
            'current': 25.0, 'prev': 24.0, 'change_pct': 4.17,
            'recent_5d': [25.0], 'week52_high': 50, 'week52_low': 10,
        }
        extremes = [{'rank': 1, 'date': '2020-03-16', 'value': 82.69}]
        result = build_indicator_analysis('VIX', data, extremes)
        assert len(result['extremes']) == 1
        assert result['extremes'][0]['value'] == 82.69


# ---------------------------------------------------------------------------
# TestBuildDashboard
# ---------------------------------------------------------------------------

class TestBuildDashboard:
    """T-24 ~ T-26: Dashboard builder tests."""

    def test_mixed_signals(self):
        """T-24: Dashboard correctly categorizes fear/stable signals."""
        analyses = [
            {'name': 'VIX', 'current': 35, 'signal': 'red'},
            {'name': 'EWY', 'current': 126, 'signal': 'green'},
            {'name': 'USDKRW', 'current': 1472, 'signal': 'orange'},
        ]
        dashboard = build_dashboard(analyses)
        assert len(dashboard['fear_signals']) == 1
        assert 'VIX' in dashboard['fear_signals'][0]
        assert len(dashboard['stable_signals']) == 1
        assert 'EWY' in dashboard['stable_signals'][0]
        assert len(dashboard['caution_signals']) == 1
        assert dashboard['total'] == 3
        assert dashboard['errors'] == 0

    def test_all_errors(self):
        """T-25: Dashboard handles all-error inputs."""
        analyses = [
            {'name': 'VIX', 'error': 'timeout'},
            {'name': 'EWY', 'error': 'no data'},
        ]
        dashboard = build_dashboard(analyses)
        assert dashboard['errors'] == 2
        assert len(dashboard['fear_signals']) == 0

    def test_empty(self):
        """T-26: Empty analyses list."""
        dashboard = build_dashboard([])
        assert dashboard['total'] == 0
        assert dashboard['errors'] == 0


# ---------------------------------------------------------------------------
# TestLoadHistoricalExtremes
# ---------------------------------------------------------------------------

class TestLoadHistoricalExtremes:
    """T-27 ~ T-28: Historical extremes loading tests."""

    def test_load_existing(self):
        """T-27: Load actual historical_extremes.json from references/."""
        extremes = load_historical_extremes()
        assert isinstance(extremes, dict)
        # Should have VIX, EWY, USDKRW, KOSPI at minimum
        assert 'VIX' in extremes
        assert len(extremes['VIX']) >= 5

    def test_load_missing(self, tmp_path, monkeypatch):
        """T-28: Missing file returns empty dict."""
        import indicator_fetcher as mod
        monkeypatch.setattr(mod, '_EXTREMES_PATH', str(tmp_path / 'nonexistent.json'))
        result = mod.load_historical_extremes()
        assert result == {}


# ---------------------------------------------------------------------------
# TestFormatChange
# ---------------------------------------------------------------------------

class TestFormatChange:
    """T-29 ~ T-30: Format helper tests."""

    def test_positive(self):
        """T-29: Positive change formats with + sign."""
        assert format_change(2.5) == "+2.50%"

    def test_none(self):
        """T-30: None returns dash."""
        assert format_change(None) == "-"
