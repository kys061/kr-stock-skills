"""kr-strategy-synthesizer 테스트."""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from report_loader import (
    REPORT_CONFIG, REQUIRED_FIELDS, validate_report, load_skill_reports,
)
from conviction_scorer import (
    CONVICTION_COMPONENTS, CONVICTION_ZONES, KR_ADAPTATION,
    normalize_signal, calc_component_scores, calc_conviction_score,
)
from pattern_classifier import (
    MARKET_PATTERNS, classify_pattern,
)
from allocation_engine import (
    generate_allocation, apply_kr_adjustment,
)
from report_generator import StrategySynthesizerReportGenerator


# ═══════════════════════════════════════════════════════
# 1. 상수 테스트
# ═══════════════════════════════════════════════════════

class TestConstants:
    """상수 정의 검증."""

    def test_conviction_7_components(self):
        assert len(CONVICTION_COMPONENTS) == 7

    def test_conviction_weights_sum_1(self):
        total = sum(c['weight'] for c in CONVICTION_COMPONENTS.values())
        assert abs(total - 1.0) < 0.001

    def test_conviction_weights_match_design(self):
        assert CONVICTION_COMPONENTS['market_structure']['weight'] == 0.18
        assert CONVICTION_COMPONENTS['distribution_risk']['weight'] == 0.18
        assert CONVICTION_COMPONENTS['bottom_confirmation']['weight'] == 0.12
        assert CONVICTION_COMPONENTS['macro_alignment']['weight'] == 0.18
        assert CONVICTION_COMPONENTS['theme_quality']['weight'] == 0.12
        assert CONVICTION_COMPONENTS['setup_availability']['weight'] == 0.10
        assert CONVICTION_COMPONENTS['signal_convergence']['weight'] == 0.12

    def test_conviction_5_zones(self):
        assert len(CONVICTION_ZONES) == 5
        assert set(CONVICTION_ZONES.keys()) == {
            'MAXIMUM', 'HIGH', 'MODERATE', 'LOW', 'PRESERVATION',
        }

    def test_zone_thresholds(self):
        assert CONVICTION_ZONES['MAXIMUM']['min_score'] == 80
        assert CONVICTION_ZONES['HIGH']['min_score'] == 60
        assert CONVICTION_ZONES['MODERATE']['min_score'] == 40
        assert CONVICTION_ZONES['LOW']['min_score'] == 20
        assert CONVICTION_ZONES['PRESERVATION']['min_score'] == 0

    def test_market_patterns_4(self):
        assert len(MARKET_PATTERNS) == 4
        assert set(MARKET_PATTERNS.keys()) == {
            'POLICY_PIVOT', 'UNSUSTAINABLE_DISTORTION',
            'EXTREME_CONTRARIAN', 'WAIT_OBSERVE',
        }

    def test_kr_adaptation_5_keys(self):
        assert len(KR_ADAPTATION) == 5
        assert KR_ADAPTATION['foreign_flow_weight'] == 0.15
        assert KR_ADAPTATION['geopolitical_premium'] == 0.05

    def test_required_skills_8(self):
        assert len(REPORT_CONFIG['required_skills']) == 8

    def test_required_fields_all_skills(self):
        for skill in REPORT_CONFIG['required_skills']:
            assert skill in REQUIRED_FIELDS


# ═══════════════════════════════════════════════════════
# 2. 리포트 로더 테스트
# ═══════════════════════════════════════════════════════

class TestValidateReport:
    """리포트 유효성 검증 테스트."""

    def test_valid_report(self):
        report = {'breadth_score': 65, 'above_ma200_pct': 58}
        assert validate_report(report, 'kr-market-breadth') is True

    def test_missing_field(self):
        report = {'breadth_score': 65}
        assert validate_report(report, 'kr-market-breadth') is False

    def test_non_dict_report(self):
        assert validate_report('not a dict', 'kr-market-breadth') is False
        assert validate_report(None, 'kr-market-breadth') is False

    def test_unknown_skill_passes(self):
        assert validate_report({}, 'unknown-skill') is True


class TestLoadSkillReports:
    """리포트 로드 테스트."""

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_skill_reports(tmpdir)
            assert '_meta' in result
            assert len(result['_meta']['missing']) == 8

    def test_load_valid_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = {'breadth_score': 65, 'above_ma200_pct': 58}
            path = os.path.join(tmpdir, 'kr-market-breadth.json')
            with open(path, 'w') as f:
                json.dump(report, f)
            result = load_skill_reports(tmpdir)
            assert 'kr-market-breadth' in result
            assert 'kr-market-breadth' in result['_meta']['loaded']

    def test_coverage_calculation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_skill_reports(tmpdir)
            assert result['_meta']['coverage'] == 0.0


# ═══════════════════════════════════════════════════════
# 3. 정규화 테스트
# ═══════════════════════════════════════════════════════

class TestNormalizeSignal:
    """시그널 정규화 테스트."""

    def test_breadth_passthrough(self):
        assert normalize_signal(75, 'kr-market-breadth') == 75

    def test_breadth_clamp(self):
        assert normalize_signal(120, 'kr-market-breadth') == 100
        assert normalize_signal(-10, 'kr-market-breadth') == 0

    def test_top_risk_inverted(self):
        assert normalize_signal(80, 'kr-market-top-detector') == 20
        assert normalize_signal(20, 'kr-market-top-detector') == 80

    def test_ftd_confirmed(self):
        assert normalize_signal(True, 'kr-ftd-detector') == 70.0
        assert normalize_signal(False, 'kr-ftd-detector') == 30.0

    def test_macro_regime_mapping(self):
        assert normalize_signal('expansion', 'kr-macro-regime') == 85
        assert normalize_signal('contraction', 'kr-macro-regime') == 25
        assert normalize_signal('transitional', 'kr-macro-regime') == 50

    def test_theme_list_scoring(self):
        assert normalize_signal(['반도체', '자동차'], 'kr-theme-detector') == 50
        assert normalize_signal([], 'kr-theme-detector') == 20

    def test_screener_count_scoring(self):
        assert normalize_signal(['A', 'B', 'C'], 'kr-vcp-screener') == 40
        assert normalize_signal([], 'kr-vcp-screener') == 10

    def test_none_returns_50(self):
        assert normalize_signal(None, 'kr-market-breadth') == 50.0


# ═══════════════════════════════════════════════════════
# 4. 컴포넌트 스코어링 테스트
# ═══════════════════════════════════════════════════════

class TestComponentScores:
    """컴포넌트 점수 계산 테스트."""

    def _make_reports(self):
        return {
            'kr-market-breadth': {'breadth_score': 70, 'above_ma200_pct': 60},
            'kr-uptrend-analyzer': {'uptrend_score': 65, 'uptrend_ratio': 0.62},
            'kr-market-top-detector': {'top_risk_score': 30, 'distribution_days': 2},
            'kr-ftd-detector': {'ftd_confirmed': True, 'rally_day': 4},
            'kr-macro-regime': {'regime': 'expansion', 'transition_probability': 0.1},
            'kr-theme-detector': {'bullish_themes': ['반도체', '자동차', '2차전지'], 'bearish_themes': ['건설']},
            'kr-vcp-screener': {'vcp_candidates': ['A', 'B']},
            'kr-canslim-screener': {'canslim_candidates': ['C', 'D', 'E']},
        }

    def test_returns_7_components(self):
        reports = self._make_reports()
        components = calc_component_scores(reports)
        assert len(components) == 7

    def test_all_scores_in_range(self):
        reports = self._make_reports()
        components = calc_component_scores(reports)
        for name, comp in components.items():
            assert 0 <= comp['score'] <= 100, f'{name} out of range'

    def test_market_structure_average(self):
        reports = self._make_reports()
        components = calc_component_scores(reports)
        ms = components['market_structure']
        expected = (70 + 65) / 2
        assert ms['score'] == expected

    def test_distribution_risk_inverted(self):
        reports = self._make_reports()
        components = calc_component_scores(reports)
        dr = components['distribution_risk']
        assert dr['score'] == 70.0  # 100 - 30

    def test_convergence_high_when_aligned(self):
        reports = self._make_reports()
        components = calc_component_scores(reports)
        conv = components['signal_convergence']
        assert conv['score'] > 50  # All bullish → convergent


class TestConvictionScore:
    """확신도 종합 점수 테스트."""

    def test_high_conviction(self):
        components = {name: {'score': 80} for name in CONVICTION_COMPONENTS}
        result = calc_conviction_score(components)
        assert result['score'] >= 75
        assert result['zone'] in ('MAXIMUM', 'HIGH')

    def test_low_conviction(self):
        components = {name: {'score': 20} for name in CONVICTION_COMPONENTS}
        result = calc_conviction_score(components)
        assert result['score'] <= 25
        assert result['zone'] in ('LOW', 'PRESERVATION')

    def test_returns_zone_details(self):
        components = {name: {'score': 50} for name in CONVICTION_COMPONENTS}
        result = calc_conviction_score(components)
        assert 'zone_details' in result
        assert 'equity_range' in result['zone_details']
        assert 'max_single_position' in result['zone_details']

    def test_empty_components(self):
        result = calc_conviction_score({})
        assert result['score'] == 50.0


# ═══════════════════════════════════════════════════════
# 5. 패턴 분류 테스트
# ═══════════════════════════════════════════════════════

class TestPatternClassifier:
    """패턴 분류 테스트."""

    def test_policy_pivot(self):
        components = {}
        reports = {
            'kr-macro-regime': {'regime': 'transitional', 'transition_probability': 0.7},
            'kr-market-top-detector': {'top_risk_score': 30},
            'kr-ftd-detector': {'ftd_confirmed': False},
            'kr-market-breadth': {'breadth_score': 50},
        }
        result = classify_pattern(components, reports)
        assert result['pattern'] == 'POLICY_PIVOT'

    def test_unsustainable_distortion(self):
        components = {}
        reports = {
            'kr-macro-regime': {'regime': 'contraction', 'transition_probability': 0.2},
            'kr-market-top-detector': {'top_risk_score': 70},
            'kr-ftd-detector': {'ftd_confirmed': False},
            'kr-market-breadth': {'breadth_score': 50},
        }
        result = classify_pattern(components, reports)
        assert result['pattern'] == 'UNSUSTAINABLE_DISTORTION'

    def test_extreme_contrarian(self):
        components = {}
        reports = {
            'kr-macro-regime': {'regime': 'expansion', 'transition_probability': 0.1},
            'kr-market-top-detector': {'top_risk_score': 55},
            'kr-ftd-detector': {'ftd_confirmed': True},
            'kr-market-breadth': {'breadth_score': 30},
        }
        result = classify_pattern(components, reports)
        assert result['pattern'] == 'EXTREME_CONTRARIAN'

    def test_wait_observe_default(self):
        components = {}
        reports = {
            'kr-macro-regime': {'regime': 'expansion', 'transition_probability': 0.1},
            'kr-market-top-detector': {'top_risk_score': 20},
            'kr-ftd-detector': {'ftd_confirmed': False},
            'kr-market-breadth': {'breadth_score': 60},
        }
        result = classify_pattern(components, reports)
        assert result['pattern'] == 'WAIT_OBSERVE'

    def test_pattern_has_required_fields(self):
        result = classify_pattern({}, {})
        assert 'pattern' in result
        assert 'name' in result
        assert 'confidence' in result
        assert 'principle' in result
        assert 'equity_range' in result


# ═══════════════════════════════════════════════════════
# 6. 자산 배분 테스트
# ═══════════════════════════════════════════════════════

class TestAllocationEngine:
    """자산 배분 테스트."""

    def test_high_conviction_high_equity(self):
        conviction = {'score': 85, 'zone': 'MAXIMUM'}
        result = generate_allocation(conviction)
        assert result['equity'] >= 80

    def test_low_conviction_low_equity(self):
        conviction = {'score': 10, 'zone': 'PRESERVATION'}
        result = generate_allocation(conviction)
        assert result['equity'] <= 30

    def test_allocation_sums_to_100(self):
        conviction = {'score': 60, 'zone': 'HIGH'}
        result = generate_allocation(conviction)
        total = result['equity'] + result['bonds'] + result['alternatives'] + result['cash']
        assert abs(total - 100) < 0.5

    def test_pattern_override(self):
        conviction = {'score': 70, 'zone': 'HIGH'}
        pattern = {'equity_range': (30, 50)}
        result = generate_allocation(conviction, pattern)
        # Should be lower than without pattern
        result_no_pattern = generate_allocation(conviction)
        assert result['equity'] < result_no_pattern['equity']

    def test_max_single_position(self):
        conviction = {'score': 85, 'zone': 'MAXIMUM'}
        result = generate_allocation(conviction)
        assert result['max_single'] == 0.25


class TestKRAdjustment:
    """한국 시장 조정 테스트."""

    def test_no_signals_no_change(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc)
        assert result['equity'] == 70

    def test_foreign_buy_increases_equity(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc, {'foreign_flow': 'buy'})
        assert result['equity'] > 70

    def test_foreign_sell_decreases_equity(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc, {'foreign_flow': 'sell'})
        assert result['equity'] < 70

    def test_bok_cut_increases_equity(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc, {'bok_rate_direction': 'cut'})
        assert result['equity'] == 73.0

    def test_geopolitical_risk_decreases(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc, {'geopolitical_risk': True})
        assert result['equity'] < 70

    def test_equity_clamped_to_0_100(self):
        alloc = {'equity': 98, 'bonds': 1, 'alternatives': 0.5, 'cash': 0.5, 'max_single': 0.25}
        result = apply_kr_adjustment(alloc, {
            'foreign_flow': 'buy', 'bok_rate_direction': 'cut',
            'usd_krw_trend': 'weakening',
        })
        assert result['equity'] <= 100

    def test_adjusted_sums_to_100(self):
        alloc = {'equity': 70, 'bonds': 12, 'alternatives': 6, 'cash': 12, 'max_single': 0.15}
        result = apply_kr_adjustment(alloc, {
            'foreign_flow': 'buy', 'bok_rate_direction': 'cut',
        })
        total = result['equity'] + result['bonds'] + result['alternatives'] + result['cash']
        assert abs(total - 100) < 0.5


# ═══════════════════════════════════════════════════════
# 7. 리포트 생성기 테스트
# ═══════════════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성기 테스트."""

    def test_empty_report(self):
        gen = StrategySynthesizerReportGenerator()
        report = gen.generate()
        assert '전략 통합' in report

    def test_full_report(self):
        gen = StrategySynthesizerReportGenerator()
        gen.add_conviction({
            'score': 72.5,
            'zone': 'HIGH',
            'components': {
                'market_structure': {'score': 70, 'description': '시장 참여도'},
                'distribution_risk': {'score': 75, 'description': '분배 리스크'},
            },
            'zone_details': {
                'equity_range': (70, 90),
                'daily_vol': 0.003,
                'max_single_position': 0.15,
            },
        })
        gen.add_pattern({
            'pattern': 'POLICY_PIVOT',
            'name': '정책 전환 예측',
            'confidence': 70.0,
            'principle': '중앙은행과 유동성에 집중하라',
            'equity_range': (70, 90),
        })
        gen.add_allocation({
            'equity': 80.0,
            'bonds': 8.0,
            'alternatives': 4.0,
            'cash': 8.0,
            'max_single': 0.15,
        })
        gen.add_meta({
            'loaded': ['a', 'b', 'c'],
            'missing': ['d'],
            'stale': [],
            'total_required': 8,
        })
        report = gen.generate()
        assert 'HIGH' in report
        assert '72.5' in report
        assert 'POLICY_PIVOT' in report
        assert '80.0' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
