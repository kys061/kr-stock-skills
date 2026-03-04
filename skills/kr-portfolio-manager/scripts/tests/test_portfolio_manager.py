"""kr-portfolio-manager 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from portfolio_analyzer import (
    ALLOCATION_DIMENSIONS, DIVERSIFICATION, REBALANCING,
    KR_TAX_MODEL, POSITION_ACTIONS, REBALANCING_PRIORITY,
    KRX_SECTORS, MARKET_CAP_TIERS,
    classify_market_cap, calc_position_weight,
    analyze_allocation, analyze_diversification,
    calc_dividend_tax, calc_transaction_cost,
    check_large_shareholder, determine_action,
    analyze_portfolio,
)
from risk_calculator import (
    calc_portfolio_variance, calc_portfolio_volatility,
    calc_sharpe_ratio, calc_max_drawdown, calc_correlation,
    detect_correlation_redundancy, calc_risk_metrics,
)
from rebalancing_engine import (
    build_target_allocation, generate_rebalancing_actions,
    calc_total_rebalancing_cost, apply_tax_optimization,
    generate_rebalancing_report,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_allocation_dimensions(self):
        assert len(ALLOCATION_DIMENSIONS) == 4
        assert 'sector' in ALLOCATION_DIMENSIONS
        assert 'market' in ALLOCATION_DIMENSIONS

    def test_diversification(self):
        assert DIVERSIFICATION['optimal_positions'] == (15, 30)
        assert DIVERSIFICATION['under_diversified'] == 10
        assert DIVERSIFICATION['over_diversified'] == 50
        assert DIVERSIFICATION['max_single_position'] == 0.15
        assert DIVERSIFICATION['max_sector'] == 0.35
        assert DIVERSIFICATION['correlation_redundancy'] == 0.8

    def test_rebalancing(self):
        assert REBALANCING['major_drift'] == 0.10
        assert REBALANCING['moderate_drift'] == 0.05
        assert REBALANCING['excess_cash'] == 0.10

    def test_kr_tax_model(self):
        assert KR_TAX_MODEL['dividend_tax'] == 0.154
        assert KR_TAX_MODEL['financial_income_threshold'] == 20_000_000
        assert KR_TAX_MODEL['capital_gains_tax'] == 0.22
        assert KR_TAX_MODEL['capital_gains_threshold'] == 1_000_000_000
        assert KR_TAX_MODEL['transaction_tax'] == 0.0023
        assert KR_TAX_MODEL['isa_tax_free'] == 2_000_000

    def test_position_actions(self):
        assert POSITION_ACTIONS == ['HOLD', 'ADD', 'TRIM', 'SELL']

    def test_rebalancing_priority(self):
        assert REBALANCING_PRIORITY == ['IMMEDIATE', 'HIGH', 'MEDIUM', 'LOW']

    def test_krx_sectors(self):
        assert len(KRX_SECTORS) == 14
        assert '반도체' in KRX_SECTORS

    def test_market_cap_tiers(self):
        assert MARKET_CAP_TIERS['large'] == 1_000_000_000_000


# ─── 시가총액 분류 ───

class TestClassifyMarketCap:

    def test_large_cap(self):
        assert classify_market_cap(5_000_000_000_000) == 'large'

    def test_mid_cap(self):
        assert classify_market_cap(500_000_000_000) == 'mid'

    def test_small_cap(self):
        assert classify_market_cap(100_000_000_000) == 'small'


# ─── 비중 계산 ───

class TestCalcPositionWeight:

    def test_normal(self):
        assert calc_position_weight(10_000_000, 100_000_000) == 0.1

    def test_zero_total(self):
        assert calc_position_weight(10_000_000, 0) == 0.0


# ─── 자산배분 분석 ───

class TestAnalyzeAllocation:

    def _make_holdings(self):
        return [
            {'symbol': '005930', 'name': '삼성전자', 'value': 50_000_000,
             'sector': '반도체', 'market': 'KOSPI', 'market_cap': 5e12,
             'asset_class': 'stock'},
            {'symbol': '000270', 'name': '기아', 'value': 30_000_000,
             'sector': '자동차', 'market': 'KOSPI', 'market_cap': 1e12,
             'asset_class': 'stock'},
            {'symbol': 'CASH', 'name': '현금', 'value': 20_000_000,
             'sector': '-', 'market': '-', 'market_cap': 0,
             'asset_class': 'cash'},
        ]

    def test_allocation_has_all_dimensions(self):
        result = analyze_allocation(self._make_holdings())
        for dim in ALLOCATION_DIMENSIONS:
            assert dim in result

    def test_sector_allocation(self):
        result = analyze_allocation(self._make_holdings())
        assert '반도체' in result['sector']
        assert result['sector']['반도체']['weight'] == 0.5

    def test_empty_holdings(self):
        result = analyze_allocation([])
        assert all(v == {} for v in result.values())


# ─── 분산투자 분석 ───

class TestAnalyzeDiversification:

    def test_under_diversified(self):
        holdings = [{'value': 100_000_000}] * 5
        result = analyze_diversification(holdings)
        assert result['diversification_status'] == 'under_diversified'

    def test_optimal(self):
        holdings = [{'value': 10_000_000}] * 20
        result = analyze_diversification(holdings)
        assert result['diversification_status'] == 'optimal'

    def test_over_diversified(self):
        holdings = [{'value': 1_000_000}] * 60
        result = analyze_diversification(holdings)
        assert result['diversification_status'] == 'over_diversified'

    def test_concentration_detected(self):
        holdings = [
            {'symbol': 'A', 'name': 'A', 'value': 80_000_000, 'sector': 'X'},
            {'symbol': 'B', 'name': 'B', 'value': 20_000_000, 'sector': 'Y'},
        ]
        result = analyze_diversification(holdings)
        assert len(result['concentration_issues']) > 0
        assert result['concentration_issues'][0]['type'] == 'position_concentration'

    def test_sector_concentration(self):
        holdings = [
            {'symbol': f'S{i}', 'value': 10_000_000, 'sector': '반도체'}
            for i in range(5)
        ] + [
            {'symbol': 'OTHER', 'value': 10_000_000, 'sector': '자동차'}
        ]
        result = analyze_diversification(holdings)
        sector_issues = [i for i in result['concentration_issues']
                         if i['type'] == 'sector_concentration']
        # 반도체 50/60 = 83% > 35%
        assert len(sector_issues) > 0


# ─── 세금 계산 ───

class TestDividendTax:

    def test_normal_dividend(self):
        result = calc_dividend_tax(1_000_000)
        assert result['tax'] == round(1_000_000 * 0.154)
        assert result['effective_rate'] == 0.154
        assert result['comprehensive_taxation'] is False

    def test_comprehensive_taxation(self):
        result = calc_dividend_tax(30_000_000)
        assert result['comprehensive_taxation'] is True

    def test_isa_dividend(self):
        result = calc_dividend_tax(1_000_000, use_isa=True)
        assert result['account_type'] == 'ISA'
        assert result['tax_free'] == 1_000_000
        assert result['tax'] == 0


class TestTransactionCost:

    def test_buy_cost(self):
        result = calc_transaction_cost(10_000_000, is_sell=False)
        assert result['brokerage'] == round(10_000_000 * 0.00015)
        assert result['sell_tax'] == 0

    def test_sell_cost(self):
        result = calc_transaction_cost(10_000_000, is_sell=True)
        assert result['sell_tax'] == round(10_000_000 * 0.0023)
        assert result['total'] > result['brokerage']


# ─── 대주주 확인 ───

class TestLargeShareholder:

    def test_below_threshold(self):
        holdings = [{'symbol': 'A', 'name': 'A', 'value': 500_000_000}]
        assert check_large_shareholder(holdings) == []

    def test_above_threshold(self):
        holdings = [{'symbol': 'A', 'name': 'A', 'value': 1_500_000_000}]
        result = check_large_shareholder(holdings)
        assert len(result) == 1
        assert result[0]['tax_rate'] == 0.22


# ─── 액션 결정 ───

class TestDetermineAction:

    def test_hold(self):
        result = determine_action({'symbol': 'A', 'name': 'A'}, 0.10, 0.11)
        assert result['action'] == 'HOLD'

    def test_trim(self):
        result = determine_action({'symbol': 'A', 'name': 'A'}, 0.10, 0.25)
        assert result['action'] == 'TRIM'
        assert result['priority'] == 'IMMEDIATE'

    def test_add(self):
        result = determine_action({'symbol': 'A', 'name': 'A'}, 0.20, 0.05)
        assert result['action'] == 'ADD'
        assert result['priority'] == 'IMMEDIATE'


# ─── 종합 분석 ───

class TestAnalyzePortfolio:

    def test_valid_analysis(self):
        holdings = [
            {'symbol': '005930', 'name': '삼성전자', 'value': 50_000_000,
             'sector': '반도체', 'market': 'KOSPI', 'market_cap': 5e12,
             'asset_class': 'stock'},
            {'symbol': 'CASH', 'name': '현금', 'value': 5_000_000,
             'sector': '-', 'market': '-', 'market_cap': 0,
             'asset_class': 'cash'},
        ]
        result = analyze_portfolio(holdings)
        assert result['valid'] is True
        assert result['total_value'] == 55_000_000
        assert result['position_count'] == 2

    def test_empty_holdings(self):
        result = analyze_portfolio([])
        assert result['valid'] is False

    def test_excess_cash(self):
        holdings = [
            {'symbol': 'A', 'value': 50_000_000, 'asset_class': 'stock'},
            {'symbol': 'CASH', 'value': 20_000_000, 'asset_class': 'cash'},
        ]
        result = analyze_portfolio(holdings)
        # 현금 20/70 = 28.6% > 10%
        assert result['excess_cash'] is True


# ─── 리스크 계산 ───

class TestRiskCalculator:

    def test_sharpe_ratio(self):
        sharpe = calc_sharpe_ratio(0.12, 0.15)
        # (0.12 - 0.035) / 0.15 = 0.567
        assert 0.5 < sharpe < 0.6

    def test_sharpe_zero_vol(self):
        assert calc_sharpe_ratio(0.12, 0) == 0.0

    def test_max_drawdown(self):
        curve = [100, 110, 105, 90, 95, 100]
        result = calc_max_drawdown(curve)
        # Peak 110, Trough 90, DD = 18.18%
        assert 18 < result['max_drawdown_pct'] < 19

    def test_max_drawdown_empty(self):
        result = calc_max_drawdown([])
        assert result['max_drawdown_pct'] == 0.0

    def test_correlation_positive(self):
        a = [0.01, 0.02, -0.01, 0.03, -0.02]
        b = [0.02, 0.03, -0.005, 0.04, -0.01]
        corr = calc_correlation(a, b)
        assert corr > 0.8

    def test_correlation_insufficient(self):
        assert calc_correlation([0.01], [0.02]) == 0.0

    def test_detect_redundancy(self):
        holdings = [{'symbol': 'A'}, {'symbol': 'B'}]
        returns_data = {
            'A': [0.01, 0.02, -0.01, 0.03, -0.02],
            'B': [0.01, 0.02, -0.01, 0.03, -0.02],  # 완전 동일
        }
        result = detect_correlation_redundancy(holdings, returns_data)
        assert len(result) >= 1
        assert result[0]['correlation'] >= 0.8

    def test_risk_metrics(self):
        holdings = [
            {'symbol': 'A', 'value': 60_000_000},
            {'symbol': 'B', 'value': 40_000_000},
        ]
        result = calc_risk_metrics(holdings)
        assert result['total_value'] == 100_000_000
        assert result['max_position_weight'] == 0.6
        assert result['concentration_risk'] is True


# ─── 리밸런싱 ───

class TestRebalancing:

    def _make_holdings(self):
        return [
            {'symbol': 'A', 'name': 'A종목', 'value': 60_000_000,
             'asset_class': 'stock'},
            {'symbol': 'B', 'name': 'B종목', 'value': 30_000_000,
             'asset_class': 'stock'},
            {'symbol': 'C', 'name': 'C종목', 'value': 10_000_000,
             'asset_class': 'stock'},
        ]

    def test_equal_weight_target(self):
        targets = build_target_allocation(self._make_holdings())
        assert len(targets) == 3
        for w in targets.values():
            assert abs(w - 1/3) < 0.01

    def test_custom_target(self):
        targets = build_target_allocation(
            self._make_holdings(),
            target_weights={'A': 0.4, 'B': 0.4, 'C': 0.2}
        )
        assert targets['A'] == 0.4

    def test_generate_actions(self):
        result = generate_rebalancing_actions(self._make_holdings())
        assert result['valid'] is True
        assert result['action_count'] > 0
        # A는 60% → 33% = TRIM
        a_action = [a for a in result['actions'] if a['symbol'] == 'A'][0]
        assert a_action['action'] == 'TRIM'

    def test_estimated_cost(self):
        result = generate_rebalancing_actions(self._make_holdings())
        assert result['estimated_cost']['total_cost'] > 0

    def test_rebalancing_report(self):
        result = generate_rebalancing_actions(self._make_holdings())
        report = generate_rebalancing_report(result)
        assert '리밸런싱' in report
        assert 'A종목' in report


# ─── 세금 최적화 ───

class TestTaxOptimization:

    def test_comprehensive_tax_warning(self):
        suggestions = apply_tax_optimization([], annual_dividend=25_000_000)
        types = [s['type'] for s in suggestions]
        assert 'comprehensive_tax_warning' in types

    def test_isa_suggestion(self):
        suggestions = apply_tax_optimization([], annual_dividend=3_000_000)
        types = [s['type'] for s in suggestions]
        assert 'isa_suggestion' in types

    def test_sell_tax_impact(self):
        actions = [
            {'action': 'SELL', 'trade_value': 50_000_000},
        ]
        suggestions = apply_tax_optimization(actions)
        types = [s['type'] for s in suggestions]
        assert 'transaction_tax_impact' in types
