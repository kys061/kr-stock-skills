"""kr-credit-monitor 종합 테스트."""

import pytest

from ..credit_balance_analyzer import (
    CREDIT_BALANCE_CONFIG,
    CREDIT_MARKET_RATIO_LEVELS,
    LEVERAGE_CYCLE_PHASES,
    DEPOSIT_CREDIT_RATIO,
    DEPOSIT_LEVEL_THRESHOLDS,
    DEPOSIT_CHANGE_SIGNALS,
    DEPOSIT_LEVEL_SCORES,
    DEPOSIT_SIGNAL_SCORES,
    _classify_market_ratio,
    calc_credit_percentile,
    classify_leverage_cycle,
    calc_deposit_credit_ratio,
    analyze_credit_balance,
    analyze_investor_deposits,
)
from ..forced_liquidation_risk import (
    MARGIN_CALL_CONFIG,
    FORCED_LIQUIDATION_SCENARIOS,
    LIQUIDATION_IMPACT_LEVELS,
    CREDIT_RISK_WEIGHTS,
    CREDIT_RISK_GRADES,
    calc_margin_call_threshold,
    estimate_forced_liquidation,
    calc_credit_risk_score,
)
from ..report_generator import generate_credit_report


# ═══════════════════════════════════════════════
# 상수 검증
# ═══════════════════════════════════════════════

class TestConstants:
    """설계 상수 검증."""

    def test_credit_balance_config(self):
        assert CREDIT_BALANCE_CONFIG['lookback_years'] == 3
        assert CREDIT_BALANCE_CONFIG['yoy_warning'] == 0.15
        assert CREDIT_BALANCE_CONFIG['yoy_critical'] == 0.30
        assert CREDIT_BALANCE_CONFIG['mom_warning'] == 0.05
        assert CREDIT_BALANCE_CONFIG['mom_critical'] == 0.10

    def test_market_ratio_levels(self):
        assert CREDIT_MARKET_RATIO_LEVELS['critical'] == 0.030
        assert CREDIT_MARKET_RATIO_LEVELS['high'] == 0.025
        assert CREDIT_MARKET_RATIO_LEVELS['elevated'] == 0.020
        assert CREDIT_MARKET_RATIO_LEVELS['normal'] == 0.015
        assert CREDIT_MARKET_RATIO_LEVELS['safe'] == 0.0

    def test_leverage_cycle_phases(self):
        assert set(LEVERAGE_CYCLE_PHASES.keys()) == {'EXPANSION', 'PEAK', 'CONTRACTION', 'TROUGH'}

    def test_deposit_credit_ratio(self):
        assert DEPOSIT_CREDIT_RATIO['overheated'] == 0.80
        assert DEPOSIT_CREDIT_RATIO['high'] == 0.60
        assert DEPOSIT_CREDIT_RATIO['normal'] == 0.40
        assert DEPOSIT_CREDIT_RATIO['healthy'] == 0.0

    def test_margin_call_config(self):
        assert MARGIN_CALL_CONFIG['maintenance_ratio'] == 1.40
        assert MARGIN_CALL_CONFIG['initial_ratio'] == 2.00
        assert MARGIN_CALL_CONFIG['liquidation_delay_days'] == 2

    def test_scenarios_count(self):
        assert len(FORCED_LIQUIDATION_SCENARIOS) == 3
        drops = [s['drop_pct'] for s in FORCED_LIQUIDATION_SCENARIOS]
        assert drops == [0.10, 0.20, 0.30]

    def test_risk_weights_sum(self):
        total = sum(v['weight'] for v in CREDIT_RISK_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_risk_weights_values(self):
        w = CREDIT_RISK_WEIGHTS
        assert w['credit_level']['weight'] == 0.30
        assert w['growth_rate']['weight'] == 0.25
        assert w['forced_liquidation']['weight'] == 0.25
        assert w['leverage_cycle']['weight'] == 0.20

    def test_risk_grades_count(self):
        assert len(CREDIT_RISK_GRADES) == 5

    def test_risk_grades_coverage(self):
        assert CREDIT_RISK_GRADES['SAFE']['min_score'] == 0
        assert CREDIT_RISK_GRADES['CRITICAL']['max_score'] == 100


# ═══════════════════════════════════════════════
# credit_balance_analyzer 테스트
# ═══════════════════════════════════════════════

class TestClassifyMarketRatio:
    """시총 대비 비율 분류 테스트."""

    def test_critical(self):
        assert _classify_market_ratio(0.035) == 'critical'

    def test_high(self):
        assert _classify_market_ratio(0.026) == 'high'

    def test_elevated(self):
        assert _classify_market_ratio(0.021) == 'elevated'

    def test_normal(self):
        assert _classify_market_ratio(0.016) == 'normal'

    def test_safe(self):
        assert _classify_market_ratio(0.010) == 'safe'

    def test_boundary(self):
        assert _classify_market_ratio(0.030) == 'critical'
        assert _classify_market_ratio(0.025) == 'high'


class TestCreditPercentile:
    """calc_credit_percentile 테스트."""

    def test_empty_history(self):
        assert calc_credit_percentile(100, []) == 50.0

    def test_high_percentile(self):
        history = list(range(10, 101, 10))  # 10, 20, ... 100
        result = calc_credit_percentile(95, history)
        assert result >= 80

    def test_low_percentile(self):
        history = list(range(10, 101, 10))
        result = calc_credit_percentile(15, history)
        assert result <= 20


class TestLeverageCycle:
    """classify_leverage_cycle 테스트."""

    def test_empty_data(self):
        assert classify_leverage_cycle([]) == 'TROUGH'

    def test_peak(self):
        # 100개 데이터 중 현재가 최고 → 퍼센타일 ~100%
        data = [{'total': 100 - i} for i in range(100)]
        assert classify_leverage_cycle(data) == 'PEAK'

    def test_trough(self):
        # 현재가 최저 → 퍼센타일 0%
        data = [{'total': i} for i in range(100)]
        assert classify_leverage_cycle(data) == 'TROUGH'

    def test_expansion(self):
        # MoM > 0, YoY > 0, 퍼센타일 중간
        data = []
        for i in range(300):
            # 최근이 높지만 극단적이지 않음
            val = 50 + (300 - i) * 0.1
            data.append({'total': val})
        result = classify_leverage_cycle(data)
        assert result in ('EXPANSION', 'PEAK')


class TestDepositCreditRatio:
    """calc_deposit_credit_ratio 테스트."""

    def test_overheated(self):
        result = calc_deposit_credit_ratio(90, 100)
        assert result['level'] == 'overheated'

    def test_high(self):
        result = calc_deposit_credit_ratio(70, 100)
        assert result['level'] == 'high'

    def test_normal(self):
        result = calc_deposit_credit_ratio(50, 100)
        assert result['level'] == 'normal'

    def test_healthy(self):
        result = calc_deposit_credit_ratio(30, 100)
        assert result['level'] == 'healthy'

    def test_zero_deposit(self):
        result = calc_deposit_credit_ratio(100, 0)
        assert result['ratio'] == 0.0
        assert result['level'] == 'healthy'


class TestAnalyzeCreditBalance:
    """analyze_credit_balance 종합 테스트."""

    def test_empty_data(self):
        result = analyze_credit_balance([], 1_000_000_000_000)
        assert result['total'] == 0
        assert result['cycle_phase'] == 'TROUGH'

    def test_critical_level(self):
        data = [{'date': '2026-03-04', 'total': 30_000_000_000}]  # 300억
        market_cap = 1_000_000_000_000  # 1조 → 3%
        result = analyze_credit_balance(data, market_cap)
        assert result['market_ratio'] == 0.03
        assert result['market_ratio_level'] == 'critical'

    def test_safe_level(self):
        data = [{'date': '2026-03-04', 'total': 5_000_000_000}]  # 50억
        market_cap = 1_000_000_000_000  # 1조 → 0.5%
        result = analyze_credit_balance(data, market_cap)
        assert result['market_ratio'] == 0.005
        assert result['market_ratio_level'] == 'safe'


# ═══════════════════════════════════════════════
# forced_liquidation_risk 테스트
# ═══════════════════════════════════════════════

class TestMarginCallThreshold:
    """calc_margin_call_threshold 테스트."""

    def test_default_config(self):
        result = calc_margin_call_threshold(100_000_000)
        # 200% → 140%: 1 - (1.4/2.0) = 0.30 = 30% 하락
        assert result['trigger_price_drop'] == 0.3

    def test_custom_ratios(self):
        result = calc_margin_call_threshold(100_000_000, initial_ratio=2.5, maintenance_ratio=1.5)
        expected = 1 - (1.5 / 2.5)  # 0.4
        assert result['trigger_price_drop'] == 0.4

    def test_zero_ratio(self):
        result = calc_margin_call_threshold(100, initial_ratio=0, maintenance_ratio=1.4)
        assert result['trigger_price_drop'] == 0.0


class TestEstimateForcedLiquidation:
    """estimate_forced_liquidation 테스트."""

    def test_basic_estimation(self):
        credit_data = {'total': 10_000_000_000_000}  # 10조
        result = estimate_forced_liquidation(credit_data)
        assert len(result['scenarios']) == 3
        assert result['trigger_price_drop'] == 0.3

    def test_with_daily_volume(self):
        credit_data = {'total': 5_000_000_000_000}  # 5조
        result = estimate_forced_liquidation(credit_data, daily_volume=10_000_000_000_000)
        # 30% 하락 시나리오에서만 margin call 발동
        severe = result['scenarios'][2]  # -30%
        assert severe['triggers_margin_call'] is True

    def test_no_margin_call_at_10pct(self):
        credit_data = {'total': 1_000_000_000_000}
        result = estimate_forced_liquidation(credit_data)
        mild = result['scenarios'][0]  # -10%
        assert mild['triggers_margin_call'] is False

    def test_worst_case(self):
        credit_data = {'total': 5_000_000_000_000}
        # 커스텀 시나리오: trigger_drop(0.30)보다 큰 하락률 포함
        scenarios = [
            {'drop_pct': 0.35, 'label': '35% 하락', 'severity': 'extreme'},
        ]
        result = estimate_forced_liquidation(credit_data, scenarios=scenarios)
        assert result['worst_case'] is not None
        assert result['worst_case']['triggers_margin_call'] is True
        assert result['worst_case']['affected_amount'] > 0


class TestCreditRiskScore:
    """calc_credit_risk_score 테스트."""

    def test_safe_scenario(self):
        balance = {
            'market_ratio_level': 'safe',
            'growth': {'yoy': 0.0, 'yoy_level': 'normal', 'mom': 0.0, 'mom_level': 'normal'},
            'cycle_phase': 'TROUGH',
        }
        result = calc_credit_risk_score(balance)
        assert result['grade'] in ('SAFE', 'NORMAL')
        assert result['score'] < 30

    def test_critical_scenario(self):
        balance = {
            'market_ratio_level': 'critical',
            'growth': {'yoy': 0.35, 'yoy_level': 'critical', 'mom': 0.12, 'mom_level': 'critical'},
            'cycle_phase': 'PEAK',
        }
        result = calc_credit_risk_score(balance)
        assert result['grade'] in ('HIGH', 'CRITICAL')

    def test_components_present(self):
        balance = {
            'market_ratio_level': 'elevated',
            'growth': {'yoy_level': 'warning', 'mom_level': 'normal'},
            'cycle_phase': 'EXPANSION',
        }
        result = calc_credit_risk_score(balance)
        assert len(result['components']) == 4
        for key in CREDIT_RISK_WEIGHTS:
            assert key in result['components']

    def test_with_liquidation(self):
        balance = {
            'market_ratio_level': 'high',
            'growth': {'yoy_level': 'warning', 'mom_level': 'warning'},
            'cycle_phase': 'PEAK',
        }
        liquidation = {
            'trigger_price_drop': 0.3,
            'scenarios': [
                {'drop_pct': 0.10, 'triggers_margin_call': False, 'impact_level': 'negligible'},
                {'drop_pct': 0.20, 'triggers_margin_call': False, 'impact_level': 'negligible'},
                {'drop_pct': 0.30, 'triggers_margin_call': True, 'impact_level': 'minor'},
            ],
        }
        result = calc_credit_risk_score(balance, liquidation)
        assert result['score'] > 0


# ═══════════════════════════════════════════════
# report_generator 테스트
# ═══════════════════════════════════════════════

class TestGenerateReport:
    """generate_credit_report 테스트."""

    def test_basic_report(self):
        balance = {
            'total': 15_000_000_000_000,
            'market_ratio': 0.025,
            'market_ratio_level': 'high',
            'growth': {'yoy': 0.18, 'yoy_level': 'warning', 'mom': 0.06, 'mom_level': 'warning'},
            'percentile': 78.5,
            'cycle_phase': 'EXPANSION',
        }
        report = generate_credit_report(balance)
        assert '# 신용잔고 분석 리포트' in report
        assert 'EXPANSION' in report
        assert '2.50%' in report

    def test_with_liquidation(self):
        balance = {
            'total': 10_000_000_000_000,
            'market_ratio': 0.020,
            'market_ratio_level': 'elevated',
            'growth': {'yoy': 0.10, 'yoy_level': 'normal', 'mom': 0.03, 'mom_level': 'normal'},
            'percentile': 60.0,
            'cycle_phase': 'EXPANSION',
        }
        liquidation = {
            'trigger_price_drop': 0.3,
            'scenarios': [
                {'label': '10% 하락', 'drop_pct': 0.10, 'triggers_margin_call': False,
                 'affected_amount': 0, 'impact_level': 'negligible'},
                {'label': '20% 하락', 'drop_pct': 0.20, 'triggers_margin_call': False,
                 'affected_amount': 0, 'impact_level': 'negligible'},
                {'label': '30% 하락', 'drop_pct': 0.30, 'triggers_margin_call': True,
                 'affected_amount': 5_000_000_000_000, 'impact_level': 'major'},
            ],
        }
        report = generate_credit_report(balance, liquidation)
        assert '반대매매 리스크' in report
        assert '30%' in report

    def test_with_risk_score(self):
        balance = {
            'total': 5_000_000_000_000,
            'market_ratio': 0.015,
            'market_ratio_level': 'normal',
            'growth': {'yoy': 0.05, 'yoy_level': 'normal', 'mom': 0.02, 'mom_level': 'normal'},
            'percentile': 45.0,
            'cycle_phase': 'CONTRACTION',
        }
        risk = {
            'score': 35.0,
            'grade': 'NORMAL',
            'label': '보통',
            'components': {
                'credit_level': {'score': 30, 'weight': 0.30},
                'growth_rate': {'score': 30, 'weight': 0.25},
                'forced_liquidation': {'score': 20, 'weight': 0.25},
                'leverage_cycle': {'score': 35, 'weight': 0.20},
            },
        }
        report = generate_credit_report(balance, risk_score=risk)
        assert '리스크 등급' in report
        assert 'NORMAL' in report


# ═══════════════════════════════════════════════
# 고객 예탁금 분석 (신규)
# ═══════════════════════════════════════════════

class TestInvestorDeposits:

    def test_deposit_level_very_high(self):
        r = analyze_investor_deposits(65.0)
        assert r['level'] == 'very_high'

    def test_deposit_level_high(self):
        r = analyze_investor_deposits(52.0)
        assert r['level'] == 'high'

    def test_deposit_level_normal(self):
        r = analyze_investor_deposits(42.0)
        assert r['level'] == 'normal'

    def test_deposit_level_low(self):
        r = analyze_investor_deposits(32.0)
        assert r['level'] == 'low'

    def test_deposit_level_very_low(self):
        r = analyze_investor_deposits(25.0)
        assert r['level'] == 'very_low'

    def test_deposit_signal_surge(self):
        r = analyze_investor_deposits(50.0, deposit_change_1m_pct=12.0)
        assert r['signal'] == 'surge'

    def test_deposit_signal_stable(self):
        r = analyze_investor_deposits(50.0, deposit_change_1m_pct=1.0)
        assert r['signal'] == 'stable'

    def test_deposit_signal_exodus(self):
        r = analyze_investor_deposits(50.0, deposit_change_1m_pct=-15.0)
        assert r['signal'] == 'exodus'

    def test_buying_power_score_range(self):
        r = analyze_investor_deposits(50.0, deposit_change_1m_pct=0.0)
        assert 0 <= r['buying_power_score'] <= 100

    def test_buying_power_high_balance_surge(self):
        r = analyze_investor_deposits(65.0, deposit_change_1m_pct=12.0)
        assert r['buying_power_score'] >= 80

    def test_buying_power_low_balance_exodus(self):
        r = analyze_investor_deposits(25.0, deposit_change_1m_pct=-15.0)
        assert r['buying_power_score'] <= 20

    def test_deposit_interpretation_korean(self):
        r = analyze_investor_deposits(50.0)
        assert isinstance(r['interpretation'], str)
        assert len(r['interpretation']) > 0
