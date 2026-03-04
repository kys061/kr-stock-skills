"""kr-dividend-sop 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dividend_screener import (
    SOP_STEPS, SCREENING_CRITERIA, ENTRY_SCORING, ENTRY_GRADES,
    check_screening_criteria, calc_entry_score,
    _calc_valuation_score, _calc_dividend_quality_score,
    _calc_financial_health_score, _calc_timing_score,
)
from hold_monitor import (
    HOLD_CHECKLIST, HOLD_STATUS, KR_DIVIDEND_CALENDAR, EX_DATE_STRATEGY,
    EXIT_TRIGGERS, check_hold_status, calc_ex_date,
    check_exit_triggers, generate_dividend_calendar,
)
from report_generator import DividendSOPReportGenerator


# ═══════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════

class TestConstants:
    """상수 검증."""

    def test_sop_steps_count(self):
        assert len(SOP_STEPS) == 5
        assert SOP_STEPS == ['SCREEN', 'ENTRY', 'HOLD', 'COLLECT', 'EXIT']

    def test_screening_criteria_keys(self):
        expected = {
            'min_yield', 'min_consecutive_years', 'no_cut_years',
            'max_payout_ratio', 'min_market_cap', 'max_debt_ratio',
            'min_current_ratio', 'min_roe', 'revenue_trend_years',
            'eps_trend_years',
        }
        assert set(SCREENING_CRITERIA.keys()) == expected

    def test_screening_criteria_values(self):
        assert SCREENING_CRITERIA['min_yield'] == 2.5
        assert SCREENING_CRITERIA['min_consecutive_years'] == 3
        assert SCREENING_CRITERIA['max_payout_ratio'] == 0.80
        assert SCREENING_CRITERIA['min_market_cap'] == 500_000_000_000
        assert SCREENING_CRITERIA['max_debt_ratio'] == 1.50
        assert SCREENING_CRITERIA['min_current_ratio'] == 1.0
        assert SCREENING_CRITERIA['min_roe'] == 0.05

    def test_entry_scoring_weights_sum(self):
        total = sum(v['weight'] for v in ENTRY_SCORING.values())
        assert abs(total - 1.0) < 1e-9

    def test_entry_scoring_valuation(self):
        assert ENTRY_SCORING['valuation']['weight'] == 0.40
        assert ENTRY_SCORING['valuation']['per_sweet_spot'] == (5, 12)
        assert ENTRY_SCORING['valuation']['pbr_sweet_spot'] == (0.3, 1.0)

    def test_entry_scoring_dividend_quality(self):
        assert ENTRY_SCORING['dividend_quality']['weight'] == 0.30
        assert ENTRY_SCORING['dividend_quality']['yield_excellent'] == 4.0
        assert ENTRY_SCORING['dividend_quality']['yield_good'] == 3.0

    def test_entry_grades(self):
        assert ENTRY_GRADES['STRONG_BUY'] == 85
        assert ENTRY_GRADES['BUY'] == 70
        assert ENTRY_GRADES['HOLD'] == 55
        assert ENTRY_GRADES['PASS'] == 0

    def test_hold_checklist(self):
        assert len(HOLD_CHECKLIST) == 6
        assert 'dividend_maintained' in HOLD_CHECKLIST
        assert 'payout_ratio_safe' in HOLD_CHECKLIST

    def test_hold_status(self):
        assert HOLD_STATUS == ['HEALTHY', 'CAUTION', 'WARNING', 'EXIT_SIGNAL']

    def test_kr_dividend_calendar(self):
        assert KR_DIVIDEND_CALENDAR['record_date_major'] == '12-31'
        assert KR_DIVIDEND_CALENDAR['ex_date_offset'] == -2
        assert KR_DIVIDEND_CALENDAR['payment_lag_days'] == (30, 60)

    def test_ex_date_strategy(self):
        assert EX_DATE_STRATEGY['hold_through'] is True
        assert EX_DATE_STRATEGY['min_holding_days_before_ex'] == 2

    def test_exit_triggers_count(self):
        assert len(EXIT_TRIGGERS) == 6

    def test_exit_triggers_severity(self):
        assert EXIT_TRIGGERS['dividend_cut']['severity'] == 'HIGH'
        assert EXIT_TRIGGERS['dividend_suspension']['severity'] == 'CRITICAL'
        assert EXIT_TRIGGERS['payout_exceed']['severity'] == 'MEDIUM'
        assert EXIT_TRIGGERS['earnings_loss']['severity'] == 'HIGH'
        assert EXIT_TRIGGERS['debt_spike']['severity'] == 'MEDIUM'
        assert EXIT_TRIGGERS['price_crash']['severity'] == 'HIGH'


# ═══════════════════════════════════════════════
# Step 1: Screening Tests
# ═══════════════════════════════════════════════

class TestScreening:
    """Step 1 스크리닝 테스트."""

    def _good_stock(self):
        return {
            'dividend_yield': 3.5,
            'consecutive_years': 5,
            'no_cut_years': 5,
            'payout_ratio': 0.40,
            'market_cap': 1_000_000_000_000,
            'debt_ratio': 0.80,
            'current_ratio': 1.5,
            'roe': 0.12,
            'revenue_trend': True,
            'eps_trend': True,
        }

    def test_all_pass(self):
        result = check_screening_criteria(self._good_stock())
        assert result['passed'] is True
        assert result['passed_count'] == 10
        assert result['failed_reasons'] == []

    def test_low_yield_fail(self):
        stock = self._good_stock()
        stock['dividend_yield'] = 1.5
        result = check_screening_criteria(stock)
        assert result['passed'] is False
        assert any('배당수익률' in r for r in result['failed_reasons'])

    def test_short_consecutive_fail(self):
        stock = self._good_stock()
        stock['consecutive_years'] = 2
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_high_payout_fail(self):
        stock = self._good_stock()
        stock['payout_ratio'] = 0.95
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_low_market_cap_fail(self):
        stock = self._good_stock()
        stock['market_cap'] = 100_000_000_000
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_high_debt_fail(self):
        stock = self._good_stock()
        stock['debt_ratio'] = 2.0
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_low_roe_fail(self):
        stock = self._good_stock()
        stock['roe'] = 0.03
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_no_revenue_trend_fail(self):
        stock = self._good_stock()
        stock['revenue_trend'] = False
        result = check_screening_criteria(stock)
        assert result['passed'] is False

    def test_multiple_fails(self):
        stock = self._good_stock()
        stock['dividend_yield'] = 1.0
        stock['roe'] = 0.01
        stock['eps_trend'] = False
        result = check_screening_criteria(stock)
        assert result['passed'] is False
        assert result['passed_count'] == 7
        assert len(result['failed_reasons']) == 3


# ═══════════════════════════════════════════════
# Step 2: Entry Score Tests
# ═══════════════════════════════════════════════

class TestValuationScore:
    """밸류에이션 점수 테스트."""

    def test_sweet_spot_per(self):
        score = _calc_valuation_score(8, 0.7)
        assert score == 100.0

    def test_high_per(self):
        score = _calc_valuation_score(25, 0.7)
        assert score < 80

    def test_negative_per(self):
        score = _calc_valuation_score(-5, 0.7)
        assert score < 60

    def test_high_pbr(self):
        score = _calc_valuation_score(8, 3.0)
        assert score < 80


class TestDividendQualityScore:
    """배당 품질 점수 테스트."""

    def test_excellent_yield(self):
        score = _calc_dividend_quality_score(5.0)
        assert score == 100

    def test_good_yield(self):
        score = _calc_dividend_quality_score(3.5)
        assert 80 < score < 100

    def test_low_yield(self):
        score = _calc_dividend_quality_score(1.0)
        assert score < 50

    def test_growth_bonus(self):
        base = _calc_dividend_quality_score(3.0)
        with_bonus = _calc_dividend_quality_score(3.0, is_growing=True)
        assert with_bonus > base


class TestFinancialHealthScore:
    """재무 건전성 점수 테스트."""

    def test_excellent_roe(self):
        score = _calc_financial_health_score(0.20)
        assert score == 100

    def test_good_roe(self):
        score = _calc_financial_health_score(0.12)
        assert 80 < score < 100

    def test_low_roe(self):
        score = _calc_financial_health_score(0.03)
        assert score < 50


class TestTimingScore:
    """타이밍 점수 테스트."""

    def test_oversold_rsi(self):
        score = _calc_timing_score(rsi=25)
        assert score == 100

    def test_neutral_rsi(self):
        score = _calc_timing_score(rsi=50)
        assert score == 50

    def test_overbought_rsi(self):
        score = _calc_timing_score(rsi=80)
        assert score < 30

    def test_no_rsi(self):
        score = _calc_timing_score(rsi=None)
        assert score == 50

    def test_ex_date_penalty(self):
        base = _calc_timing_score(rsi=35, days_to_ex_date=60)
        penalized = _calc_timing_score(rsi=35, days_to_ex_date=5)
        assert penalized < base


class TestEntryScore:
    """진입 점수 통합 테스트."""

    def test_strong_buy(self):
        stock = {
            'per': 8, 'pbr': 0.7,
            'dividend_yield': 5.0, 'is_growing': True,
            'roe': 0.20, 'rsi': 25,
        }
        result = calc_entry_score(stock)
        assert result['grade'] == 'STRONG_BUY'
        assert result['score'] >= 85

    def test_buy(self):
        stock = {
            'per': 10, 'pbr': 0.8,
            'dividend_yield': 3.5,
            'roe': 0.12, 'rsi': 40,
        }
        result = calc_entry_score(stock)
        assert result['grade'] in ('BUY', 'STRONG_BUY')
        assert result['score'] >= 70

    def test_pass(self):
        stock = {
            'per': 30, 'pbr': 3.0,
            'dividend_yield': 1.0,
            'roe': 0.02, 'rsi': 70,
        }
        result = calc_entry_score(stock)
        assert result['grade'] in ('PASS', 'HOLD')
        assert result['score'] < 70

    def test_components_present(self):
        stock = {'per': 10, 'pbr': 1.0, 'dividend_yield': 3.0, 'roe': 0.10}
        result = calc_entry_score(stock)
        assert 'valuation' in result['components']
        assert 'dividend_quality' in result['components']
        assert 'financial_health' in result['components']
        assert 'timing' in result['components']


# ═══════════════════════════════════════════════
# Step 3: Hold Monitor Tests
# ═══════════════════════════════════════════════

class TestHoldStatus:
    """보유 상태 점검 테스트."""

    def test_healthy(self):
        holdings = [{
            'ticker': '005930', 'name': '삼성전자',
            'dividend_maintained': True,
            'payout_ratio': 0.30,
            'debt_ratio': 0.50,
            'operating_profit': 100,
            'governance_issue': False,
            'price_change_pct': -0.05,
        }]
        results = check_hold_status(holdings)
        assert results[0]['status'] == 'HEALTHY'
        assert results[0]['issues'] == []

    def test_caution_single_issue(self):
        holdings = [{
            'ticker': '005930', 'name': '삼성전자',
            'dividend_maintained': True,
            'payout_ratio': 0.90,
            'debt_ratio': 0.50,
            'operating_profit': 100,
            'governance_issue': False,
            'price_change_pct': -0.05,
        }]
        results = check_hold_status(holdings)
        assert results[0]['status'] == 'CAUTION'
        assert len(results[0]['issues']) == 1

    def test_warning_multiple_issues(self):
        holdings = [{
            'ticker': '005930', 'name': '삼성전자',
            'dividend_maintained': True,
            'payout_ratio': 0.90,
            'debt_ratio': 1.80,
            'operating_profit': 100,
            'governance_issue': False,
            'price_change_pct': -0.05,
        }]
        results = check_hold_status(holdings)
        assert results[0]['status'] == 'WARNING'
        assert len(results[0]['issues']) >= 2

    def test_exit_signal_dividend_loss(self):
        holdings = [{
            'ticker': '005930', 'name': '삼성전자',
            'dividend_maintained': False,
            'payout_ratio': 0.30,
            'debt_ratio': 0.50,
            'operating_profit': 100,
            'governance_issue': False,
            'price_change_pct': -0.05,
        }]
        results = check_hold_status(holdings)
        assert results[0]['status'] == 'EXIT_SIGNAL'

    def test_exit_signal_operating_loss(self):
        holdings = [{
            'ticker': '005930', 'name': '삼성전자',
            'dividend_maintained': True,
            'payout_ratio': 0.30,
            'debt_ratio': 0.50,
            'operating_profit': -50,
            'governance_issue': False,
            'price_change_pct': -0.10,
        }]
        results = check_hold_status(holdings)
        assert results[0]['status'] == 'EXIT_SIGNAL'


# ═══════════════════════════════════════════════
# Step 4: Calendar Tests
# ═══════════════════════════════════════════════

class TestCalendar:
    """배당 캘린더 테스트."""

    def test_ex_date_calculation(self):
        # 2026-12-31 (목) → 2영업일 전 = 2026-12-29 (화)
        ex_date = calc_ex_date('2026-12-31')
        assert ex_date == '2026-12-29'

    def test_ex_date_over_weekend(self):
        # 2026-06-30 (화) → 2영업일 전 = 2026-06-26 (금)
        ex_date = calc_ex_date('2026-06-30')
        assert ex_date == '2026-06-26'

    def test_generate_calendar(self):
        holdings = [
            {'ticker': '005930', 'name': '삼성전자', 'record_date': '2026-12-31', 'dps': 1444},
            {'ticker': '017670', 'name': 'SK텔레콤', 'record_date': '2026-06-30', 'dps': 1000},
        ]
        calendar = generate_dividend_calendar(holdings, year=2026)
        assert len(calendar) == 2
        assert calendar[0]['ex_date'] < calendar[1]['ex_date']  # SK텔레콤(6월) < 삼성(12월)

    def test_calendar_has_payment_dates(self):
        holdings = [{'ticker': '005930', 'name': '삼성전자', 'record_date': '2026-12-31', 'dps': 1444}]
        calendar = generate_dividend_calendar(holdings, year=2026)
        entry = calendar[0]
        assert 'payment_start' in entry
        assert 'payment_end' in entry
        assert entry['payment_start'] < entry['payment_end']


# ═══════════════════════════════════════════════
# Step 5: EXIT Trigger Tests
# ═══════════════════════════════════════════════

class TestExitTriggers:
    """EXIT 트리거 테스트."""

    def test_no_triggers(self):
        data = {
            'current_dps': 1500, 'prev_dps': 1400,
            'payout_ratio': 0.40,
            'operating_profit_quarters': [100, 120, 130, 150],
            'debt_ratio': 0.80,
            'price_change_pct': -0.05,
        }
        result = check_exit_triggers(data)
        assert result['triggered'] is False
        assert result['triggers'] == []

    def test_dividend_cut(self):
        data = {'current_dps': 800, 'prev_dps': 1200}
        result = check_exit_triggers(data)
        assert result['triggered'] is True
        assert any(t['id'] == 'dividend_cut' for t in result['triggers'])

    def test_dividend_suspension(self):
        data = {'current_dps': 0, 'prev_dps': 1200}
        result = check_exit_triggers(data)
        assert result['triggered'] is True
        ids = [t['id'] for t in result['triggers']]
        assert 'dividend_suspension' in ids

    def test_payout_exceed(self):
        data = {'current_dps': 1500, 'prev_dps': 1400, 'payout_ratio': 1.20}
        result = check_exit_triggers(data)
        assert any(t['id'] == 'payout_exceed' for t in result['triggers'])

    def test_earnings_loss(self):
        data = {
            'current_dps': 1000, 'prev_dps': 1000,
            'operating_profit_quarters': [100, 50, -10, -20],
        }
        result = check_exit_triggers(data)
        assert any(t['id'] == 'earnings_loss' for t in result['triggers'])

    def test_earnings_loss_single_quarter_no_trigger(self):
        data = {
            'current_dps': 1000, 'prev_dps': 1000,
            'operating_profit_quarters': [100, 50, -10, 20],
        }
        result = check_exit_triggers(data)
        assert not any(t['id'] == 'earnings_loss' for t in result['triggers'])

    def test_debt_spike(self):
        data = {'current_dps': 1000, 'prev_dps': 1000, 'debt_ratio': 2.50}
        result = check_exit_triggers(data)
        assert any(t['id'] == 'debt_spike' for t in result['triggers'])

    def test_price_crash(self):
        data = {'current_dps': 1000, 'prev_dps': 1000, 'price_change_pct': -0.35}
        result = check_exit_triggers(data)
        assert any(t['id'] == 'price_crash' for t in result['triggers'])

    def test_multiple_triggers(self):
        data = {
            'current_dps': 0, 'prev_dps': 1000,
            'payout_ratio': 1.50,
            'debt_ratio': 3.00,
            'price_change_pct': -0.40,
        }
        result = check_exit_triggers(data)
        assert len(result['triggers']) >= 3


# ═══════════════════════════════════════════════
# Report Generator Tests
# ═══════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성기 테스트."""

    def test_generate_report(self):
        gen = DividendSOPReportGenerator()
        gen.add_screening_result(100, 15, [{'name': '삼성전자', 'passed': True}])
        gen.add_entry_scores([{
            'name': '삼성전자', 'score': 82.5, 'grade': 'BUY',
            'components': {'valuation': 90, 'dividend_quality': 80,
                          'financial_health': 75, 'timing': 60},
        }])
        gen.add_hold_status([{'ticker': '005930', 'name': '삼성전자',
                             'status': 'HEALTHY', 'issues': []}])
        gen.add_calendar([{
            'ticker': '005930', 'name': '삼성전자',
            'record_date': '2026-12-31', 'ex_date': '2026-12-29',
            'payment_start': '2027-01-30', 'payment_end': '2027-03-01',
            'dps': 1444,
        }])
        gen.add_exit_alerts([])
        report = gen.generate()
        assert '배당 SOP 리포트' in report
        assert 'Step 1' in report
        assert 'Step 2' in report
        assert '삼성전자' in report

    def test_empty_report(self):
        gen = DividendSOPReportGenerator()
        report = gen.generate()
        assert '배당 SOP 리포트' in report
