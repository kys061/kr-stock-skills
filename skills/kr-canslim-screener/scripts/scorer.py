"""
kr-canslim-screener: 7-컴포넌트 가중합 스코어러.
C(15%) + A(20%) + N(15%) + S(15%) + L(20%) + I(10%) + M(5%) = 100%.
"""

# ── 가중치 ────────────────────────────────────────────────
WEIGHTS = {
    'C': 0.15,  # Current Earnings
    'A': 0.20,  # Annual Growth
    'N': 0.15,  # New Highs
    'S': 0.15,  # Supply/Demand
    'L': 0.20,  # Leadership
    'I': 0.10,  # Institutional
    'M': 0.05,  # Market Direction
}

# ── 최소 기준선 ────────────────────────────────────────────
MIN_THRESHOLDS = {
    'C': 60,
    'A': 50,
    'N': 40,
    'S': 40,
    'L': 70,
    'I': 40,
    'M': 40,
}

# ── 등급 ──────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Exceptional+',  'min': 90, 'max': 100, 'action': '즉시 매수 (15-20% 포지션)'},
    {'name': 'Exceptional',   'min': 80, 'max': 89,  'action': '강한 매수 (10-15%)'},
    {'name': 'Strong',        'min': 70, 'max': 79,  'action': '매수 (8-12%)'},
    {'name': 'Above Average', 'min': 60, 'max': 69,  'action': '관찰 리스트'},
    {'name': 'Below Average', 'min': 0,  'max': 59,  'action': '패스'},
]

# ── I 컴포넌트 임계값 ────────────────────────────────────
I_THRESHOLDS = [
    {'foreign_pct_min': 20, 'foreign_pct_max': 50, 'net_buying': True,  'score': 100},
    {'foreign_pct_min': 10, 'foreign_pct_max': 20, 'net_buying': True,  'score': 80},
    {'foreign_pct_min': 5,  'foreign_pct_max': 10, 'net_buying': False, 'score': 60},
    {'foreign_pct_min': 0,  'foreign_pct_max': 5,  'net_buying': False, 'score': 40},
]
I_DEFAULT = 20
I_NET_BUY_BONUS = 10       # 기관+외국인 순매수 보너스
I_PENSION_BONUS = 5          # 연기금 순매수 보너스
I_SELLING_PENALTY_SCORE = 20  # 외국인 순매도 10일+


def calc_institutional_score(foreign_pct: float, net_buying_days: int = 0,
                              pension_buying: bool = False,
                              selling_days: int = 0) -> dict:
    """I 컴포넌트 (기관/외국인) 점수.

    Args:
        foreign_pct: 외국인 지분율 (%)
        net_buying_days: 기관+외국인 순매수 일수 (최근 20일)
        pension_buying: 연기금 순매수 여부
        selling_days: 외국인 순매도 연속일수
    """
    if selling_days >= 10:
        return {'score': I_SELLING_PENALTY_SCORE, 'foreign_pct': foreign_pct, 'bonuses': {}}

    base = I_DEFAULT
    for t in I_THRESHOLDS:
        if t['foreign_pct_min'] <= foreign_pct <= t['foreign_pct_max']:
            if t['net_buying'] and net_buying_days < 5:
                base = max(t['score'] - 20, I_DEFAULT)
            else:
                base = t['score']
            break

    bonuses = {}
    if net_buying_days >= 10:
        bonuses['net_buying'] = I_NET_BUY_BONUS
    if pension_buying:
        bonuses['pension'] = I_PENSION_BONUS

    score = min(100, base + sum(bonuses.values()))
    return {'score': score, 'foreign_pct': foreign_pct, 'bonuses': bonuses}


def calc_canslim_total(components: dict) -> dict:
    """7-컴포넌트 종합 스코어 계산.

    Args:
        components: {'C': int, 'A': int, 'N': int, 'S': int, 'L': int, 'I': int, 'M': int}
    Returns:
        {
            'total_score': int,
            'rating': str,
            'action': str,
            'is_m_gate': bool,
            'min_threshold_failures': list,
            'components': dict,
        }
    """
    # M = 0 CRITICAL GATE
    m_score = components.get('M', 0)
    is_m_gate = (m_score == 0)

    if is_m_gate:
        return {
            'total_score': 0,
            'rating': 'Below Average',
            'action': 'M=0 매수 금지 (시장 방향 부적합)',
            'is_m_gate': True,
            'min_threshold_failures': ['M'],
            'components': components,
            'weights': WEIGHTS,
        }

    # 가중합 계산
    total = 0
    for comp, weight in WEIGHTS.items():
        total += components.get(comp, 0) * weight
    total = round(max(0, min(100, total)))

    # 최소 기준선 검사
    failures = []
    for comp, min_val in MIN_THRESHOLDS.items():
        if components.get(comp, 0) < min_val:
            failures.append(comp)

    # 기준선 미달 시 등급 하락
    adjusted_total = total
    if failures:
        adjusted_total = max(0, total - len(failures) * 5)

    rating = 'Below Average'
    action = '패스'
    for band in RATING_BANDS:
        if band['min'] <= adjusted_total <= band['max']:
            rating = band['name']
            action = band['action']
            break

    return {
        'total_score': adjusted_total,
        'rating': rating,
        'action': action,
        'is_m_gate': False,
        'min_threshold_failures': failures,
        'components': components,
        'weights': WEIGHTS,
    }
