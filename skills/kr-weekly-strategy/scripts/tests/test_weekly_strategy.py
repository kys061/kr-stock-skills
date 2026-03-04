"""kr-weekly-strategy 테스트."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from market_environment import (
    MARKET_PHASES, KR_WEEKLY_CHECKLIST, ENVIRONMENT_WEIGHTS,
    classify_market_phase, generate_weekly_checklist,
)
from sector_strategy import (
    KR_SECTORS, WEEKLY_CONSTRAINTS,
    calc_sector_scores, recommend_sector_allocation,
    apply_rotation_constraints,
)
from weekly_planner import (
    WEEKLY_SECTIONS, generate_scenarios, generate_weekly_plan,
)
from report_generator import generate_weekly_report


# ═══════════════════════════════════════════════════════
# 1. 상수 테스트
# ═══════════════════════════════════════════════════════

class TestConstants:
    """상수 정의 검증."""

    def test_market_phases_4(self):
        assert len(MARKET_PHASES) == 4
        assert set(MARKET_PHASES.keys()) == {'RISK_ON', 'BASE', 'CAUTION', 'STRESS'}

    def test_market_phases_equity_targets(self):
        assert MARKET_PHASES['RISK_ON']['equity_target'] == (80, 100)
        assert MARKET_PHASES['BASE']['equity_target'] == (60, 80)
        assert MARKET_PHASES['CAUTION']['equity_target'] == (40, 60)
        assert MARKET_PHASES['STRESS']['equity_target'] == (10, 40)

    def test_weekly_checklist_8(self):
        assert len(KR_WEEKLY_CHECKLIST) == 8

    def test_checklist_items(self):
        expected = [
            'kospi_kosdaq_trend', 'foreign_net_flow', 'institutional_net_flow',
            'bok_rate_decision', 'major_earnings', 'dart_disclosures',
            'geopolitical_events', 'usd_krw_trend',
        ]
        assert KR_WEEKLY_CHECKLIST == expected

    def test_kr_sectors_14(self):
        assert len(KR_SECTORS) == 14

    def test_kr_sectors_content(self):
        assert '반도체' in KR_SECTORS
        assert '자동차' in KR_SECTORS
        assert '2차전지' in KR_SECTORS
        assert '방산' in KR_SECTORS

    def test_weekly_sections_6(self):
        assert len(WEEKLY_SECTIONS) == 6

    def test_weekly_constraints(self):
        assert WEEKLY_CONSTRAINTS['max_sector_change_pct'] == 0.15
        assert WEEKLY_CONSTRAINTS['max_cash_change_pct'] == 0.15
        assert WEEKLY_CONSTRAINTS['continuity_required'] is True

    def test_environment_weights_sum_1(self):
        total = sum(ENVIRONMENT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


# ═══════════════════════════════════════════════════════
# 2. 시장 환경 분류 테스트
# ═══════════════════════════════════════════════════════

class TestClassifyMarketPhase:
    """시장 환경 분류 테스트."""

    def test_risk_on(self):
        indicators = {
            'kospi_trend': 'up',
            'foreign_flow': 'buy',
            'macro_regime': 'expansion',
            'usd_krw': 'stable',
            'breadth_score': 75,
            'vix_kr': 12,
        }
        result = classify_market_phase(indicators)
        assert result['phase'] == 'RISK_ON'
        assert result['score'] >= 70

    def test_stress(self):
        indicators = {
            'kospi_trend': 'down',
            'foreign_flow': 'sell',
            'macro_regime': 'contraction',
            'usd_krw': 'crisis',
            'breadth_score': 20,
            'vix_kr': 35,
        }
        result = classify_market_phase(indicators)
        assert result['phase'] == 'STRESS'
        assert result['score'] < 35

    def test_base(self):
        indicators = {
            'kospi_trend': 'sideways',
            'foreign_flow': 'neutral',
            'macro_regime': 'transitional',
            'usd_krw': 'stable',
            'breadth_score': 50,
        }
        result = classify_market_phase(indicators)
        assert result['phase'] in ('BASE', 'CAUTION')

    def test_default_values(self):
        result = classify_market_phase({})
        assert result['phase'] in MARKET_PHASES
        assert 'equity_target' in result
        assert 'cash_target' in result

    def test_returns_all_fields(self):
        result = classify_market_phase({'kospi_trend': 'up'})
        assert 'phase' in result
        assert 'description' in result
        assert 'equity_target' in result
        assert 'cash_target' in result
        assert 'score' in result


class TestWeeklyChecklist:
    """주간 체크리스트 테스트."""

    def test_all_missing(self):
        checklist = generate_weekly_checklist({})
        assert len(checklist) == 8
        assert all(c['status'] == 'missing' for c in checklist)

    def test_partial_data(self):
        data = {
            'kospi_kosdaq_trend': {'kospi': '+1.2%', 'kosdaq': '-0.3%'},
            'foreign_net_flow': 500_000_000_000,
        }
        checklist = generate_weekly_checklist(data)
        checked = [c for c in checklist if c['status'] == 'checked']
        assert len(checked) == 2

    def test_full_data(self):
        data = {item: 'test' for item in KR_WEEKLY_CHECKLIST}
        checklist = generate_weekly_checklist(data)
        assert all(c['status'] == 'checked' for c in checklist)


# ═══════════════════════════════════════════════════════
# 3. 섹터 전략 테스트
# ═══════════════════════════════════════════════════════

class TestSectorScores:
    """섹터 점수 계산 테스트."""

    def test_all_sectors_scored(self):
        data = {s: {'momentum': 10, 'foreign_flow': 50, 'earnings_revision': 5, 'theme_score': 60}
                for s in KR_SECTORS}
        scores = calc_sector_scores(data)
        assert len(scores) == 14

    def test_scores_in_range(self):
        data = {s: {'momentum': 10, 'foreign_flow': 50} for s in KR_SECTORS}
        scores = calc_sector_scores(data)
        for sector, s in scores.items():
            assert 0 <= s['score'] <= 100

    def test_ranking_assigned(self):
        data = {'반도체': {'momentum': 80}, '자동차': {'momentum': 20}}
        scores = calc_sector_scores(data)
        assert scores['반도체']['rank'] < scores['자동차']['rank']

    def test_strong_momentum_signal(self):
        data = {'반도체': {'momentum': 50, 'foreign_flow': 300}}
        scores = calc_sector_scores(data)
        signals = scores['반도체']['signals']
        assert '강한 모멘텀' in signals
        assert '외국인 매수' in signals

    def test_empty_data(self):
        scores = calc_sector_scores({})
        assert len(scores) == 14
        for s in scores.values():
            assert s['score'] >= 0


class TestSectorAllocation:
    """섹터 비중 추천 테스트."""

    def test_top5_allocated(self):
        data = {s: {'momentum': i * 5, 'foreign_flow': i * 10}
                for i, s in enumerate(KR_SECTORS, 1)}
        scores = calc_sector_scores(data)
        result = recommend_sector_allocation(scores)
        allocations = result['allocations']
        non_zero = {s: a for s, a in allocations.items() if a > 0}
        assert len(non_zero) == 5

    def test_allocations_sum_near_100(self):
        data = {s: {'momentum': 20} for s in KR_SECTORS}
        scores = calc_sector_scores(data)
        result = recommend_sector_allocation(scores)
        total = sum(result['allocations'].values())
        assert abs(total - 100) < 1

    def test_with_previous_allocation(self):
        data = {s: {'momentum': 20} for s in KR_SECTORS}
        scores = calc_sector_scores(data)
        prev = {'반도체': 30, '자동차': 25, '바이오/제약': 20, '금융/은행': 15, '2차전지': 10}
        result = recommend_sector_allocation(scores, prev)
        assert 'constrained' in result


class TestRotationConstraints:
    """로테이션 제약 테스트."""

    def test_large_change_constrained(self):
        new_alloc = {'반도체': 50, '자동차': 30, '바이오/제약': 20}
        prev_alloc = {'반도체': 20, '자동차': 30, '바이오/제약': 50}
        for s in KR_SECTORS:
            if s not in new_alloc:
                new_alloc[s] = 0
            if s not in prev_alloc:
                prev_alloc[s] = 0
        result, constrained = apply_rotation_constraints(new_alloc, prev_alloc, 0.15)
        assert len(constrained) > 0
        # Change should be limited to ±15%
        for s in constrained:
            assert abs(result[s] - prev_alloc[s]) <= 15.5  # Small tolerance for rounding

    def test_small_change_not_constrained(self):
        new_alloc = {s: 7.14 for s in KR_SECTORS}
        prev_alloc = {s: 7.14 for s in KR_SECTORS}
        result, constrained = apply_rotation_constraints(new_alloc, prev_alloc, 0.15)
        assert len(constrained) == 0


# ═══════════════════════════════════════════════════════
# 4. 시나리오 테스트
# ═══════════════════════════════════════════════════════

class TestGenerateScenarios:
    """시나리오 생성 테스트."""

    def test_all_phases(self):
        for phase in ('RISK_ON', 'BASE', 'CAUTION', 'STRESS'):
            scenarios = generate_scenarios(phase)
            assert 'base' in scenarios
            assert 'bull' in scenarios
            assert 'bear' in scenarios

    def test_probabilities_sum_to_100(self):
        for phase in ('RISK_ON', 'BASE', 'CAUTION', 'STRESS'):
            scenarios = generate_scenarios(phase)
            total = sum(s['probability'] for s in scenarios.values())
            assert total == 100

    def test_scenario_has_actions(self):
        scenarios = generate_scenarios('RISK_ON')
        for s in scenarios.values():
            assert len(s['actions']) > 0

    def test_stress_higher_bear_probability(self):
        scenarios = generate_scenarios('STRESS')
        assert scenarios['bear']['probability'] > scenarios['bull']['probability']


# ═══════════════════════════════════════════════════════
# 5. 주간 계획 통합 테스트
# ═══════════════════════════════════════════════════════

class TestWeeklyPlan:
    """주간 계획 통합 테스트."""

    def test_generate_full_plan(self):
        env = {
            'phase': 'BASE',
            'description': '보통 (횡보장)',
            'equity_target': (60, 80),
            'cash_target': (10, 20),
            'score': 55,
        }
        sectors = {
            'allocations': {'반도체': 30, '자동차': 25, '바이오/제약': 20,
                           '금융/은행': 15, '2차전지': 10},
            'changes': {'반도체': {'from': 25, 'to': 30, 'change': 5}},
        }
        scenarios = generate_scenarios('BASE')
        plan = generate_weekly_plan(env, sectors, scenarios)

        assert 'summary' in plan
        assert 'action' in plan
        assert 'scenarios' in plan
        assert 'sectors' in plan
        assert 'risks' in plan
        assert 'guide' in plan

    def test_summary_has_3_lines(self):
        env = {'phase': 'BASE', 'description': 'test', 'equity_target': (60, 80), 'score': 55}
        plan = generate_weekly_plan(env, {'allocations': {}}, {})
        assert len(plan['summary']) == 3

    def test_caution_has_high_priority_risks(self):
        env = {'phase': 'CAUTION', 'description': 'test',
               'equity_target': (40, 60), 'cash_target': (20, 35), 'score': 40}
        plan = generate_weekly_plan(env, {'allocations': {}}, {})
        high_risks = [r for r in plan['risks'] if r['priority'] == 'high']
        assert len(high_risks) >= 2


# ═══════════════════════════════════════════════════════
# 6. 리포트 생성 테스트
# ═══════════════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성 테스트."""

    def test_generates_report(self):
        plan = {
            'summary': ['시장 상태: BASE', '환경 점수: 55/100', '주식 목표: 60-80%'],
            'action': ['현재 비중 유지', '종목 교체 검토'],
            'scenarios': {
                'base': {'probability': 50, 'description': '횡보', 'actions': ['유지']},
                'bull': {'probability': 25, 'description': '상승', 'actions': ['확대']},
                'bear': {'probability': 25, 'description': '하락', 'actions': ['축소']},
            },
            'sectors': {
                'top': [('반도체', 30), ('자동차', 25)],
                'allocations': {'반도체': 30, '자동차': 25},
                'changes': {'반도체': {'from': 25, 'to': 30, 'change': 5}},
            },
            'risks': [
                {'type': 'position_size', 'description': '단일 종목 15% 초과 금지', 'priority': 'medium'},
            ],
            'guide': {
                'frequency': '주 2회 체크',
                'actions': ['관망 위주'],
                'warnings': ['소음에 흔들리지 말 것'],
            },
        }
        report = generate_weekly_report(plan)
        assert '주간 전략' in report
        assert 'BASE' in report
        assert '반도체' in report
        assert '시나리오' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
