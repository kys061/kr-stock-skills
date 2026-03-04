"""kr-dividend-tax 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tax_calculator import (
    DIVIDEND_TAX, FINANCIAL_INCOME_TAX, CAPITAL_GAINS_TAX,
    TRANSACTION_TAX, ISA_ACCOUNT, PENSION_SAVINGS, IRP_ACCOUNT,
    TAX_OPTIMIZATION_STRATEGIES, ACCOUNT_TAX_COMPARISON,
    calc_dividend_tax, calc_financial_income_tax,
    calc_capital_gains_tax, calc_transaction_tax,
    calc_isa_tax, calc_pension_deduction, calc_total_tax_burden,
)
from account_optimizer import (
    ACCOUNT_PRIORITY, ALLOCATION_RULES,
    recommend_account_allocation, calc_account_benefit,
    optimize_threshold_management, generate_tax_optimization_tips,
)
from report_generator import DividendTaxReportGenerator


# ═══════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════

class TestConstants:
    """상수 검증."""

    def test_dividend_tax_rate(self):
        assert DIVIDEND_TAX['rate'] == 0.154

    def test_dividend_tax_components(self):
        assert abs(DIVIDEND_TAX['income_tax'] + DIVIDEND_TAX['local_tax'] - 0.154) < 1e-9

    def test_financial_threshold(self):
        assert FINANCIAL_INCOME_TAX['threshold'] == 20_000_000

    def test_progressive_rates_count(self):
        assert len(FINANCIAL_INCOME_TAX['progressive_rates']) == 8

    def test_progressive_rates_ascending(self):
        rates = FINANCIAL_INCOME_TAX['progressive_rates']
        for i in range(len(rates) - 1):
            assert rates[i][0] < rates[i + 1][0]
            assert rates[i][1] < rates[i + 1][1]

    def test_capital_gains_major_threshold(self):
        assert CAPITAL_GAINS_TAX['major_shareholder_threshold'] == 1_000_000_000

    def test_capital_gains_rates(self):
        assert CAPITAL_GAINS_TAX['major_shareholder_rate_long'] == 0.22
        assert CAPITAL_GAINS_TAX['major_shareholder_rate_short'] == 0.33
        assert CAPITAL_GAINS_TAX['sme_rate'] == 0.11

    def test_transaction_tax(self):
        assert TRANSACTION_TAX['kospi'] == 0.0023
        assert TRANSACTION_TAX['kosdaq'] == 0.0023
        assert TRANSACTION_TAX['konex'] == 0.0010

    def test_isa_limits(self):
        assert ISA_ACCOUNT['tax_free_limit'] == 2_000_000
        assert ISA_ACCOUNT['tax_free_limit_low_income'] == 4_000_000
        assert ISA_ACCOUNT['excess_tax_rate'] == 0.099

    def test_pension_limits(self):
        assert PENSION_SAVINGS['tax_deduction_limit'] == 6_000_000
        assert PENSION_SAVINGS['deduction_rate_under_5500'] == 0.165
        assert PENSION_SAVINGS['deduction_rate_over_5500'] == 0.132

    def test_irp_limits(self):
        assert IRP_ACCOUNT['tax_deduction_limit'] == 9_000_000
        assert IRP_ACCOUNT['safe_asset_ratio'] == 0.30

    def test_irp_combined_limit(self):
        assert IRP_ACCOUNT['combined_limit_with_pension'] == 18_000_000

    def test_optimization_strategies_count(self):
        assert len(TAX_OPTIMIZATION_STRATEGIES) == 6

    def test_strategy_ids(self):
        ids = {s['id'] for s in TAX_OPTIMIZATION_STRATEGIES}
        expected = {'ISA_FIRST', 'PENSION_DEDUCTION', 'IRP_EXTRA_DEDUCTION',
                    'INCOME_THRESHOLD_MGMT', 'LOSS_HARVESTING', 'HOLDING_PERIOD'}
        assert ids == expected

    def test_account_comparison_keys(self):
        assert set(ACCOUNT_TAX_COMPARISON.keys()) == {'GENERAL', 'ISA', 'PENSION_SAVINGS', 'IRP'}

    def test_account_priority_count(self):
        assert len(ACCOUNT_PRIORITY) == 4

    def test_account_priority_order(self):
        accounts = [a['account'] for a in ACCOUNT_PRIORITY]
        assert accounts == ['ISA', 'PENSION_SAVINGS', 'IRP', 'GENERAL']

    def test_allocation_rules(self):
        assert ALLOCATION_RULES['high_yield_first_to_isa'] is True
        assert ALLOCATION_RULES['threshold_management'] is True


# ═══════════════════════════════════════════════════════
# Dividend Tax Tests
# ═══════════════════════════════════════════════════════

class TestDividendTax:
    """배당소득세 계산 테스트."""

    def test_general_account(self):
        result = calc_dividend_tax(1_000_000, 'GENERAL')
        assert result['tax'] == round(1_000_000 * 0.154)
        assert result['net'] == 1_000_000 - result['tax']

    def test_isa_within_limit(self):
        result = calc_dividend_tax(1_500_000, 'ISA')
        assert result['tax'] == 0  # 200만원 이하 비과세

    def test_isa_over_limit(self):
        result = calc_dividend_tax(3_000_000, 'ISA')
        # 200만 비과세, 100만 × 9.9%
        assert result['tax'] == round(1_000_000 * 0.099)

    def test_pension_deferred(self):
        result = calc_dividend_tax(5_000_000, 'PENSION_SAVINGS')
        assert result['tax'] == 0

    def test_irp_deferred(self):
        result = calc_dividend_tax(5_000_000, 'IRP')
        assert result['tax'] == 0

    def test_zero_dividend(self):
        result = calc_dividend_tax(0, 'GENERAL')
        assert result['tax'] == 0
        assert result['net'] == 0

    def test_effective_rate_general(self):
        result = calc_dividend_tax(10_000_000, 'GENERAL')
        assert abs(result['effective_rate'] - 0.154) < 0.001

    def test_effective_rate_isa(self):
        result = calc_dividend_tax(2_000_000, 'ISA')
        assert result['effective_rate'] == 0.0


# ═══════════════════════════════════════════════════════
# Financial Income Tax Tests
# ═══════════════════════════════════════════════════════

class TestFinancialIncomeTax:
    """금융소득종합과세 테스트."""

    def test_below_threshold(self):
        result = calc_financial_income_tax(5_000_000, 10_000_000)
        assert result['threshold_exceeded'] is False
        assert result['additional_tax'] == 0

    def test_at_threshold(self):
        result = calc_financial_income_tax(10_000_000, 10_000_000)
        assert result['threshold_exceeded'] is False

    def test_above_threshold(self):
        result = calc_financial_income_tax(10_000_000, 15_000_000)
        assert result['threshold_exceeded'] is True
        assert result['additional_tax'] > 0

    def test_base_tax(self):
        result = calc_financial_income_tax(0, 15_000_000)
        assert result['base_tax'] == round(15_000_000 * 0.154)

    def test_large_income(self):
        result = calc_financial_income_tax(0, 100_000_000)
        assert result['threshold_exceeded'] is True
        assert result['total_tax'] > result['base_tax']

    def test_zero_income(self):
        result = calc_financial_income_tax(0, 0)
        assert result['total_tax'] == 0
        assert result['threshold_exceeded'] is False


# ═══════════════════════════════════════════════════════
# Capital Gains Tax Tests
# ═══════════════════════════════════════════════════════

class TestCapitalGainsTax:
    """양도소득세 테스트."""

    def test_small_investor_exempt(self):
        result = calc_capital_gains_tax(50_000_000, is_major_shareholder=False)
        assert result['tax'] == 0

    def test_major_long(self):
        result = calc_capital_gains_tax(100_000_000, holding_period_years=2,
                                        is_major_shareholder=True)
        assert result['effective_rate'] == 0.22

    def test_major_short(self):
        result = calc_capital_gains_tax(100_000_000, holding_period_years=0.5,
                                        is_major_shareholder=True)
        assert result['effective_rate'] == 0.33

    def test_sme_major(self):
        result = calc_capital_gains_tax(100_000_000, is_major_shareholder=True,
                                        is_sme=True)
        assert result['effective_rate'] == 0.11

    def test_zero_gains(self):
        result = calc_capital_gains_tax(0, is_major_shareholder=True)
        assert result['tax'] == 0

    def test_negative_gains(self):
        result = calc_capital_gains_tax(-5_000_000)
        assert result['tax'] == 0


# ═══════════════════════════════════════════════════════
# Transaction Tax Tests
# ═══════════════════════════════════════════════════════

class TestTransactionTax:
    """증권거래세 테스트."""

    def test_kospi(self):
        result = calc_transaction_tax(100_000_000, 'kospi')
        assert result['tax'] == 230_000

    def test_kosdaq(self):
        result = calc_transaction_tax(100_000_000, 'kosdaq')
        assert result['tax'] == 230_000

    def test_konex(self):
        result = calc_transaction_tax(100_000_000, 'konex')
        assert result['tax'] == 100_000

    def test_zero_amount(self):
        result = calc_transaction_tax(0)
        assert result['tax'] == 0

    def test_default_market(self):
        result = calc_transaction_tax(10_000_000)
        assert result['market'] == 'kospi'


# ═══════════════════════════════════════════════════════
# ISA Tax Tests
# ═══════════════════════════════════════════════════════

class TestISATax:
    """ISA 계좌 세금 테스트."""

    def test_within_limit(self):
        result = calc_isa_tax(1_500_000)
        assert result['tax'] == 0
        assert result['tax_free'] == 1_500_000

    def test_at_limit(self):
        result = calc_isa_tax(2_000_000)
        assert result['tax'] == 0
        assert result['tax_free'] == 2_000_000

    def test_over_limit(self):
        result = calc_isa_tax(5_000_000)
        assert result['tax_free'] == 2_000_000
        assert result['taxable'] == 3_000_000
        assert result['tax'] == round(3_000_000 * 0.099)

    def test_low_income(self):
        result = calc_isa_tax(3_000_000, is_low_income=True)
        assert result['tax'] == 0  # 400만원 한도

    def test_low_income_over(self):
        result = calc_isa_tax(6_000_000, is_low_income=True)
        assert result['tax_free'] == 4_000_000
        assert result['tax'] == round(2_000_000 * 0.099)

    def test_zero_income(self):
        result = calc_isa_tax(0)
        assert result['tax'] == 0


# ═══════════════════════════════════════════════════════
# Pension Deduction Tests
# ═══════════════════════════════════════════════════════

class TestPensionDeduction:
    """연금저축/IRP 세액공제 테스트."""

    def test_full_pension_low_salary(self):
        result = calc_pension_deduction(6_000_000, 40_000_000)
        assert result['deduction_rate'] == 0.165
        assert result['tax_saved'] == round(6_000_000 * 0.165)

    def test_full_pension_high_salary(self):
        result = calc_pension_deduction(6_000_000, 70_000_000)
        assert result['deduction_rate'] == 0.132
        assert result['tax_saved'] == round(6_000_000 * 0.132)

    def test_partial_pension(self):
        result = calc_pension_deduction(3_000_000, 40_000_000)
        assert result['tax_saved'] == round(3_000_000 * 0.165)

    def test_over_cap(self):
        result = calc_pension_deduction(10_000_000, 40_000_000)
        # 공제 한도 600만원
        assert result['tax_saved'] == round(6_000_000 * 0.165)

    def test_pension_plus_irp(self):
        result = calc_pension_deduction(6_000_000, 40_000_000, include_irp=3_000_000)
        # 연금 600만 + IRP 300만 = 총 900만
        assert result['tax_saved'] == round(9_000_000 * 0.165)

    def test_irp_over_cap(self):
        result = calc_pension_deduction(6_000_000, 40_000_000, include_irp=5_000_000)
        # IRP 추가 한도 300만원
        assert result['tax_saved'] == round(9_000_000 * 0.165)

    def test_zero_contribution(self):
        result = calc_pension_deduction(0, 50_000_000)
        assert result['tax_saved'] == 0


# ═══════════════════════════════════════════════════════
# Total Tax Burden Tests
# ═══════════════════════════════════════════════════════

class TestTotalTaxBurden:
    """전체 세금 부담 테스트."""

    def test_basic_portfolio(self):
        portfolio = {
            'dividend_income': 5_000_000,
            'sell_amount': 50_000_000,
            'market': 'kospi',
            'account_type': 'GENERAL',
        }
        result = calc_total_tax_burden(portfolio)
        assert result['dividend_tax'] == round(5_000_000 * 0.154)
        assert result['transaction_tax'] == round(50_000_000 * 0.0023)
        assert result['total_tax'] > 0

    def test_isa_portfolio(self):
        portfolio = {
            'dividend_income': 1_500_000,
            'account_type': 'ISA',
        }
        result = calc_total_tax_burden(portfolio)
        assert result['dividend_tax'] == 0  # ISA 비과세 범위

    def test_no_financial_threshold(self):
        portfolio = {
            'dividend_income': 10_000_000,
            'interest_income': 5_000_000,
            'account_type': 'GENERAL',
        }
        result = calc_total_tax_burden(portfolio)
        assert result['financial_income_tax'] == 0

    def test_financial_threshold_exceeded(self):
        portfolio = {
            'dividend_income': 15_000_000,
            'interest_income': 10_000_000,
            'account_type': 'GENERAL',
        }
        result = calc_total_tax_burden(portfolio)
        assert result['financial_income_tax'] > 0

    def test_optimization_tips_present(self):
        portfolio = {
            'dividend_income': 5_000_000,
            'account_type': 'GENERAL',
        }
        result = calc_total_tax_burden(portfolio)
        assert isinstance(result['optimization_tips'], list)
        assert len(result['optimization_tips']) > 0

    def test_effective_rate(self):
        portfolio = {
            'dividend_income': 10_000_000,
            'account_type': 'GENERAL',
        }
        result = calc_total_tax_burden(portfolio)
        assert 0 < result['effective_rate'] <= 1.0


# ═══════════════════════════════════════════════════════
# Account Allocation Tests
# ═══════════════════════════════════════════════════════

class TestAccountAllocation:
    """계좌 배치 추천 테스트."""

    def test_high_yield_to_isa(self):
        holdings = [
            {'ticker': '005930', 'name': '삼성전자', 'dividend_yield': 3.0,
             'annual_dividend': 1_500_000, 'holding_type': 'high_yield'},
        ]
        result = recommend_account_allocation(holdings)
        assert result['allocations'][0]['recommended_account'] == 'ISA'
        assert result['total_tax_saved'] > 0

    def test_growth_to_pension(self):
        holdings = [
            {'ticker': '035720', 'name': '카카오', 'dividend_yield': 0.5,
             'annual_dividend': 100_000, 'holding_type': 'growth'},
        ]
        result = recommend_account_allocation(holdings)
        assert result['allocations'][0]['recommended_account'] == 'PENSION_SAVINGS'

    def test_bond_to_irp(self):
        holdings = [
            {'ticker': '148070', 'name': '채권ETF', 'dividend_yield': 2.0,
             'annual_dividend': 500_000, 'holding_type': 'bond_etf'},
        ]
        result = recommend_account_allocation(holdings)
        assert result['allocations'][0]['recommended_account'] == 'IRP'

    def test_trading_to_general(self):
        holdings = [
            {'ticker': '000660', 'name': 'SK하이닉스', 'dividend_yield': 1.0,
             'annual_dividend': 200_000, 'holding_type': 'trading'},
        ]
        result = recommend_account_allocation(holdings)
        assert result['allocations'][0]['recommended_account'] == 'GENERAL'

    def test_empty_holdings(self):
        result = recommend_account_allocation([])
        assert result['total_tax_saved'] == 0

    def test_multiple_holdings(self):
        holdings = [
            {'ticker': '005930', 'name': '삼성전자', 'dividend_yield': 3.0,
             'annual_dividend': 1_000_000, 'holding_type': 'high_yield'},
            {'ticker': '035720', 'name': '카카오', 'dividend_yield': 0.5,
             'annual_dividend': 100_000, 'holding_type': 'growth'},
            {'ticker': '148070', 'name': '채권ETF', 'dividend_yield': 2.0,
             'annual_dividend': 500_000, 'holding_type': 'bond_etf'},
        ]
        result = recommend_account_allocation(holdings)
        assert len(result['allocations']) == 3
        accounts = {a['recommended_account'] for a in result['allocations']}
        assert 'ISA' in accounts


# ═══════════════════════════════════════════════════════
# Account Benefit Tests
# ═══════════════════════════════════════════════════════

class TestAccountBenefit:
    """계좌별 세금 혜택 비교 테스트."""

    def test_general_baseline(self):
        result = calc_account_benefit({'annual_dividend': 5_000_000}, 'GENERAL')
        assert result['vs_general_saved'] == 0

    def test_isa_benefit(self):
        result = calc_account_benefit({'annual_dividend': 2_000_000}, 'ISA')
        assert result['vs_general_saved'] > 0

    def test_pension_benefit(self):
        result = calc_account_benefit({'annual_dividend': 3_000_000}, 'PENSION_SAVINGS')
        assert result['total_tax'] == 0
        assert result['vs_general_saved'] > 0

    def test_zero_holding(self):
        result = calc_account_benefit({'annual_dividend': 0}, 'ISA')
        assert result['vs_general_saved'] == 0


# ═══════════════════════════════════════════════════════
# Threshold Management Tests
# ═══════════════════════════════════════════════════════

class TestThresholdManagement:
    """금융소득 기준 관리 테스트."""

    def test_safe(self):
        result = optimize_threshold_management(10_000_000)
        assert result['risk_level'] == 'SAFE'
        assert result['exceeded'] is False

    def test_caution(self):
        result = optimize_threshold_management(15_000_000)
        assert result['risk_level'] == 'CAUTION'

    def test_warning(self):
        result = optimize_threshold_management(19_000_000)
        assert result['risk_level'] == 'WARNING'

    def test_exceeded(self):
        result = optimize_threshold_management(25_000_000)
        assert result['risk_level'] == 'EXCEEDED'
        assert result['exceeded'] is True
        assert result['excess'] == 5_000_000

    def test_remaining(self):
        result = optimize_threshold_management(15_000_000)
        assert result['remaining'] == 5_000_000

    def test_recommendations_on_warning(self):
        result = optimize_threshold_management(19_000_000)
        assert len(result['recommendations']) > 0


# ═══════════════════════════════════════════════════════
# Tax Optimization Tips Tests
# ═══════════════════════════════════════════════════════

class TestTaxOptimizationTips:
    """절세 팁 테스트."""

    def test_isa_tip_for_general(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 3_000_000,
            'total_interest': 0,
            'account_type': 'GENERAL',
            'salary': 50_000_000,
            'pension_contribution': 0,
            'irp_contribution': 0,
        })
        ids = [t['id'] for t in tips]
        assert 'ISA_FIRST' in ids

    def test_pension_tip(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 1_000_000,
            'total_interest': 0,
            'account_type': 'ISA',
            'salary': 50_000_000,
            'pension_contribution': 0,
            'irp_contribution': 0,
        })
        ids = [t['id'] for t in tips]
        assert 'PENSION_DEDUCTION' in ids

    def test_irp_tip(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 1_000_000,
            'total_interest': 0,
            'account_type': 'ISA',
            'salary': 50_000_000,
            'pension_contribution': 6_000_000,
            'irp_contribution': 0,
        })
        ids = [t['id'] for t in tips]
        assert 'IRP_EXTRA_DEDUCTION' in ids

    def test_threshold_warning(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 12_000_000,
            'total_interest': 5_000_000,
            'account_type': 'GENERAL',
            'salary': 50_000_000,
            'pension_contribution': 6_000_000,
            'irp_contribution': 3_000_000,
        })
        ids = [t['id'] for t in tips]
        assert 'INCOME_THRESHOLD_MGMT' in ids

    def test_major_shareholder_tip(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 1_000_000,
            'total_interest': 0,
            'account_type': 'GENERAL',
            'salary': 50_000_000,
            'pension_contribution': 6_000_000,
            'irp_contribution': 3_000_000,
            'is_major_shareholder': True,
        })
        ids = [t['id'] for t in tips]
        assert 'HOLDING_PERIOD' in ids

    def test_tips_have_benefit(self):
        tips = generate_tax_optimization_tips({
            'total_dividend': 3_000_000,
            'total_interest': 0,
            'account_type': 'GENERAL',
            'salary': 40_000_000,
            'pension_contribution': 0,
            'irp_contribution': 0,
        })
        for tip in tips:
            assert 'potential_benefit' in tip


# ═══════════════════════════════════════════════════════
# Report Generator Tests
# ═══════════════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성 테스트."""

    def test_generate(self):
        gen = DividendTaxReportGenerator()
        gen.add_tax_summary({
            'dividend_tax': 770_000, 'transaction_tax': 115_000,
            'gains_tax': 0, 'financial_income_tax': 0,
            'total_tax': 885_000, 'net_income': 4_115_000,
            'effective_rate': 0.177,
        })
        gen.add_account_allocations({
            'allocations': [
                {'name': '삼성전자', 'recommended_account': 'ISA', 'tax_saved': 308_000},
            ],
            'total_tax_saved': 308_000,
        })
        gen.add_threshold_status({
            'current_income': 15_000_000, 'threshold': 20_000_000,
            'remaining': 5_000_000, 'risk_level': 'CAUTION',
        })
        gen.add_optimization_tips([
            {'id': 'ISA_FIRST', 'name': 'ISA 우선 활용',
             'description': 'ISA로 이전 시 절세', 'potential_benefit': 308_000},
        ])
        report = gen.generate()
        assert '배당 세금 최적화 리포트' in report
        assert '삼성전자' in report
        assert 'ISA' in report
        assert 'CAUTION' in report
