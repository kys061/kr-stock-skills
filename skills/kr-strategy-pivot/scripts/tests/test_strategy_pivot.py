"""kr-strategy-pivot 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from detect_stagnation import (
    STAGNATION_TRIGGERS, DIAGNOSIS_OUTCOMES,
    MAX_DRAWDOWN_ABANDON, RISK_MGMT_CRITICAL,
    ABANDON_MIN_ITERATIONS, ABANDON_SCORE_THRESHOLD,
    check_improvement_plateau, check_overfitting_proxy,
    check_cost_defeat, check_tail_risk,
    run_all_triggers, determine_recommendation, diagnose,
)
from generate_pivots import (
    ARCHETYPE_CATALOG, INVERSION_MAP, REFRAME_MAP,
    generate_inversions, generate_archetype_switches,
    generate_reframes, identify_current_archetype,
    generate_all_pivots,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_stagnation_triggers_count(self):
        assert len(STAGNATION_TRIGGERS) == 4

    def test_diagnosis_outcomes(self):
        assert DIAGNOSIS_OUTCOMES == ['continue', 'pivot', 'abandon']

    def test_max_drawdown_abandon(self):
        assert MAX_DRAWDOWN_ABANDON == 35

    def test_risk_mgmt_critical(self):
        assert RISK_MGMT_CRITICAL == 5

    def test_abandon_min_iterations(self):
        assert ABANDON_MIN_ITERATIONS == 3

    def test_abandon_score_threshold(self):
        assert ABANDON_SCORE_THRESHOLD == 30

    def test_archetype_catalog_count(self):
        assert len(ARCHETYPE_CATALOG) == 8

    def test_inversion_map_keys(self):
        for key in ['cost_defeat', 'tail_risk_elevation',
                     'improvement_plateau', 'overfitting_proxy']:
            assert key in INVERSION_MAP

    def test_reframe_map_keys(self):
        for key in ['tail_risk_elevation', 'cost_defeat',
                     'improvement_plateau', 'overfitting_proxy']:
            assert key in REFRAME_MAP


# ─── 정체 트리거 ───

class TestImprovementPlateau:

    def test_plateau_detected(self):
        history = [
            {'composite_score': 55},
            {'composite_score': 56},
            {'composite_score': 55},
        ]
        result = check_improvement_plateau(history)
        assert result['fired'] is True

    def test_no_plateau(self):
        history = [
            {'composite_score': 50},
            {'composite_score': 60},
            {'composite_score': 70},
        ]
        result = check_improvement_plateau(history)
        assert result['fired'] is False

    def test_insufficient_data(self):
        history = [{'composite_score': 50}]
        result = check_improvement_plateau(history)
        assert result['fired'] is False


class TestOverfittingProxy:

    def test_overfitting_detected(self):
        latest = {
            'dimensions': {
                'expectancy': 18,
                'risk_management': 16,
                'robustness': 5,
            }
        }
        result = check_overfitting_proxy(latest)
        assert result['fired'] is True

    def test_no_overfitting(self):
        latest = {
            'dimensions': {
                'expectancy': 18,
                'risk_management': 16,
                'robustness': 15,
            }
        }
        result = check_overfitting_proxy(latest)
        assert result['fired'] is False


class TestCostDefeat:

    def test_cost_defeat_detected(self):
        latest = {
            'expectancy_pct': 0.1,
            'profit_factor': 1.1,
            'slippage_tested': True,
        }
        result = check_cost_defeat(latest)
        assert result['fired'] is True

    def test_no_cost_defeat(self):
        latest = {
            'expectancy_pct': 1.5,
            'profit_factor': 2.0,
            'slippage_tested': True,
        }
        result = check_cost_defeat(latest)
        assert result['fired'] is False


class TestTailRisk:

    def test_high_drawdown(self):
        latest = {
            'max_drawdown_pct': 40,
            'dimensions': {'risk_management': 10},
        }
        result = check_tail_risk(latest)
        assert result['fired'] is True

    def test_low_risk_mgmt_score(self):
        latest = {
            'max_drawdown_pct': 20,
            'dimensions': {'risk_management': 3},
        }
        result = check_tail_risk(latest)
        assert result['fired'] is True

    def test_safe(self):
        latest = {
            'max_drawdown_pct': 15,
            'dimensions': {'risk_management': 15},
        }
        result = check_tail_risk(latest)
        assert result['fired'] is False


# ─── 판정 ───

class TestDetermineRecommendation:

    def test_continue_no_triggers(self):
        triggers = [{'fired': False}, {'fired': False}]
        assert determine_recommendation([], triggers) == 'continue'

    def test_pivot_with_trigger(self):
        triggers = [{'fired': True}]
        assert determine_recommendation([{'composite_score': 50}],
                                         triggers) == 'pivot'

    def test_abandon_conditions(self):
        history = [
            {'composite_score': 28},
            {'composite_score': 25},
            {'composite_score': 22},
        ]
        triggers = [{'fired': True}]
        result = determine_recommendation(history, triggers)
        assert result == 'abandon'


# ─── 통합 진단 ───

class TestDiagnose:

    def test_diagnose_healthy(self):
        history = [
            {'composite_score': 60, 'dimensions': {
                'expectancy': 15, 'risk_management': 15, 'robustness': 15},
             'max_drawdown_pct': 10, 'expectancy_pct': 1.5,
             'profit_factor': 2.0, 'slippage_tested': True},
        ]
        result = diagnose(history)
        assert result['recommendation'] == 'continue'
        assert 'diagnosed_at' in result

    def test_diagnose_empty(self):
        result = diagnose([])
        assert result['recommendation'] == 'continue'
        assert result['iterations'] == 0


# ─── 피벗 생성 ───

class TestGenerateInversions:

    def test_cost_defeat_inversions(self):
        triggers = [{'trigger': 'cost_defeat', 'severity': 'HIGH'}]
        proposals = generate_inversions(triggers)
        assert len(proposals) == 2
        assert all(p['technique'] == 'assumption_inversion'
                   for p in proposals)

    def test_empty_triggers(self):
        assert generate_inversions([]) == []


class TestArchetypeSwitches:

    def test_breakout_switches(self):
        switches = generate_archetype_switches('trend_following_breakout')
        assert len(switches) == 2
        targets = [s['to_archetype'] for s in switches]
        assert 'mean_reversion_pullback' in targets

    def test_unknown_archetype(self):
        switches = generate_archetype_switches('unknown')
        assert len(switches) == 0


class TestGenerateReframes:

    def test_tail_risk_reframe(self):
        triggers = [{'trigger': 'tail_risk_elevation'}]
        reframes = generate_reframes(triggers)
        assert len(reframes) == 1
        assert 'max_drawdown_pct' in reframes[0]['new_objective']


class TestIdentifyArchetype:

    def test_breakout_match(self):
        draft = {'hypothesis_type': 'breakout',
                 'entry_family': 'pivot_breakout'}
        assert identify_current_archetype(draft) in [
            'trend_following_breakout', 'volatility_contraction']

    def test_fallback(self):
        draft = {'hypothesis_type': 'unknown'}
        result = identify_current_archetype(draft)
        assert result == 'trend_following_breakout'


# ─── 통합 피벗 생성 ───

class TestGenerateAllPivots:

    def test_with_diagnosis_and_draft(self):
        diagnosis = {
            'recommendation': 'pivot',
            'fired_triggers': [
                {'trigger': 'cost_defeat', 'severity': 'HIGH'},
            ],
        }
        draft = {
            'hypothesis_type': 'breakout',
            'entry_family': 'pivot_breakout',
        }
        result = generate_all_pivots(diagnosis, draft)
        assert result['recommendation'] == 'pivot'
        assert len(result['inversions']) >= 1
        assert len(result['archetype_switches']) >= 1
        assert len(result['reframes']) >= 1
        assert result['meta']['total_proposals'] > 0

    def test_empty_diagnosis(self):
        result = generate_all_pivots({'recommendation': 'continue',
                                       'fired_triggers': []})
        assert result['meta']['total_proposals'] == 0
