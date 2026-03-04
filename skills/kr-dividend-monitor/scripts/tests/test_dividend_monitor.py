"""kr-dividend-monitor 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trigger_detector import (
    REVIEW_TRIGGERS, MONITOR_STATES, STATE_TRANSITIONS, DART_MONITORING,
    detect_dividend_cut, detect_dividend_suspension,
    detect_earnings_deterioration, detect_payout_danger,
    detect_governance_issue, run_all_triggers, determine_state,
)
from safety_scorer import (
    SAFETY_SCORING, SAFETY_GRADES,
    calc_payout_score, calc_earnings_stability_score,
    calc_dividend_history_score, calc_debt_health_score,
    calc_safety_score,
)
from report_generator import DividendMonitorReportGenerator


# ═══════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════

class TestConstants:
    """상수 검증."""

    def test_review_triggers_count(self):
        assert len(REVIEW_TRIGGERS) == 5

    def test_trigger_ids(self):
        expected = {'T1_DIVIDEND_CUT', 'T2_DIVIDEND_SUSPENSION',
                    'T3_EARNINGS_DETERIORATION', 'T4_PAYOUT_DANGER',
                    'T5_GOVERNANCE_ISSUE'}
        assert set(REVIEW_TRIGGERS.keys()) == expected

    def test_trigger_severities(self):
        assert REVIEW_TRIGGERS['T1_DIVIDEND_CUT']['severity'] == 'CRITICAL'
        assert REVIEW_TRIGGERS['T2_DIVIDEND_SUSPENSION']['severity'] == 'CRITICAL'
        assert REVIEW_TRIGGERS['T3_EARNINGS_DETERIORATION']['severity'] == 'HIGH'
        assert REVIEW_TRIGGERS['T4_PAYOUT_DANGER']['severity'] == 'HIGH'
        assert REVIEW_TRIGGERS['T5_GOVERNANCE_ISSUE']['severity'] == 'MEDIUM'

    def test_monitor_states(self):
        assert MONITOR_STATES == ['OK', 'WARN', 'REVIEW', 'EXIT_REVIEW']

    def test_state_transitions_ok(self):
        t = STATE_TRANSITIONS['OK']
        assert t['T3_minor'] == 'WARN'
        assert t['T4'] == 'WARN'
        assert t['T1'] == 'REVIEW'
        assert t['T2'] == 'EXIT_REVIEW'

    def test_state_transitions_warn(self):
        t = STATE_TRANSITIONS['WARN']
        assert t['resolved'] == 'OK'
        assert t['T1'] == 'REVIEW'
        assert t['T2'] == 'EXIT_REVIEW'

    def test_state_transitions_review(self):
        t = STATE_TRANSITIONS['REVIEW']
        assert t['resolved'] == 'OK'
        assert t['T2'] == 'EXIT_REVIEW'

    def test_dart_monitoring_types(self):
        assert len(DART_MONITORING) == 4
        assert 'dividend_disclosure' in DART_MONITORING
        assert DART_MONITORING['dividend_disclosure']['kind'] == 'B'
        assert DART_MONITORING['earnings_report']['kind'] == 'A'

    def test_t3_thresholds(self):
        t = REVIEW_TRIGGERS['T3_EARNINGS_DETERIORATION']['thresholds']
        assert t['earnings_decline_pct'] == -0.50
        assert t['consecutive_decline'] == 2

    def test_t4_threshold(self):
        assert REVIEW_TRIGGERS['T4_PAYOUT_DANGER']['threshold'] == 1.00

    def test_t5_subtypes(self):
        subtypes = REVIEW_TRIGGERS['T5_GOVERNANCE_ISSUE']['subtypes']
        assert len(subtypes) == 4
        assert 'major_shareholder_sale' in subtypes
        assert 'audit_qualified' in subtypes

    def test_safety_scoring_weights_sum(self):
        total = sum(v['weight'] for v in SAFETY_SCORING.values())
        assert abs(total - 1.0) < 1e-9

    def test_safety_grades(self):
        assert SAFETY_GRADES['SAFE'] == 80
        assert SAFETY_GRADES['MODERATE'] == 60
        assert SAFETY_GRADES['AT_RISK'] == 40
        assert SAFETY_GRADES['DANGEROUS'] == 0


# ═══════════════════════════════════════════════
# T1: Dividend Cut Tests
# ═══════════════════════════════════════════════

class TestT1DividendCut:
    """T1 감배 감지 테스트."""

    def test_cut_detected(self):
        result = detect_dividend_cut(800, 1200)
        assert result['detected'] is True
        assert result['trigger'] == 'T1_DIVIDEND_CUT'
        assert result['severity'] == 'CRITICAL'

    def test_no_cut(self):
        result = detect_dividend_cut(1500, 1200)
        assert result['detected'] is False

    def test_same_dps(self):
        result = detect_dividend_cut(1200, 1200)
        assert result['detected'] is False

    def test_zero_prev(self):
        result = detect_dividend_cut(500, 0)
        assert result['detected'] is False


# ═══════════════════════════════════════════════
# T2: Dividend Suspension Tests
# ═══════════════════════════════════════════════

class TestT2DividendSuspension:
    """T2 무배당 전환 테스트."""

    def test_suspension_detected(self):
        result = detect_dividend_suspension(0, 1000)
        assert result['detected'] is True
        assert result['trigger'] == 'T2_DIVIDEND_SUSPENSION'

    def test_no_suspension(self):
        result = detect_dividend_suspension(1000, 1000)
        assert result['detected'] is False

    def test_both_zero(self):
        result = detect_dividend_suspension(0, 0)
        assert result['detected'] is False


# ═══════════════════════════════════════════════
# T3: Earnings Deterioration Tests
# ═══════════════════════════════════════════════

class TestT3EarningsDeterioration:
    """T3 실적 악화 테스트."""

    def test_operating_loss(self):
        result = detect_earnings_deterioration(-100, 500)
        assert result['detected'] is True
        assert result['sub_type'] == 'T3_major'

    def test_50pct_decline(self):
        result = detect_earnings_deterioration(200, 500)
        assert result['detected'] is True
        assert result['sub_type'] == 'T3_major'

    def test_minor_decline(self):
        result = detect_earnings_deterioration(400, 500)
        assert result['detected'] is True
        assert result['sub_type'] == 'T3_minor'

    def test_consecutive_loss(self):
        result = detect_earnings_deterioration(100, 100, quarters=[-10, -20])
        assert result['detected'] is True
        assert result['sub_type'] == 'T3_major'

    def test_no_deterioration(self):
        result = detect_earnings_deterioration(600, 500)
        assert result['detected'] is False


# ═══════════════════════════════════════════════
# T4: Payout Danger Tests
# ═══════════════════════════════════════════════

class TestT4PayoutDanger:
    """T4 배당성향 위험 테스트."""

    def test_danger_detected(self):
        result = detect_payout_danger(1.20)
        assert result['detected'] is True
        assert result['trigger'] == 'T4_PAYOUT_DANGER'

    def test_safe(self):
        result = detect_payout_danger(0.50)
        assert result['detected'] is False

    def test_boundary(self):
        result = detect_payout_danger(1.00)
        assert result['detected'] is False

    def test_just_over(self):
        result = detect_payout_danger(1.01)
        assert result['detected'] is True


# ═══════════════════════════════════════════════
# T5: Governance Issue Tests
# ═══════════════════════════════════════════════

class TestT5GovernanceIssue:
    """T5 지배구조 이슈 테스트."""

    def test_shareholder_sale(self):
        result = detect_governance_issue('major_shareholder_sale', True)
        assert result['detected'] is True
        assert result['trigger'] == 'T5_GOVERNANCE_ISSUE'

    def test_audit_qualified(self):
        result = detect_governance_issue('audit_qualified', True)
        assert result['detected'] is True

    def test_no_issue(self):
        result = detect_governance_issue('major_shareholder_sale', False)
        assert result['detected'] is False

    def test_invalid_type(self):
        result = detect_governance_issue('unknown_type', True)
        assert result['detected'] is False


# ═══════════════════════════════════════════════
# Run All Triggers Tests
# ═══════════════════════════════════════════════

class TestRunAllTriggers:
    """전체 트리거 실행 테스트."""

    def test_no_triggers(self):
        data = {
            'current_dps': 1500, 'prev_dps': 1400,
            'current_op': 600, 'prev_op': 500,
            'payout_ratio': 0.40,
        }
        results = run_all_triggers(data)
        assert len(results) == 0

    def test_multiple_triggers(self):
        data = {
            'current_dps': 0, 'prev_dps': 1000,
            'current_op': -100, 'prev_op': 500,
            'payout_ratio': 1.50,
            'has_governance_issue': True,
            'governance_issue_type': 'audit_qualified',
        }
        results = run_all_triggers(data)
        assert len(results) >= 3

    def test_only_minor(self):
        data = {
            'current_dps': 1200, 'prev_dps': 1000,
            'current_op': 450, 'prev_op': 500,
            'payout_ratio': 0.60,
        }
        results = run_all_triggers(data)
        triggers = [r['trigger'] for r in results]
        assert 'T1_DIVIDEND_CUT' not in triggers
        assert 'T2_DIVIDEND_SUSPENSION' not in triggers


# ═══════════════════════════════════════════════
# State Machine Tests
# ═══════════════════════════════════════════════

class TestStateMachine:
    """상태 전이 테스트."""

    def test_ok_no_triggers(self):
        assert determine_state('OK', []) == 'OK'

    def test_ok_to_warn_minor(self):
        triggers = [{'trigger': 'T3_EARNINGS_DETERIORATION', 'sub_type': 'T3_minor'}]
        assert determine_state('OK', triggers) == 'WARN'

    def test_ok_to_review_t1(self):
        triggers = [{'trigger': 'T1_DIVIDEND_CUT'}]
        assert determine_state('OK', triggers) == 'REVIEW'

    def test_ok_to_exit_review_t2(self):
        triggers = [{'trigger': 'T2_DIVIDEND_SUSPENSION'}]
        assert determine_state('OK', triggers) == 'EXIT_REVIEW'

    def test_warn_resolved(self):
        assert determine_state('WARN', []) == 'OK'

    def test_warn_to_review(self):
        triggers = [{'trigger': 'T1_DIVIDEND_CUT'}]
        assert determine_state('WARN', triggers) == 'REVIEW'

    def test_review_resolved(self):
        assert determine_state('REVIEW', []) == 'OK'

    def test_review_to_exit(self):
        triggers = [{'trigger': 'T2_DIVIDEND_SUSPENSION'}]
        assert determine_state('REVIEW', triggers) == 'EXIT_REVIEW'

    def test_t2_highest_priority(self):
        triggers = [
            {'trigger': 'T1_DIVIDEND_CUT'},
            {'trigger': 'T2_DIVIDEND_SUSPENSION'},
            {'trigger': 'T4_PAYOUT_DANGER'},
        ]
        assert determine_state('OK', triggers) == 'EXIT_REVIEW'


# ═══════════════════════════════════════════════
# Safety Score Tests
# ═══════════════════════════════════════════════

class TestPayoutScore:
    def test_safe(self):
        assert calc_payout_score(0.40) == 100

    def test_caution(self):
        score = calc_payout_score(0.60)
        assert 70 <= score <= 100

    def test_warning(self):
        score = calc_payout_score(0.85)
        assert 40 <= score < 70

    def test_danger(self):
        score = calc_payout_score(1.10)
        assert score == 0

    def test_zero_payout(self):
        assert calc_payout_score(0) == 0


class TestEarningsStabilityScore:
    def test_excellent(self):
        assert calc_earnings_stability_score(5) == 100

    def test_good(self):
        score = calc_earnings_stability_score(4)
        assert 50 < score < 100

    def test_minimum(self):
        score = calc_earnings_stability_score(3)
        assert score == 50

    def test_below_min(self):
        score = calc_earnings_stability_score(1)
        assert 0 < score < 50

    def test_zero(self):
        assert calc_earnings_stability_score(0) == 0


class TestDividendHistoryScore:
    def test_excellent(self):
        assert calc_dividend_history_score(10) == 100

    def test_good(self):
        score = calc_dividend_history_score(7)
        assert 70 < score < 100

    def test_minimum(self):
        score = calc_dividend_history_score(3)
        assert 40 <= score <= 70

    def test_below_min(self):
        score = calc_dividend_history_score(1)
        assert 0 < score < 40

    def test_zero(self):
        assert calc_dividend_history_score(0) == 0


class TestDebtHealthScore:
    def test_safe(self):
        assert calc_debt_health_score(0.50) == 100

    def test_caution(self):
        score = calc_debt_health_score(1.0)
        assert 60 <= score < 100

    def test_warning(self):
        score = calc_debt_health_score(1.35)
        assert 30 <= score < 60

    def test_danger(self):
        score = calc_debt_health_score(1.80)
        assert 0 < score < 30

    def test_extreme(self):
        assert calc_debt_health_score(3.0) == 0


class TestSafetyScore:
    def test_safe_stock(self):
        data = {
            'payout_ratio': 0.40,
            'positive_earnings_years': 7,
            'consecutive_dividend_years': 12,
            'debt_ratio': 0.50,
        }
        result = calc_safety_score(data)
        assert result['grade'] == 'SAFE'
        assert result['score'] >= 80

    def test_moderate_stock(self):
        data = {
            'payout_ratio': 0.65,
            'positive_earnings_years': 4,
            'consecutive_dividend_years': 5,
            'debt_ratio': 1.0,
        }
        result = calc_safety_score(data)
        assert result['grade'] in ('MODERATE', 'SAFE')
        assert result['score'] >= 60

    def test_dangerous_stock(self):
        data = {
            'payout_ratio': 1.20,
            'positive_earnings_years': 1,
            'consecutive_dividend_years': 1,
            'debt_ratio': 2.50,
        }
        result = calc_safety_score(data)
        assert result['grade'] == 'DANGEROUS'
        assert result['score'] < 40

    def test_components_present(self):
        data = {
            'payout_ratio': 0.50,
            'positive_earnings_years': 5,
            'consecutive_dividend_years': 5,
            'debt_ratio': 1.0,
        }
        result = calc_safety_score(data)
        assert 'payout_ratio' in result['components']
        assert 'earnings_stability' in result['components']
        assert 'dividend_history' in result['components']
        assert 'debt_health' in result['components']


# ═══════════════════════════════════════════════
# Report Generator Tests
# ═══════════════════════════════════════════════

class TestReportGenerator:
    def test_generate(self):
        gen = DividendMonitorReportGenerator()
        gen.add_trigger_summary({'005930': [{'severity': 'HIGH', 'detail': 'test'}]})
        gen.add_state_changes([{'ticker': '005930', 'prev_state': 'OK', 'new_state': 'WARN'}])
        gen.add_safety_scores([{
            'name': '삼성전자', 'score': 85, 'grade': 'SAFE',
            'components': {'payout_ratio': 100, 'earnings_stability': 80,
                          'dividend_history': 90, 'debt_health': 70},
        }])
        report = gen.generate()
        assert '모니터링 리포트' in report
        assert '삼성전자' in report
