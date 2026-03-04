"""
kr-pair-trade: 4-컴포넌트 가중합 스코어러.
Correlation(30%) + Cointegration(30%) + Z-Score Signal(25%) + Risk/Reward(15%) = 100%.
"""

# ── 가중치 ────────────────────────────────────────────────────
WEIGHTS = {
    'correlation':    0.30,
    'cointegration':  0.30,
    'zscore_signal':  0.25,
    'risk_reward':    0.15,
}

# ── 등급 ──────────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Prime Pair',     'min': 85, 'max': 100, 'action': '즉시 진입 (최적 조건)'},
    {'name': 'Strong Pair',    'min': 70, 'max': 84,  'action': '진입 후보 (표준 사이징)'},
    {'name': 'Good Pair',      'min': 55, 'max': 69,  'action': '관찰 리스트'},
    {'name': 'Weak Pair',      'min': 40, 'max': 54,  'action': '추가 분석 필요'},
    {'name': 'No Pair',        'min': 0,  'max': 39,  'action': '패스'},
]

# ── 필수 조건 ────────────────────────────────────────────────
MIN_CORRELATION = 0.70           # 상관계수 ≥ 0.70 필수
COINTEGRATION_REQUIRED = True    # 공적분 통과 필수

# ── 한국 거래비용 ────────────────────────────────────────────
KR_ROUND_TRIP_COST = 0.0025     # 0.25% round-trip (수수료+세금)
MAX_CONCURRENT_PAIRS = 8        # 최대 동시 페어
PAIR_PORTFOLIO_PCT = (10, 20)   # 페어당 포트폴리오 비중 (%)


def calc_risk_reward_score(ratio: float) -> int:
    """R/R 비율을 점수로 변환.

    Args:
        ratio: Risk/Reward 비율
    Returns:
        score (0-100)
    """
    if ratio >= 3.0:
        return 100
    elif ratio >= 2.0:
        return 80
    elif ratio >= 1.5:
        return 60
    elif ratio >= 1.0:
        return 40
    else:
        return 20


def calc_pair_total(components: dict,
                    correlation: float = 0,
                    is_cointegrated: bool = False) -> dict:
    """4-컴포넌트 페어 트레이딩 종합 스코어 계산.

    Args:
        components: {
            'correlation': int (0-100),
            'cointegration': int (0-100),
            'zscore_signal': int (0-100),
            'risk_reward': int (0-100),
        }
        correlation: 실제 상관계수 (Gate 검사용)
        is_cointegrated: 공적분 통과 여부 (Gate 검사용)
    Returns:
        {
            'total_score': int,
            'rating': str,
            'action': str,
            'gates': dict,
            'components': dict,
            'weights': dict,
        }
    """
    # Gate 검사
    gates = {
        'correlation_ok': correlation >= MIN_CORRELATION,
        'cointegration_ok': is_cointegrated or not COINTEGRATION_REQUIRED,
    }

    if not gates['correlation_ok']:
        return {
            'total_score': 0,
            'rating': 'No Pair',
            'action': f'상관계수 부족 (ρ={correlation:.2f} < {MIN_CORRELATION})',
            'gates': gates,
            'components': components,
            'weights': WEIGHTS,
        }

    if not gates['cointegration_ok']:
        return {
            'total_score': 0,
            'rating': 'No Pair',
            'action': '공적분 미통과 (p > 0.05)',
            'gates': gates,
            'components': components,
            'weights': WEIGHTS,
        }

    # 가중합 계산
    total = 0
    for comp, weight in WEIGHTS.items():
        total += components.get(comp, 0) * weight
    total = round(max(0, min(100, total)))

    rating = 'No Pair'
    action = '패스'
    for band in RATING_BANDS:
        if band['min'] <= total <= band['max']:
            rating = band['name']
            action = band['action']
            break

    return {
        'total_score': total,
        'rating': rating,
        'action': action,
        'gates': gates,
        'components': components,
        'weights': WEIGHTS,
    }
