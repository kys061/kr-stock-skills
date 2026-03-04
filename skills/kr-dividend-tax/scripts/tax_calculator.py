"""kr-dividend-tax: 한국 투자 세금 계산 엔진.

2026년 한국 세법 기준.
배당소득세, 금융소득종합과세, 양도소득세, 증권거래세,
ISA, 연금저축, IRP 세제를 계산한다.
"""

# ═══════════════════════════════════════════════════════
# 한국 투자 세제 상수 (2026년 기준)
# ═══════════════════════════════════════════════════════

# ─── 1. 배당소득세 ───
DIVIDEND_TAX = {
    'rate': 0.154,                      # 15.4% (소득세 14% + 지방세 1.4%)
    'income_tax': 0.14,                 # 소득세 14%
    'local_tax': 0.014,                 # 지방소득세 1.4% (소득세의 10%)
    'withholding': True,                # 원천징수 여부
}

# ─── 2. 금융소득종합과세 ───
FINANCIAL_INCOME_TAX = {
    'threshold': 20_000_000,            # 2,000만원
    'includes': ['interest', 'dividend'],
    'excludes': ['isa_tax_free', 'pension_deferred'],
    'progressive_rates': [
        (12_000_000, 0.06),
        (46_000_000, 0.15),
        (88_000_000, 0.24),
        (150_000_000, 0.35),
        (300_000_000, 0.38),
        (500_000_000, 0.40),
        (1_000_000_000, 0.42),
        (float('inf'), 0.45),
    ],
    'local_tax_surcharge': 0.10,        # 지방소득세 = 소득세의 10%
}

# ─── 3. 양도소득세 (주식) ───
CAPITAL_GAINS_TAX = {
    'major_shareholder_threshold': 1_000_000_000,
    'major_shareholder_rate_long': 0.22,
    'major_shareholder_rate_short': 0.33,
    'sme_rate': 0.11,
    'small_investor_rate': 0.22,
    'small_investor_exempt': 50_000_000,
    'foreign_stock_rate': 0.22,
    'foreign_stock_exempt': 2_500_000,
}

# ─── 4. 증권거래세 ───
TRANSACTION_TAX = {
    'kospi': 0.0023,
    'kosdaq': 0.0023,
    'konex': 0.0010,
    'k_otc': 0.0023,
    'seller_only': True,
}

# ─── 5. ISA (개인종합자산관리계좌) ───
ISA_ACCOUNT = {
    'tax_free_limit': 2_000_000,
    'tax_free_limit_low_income': 4_000_000,
    'excess_tax_rate': 0.099,
    'annual_contribution_limit': 20_000_000,
    'mandatory_period_years': 3,
    'eligible_products': ['stocks', 'domestic_funds', 'etf', 'elw', 'rp'],
}

# ─── 6. 연금저축 ───
PENSION_SAVINGS = {
    'annual_contribution_limit': 18_000_000,
    'tax_deduction_limit': 6_000_000,
    'deduction_rate_under_5500': 0.165,
    'deduction_rate_over_5500': 0.132,
    'withdrawal_tax_before_55': 0.165,
    'withdrawal_tax_after_55': {
        'under_1200': 0.055,
        'over_1200_70': 0.055,
        'over_1200_80': 0.044,
        'over_1200_90': 0.033,
    },
    'eligible_products': ['pension_fund', 'pension_etf', 'pension_trust'],
}

# ─── 7. IRP (개인형 퇴직연금) ───
IRP_ACCOUNT = {
    'annual_contribution_limit': 18_000_000,
    'combined_limit_with_pension': 18_000_000,
    'tax_deduction_limit': 9_000_000,
    'deduction_rate_under_5500': 0.165,
    'deduction_rate_over_5500': 0.132,
    'mandatory_products': ['safe_assets_30'],
    'safe_asset_ratio': 0.30,
}

# ─── 절세 전략 ───
TAX_OPTIMIZATION_STRATEGIES = [
    {
        'id': 'ISA_FIRST',
        'name': 'ISA 우선 활용',
        'description': '고배당주를 ISA에 우선 배치하여 200만원 비과세 혜택 극대화',
        'max_benefit': 308_000,
    },
    {
        'id': 'PENSION_DEDUCTION',
        'name': '연금저축 세액공제',
        'description': '연금저축 600만원 납입으로 최대 99만원 세액공제',
        'max_benefit': 990_000,
    },
    {
        'id': 'IRP_EXTRA_DEDUCTION',
        'name': 'IRP 추가 공제',
        'description': 'IRP에 추가 300만원 납입으로 49.5만원 추가 공제',
        'max_benefit': 495_000,
    },
    {
        'id': 'INCOME_THRESHOLD_MGMT',
        'name': '금융소득 2,000만원 관리',
        'description': '금융소득종합과세 회피를 위해 배당/이자 수입 2,000만원 이하 유지',
        'action': 'split_across_family',
    },
    {
        'id': 'LOSS_HARVESTING',
        'name': '손실 매도 (Tax-Loss Harvesting)',
        'description': '손실 종목 매도로 양도소득과 상계',
        'applicable': 'major_shareholder_or_financial_tax',
    },
    {
        'id': 'HOLDING_PERIOD',
        'name': '보유기간 관리',
        'description': '대주주 양도세 1년 이상 보유 시 22% (미만 33%)',
        'benefit': '11%p 세율 차이',
    },
]

# ─── 계좌별 세제 비교표 ───
ACCOUNT_TAX_COMPARISON = {
    'GENERAL': {
        'dividend_tax': 0.154,
        'capital_gains': 'major_shareholder_only',
        'transaction_tax': 0.0023,
        'deduction': 0,
    },
    'ISA': {
        'dividend_tax': 0,
        'excess_tax': 0.099,
        'capital_gains': 'exempt',
        'transaction_tax': 0.0023,
        'deduction': 0,
    },
    'PENSION_SAVINGS': {
        'dividend_tax': 'deferred',
        'capital_gains': 'deferred',
        'transaction_tax': 0,
        'deduction': 0.165,
        'withdrawal_tax': 0.055,
    },
    'IRP': {
        'dividend_tax': 'deferred',
        'capital_gains': 'deferred',
        'transaction_tax': 0,
        'deduction': 0.165,
        'withdrawal_tax': 0.055,
        'constraint': 'safe_30pct',
    },
}


# ═══════════════════════════════════════════════════════
# 세금 계산 함수
# ═══════════════════════════════════════════════════════

def calc_dividend_tax(gross_dividend, account_type='GENERAL'):
    """배당소득세 계산 (계좌 유형별).

    Args:
        gross_dividend: 세전 배당금 (원)
        account_type: 'GENERAL', 'ISA', 'PENSION_SAVINGS', 'IRP'

    Returns:
        dict: {gross, tax, net, effective_rate, account_type}
    """
    if gross_dividend <= 0:
        return {
            'gross': 0, 'tax': 0, 'net': 0,
            'effective_rate': 0, 'account_type': account_type,
        }

    if account_type == 'ISA':
        tax_free = min(gross_dividend, ISA_ACCOUNT['tax_free_limit'])
        taxable = max(0, gross_dividend - tax_free)
        tax = round(taxable * ISA_ACCOUNT['excess_tax_rate'])
    elif account_type in ('PENSION_SAVINGS', 'IRP'):
        tax = 0  # 과세이연
    else:  # GENERAL
        tax = round(gross_dividend * DIVIDEND_TAX['rate'])

    net = gross_dividend - tax
    effective_rate = tax / gross_dividend if gross_dividend > 0 else 0

    return {
        'gross': gross_dividend,
        'tax': tax,
        'net': net,
        'effective_rate': round(effective_rate, 4),
        'account_type': account_type,
    }


def _calc_progressive_tax(taxable_income):
    """종합소득세 누진세 계산 (내부 함수).

    Args:
        taxable_income: 과세표준 금액

    Returns:
        int: 산출세액
    """
    tax = 0
    prev_limit = 0
    for limit, rate in FINANCIAL_INCOME_TAX['progressive_rates']:
        bracket = min(taxable_income, limit) - prev_limit
        if bracket <= 0:
            break
        tax += bracket * rate
        prev_limit = limit
    return round(tax)


def calc_financial_income_tax(total_interest, total_dividend, other_income=0):
    """금융소득종합과세 판정 및 추가세 계산.

    Args:
        total_interest: 연간 이자소득 (원)
        total_dividend: 연간 배당소득 (원)
        other_income: 기타 종합소득 (원)

    Returns:
        dict: {total_financial, threshold_exceeded, base_tax,
               additional_tax, total_tax, effective_rate}
    """
    total_financial = total_interest + total_dividend
    threshold = FINANCIAL_INCOME_TAX['threshold']
    exceeded = total_financial > threshold

    # 기본 원천징수세 (2,000만원까지)
    base_amount = min(total_financial, threshold)
    base_tax = round(base_amount * DIVIDEND_TAX['rate'])

    additional_tax = 0
    if exceeded:
        excess = total_financial - threshold
        taxable = excess + other_income
        progressive = _calc_progressive_tax(taxable)
        surcharge = round(progressive * FINANCIAL_INCOME_TAX['local_tax_surcharge'])
        additional_tax = progressive + surcharge

    total_tax = base_tax + additional_tax
    effective_rate = total_tax / total_financial if total_financial > 0 else 0

    return {
        'total_financial': total_financial,
        'threshold_exceeded': exceeded,
        'base_tax': base_tax,
        'additional_tax': additional_tax,
        'total_tax': total_tax,
        'effective_rate': round(effective_rate, 4),
    }


def calc_capital_gains_tax(gains, holding_period_years=1,
                           is_major_shareholder=False, is_sme=False):
    """양도소득세 계산.

    Args:
        gains: 양도차익 (원)
        holding_period_years: 보유기간 (년)
        is_major_shareholder: 대주주 여부
        is_sme: 중소기업 대주주 여부

    Returns:
        dict: {gross_gain, exempt, taxable, tax, effective_rate}
    """
    if gains <= 0:
        return {
            'gross_gain': gains, 'exempt': 0, 'taxable': 0,
            'tax': 0, 'effective_rate': 0,
        }

    if not is_major_shareholder:
        # 소액주주: 국내 상장주식 양도세 비과세 (금투세 미시행 기준)
        return {
            'gross_gain': gains, 'exempt': gains, 'taxable': 0,
            'tax': 0, 'effective_rate': 0,
        }

    # 대주주
    if is_sme:
        rate = CAPITAL_GAINS_TAX['sme_rate']
    elif holding_period_years >= 1:
        rate = CAPITAL_GAINS_TAX['major_shareholder_rate_long']
    else:
        rate = CAPITAL_GAINS_TAX['major_shareholder_rate_short']

    exempt = 0  # 대주주는 기본공제 2,500,000원 (간편 적용)
    taxable = max(0, gains - exempt)
    tax = round(taxable * rate)
    effective_rate = tax / gains if gains > 0 else 0

    return {
        'gross_gain': gains,
        'exempt': exempt,
        'taxable': taxable,
        'tax': tax,
        'effective_rate': round(effective_rate, 4),
    }


def calc_transaction_tax(sell_amount, market='kospi'):
    """증권거래세 계산.

    Args:
        sell_amount: 매도 금액 (원)
        market: 'kospi', 'kosdaq', 'konex', 'k_otc'

    Returns:
        dict: {amount, tax, rate, market}
    """
    if sell_amount <= 0:
        return {'amount': 0, 'tax': 0, 'rate': 0, 'market': market}

    rate = TRANSACTION_TAX.get(market, TRANSACTION_TAX['kospi'])
    tax = round(sell_amount * rate)

    return {
        'amount': sell_amount,
        'tax': tax,
        'rate': rate,
        'market': market,
    }


def calc_isa_tax(total_income, is_low_income=False):
    """ISA 계좌 세금 계산.

    Args:
        total_income: ISA 계좌 내 총 소득 (배당+양도) (원)
        is_low_income: 서민형 여부

    Returns:
        dict: {total_income, tax_free, taxable, tax, effective_rate}
    """
    if total_income <= 0:
        return {
            'total_income': 0, 'tax_free': 0, 'taxable': 0,
            'tax': 0, 'effective_rate': 0,
        }

    limit = (ISA_ACCOUNT['tax_free_limit_low_income'] if is_low_income
             else ISA_ACCOUNT['tax_free_limit'])
    tax_free = min(total_income, limit)
    taxable = max(0, total_income - limit)
    tax = round(taxable * ISA_ACCOUNT['excess_tax_rate'])
    effective_rate = tax / total_income if total_income > 0 else 0

    return {
        'total_income': total_income,
        'tax_free': tax_free,
        'taxable': taxable,
        'tax': tax,
        'effective_rate': round(effective_rate, 4),
    }


def calc_pension_deduction(contribution, salary, include_irp=0):
    """연금저축/IRP 세액공제 계산.

    Args:
        contribution: 연금저축 납입액 (원)
        salary: 총급여 (원)
        include_irp: IRP 추가 납입액 (원)

    Returns:
        dict: {pension_contribution, irp_contribution, total_contribution,
               deduction_limit, deduction_rate, tax_saved}
    """
    pension_cap = PENSION_SAVINGS['tax_deduction_limit']
    pension_eligible = min(contribution, pension_cap)

    irp_cap = IRP_ACCOUNT['tax_deduction_limit'] - pension_cap  # 300만원
    irp_eligible = min(include_irp, irp_cap)

    total_eligible = pension_eligible + irp_eligible

    if salary <= 55_000_000:
        rate = PENSION_SAVINGS['deduction_rate_under_5500']
    else:
        rate = PENSION_SAVINGS['deduction_rate_over_5500']

    tax_saved = round(total_eligible * rate)

    return {
        'pension_contribution': contribution,
        'irp_contribution': include_irp,
        'total_contribution': contribution + include_irp,
        'deduction_limit': pension_cap + irp_cap,
        'deduction_rate': rate,
        'tax_saved': tax_saved,
    }


def calc_total_tax_burden(portfolio):
    """포트폴리오 전체 세금 부담 계산.

    Args:
        portfolio: {
            'dividend_income': int,       # 총 배당소득
            'interest_income': int,       # 총 이자소득 (default 0)
            'capital_gains': int,         # 양도차익 (default 0)
            'sell_amount': int,           # 매도 금액 (default 0)
            'market': str,               # 시장 (default 'kospi')
            'account_type': str,         # 계좌 유형 (default 'GENERAL')
            'is_major_shareholder': bool, # 대주주 여부 (default False)
        }

    Returns:
        dict: {dividend_tax, transaction_tax, gains_tax, financial_income_tax,
               total_tax, net_income, effective_rate, optimization_tips}
    """
    dividend_income = portfolio.get('dividend_income', 0)
    interest_income = portfolio.get('interest_income', 0)
    capital_gains = portfolio.get('capital_gains', 0)
    sell_amount = portfolio.get('sell_amount', 0)
    market = portfolio.get('market', 'kospi')
    account_type = portfolio.get('account_type', 'GENERAL')
    is_major = portfolio.get('is_major_shareholder', False)

    # 개별 세금 계산
    div_result = calc_dividend_tax(dividend_income, account_type)
    tx_result = calc_transaction_tax(sell_amount, market)
    gains_result = calc_capital_gains_tax(capital_gains,
                                          is_major_shareholder=is_major)

    # 금융소득종합과세 (일반계좌만)
    fin_result = {'total_tax': 0, 'threshold_exceeded': False}
    if account_type == 'GENERAL':
        fin_result = calc_financial_income_tax(interest_income, dividend_income)

    total_tax = div_result['tax'] + tx_result['tax'] + gains_result['tax']
    if fin_result['threshold_exceeded']:
        total_tax += fin_result['additional_tax']

    gross = dividend_income + capital_gains
    net = gross - total_tax
    effective_rate = total_tax / gross if gross > 0 else 0

    # 절세 팁
    tips = _generate_tips(portfolio, fin_result)

    return {
        'dividend_tax': div_result['tax'],
        'transaction_tax': tx_result['tax'],
        'gains_tax': gains_result['tax'],
        'financial_income_tax': fin_result.get('additional_tax', 0),
        'total_tax': total_tax,
        'net_income': net,
        'effective_rate': round(effective_rate, 4),
        'optimization_tips': tips,
    }


def _generate_tips(portfolio, fin_result):
    """절세 팁 생성 (내부 함수)."""
    tips = []
    account = portfolio.get('account_type', 'GENERAL')
    dividend = portfolio.get('dividend_income', 0)

    if account == 'GENERAL' and dividend > 0:
        tips.append(TAX_OPTIMIZATION_STRATEGIES[0])  # ISA_FIRST

    if fin_result.get('threshold_exceeded'):
        tips.append(TAX_OPTIMIZATION_STRATEGIES[3])  # INCOME_THRESHOLD_MGMT

    if portfolio.get('is_major_shareholder'):
        tips.append(TAX_OPTIMIZATION_STRATEGIES[5])  # HOLDING_PERIOD

    return tips
