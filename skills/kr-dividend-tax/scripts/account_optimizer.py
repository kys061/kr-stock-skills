"""kr-dividend-tax: 계좌 배치 최적화 엔진.

계좌 유형별 세금 혜택을 비교하고,
포트폴리오의 최적 계좌 배치를 추천한다.
"""

from tax_calculator import (
    DIVIDEND_TAX, ISA_ACCOUNT, PENSION_SAVINGS, IRP_ACCOUNT,
    FINANCIAL_INCOME_TAX, ACCOUNT_TAX_COMPARISON,
    TAX_OPTIMIZATION_STRATEGIES,
    calc_dividend_tax, calc_isa_tax, calc_pension_deduction,
)

# ═══════════════════════════════════════════════════════
# 계좌 우선순위
# ═══════════════════════════════════════════════════════

ACCOUNT_PRIORITY = [
    {
        'account': 'ISA',
        'priority': 1,
        'reason': '비과세 200만원 + 초과분 9.9%',
        'best_for': ['high_yield_stocks', 'etf'],
        'tax_benefit': 'tax_free_first',
    },
    {
        'account': 'PENSION_SAVINGS',
        'priority': 2,
        'reason': '세액공제 16.5%/13.2% + 과세이연',
        'best_for': ['long_term_growth', 'pension_etf'],
        'tax_benefit': 'tax_deduction',
    },
    {
        'account': 'IRP',
        'priority': 3,
        'reason': '추가 세액공제 300만원 + 과세이연',
        'best_for': ['safe_assets', 'bond_etf'],
        'tax_benefit': 'tax_deduction',
        'constraint': 'safe_asset_30pct',
    },
    {
        'account': 'GENERAL',
        'priority': 4,
        'reason': '제한 없음, 15.4% 원천징수',
        'best_for': ['trading', 'all_products'],
        'tax_benefit': 'none',
    },
]

# ─── 계좌 배치 규칙 ───
ALLOCATION_RULES = {
    'high_yield_first_to_isa': True,
    'growth_stocks_to_pension': True,
    'bond_etf_to_irp': True,
    'trading_to_general': True,
    'threshold_management': True,
}


# ═══════════════════════════════════════════════════════
# 계좌 최적화 함수
# ═══════════════════════════════════════════════════════

def recommend_account_allocation(holdings):
    """보유 종목의 최적 계좌 배치 추천.

    Args:
        holdings: list of dict, each:
            {
                'ticker': str,
                'name': str,
                'dividend_yield': float,     # 배당수익률
                'annual_dividend': int,       # 연간 배당금 (원)
                'holding_type': str,          # 'high_yield', 'growth', 'bond_etf', 'trading'
            }

    Returns:
        dict: {allocations: list, total_tax_saved: int, summary: str}
    """
    if not holdings:
        return {'allocations': [], 'total_tax_saved': 0, 'summary': '보유 종목 없음'}

    allocations = []
    isa_dividend = 0
    total_saved = 0

    sorted_holdings = sorted(holdings,
                             key=lambda h: h.get('dividend_yield', 0),
                             reverse=True)

    for h in sorted_holdings:
        htype = h.get('holding_type', 'trading')
        annual_div = h.get('annual_dividend', 0)

        if htype == 'high_yield' and isa_dividend + annual_div <= ISA_ACCOUNT['tax_free_limit']:
            account = 'ISA'
            saved = round(annual_div * DIVIDEND_TAX['rate'])
            isa_dividend += annual_div
        elif htype == 'high_yield' and isa_dividend < ISA_ACCOUNT['tax_free_limit']:
            account = 'ISA'
            free_part = ISA_ACCOUNT['tax_free_limit'] - isa_dividend
            taxable_part = annual_div - free_part
            saved = round(free_part * DIVIDEND_TAX['rate'])
            saved += round(taxable_part * (DIVIDEND_TAX['rate'] - ISA_ACCOUNT['excess_tax_rate']))
            isa_dividend += annual_div
        elif htype in ('growth', 'long_term'):
            account = 'PENSION_SAVINGS'
            saved = round(annual_div * DIVIDEND_TAX['rate'])  # 과세이연
        elif htype == 'bond_etf':
            account = 'IRP'
            saved = round(annual_div * DIVIDEND_TAX['rate'])
        else:
            account = 'GENERAL'
            saved = 0

        allocations.append({
            'ticker': h.get('ticker', ''),
            'name': h.get('name', ''),
            'recommended_account': account,
            'reason': _get_allocation_reason(account, htype),
            'tax_saved': saved,
        })
        total_saved += saved

    summary = f'{len(allocations)}개 종목 배치 완료, 예상 절세 {total_saved:,}원'

    return {
        'allocations': allocations,
        'total_tax_saved': total_saved,
        'summary': summary,
    }


def _get_allocation_reason(account, holding_type):
    """배치 사유 생성."""
    reasons = {
        'ISA': '고배당주 → ISA 비과세 혜택 활용',
        'PENSION_SAVINGS': '장기 보유 → 연금저축 과세이연 + 세액공제',
        'IRP': '채권/안전자산 → IRP 안전자산 비율 충족 + 세액공제',
        'GENERAL': '매매 빈도 높음 or 제한 없는 계좌 필요',
    }
    return reasons.get(account, '')


def calc_account_benefit(holding, account_type):
    """특정 종목을 특정 계좌에 넣을 때 세금 혜택 계산.

    Args:
        holding: {
            'annual_dividend': int,   # 연간 배당금
            'capital_gains': int,     # 예상 양도차익
        }
        account_type: 'GENERAL', 'ISA', 'PENSION_SAVINGS', 'IRP'

    Returns:
        dict: {account_type, dividend_tax, gains_tax, total_tax,
               vs_general_saved, effective_rate}
    """
    annual_div = holding.get('annual_dividend', 0)
    cap_gains = holding.get('capital_gains', 0)
    total_income = annual_div + cap_gains

    if total_income <= 0:
        return {
            'account_type': account_type, 'dividend_tax': 0,
            'gains_tax': 0, 'total_tax': 0,
            'vs_general_saved': 0, 'effective_rate': 0,
        }

    # 일반계좌 기준세
    general_div_tax = round(annual_div * DIVIDEND_TAX['rate'])
    general_total = general_div_tax  # 소액주주 양도세 없음

    if account_type == 'GENERAL':
        return {
            'account_type': 'GENERAL',
            'dividend_tax': general_div_tax,
            'gains_tax': 0,
            'total_tax': general_div_tax,
            'vs_general_saved': 0,
            'effective_rate': round(general_div_tax / total_income, 4) if total_income else 0,
        }

    if account_type == 'ISA':
        isa_result = calc_isa_tax(total_income)
        tax = isa_result['tax']
    elif account_type in ('PENSION_SAVINGS', 'IRP'):
        tax = 0  # 과세이연
    else:
        tax = general_div_tax

    saved = general_total - tax
    effective_rate = tax / total_income if total_income > 0 else 0

    return {
        'account_type': account_type,
        'dividend_tax': tax if account_type == 'ISA' else 0,
        'gains_tax': 0,
        'total_tax': tax,
        'vs_general_saved': saved,
        'effective_rate': round(effective_rate, 4),
    }


def optimize_threshold_management(total_financial_income):
    """금융소득종합과세 2,000만원 기준 관리.

    Args:
        total_financial_income: 현재 금융소득 합계 (원)

    Returns:
        dict: {current_income, threshold, remaining, exceeded,
               risk_level, recommendations}
    """
    threshold = FINANCIAL_INCOME_TAX['threshold']
    remaining = max(0, threshold - total_financial_income)
    exceeded = total_financial_income > threshold
    excess = max(0, total_financial_income - threshold)

    if total_financial_income <= threshold * 0.70:
        risk_level = 'SAFE'
    elif total_financial_income <= threshold * 0.90:
        risk_level = 'CAUTION'
    elif total_financial_income <= threshold:
        risk_level = 'WARNING'
    else:
        risk_level = 'EXCEEDED'

    recommendations = []
    if risk_level in ('CAUTION', 'WARNING'):
        recommendations.append('고배당주를 ISA/연금저축으로 이전 검토')
        recommendations.append(f'잔여 여유: {remaining:,}원')
    if risk_level == 'EXCEEDED':
        recommendations.append(f'금융소득종합과세 대상 (초과: {excess:,}원)')
        recommendations.append('ISA/연금저축 활용으로 과세 대상 소득 분산')

    return {
        'current_income': total_financial_income,
        'threshold': threshold,
        'remaining': remaining,
        'exceeded': exceeded,
        'excess': excess,
        'risk_level': risk_level,
        'recommendations': recommendations,
    }


def generate_tax_optimization_tips(portfolio):
    """맞춤형 절세 팁 생성.

    Args:
        portfolio: {
            'total_dividend': int,
            'total_interest': int,
            'account_type': str,
            'salary': int,
            'pension_contribution': int,
            'irp_contribution': int,
            'is_major_shareholder': bool,
        }

    Returns:
        list of dict: [{id, name, description, potential_benefit}]
    """
    tips = []
    total_div = portfolio.get('total_dividend', 0)
    total_int = portfolio.get('total_interest', 0)
    account = portfolio.get('account_type', 'GENERAL')
    salary = portfolio.get('salary', 0)
    pension = portfolio.get('pension_contribution', 0)
    irp = portfolio.get('irp_contribution', 0)

    # Tip 1: ISA 활용
    if account == 'GENERAL' and total_div > 0:
        benefit = min(total_div, ISA_ACCOUNT['tax_free_limit']) * DIVIDEND_TAX['rate']
        tips.append({
            'id': 'ISA_FIRST',
            'name': 'ISA 우선 활용',
            'description': f'ISA로 이전 시 최대 {round(benefit):,}원 절세 가능',
            'potential_benefit': round(benefit),
        })

    # Tip 2: 연금저축
    pension_cap = PENSION_SAVINGS['tax_deduction_limit']
    if pension < pension_cap:
        gap = pension_cap - pension
        rate = (PENSION_SAVINGS['deduction_rate_under_5500'] if salary <= 55_000_000
                else PENSION_SAVINGS['deduction_rate_over_5500'])
        benefit = gap * rate
        tips.append({
            'id': 'PENSION_DEDUCTION',
            'name': '연금저축 추가 납입',
            'description': f'{gap:,}원 추가 납입 시 {round(benefit):,}원 세액공제',
            'potential_benefit': round(benefit),
        })

    # Tip 3: IRP 추가
    irp_extra_cap = IRP_ACCOUNT['tax_deduction_limit'] - pension_cap
    if irp < irp_extra_cap:
        gap = irp_extra_cap - irp
        rate = (IRP_ACCOUNT['deduction_rate_under_5500'] if salary <= 55_000_000
                else IRP_ACCOUNT['deduction_rate_over_5500'])
        benefit = gap * rate
        tips.append({
            'id': 'IRP_EXTRA_DEDUCTION',
            'name': 'IRP 추가 납입',
            'description': f'{gap:,}원 추가 납입 시 {round(benefit):,}원 추가 공제',
            'potential_benefit': round(benefit),
        })

    # Tip 4: 금융소득 관리
    total_financial = total_div + total_int
    if total_financial > FINANCIAL_INCOME_TAX['threshold'] * 0.70:
        tips.append({
            'id': 'INCOME_THRESHOLD_MGMT',
            'name': '금융소득 2,000만원 관리',
            'description': f'현재 금융소득 {total_financial:,}원 — 종합과세 기준 관리 필요',
            'potential_benefit': 0,
        })

    # Tip 5: 보유기간 관리
    if portfolio.get('is_major_shareholder'):
        tips.append({
            'id': 'HOLDING_PERIOD',
            'name': '보유기간 관리',
            'description': '1년 이상 보유 시 양도세 22% (미만 33%)',
            'potential_benefit': 0,
        })

    return tips
