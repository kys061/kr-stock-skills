"""kr-program-trade-analyzer 종합 테스트."""

import pytest
from datetime import date

from ..program_trade_analyzer import (
    PROGRAM_TRADE_CONFIG,
    ARBITRAGE_CONFIG,
    NON_ARBITRAGE_CONFIG,
    PROGRAM_FLOW_SIGNALS,
    classify_program_signal,
    analyze_program_trades,
)
from ..basis_analyzer import (
    KOSPI200_MULTIPLIER,
    BASIS_CONFIG,
    BASIS_STATES,
    OI_CONFIG,
    calc_theoretical_basis,
    analyze_basis,
    analyze_open_interest,
)
from ..expiry_effect_analyzer import (
    EXPIRY_CONFIG,
    EXPIRY_TYPES,
    EXPIRY_PROXIMITY,
    EXPIRY_PATTERNS,
    PROGRAM_IMPACT_WEIGHTS,
    PROGRAM_IMPACT_GRADES,
    get_next_expiry,
    analyze_expiry_effect,
    calc_max_pain,
    calc_program_impact_score,
)
from ..report_generator import generate_program_trade_report


# ═══════════════════════════════════════════════
# 상수 검증
# ═══════════════════════════════════════════════

class TestConstants:
    """설계 상수 검증."""

    def test_trade_types(self):
        assert PROGRAM_TRADE_CONFIG['trade_types'] == ['arbitrage', 'non_arbitrage']
        assert PROGRAM_TRADE_CONFIG['flow_periods'] == [1, 5, 20]

    def test_arbitrage_config(self):
        assert ARBITRAGE_CONFIG['significant_amount'] == 500_000_000_000
        assert ARBITRAGE_CONFIG['large_amount'] == 1_000_000_000_000

    def test_non_arbitrage_config(self):
        assert NON_ARBITRAGE_CONFIG['significant_amount'] == 300_000_000_000
        assert NON_ARBITRAGE_CONFIG['large_amount'] == 500_000_000_000
        assert NON_ARBITRAGE_CONFIG['warning_consecutive'] == 5

    def test_flow_signals_count(self):
        assert len(PROGRAM_FLOW_SIGNALS) == 5

    def test_kospi200_multiplier(self):
        assert KOSPI200_MULTIPLIER == 250_000

    def test_basis_config(self):
        assert BASIS_CONFIG['normal_range_pct'] == 0.003
        assert BASIS_CONFIG['warning_range_pct'] == 0.007
        assert BASIS_CONFIG['critical_range_pct'] == 0.015
        assert BASIS_CONFIG['risk_free_rate'] == 0.035

    def test_basis_states_count(self):
        assert len(BASIS_STATES) == 5
        assert set(BASIS_STATES.keys()) == {
            'DEEP_CONTANGO', 'CONTANGO', 'FAIR', 'BACKWARDATION', 'DEEP_BACKWARDATION',
        }

    def test_oi_config(self):
        assert OI_CONFIG['change_significant'] == 0.05
        assert OI_CONFIG['change_large'] == 0.10

    def test_expiry_config(self):
        assert EXPIRY_CONFIG['monthly_expiry_weekday'] == 3
        assert EXPIRY_CONFIG['monthly_expiry_week'] == 2
        assert EXPIRY_CONFIG['quarterly_months'] == [3, 6, 9, 12]

    def test_expiry_types(self):
        assert EXPIRY_TYPES['MONTHLY']['volatility_premium'] == 1.05
        assert EXPIRY_TYPES['QUARTERLY']['volatility_premium'] == 1.15

    def test_expiry_proximity(self):
        assert EXPIRY_PROXIMITY['expiry_day'] == 0
        assert EXPIRY_PROXIMITY['near'] == 1
        assert EXPIRY_PROXIMITY['approaching'] == 3
        assert EXPIRY_PROXIMITY['week'] == 5
        assert EXPIRY_PROXIMITY['far'] == 999

    def test_patterns_count(self):
        assert len(EXPIRY_PATTERNS) == 4

    def test_impact_weights_sum(self):
        total = sum(v['weight'] for v in PROGRAM_IMPACT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_impact_weights_values(self):
        w = PROGRAM_IMPACT_WEIGHTS
        assert w['arbitrage_flow']['weight'] == 0.25
        assert w['non_arb_flow']['weight'] == 0.30
        assert w['basis_signal']['weight'] == 0.25
        assert w['expiry_effect']['weight'] == 0.20

    def test_impact_grades_count(self):
        assert len(PROGRAM_IMPACT_GRADES) == 4


# ═══════════════════════════════════════════════
# program_trade_analyzer 테스트
# ═══════════════════════════════════════════════

class TestClassifyProgramSignal:
    """classify_program_signal 테스트."""

    def test_strong_buy(self):
        signal = classify_program_signal(1_200_000_000_000, 600_000_000_000)
        assert signal == 'STRONG_BUY'

    def test_neutral(self):
        signal = classify_program_signal(100_000_000_000, -100_000_000_000)
        assert signal == 'NEUTRAL'

    def test_strong_sell(self):
        signal = classify_program_signal(-1_200_000_000_000, -600_000_000_000)
        assert signal == 'STRONG_SELL'

    def test_mixed(self):
        signal = classify_program_signal(600_000_000_000, -400_000_000_000)
        assert signal in ('BUY', 'NEUTRAL', 'SELL')


class TestAnalyzeProgramTrades:
    """analyze_program_trades 종합 테스트."""

    def test_empty_data(self):
        result = analyze_program_trades([])
        assert result['signal'] == 'NEUTRAL'
        assert result['combined_score'] == 50

    def test_bullish_program(self):
        data = [{
            'date': '2026-03-04',
            'arb_buy': 800_000_000_000,
            'arb_sell': 200_000_000_000,
            'non_arb_buy': 600_000_000_000,
            'non_arb_sell': 100_000_000_000,
        }]
        result = analyze_program_trades(data)
        assert result['arbitrage']['net'] == 600_000_000_000
        assert result['signal'] in ('STRONG_BUY', 'BUY')

    def test_bearish_program(self):
        data = [{
            'date': '2026-03-04',
            'arb_buy': 100_000_000_000,
            'arb_sell': 800_000_000_000,
            'non_arb_buy': 50_000_000_000,
            'non_arb_sell': 700_000_000_000,
        }]
        result = analyze_program_trades(data)
        assert result['signal'] in ('STRONG_SELL', 'SELL')

    def test_consecutive_sell(self):
        data = [
            {'non_arb_buy': 100, 'non_arb_sell': 500, 'arb_buy': 0, 'arb_sell': 0}
            for _ in range(6)
        ]
        result = analyze_program_trades(data)
        assert result['consecutive_sell'] == 6


# ═══════════════════════════════════════════════
# basis_analyzer 테스트
# ═══════════════════════════════════════════════

class TestTheoreticalBasis:
    """calc_theoretical_basis 테스트."""

    def test_basic(self):
        # S=350, r=3.5%, t=30일
        result = calc_theoretical_basis(350, 0.035, 30)
        expected = 350 * (1 + 0.035 * 30 / 365)
        assert abs(result - expected) < 0.01

    def test_zero_spot(self):
        assert calc_theoretical_basis(0) == 0.0

    def test_none_spot(self):
        assert calc_theoretical_basis(None) == 0.0

    def test_default_rate(self):
        result = calc_theoretical_basis(350, days=30)
        assert result > 350


class TestAnalyzeBasis:
    """analyze_basis 테스트."""

    def test_fair_basis(self):
        spot = 350
        futures = spot * 1.001  # +0.1% → FAIR
        result = analyze_basis(futures, spot, days_to_expiry=30)
        assert result['state'] == 'FAIR'

    def test_contango(self):
        spot = 350
        futures = spot * 1.01  # +1% → CONTANGO
        result = analyze_basis(futures, spot)
        assert result['state'] == 'CONTANGO'

    def test_deep_contango(self):
        spot = 350
        futures = spot * 1.02  # +2% → DEEP_CONTANGO
        result = analyze_basis(futures, spot)
        assert result['state'] == 'DEEP_CONTANGO'

    def test_backwardation(self):
        spot = 350
        futures = spot * 0.995  # -0.5% → BACKWARDATION
        result = analyze_basis(futures, spot)
        assert result['state'] == 'BACKWARDATION'

    def test_deep_backwardation(self):
        spot = 350
        futures = spot * 0.98  # -2% → DEEP_BACKWARDATION
        result = analyze_basis(futures, spot)
        assert result['state'] == 'DEEP_BACKWARDATION'

    def test_empty_data(self):
        result = analyze_basis(0, 0)
        assert result['state'] == 'FAIR'
        assert result['score'] == 70

    def test_score_range(self):
        result = analyze_basis(360, 350)
        assert 0 <= result['score'] <= 100


class TestOpenInterest:
    """analyze_open_interest 테스트."""

    def test_empty_data(self):
        result = analyze_open_interest([])
        assert result['trend'] == 'stable'

    def test_single_data(self):
        result = analyze_open_interest([1000])
        assert result['current'] == 1000

    def test_increasing_oi(self):
        data = [1100, 1000, 900, 800, 700, 600]
        result = analyze_open_interest(data)
        assert result['trend'] == 'increasing'

    def test_large_change(self):
        data = [1200, 1000]  # +20%
        result = analyze_open_interest(data)
        assert result['significance'] == 'large'

    def test_small_change(self):
        data = [1010, 1000]  # +1%
        result = analyze_open_interest(data)
        assert result['significance'] == 'none'


# ═══════════════════════════════════════════════
# expiry_effect_analyzer 테스트
# ═══════════════════════════════════════════════

class TestGetNextExpiry:
    """get_next_expiry 테스트."""

    def test_basic(self):
        result = get_next_expiry(date(2026, 3, 1))
        assert result['date'] is not None
        assert result['type'] in ('MONTHLY', 'QUARTERLY')

    def test_quarterly_month(self):
        result = get_next_expiry(date(2026, 3, 1))
        # 3월은 분기 만기
        assert result['type'] == 'QUARTERLY'

    def test_monthly_month(self):
        result = get_next_expiry(date(2026, 4, 1))
        assert result['type'] == 'MONTHLY'

    def test_expiry_day(self):
        # 2026년 3월 둘째 주 목요일 찾기
        result = get_next_expiry(date(2026, 3, 1))
        expiry_date = date.fromisoformat(result['date'])
        assert expiry_date.weekday() == 3  # 목요일

    def test_proximity_far(self):
        result = get_next_expiry(date(2026, 3, 1))
        # 3월 1일 → 만기까지 최소 7일
        if result['days_until'] > 5:
            assert result['proximity'] == 'far'

    def test_volatility_premium(self):
        result = get_next_expiry(date(2026, 3, 1))
        assert result['volatility_premium'] in (1.05, 1.15)


class TestAnalyzeExpiryEffect:
    """analyze_expiry_effect 테스트."""

    def test_far_expiry(self):
        expiry_info = {
            'type': 'MONTHLY',
            'proximity': 'far',
            'days_until': 20,
            'volatility_premium': 1.05,
        }
        result = analyze_expiry_effect(expiry_info)
        assert result['impact_score'] == 15
        assert result['patterns'] == []

    def test_expiry_day(self):
        expiry_info = {
            'type': 'QUARTERLY',
            'proximity': 'expiry_day',
            'days_until': 0,
            'volatility_premium': 1.15,
        }
        result = analyze_expiry_effect(expiry_info)
        assert result['impact_score'] > 90
        assert len(result['patterns']) == 4

    def test_approaching(self):
        expiry_info = {
            'type': 'MONTHLY',
            'proximity': 'approaching',
            'days_until': 3,
            'volatility_premium': 1.05,
        }
        result = analyze_expiry_effect(expiry_info)
        assert 'rollover_pressure' in result['patterns']


class TestMaxPain:
    """calc_max_pain 테스트."""

    def test_empty_data(self):
        result = calc_max_pain(None)
        assert result['max_pain_price'] is None

    def test_basic_max_pain(self):
        data = {
            340: {'call_oi': 1000, 'put_oi': 100},
            345: {'call_oi': 500, 'put_oi': 500},
            350: {'call_oi': 100, 'put_oi': 1000},
        }
        result = calc_max_pain(data)
        assert result['max_pain_price'] is not None
        # 중간 행사가(345) 근처가 max pain일 가능성 높음
        assert result['max_pain_price'] in (340, 345, 350)


class TestProgramImpactScore:
    """calc_program_impact_score 테스트."""

    def test_positive(self):
        program = {
            'arbitrage': {'score': 80},
            'non_arbitrage': {'score': 75},
        }
        basis = {'score': 70}
        expiry = {'impact_score': 15}  # far → 영향 작음

        result = calc_program_impact_score(program, basis, expiry)
        assert result['grade'] == 'POSITIVE'

    def test_warning(self):
        program = {
            'arbitrage': {'score': 10},
            'non_arbitrage': {'score': 15},
        }
        basis = {'score': 25}
        expiry = {'impact_score': 95}  # expiry_day → 영향 큼

        result = calc_program_impact_score(program, basis, expiry)
        assert result['grade'] in ('NEGATIVE', 'WARNING')

    def test_components_present(self):
        program = {
            'arbitrage': {'score': 50},
            'non_arbitrage': {'score': 50},
        }
        basis = {'score': 50}
        expiry = {'impact_score': 50}

        result = calc_program_impact_score(program, basis, expiry)
        assert len(result['components']) == 4
        for key in PROGRAM_IMPACT_WEIGHTS:
            assert key in result['components']

    def test_weight_sum(self):
        program = {
            'arbitrage': {'score': 100},
            'non_arbitrage': {'score': 100},
        }
        basis = {'score': 100}
        expiry = {'impact_score': 0}

        result = calc_program_impact_score(program, basis, expiry)
        assert result['score'] == 100.0


# ═══════════════════════════════════════════════
# report_generator 테스트
# ═══════════════════════════════════════════════

class TestGenerateReport:
    """generate_program_trade_report 테스트."""

    def test_basic_report(self):
        program = {
            'signal': 'BUY',
            'arbitrage': {'net': 600_000_000_000, 'classification': 'buy', 'score': 70},
            'non_arbitrage': {'net': 400_000_000_000, 'classification': 'buy', 'score': 70},
            'total': 1_000_000_000_000,
            'consecutive_sell': 0,
        }
        basis = {
            'state': 'FAIR',
            'basis': 0.5,
            'basis_pct': 0.001,
            'deviation': 0.0005,
            'score': 70,
        }
        expiry = {
            'type': 'MONTHLY',
            'date': '2026-03-12',
            'days_until': 8,
            'proximity': 'far',
            'volatility_premium': 1.05,
            'patterns': [],
        }
        report = generate_program_trade_report(program, basis, expiry)
        assert '# 프로그램 매매 분석 리포트' in report
        assert 'BUY' in report
        assert 'FAIR' in report

    def test_with_impact(self):
        program = {
            'signal': 'NEUTRAL',
            'arbitrage': {'net': 0, 'classification': 'neutral', 'score': 50},
            'non_arbitrage': {'net': 0, 'classification': 'neutral', 'score': 50},
            'total': 0,
            'consecutive_sell': 0,
        }
        basis = {'state': 'FAIR', 'basis': 0, 'basis_pct': 0, 'deviation': 0, 'score': 70}
        expiry = {
            'type': 'MONTHLY',
            'date': '2026-03-12',
            'days_until': 8,
            'proximity': 'far',
            'volatility_premium': 1.05,
            'patterns': [],
        }
        impact = {
            'score': 55.0,
            'grade': 'NEUTRAL',
            'label': '중립',
            'components': {
                'arbitrage_flow': {'score': 50, 'weight': 0.25},
                'non_arb_flow': {'score': 50, 'weight': 0.30},
                'basis_signal': {'score': 70, 'weight': 0.25},
                'expiry_effect': {'score': 85, 'weight': 0.20},
            },
        }
        report = generate_program_trade_report(program, basis, expiry, impact)
        assert '종합 등급' in report
        assert 'NEUTRAL' in report
