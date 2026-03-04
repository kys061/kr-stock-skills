"""kr-options-advisor 테스트."""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from black_scholes import (
    KOSPI200_MULTIPLIER, KOSPI200_TICK_SIZE, KOSPI200_TICK_VALUE,
    KR_RISK_FREE_RATE, VKOSPI_DEFAULT, HV_LOOKBACK, HV_WINDOW,
    ATM_TOLERANCE, STRATEGIES, GREEKS_TARGETS, POSITION_SIZING,
    IV_CRUSH_MODEL,
    calc_d1_d2, bs_call_price, bs_put_price, bs_price,
    calc_greeks, dte_to_years, classify_moneyness,
    premium_to_krw, tick_size_for_premium, round_to_tick,
    calc_iv_crush, calc_historical_volatility,
    calc_position_size, price_option,
)
from strategy_simulator import (
    build_strategy_legs, calc_strategy_cost, calc_strategy_greeks,
    calc_expiry_payoff, calc_breakeven_points, calc_max_profit_loss,
    simulate_iv_crush, check_greeks_warnings,
    simulate_strategy, get_strategies_by_category,
    get_strategy_categories,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_kospi200_multiplier(self):
        assert KOSPI200_MULTIPLIER == 250_000

    def test_tick_size(self):
        assert KOSPI200_TICK_SIZE == 0.01

    def test_tick_value(self):
        assert KOSPI200_TICK_VALUE == 2_500

    def test_risk_free_rate(self):
        assert KR_RISK_FREE_RATE == 0.035

    def test_vkospi_default(self):
        assert VKOSPI_DEFAULT == 0.20

    def test_hv_lookback(self):
        assert HV_LOOKBACK == 90

    def test_hv_window(self):
        assert HV_WINDOW == 30

    def test_atm_tolerance(self):
        assert ATM_TOLERANCE == 0.02

    def test_strategies_count(self):
        assert len(STRATEGIES) == 18

    def test_strategy_categories(self):
        categories = set(s['category'] for s in STRATEGIES.values())
        assert categories == {'income', 'protection', 'directional',
                              'volatility', 'advanced'}

    def test_greeks_targets(self):
        assert GREEKS_TARGETS['delta'] == (-10, 10)
        assert GREEKS_TARGETS['theta'] == 'positive'
        assert GREEKS_TARGETS['vega_warning'] == 500

    def test_position_sizing(self):
        assert POSITION_SIZING['risk_tolerance'] == 0.02

    def test_iv_crush_model(self):
        assert IV_CRUSH_MODEL['pre_earnings_iv_premium'] == 1.5
        assert IV_CRUSH_MODEL['post_earnings_iv_drop'] == 0.625


# ─── d1/d2 계산 ───

class TestCalcD1D2:

    def test_atm_option(self):
        d1, d2 = calc_d1_d2(350, 350, 30/365, 0.20, 0.035)
        assert d1 > d2
        assert abs(d1 - d2) == pytest.approx(0.20 * math.sqrt(30/365), abs=0.001)

    def test_zero_time(self):
        d1, d2 = calc_d1_d2(350, 350, 0, 0.20, 0.035)
        assert d1 == 0.0
        assert d2 == 0.0

    def test_zero_vol(self):
        d1, d2 = calc_d1_d2(350, 350, 30/365, 0, 0.035)
        assert d1 == 0.0
        assert d2 == 0.0


# ─── BS 가격결정 ───

class TestBSPricing:

    def test_call_positive(self):
        price = bs_call_price(350, 350, 30/365, 0.20, 0.035)
        assert price > 0

    def test_put_positive(self):
        price = bs_put_price(350, 350, 30/365, 0.20, 0.035)
        assert price > 0

    def test_put_call_parity(self):
        """풋-콜 패리티: C - P = S - K*e^(-rT)"""
        spot, strike, t, vol, r = 350, 355, 30/365, 0.20, 0.035
        call = bs_call_price(spot, strike, t, vol, r)
        put = bs_put_price(spot, strike, t, vol, r)
        parity = spot - strike * math.exp(-r * t)
        assert call - put == pytest.approx(parity, abs=0.01)

    def test_deep_itm_call(self):
        price = bs_call_price(400, 300, 30/365, 0.20, 0.035)
        assert price > 99.0  # 깊은 ITM

    def test_deep_otm_call(self):
        price = bs_call_price(300, 400, 30/365, 0.20, 0.035)
        assert price < 1.0  # 깊은 OTM

    def test_expired_call_itm(self):
        price = bs_call_price(360, 350, 0, 0.20, 0.035)
        assert price == 10.0

    def test_expired_call_otm(self):
        price = bs_call_price(340, 350, 0, 0.20, 0.035)
        assert price == 0.0

    def test_bs_price_unified(self):
        c1 = bs_call_price(350, 355, 30/365, 0.20, 0.035)
        c2 = bs_price(350, 355, 30/365, 0.20, 'call', 0.035)
        assert c1 == c2

    def test_higher_vol_higher_price(self):
        low_vol = bs_call_price(350, 350, 30/365, 0.15, 0.035)
        high_vol = bs_call_price(350, 350, 30/365, 0.30, 0.035)
        assert high_vol > low_vol

    def test_longer_dte_higher_price(self):
        short = bs_call_price(350, 350, 15/365, 0.20, 0.035)
        long = bs_call_price(350, 350, 60/365, 0.20, 0.035)
        assert long > short


# ─── 그릭스 ───

class TestGreeks:

    def test_call_delta_range(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'call')
        assert 0 < greeks['delta'] < 1

    def test_put_delta_range(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'put')
        assert -1 < greeks['delta'] < 0

    def test_atm_call_delta_near_05(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'call')
        assert 0.4 < greeks['delta'] < 0.7

    def test_gamma_positive(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'call')
        assert greeks['gamma'] > 0

    def test_theta_negative(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'call')
        assert greeks['theta'] < 0

    def test_vega_positive(self):
        greeks = calc_greeks(350, 350, 30/365, 0.20, 'call')
        assert greeks['vega'] > 0

    def test_expired_greeks(self):
        greeks = calc_greeks(350, 350, 0, 0.20, 'call')
        assert greeks['gamma'] == 0.0
        assert greeks['theta'] == 0.0
        assert greeks['vega'] == 0.0


# ─── 유틸리티 ───

class TestUtilities:

    def test_dte_to_years(self):
        assert dte_to_years(365) == 1.0
        assert dte_to_years(30) == pytest.approx(30/365)

    def test_classify_moneyness_atm(self):
        assert classify_moneyness(350, 350, 'call') == 'ATM'
        assert classify_moneyness(350, 353, 'call') == 'ATM'  # 0.86% < 2%

    def test_classify_moneyness_itm(self):
        assert classify_moneyness(370, 350, 'call') == 'ITM'
        assert classify_moneyness(330, 350, 'put') == 'ITM'

    def test_classify_moneyness_otm(self):
        assert classify_moneyness(330, 350, 'call') == 'OTM'
        assert classify_moneyness(370, 350, 'put') == 'OTM'

    def test_premium_to_krw(self):
        assert premium_to_krw(1.0) == 250_000
        assert premium_to_krw(5.0, 2) == 2_500_000

    def test_tick_size_for_premium(self):
        assert tick_size_for_premium(2.5) == 0.01
        assert tick_size_for_premium(3.0) == 0.05
        assert tick_size_for_premium(10.0) == 0.05

    def test_round_to_tick(self):
        assert round_to_tick(2.534) == 2.53
        assert round_to_tick(5.13) == 5.15  # 0.05 단위

    def test_iv_crush(self):
        result = calc_iv_crush(0.20)
        assert result['pre_earnings_iv'] == 0.30  # 0.20 * 1.5
        assert result['post_earnings_iv'] == 0.1875  # 0.30 * 0.625
        assert result['crush_pct'] == 37.5

    def test_historical_volatility_insufficient_data(self):
        assert calc_historical_volatility([100, 101]) == VKOSPI_DEFAULT

    def test_historical_volatility_valid(self):
        # 31개 가격 (window=30 이상 필요)
        prices = [100 + i * 0.1 for i in range(31)]
        vol = calc_historical_volatility(prices)
        assert vol > 0
        assert vol < 1.0  # 연율 100% 미만

    def test_position_size(self):
        result = calc_position_size(100_000_000, 2.0)
        assert result['max_contracts'] > 0
        assert result['required_capital'] > 0
        assert result['risk_pct'] <= 2.0


# ─── 종합 분석 ───

class TestPriceOption:

    def test_full_analysis(self):
        result = price_option(350, 355, 30, 0.20, 'call')
        assert result['spot'] == 350
        assert result['strike'] == 355
        assert result['dte'] == 30
        assert result['option_type'] == 'call'
        assert result['price'] > 0
        assert result['price_krw'] > 0
        assert result['moneyness'] in ('ITM', 'ATM', 'OTM')
        assert 'delta' in result['greeks']

    def test_default_vol(self):
        result = price_option(350, 350, 30)
        assert result['volatility'] == VKOSPI_DEFAULT


# ─── 전략 레그 빌드 ───

class TestBuildStrategyLegs:

    def test_bull_call_spread(self):
        legs = build_strategy_legs('bull_call_spread', 350, 30, 0.20, 5.0)
        assert len(legs) == 2
        assert legs[0]['action'] == 'buy'
        assert legs[1]['action'] == 'sell'
        assert legs[0]['type'] == 'call'

    def test_iron_condor(self):
        legs = build_strategy_legs('iron_condor', 350, 30, 0.20, 5.0)
        assert len(legs) == 4

    def test_unknown_strategy(self):
        legs = build_strategy_legs('unknown', 350, 30, 0.20)
        assert legs == []


# ─── 전략 비용 ───

class TestStrategyCost:

    def test_debit_spread(self):
        legs = build_strategy_legs('bull_call_spread', 350, 30, 0.20)
        cost = calc_strategy_cost(legs)
        assert cost['is_debit'] is True
        assert cost['net_premium'] < 0

    def test_credit_spread(self):
        legs = build_strategy_legs('bull_put_spread', 350, 30, 0.20)
        cost = calc_strategy_cost(legs)
        assert cost['is_debit'] is False
        assert cost['net_premium'] > 0


# ─── 전략 그릭스 ───

class TestStrategyGreeks:

    def test_straddle_delta_near_zero(self):
        legs = build_strategy_legs('long_straddle', 350, 30, 0.20)
        greeks = calc_strategy_greeks(legs)
        assert abs(greeks['delta']) < 0.2  # 델타 중립에 근접

    def test_iron_condor_greeks(self):
        legs = build_strategy_legs('iron_condor', 350, 30, 0.20)
        greeks = calc_strategy_greeks(legs)
        assert 'delta' in greeks
        assert 'gamma' in greeks


# ─── 만기 손익 ───

class TestExpiryPayoff:

    def test_long_call_itm(self):
        legs = [{'type': 'call', 'strike': 350, 'action': 'buy'}]
        payoff = calc_expiry_payoff(legs, 360, -5.0)
        assert payoff == 5.0  # 10 intrinsic - 5 premium

    def test_long_call_otm(self):
        legs = [{'type': 'call', 'strike': 350, 'action': 'buy'}]
        payoff = calc_expiry_payoff(legs, 340, -5.0)
        assert payoff == -5.0  # 0 intrinsic - 5 premium

    def test_short_put_otm(self):
        legs = [{'type': 'put', 'strike': 340, 'action': 'sell'}]
        payoff = calc_expiry_payoff(legs, 350, 3.0)
        assert payoff == 3.0  # premium received, OTM


# ─── 손익분기 ───

class TestBreakeven:

    def test_single_leg_breakeven(self):
        legs = [{'type': 'call', 'strike': 350, 'action': 'buy'}]
        bkevens = calc_breakeven_points(legs, -5.0, 350)
        assert len(bkevens) >= 1
        # 손익분기 = 행사가 + 프리미엄 = 355 부근
        assert any(354 < b < 356 for b in bkevens)


# ─── 최대 이익/손실 ───

class TestMaxProfitLoss:

    def test_bull_call_spread(self):
        legs = build_strategy_legs('bull_call_spread', 350, 30, 0.20, 5.0)
        cost = calc_strategy_cost(legs)
        result = calc_max_profit_loss(legs, cost['net_premium'], 350)
        assert result['max_profit'] > 0
        assert result['max_loss'] < 0
        # 최대이익은 스프레드 폭 - 순비용 이하
        assert result['max_profit'] <= 5.0


# ─── IV Crush 시뮬레이션 ───

class TestIVCrush:

    def test_short_straddle_benefits(self):
        """숏 스트래들은 IV 하락 시 이익."""
        legs = build_strategy_legs('short_straddle', 350, 30, 0.20)
        result = simulate_iv_crush(legs, 350, 30, 0.20)
        assert result['pnl'] > 0  # IV 하락 시 매도 포지션 이익


# ─── 그릭스 경고 ───

class TestGreeksWarnings:

    def test_no_warnings(self):
        greeks = {'delta': 0.5, 'gamma': 0.01, 'theta': -0.05,
                  'vega': 100, 'rho': 0.01}
        warnings = check_greeks_warnings(greeks)
        assert len(warnings) == 0

    def test_delta_warning(self):
        greeks = {'delta': 15.0, 'vega': 100}
        warnings = check_greeks_warnings(greeks)
        assert any('델타' in w for w in warnings)

    def test_vega_warning(self):
        greeks = {'delta': 0.5, 'vega': 600}
        warnings = check_greeks_warnings(greeks)
        assert any('베가' in w for w in warnings)


# ─── 전략 시뮬레이션 통합 ───

class TestSimulateStrategy:

    def test_valid_strategy(self):
        result = simulate_strategy('bull_call_spread', 350, 30, 0.20)
        assert result['valid'] is True
        assert result['strategy'] == 'bull_call_spread'
        assert result['category'] == 'directional'
        assert result['max_profit'] > 0
        assert result['max_loss'] < 0

    def test_invalid_strategy(self):
        result = simulate_strategy('nonexistent', 350, 30)
        assert result['valid'] is False

    def test_all_strategies_simulate(self):
        """18개 전략 모두 시뮬레이션 가능."""
        for name in STRATEGIES:
            result = simulate_strategy(name, 350, 30, 0.20)
            assert result['valid'] is True, f'{name} failed'
            assert len(result['legs']) > 0


# ─── 카테고리 조회 ───

class TestCategories:

    def test_get_by_category(self):
        income = get_strategies_by_category('income')
        assert len(income) == 3
        assert 'covered_call' in income

    def test_get_categories(self):
        cats = get_strategy_categories()
        assert len(cats) == 5
