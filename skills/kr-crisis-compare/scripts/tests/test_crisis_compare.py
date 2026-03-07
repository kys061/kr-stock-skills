"""Tests for crisis_compare.py - Historical crisis pattern comparison."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crisis_compare import (
    HISTORICAL_CRISES,
    get_type_similarity,
    calculate_drawdown,
    calculate_decline_speed,
    classify_speed,
    dimension_similarity,
    calculate_overall_similarity,
    rank_crises_by_similarity,
    get_recovery_pattern,
    generate_scenarios,
    identify_unique_risks,
    format_pct,
    format_number,
)


class TestCalculateDrawdown:
    def test_normal_drawdown(self):
        assert calculate_drawdown(900, 1000) == -10.0

    def test_no_drawdown(self):
        assert calculate_drawdown(1000, 1000) == 0.0

    def test_above_peak(self):
        assert calculate_drawdown(1200, 1000) == 20.0

    def test_large_drawdown(self):
        assert calculate_drawdown(500, 1000) == -50.0

    def test_zero_peak(self):
        assert calculate_drawdown(100, 0) is None

    def test_negative_peak(self):
        assert calculate_drawdown(100, -10) is None


class TestCalculateDeclineSpeed:
    def test_normal(self):
        assert calculate_decline_speed(-20, 10) == 2.0

    def test_slow(self):
        assert calculate_decline_speed(-25, 250) == 0.1

    def test_flash(self):
        assert calculate_decline_speed(-15, 3) == 5.0

    def test_zero_days(self):
        assert calculate_decline_speed(-10, 0) is None

    def test_positive_drawdown_uses_abs(self):
        assert calculate_decline_speed(20, 10) == 2.0


class TestClassifySpeed:
    def test_flash(self):
        assert classify_speed(5) == 'flash'

    def test_rapid(self):
        assert classify_speed(23) == 'rapid'

    def test_moderate(self):
        assert classify_speed(60) == 'moderate'

    def test_gradual(self):
        assert classify_speed(155) == 'gradual'

    def test_prolonged(self):
        assert classify_speed(270) == 'prolonged'

    def test_boundary_10(self):
        assert classify_speed(10) == 'flash'

    def test_boundary_30(self):
        assert classify_speed(30) == 'rapid'

    def test_boundary_90(self):
        assert classify_speed(90) == 'moderate'

    def test_boundary_180(self):
        assert classify_speed(180) == 'gradual'


class TestDimensionSimilarity:
    def test_identical(self):
        assert dimension_similarity(50, 50, 25) == 100.0

    def test_half_scale(self):
        assert dimension_similarity(50, 75, 25) == 50.0

    def test_full_scale(self):
        assert dimension_similarity(50, 100, 25) == 0.0

    def test_beyond_scale(self):
        assert dimension_similarity(0, 100, 25) == 0.0

    def test_none_current(self):
        assert dimension_similarity(None, 50, 25) is None

    def test_none_historical(self):
        assert dimension_similarity(50, None, 25) is None

    def test_small_diff(self):
        result = dimension_similarity(45, 50, 25)
        assert 80 < result < 100

    def test_symmetric(self):
        assert dimension_similarity(30, 50, 25) == dimension_similarity(50, 30, 25)


class TestGetTypeSimilarity:
    def test_same_type(self):
        assert get_type_similarity('financial', 'financial') == 100

    def test_symmetric(self):
        assert (get_type_similarity('trade', 'geopolitical')
                == get_type_similarity('geopolitical', 'trade'))

    def test_financial_pandemic(self):
        assert get_type_similarity('financial', 'pandemic') == 30

    def test_trade_geopolitical(self):
        assert get_type_similarity('trade', 'geopolitical') == 60

    def test_monetary_trade(self):
        assert get_type_similarity('monetary', 'trade') == 55

    def test_all_same_types_100(self):
        for t in ['financial', 'pandemic', 'monetary', 'trade', 'geopolitical']:
            assert get_type_similarity(t, t) == 100


class TestOverallSimilarity:
    def test_identical_crisis(self):
        crisis = HISTORICAL_CRISES['covid_2020']
        current = {
            'vix': crisis['vix_peak'],
            'kospi_drop_pct': crisis['kospi_drop_pct'],
            'sp500_drop_pct': crisis['sp500_drop_pct'],
            'decline_speed': abs(crisis['kospi_drop_pct']) / crisis['days_to_bottom'],
            'crisis_type': crisis['crisis_type'],
        }
        score = calculate_overall_similarity(current, crisis)
        assert score == 100.0

    def test_very_different(self):
        crisis = HISTORICAL_CRISES['gfc_2008']
        current = {
            'vix': 15,
            'kospi_drop_pct': -2,
            'sp500_drop_pct': -1,
            'decline_speed': 0.1,
            'crisis_type': 'trade',
        }
        score = calculate_overall_similarity(current, crisis)
        assert score < 30

    def test_score_range(self):
        crisis = HISTORICAL_CRISES['tariff_2025']
        current = {
            'vix': 45,
            'kospi_drop_pct': -15,
            'sp500_drop_pct': -12,
            'decline_speed': 3.0,
            'crisis_type': 'geopolitical',
        }
        score = calculate_overall_similarity(current, crisis)
        assert 0 <= score <= 100

    def test_empty_current(self):
        crisis = HISTORICAL_CRISES['gfc_2008']
        score = calculate_overall_similarity({}, crisis)
        assert score == 0

    def test_partial_data(self):
        crisis = HISTORICAL_CRISES['covid_2020']
        current = {
            'vix': 80,
            'crisis_type': 'pandemic',
        }
        score = calculate_overall_similarity(current, crisis)
        assert score > 0

    def test_higher_similarity_for_closer_match(self):
        crisis = HISTORICAL_CRISES['tariff_2025']
        close = {
            'vix': 50,
            'kospi_drop_pct': -13,
            'sp500_drop_pct': -18,
            'decline_speed': 3.0,
            'crisis_type': 'trade',
        }
        far = {
            'vix': 85,
            'kospi_drop_pct': -50,
            'sp500_drop_pct': -55,
            'decline_speed': 0.3,
            'crisis_type': 'financial',
        }
        assert (calculate_overall_similarity(close, crisis)
                > calculate_overall_similarity(far, crisis))


class TestRankCrises:
    def test_returns_five(self):
        current = {
            'vix': 45,
            'kospi_drop_pct': -18,
            'sp500_drop_pct': -14,
            'decline_speed': 3.6,
            'crisis_type': 'geopolitical',
        }
        rankings = rank_crises_by_similarity(current)
        assert len(rankings) == 5

    def test_sorted_desc(self):
        current = {
            'vix': 50,
            'kospi_drop_pct': -20,
            'sp500_drop_pct': -15,
            'decline_speed': 2.0,
            'crisis_type': 'trade',
        }
        rankings = rank_crises_by_similarity(current)
        scores = [s for _, s, _ in rankings]
        assert scores == sorted(scores, reverse=True)

    def test_covid_matches_covid(self):
        crisis = HISTORICAL_CRISES['covid_2020']
        current = {
            'vix': crisis['vix_peak'],
            'kospi_drop_pct': crisis['kospi_drop_pct'],
            'sp500_drop_pct': crisis['sp500_drop_pct'],
            'decline_speed': abs(crisis['kospi_drop_pct']) / crisis['days_to_bottom'],
            'crisis_type': crisis['crisis_type'],
        }
        rankings = rank_crises_by_similarity(current)
        assert rankings[0][0] == 'covid_2020'

    def test_gfc_matches_gfc(self):
        crisis = HISTORICAL_CRISES['gfc_2008']
        current = {
            'vix': crisis['vix_peak'],
            'kospi_drop_pct': crisis['kospi_drop_pct'],
            'sp500_drop_pct': crisis['sp500_drop_pct'],
            'decline_speed': abs(crisis['kospi_drop_pct']) / crisis['days_to_bottom'],
            'crisis_type': crisis['crisis_type'],
        }
        rankings = rank_crises_by_similarity(current)
        assert rankings[0][0] == 'gfc_2008'

    def test_tariff_matches_tariff(self):
        crisis = HISTORICAL_CRISES['tariff_2025']
        current = {
            'vix': crisis['vix_peak'],
            'kospi_drop_pct': crisis['kospi_drop_pct'],
            'sp500_drop_pct': crisis['sp500_drop_pct'],
            'decline_speed': abs(crisis['kospi_drop_pct']) / crisis['days_to_bottom'],
            'crisis_type': crisis['crisis_type'],
        }
        rankings = rank_crises_by_similarity(current)
        assert rankings[0][0] == 'tariff_2025'


class TestGetRecoveryPattern:
    def test_gfc(self):
        pattern = get_recovery_pattern('gfc_2008')
        assert pattern is not None
        assert pattern['days_to_bottom'] == 155
        assert pattern['recovery_1w'] == 7.2
        assert pattern['speed_category'] == 'gradual'

    def test_covid(self):
        pattern = get_recovery_pattern('covid_2020')
        assert pattern['days_to_bottom'] == 23
        assert pattern['speed_category'] == 'rapid'
        assert pattern['recovery_1m'] == 24.1

    def test_iran_ongoing(self):
        pattern = get_recovery_pattern('iran_2026')
        assert pattern['recovery_1w'] is None
        assert pattern['recovery_1m'] is None
        assert pattern['recovery_3m'] is None

    def test_invalid_key(self):
        assert get_recovery_pattern('nonexistent') is None

    def test_rate_hike(self):
        pattern = get_recovery_pattern('rate_hike_2022')
        assert pattern['speed_category'] == 'prolonged'
        assert pattern['recovery_6m'] == 18.5


class TestGenerateScenarios:
    def test_basic_structure(self):
        current = {'kospi_current': 2200}
        scenarios = generate_scenarios('covid_2020', current)
        assert scenarios is not None
        assert 'optimistic' in scenarios
        assert 'base' in scenarios
        assert 'conservative' in scenarios

    def test_optimistic_gt_base_gt_conservative(self):
        current = {'kospi_current': 2200}
        scenarios = generate_scenarios('covid_2020', current)
        assert scenarios['optimistic']['kospi_1m'] > scenarios['base']['kospi_1m']
        assert scenarios['base']['kospi_1m'] > scenarios['conservative']['kospi_1m']
        assert scenarios['optimistic']['kospi_3m'] > scenarios['base']['kospi_3m']

    def test_base_uses_historical_recovery(self):
        current = {'kospi_current': 1000}
        scenarios = generate_scenarios('tariff_2025', current)
        expected_1m = round(1000 * (1 + 14.2 / 100))
        assert scenarios['base']['kospi_1m'] == expected_1m

    def test_ongoing_crisis_fallback(self):
        current = {'kospi_current': 2100}
        scenarios = generate_scenarios('iran_2026', current)
        assert scenarios is not None
        assert scenarios['base']['kospi_1m'] > 2100

    def test_no_kospi(self):
        scenarios = generate_scenarios('covid_2020', {})
        assert scenarios is None

    def test_invalid_key(self):
        scenarios = generate_scenarios('nonexistent', {'kospi_current': 2000})
        assert scenarios is None

    def test_recovery_factors(self):
        current = {'kospi_current': 2000}
        scenarios = generate_scenarios('covid_2020', current)
        assert scenarios['optimistic']['recovery_factor'] == 1.3
        assert scenarios['base']['recovery_factor'] == 1.0
        assert scenarios['conservative']['recovery_factor'] == 0.5


class TestIdentifyUniqueRisks:
    def test_basic(self):
        current = {'key_features': ['oil_spike', 'flight_to_safety', 'new_risk']}
        crisis = HISTORICAL_CRISES['iran_2026']
        result = identify_unique_risks(current, crisis)
        assert 'new_risk' in result['unique_to_current']
        assert 'oil_spike' in result['shared']

    def test_no_current_features(self):
        result = identify_unique_risks({}, HISTORICAL_CRISES['gfc_2008'])
        assert len(result['unique_to_current']) == 0
        assert len(result['unique_to_historical']) > 0

    def test_identical_features(self):
        crisis = HISTORICAL_CRISES['covid_2020']
        current = {'key_features': list(crisis['key_features'])}
        result = identify_unique_risks(current, crisis)
        assert len(result['unique_to_current']) == 0
        assert len(result['unique_to_historical']) == 0
        assert len(result['shared']) == 4

    def test_completely_different(self):
        current = {'key_features': ['unique_a', 'unique_b']}
        crisis = HISTORICAL_CRISES['gfc_2008']
        result = identify_unique_risks(current, crisis)
        assert len(result['shared']) == 0
        assert len(result['unique_to_current']) == 2
        assert len(result['unique_to_historical']) == 4


class TestFormatPct:
    def test_positive(self):
        assert format_pct(12.5) == "+12.5%"

    def test_negative(self):
        assert format_pct(-33.9) == "-33.9%"

    def test_zero(self):
        assert format_pct(0) == "+0.0%"

    def test_none(self):
        assert format_pct(None) == "진행중"


class TestFormatNumber:
    def test_integer(self):
        assert format_number(2500) == "2,500"

    def test_float(self):
        assert format_number(45.23) == "45.23"

    def test_none(self):
        assert format_number(None) == "-"

    def test_large(self):
        assert format_number(1234567) == "1,234,567"


class TestHistoricalDataIntegrity:
    def test_all_five_present(self):
        assert len(HISTORICAL_CRISES) == 5

    def test_required_fields(self):
        required = [
            'name', 'date', 'trigger', 'crisis_type', 'kospi_peak',
            'kospi_trough', 'kospi_drop_pct', 'vix_peak',
            'sp500_drop_pct', 'days_to_bottom', 'key_features',
        ]
        for key, crisis in HISTORICAL_CRISES.items():
            for field in required:
                assert field in crisis, f"{key} missing {field}"

    def test_valid_crisis_types(self):
        valid_types = {'financial', 'pandemic', 'monetary', 'trade', 'geopolitical'}
        for key, crisis in HISTORICAL_CRISES.items():
            assert crisis['crisis_type'] in valid_types, \
                f"{key} has invalid type {crisis['crisis_type']}"

    def test_drawdown_negative(self):
        for key, crisis in HISTORICAL_CRISES.items():
            assert crisis['kospi_drop_pct'] < 0, \
                f"{key} drawdown should be negative"

    def test_trough_less_than_peak(self):
        for key, crisis in HISTORICAL_CRISES.items():
            assert crisis['kospi_trough'] < crisis['kospi_peak'], \
                f"{key} trough should be less than peak"

    def test_recovery_keys_present(self):
        recovery_keys = [
            'recovery_1w_pct', 'recovery_1m_pct',
            'recovery_3m_pct', 'recovery_6m_pct',
        ]
        for key, crisis in HISTORICAL_CRISES.items():
            for rk in recovery_keys:
                assert rk in crisis, f"{key} missing {rk}"

    def test_completed_crises_have_recovery(self):
        completed = ['gfc_2008', 'covid_2020', 'rate_hike_2022', 'tariff_2025']
        for key in completed:
            crisis = HISTORICAL_CRISES[key]
            assert crisis['recovery_1m_pct'] is not None, \
                f"{key} should have recovery data"
            assert crisis['recovery_1m_pct'] > 0
