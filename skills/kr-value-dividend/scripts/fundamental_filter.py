"""
kr-value-dividend: 3-Phase 펀더멘털 필터.
Phase 1 정량 → Phase 2 성장 품질 → Phase 3 지속가능성.
"""

# ── Phase 1: 정량 필터 임계값 ─────────────────────────────
PHASE1_MIN_YIELD = 2.5        # 배당수익률 최소 2.5%
PHASE1_MAX_PER = 15.0         # PER 최대 15
PHASE1_MAX_PBR = 1.5          # PBR 최대 1.5
PHASE1_MIN_MARKET_CAP = 500_000_000_000  # 시가총액 최소 5,000억원

# ── Phase 2: 성장 품질 필터 ───────────────────────────────
PHASE2_MIN_DIVIDEND_YEARS = 3  # 3년 연속 무삭감

# ── Phase 3: 지속가능성 필터 ──────────────────────────────
PHASE3_MAX_PAYOUT = 80.0      # 배당성향 최대 80%
PHASE3_MAX_DE_RATIO = 150.0   # 부채비율 최대 150%
PHASE3_MIN_CURRENT_RATIO = 1.0  # 유동비율 최소 1.0


def filter_phase1(stock: dict) -> bool:
    """Phase 1: 정량 필터.

    Args:
        stock: {
            'div_yield': float,  # 배당수익률 (%)
            'per': float,        # PER
            'pbr': float,        # PBR
            'market_cap': float, # 시가총액 (원)
        }
    Returns:
        True if stock passes Phase 1
    """
    div_yield = stock.get('div_yield', 0)
    per = stock.get('per', 0)
    pbr = stock.get('pbr', 0)
    market_cap = stock.get('market_cap', 0)

    if div_yield < PHASE1_MIN_YIELD:
        return False
    if per <= 0 or per > PHASE1_MAX_PER:
        return False
    if pbr <= 0 or pbr > PHASE1_MAX_PBR:
        return False
    if market_cap < PHASE1_MIN_MARKET_CAP:
        return False
    return True


def filter_phase2(stock: dict) -> bool:
    """Phase 2: 성장 품질 필터.

    Args:
        stock: {
            'dividend_history': list[float],   # 최근 3년 배당금 [Y-3, Y-2, Y-1]
            'revenue_history': list[float],    # 최근 3년 매출 [Y-3, Y-2, Y-1]
            'eps_history': list[float],        # 최근 3년 EPS [Y-3, Y-2, Y-1]
        }
    Returns:
        True if stock passes Phase 2
    """
    div_hist = stock.get('dividend_history', [])
    rev_hist = stock.get('revenue_history', [])
    eps_hist = stock.get('eps_history', [])

    # 3년 배당 데이터 필요
    if len(div_hist) < PHASE2_MIN_DIVIDEND_YEARS:
        return False

    # 3년 연속 배당 유지 (무삭감): 각 연도 배당 > 0 & 이전 대비 감소 없음
    for i in range(len(div_hist)):
        if div_hist[i] <= 0:
            return False
    for i in range(1, len(div_hist)):
        if div_hist[i] < div_hist[i - 1]:
            return False

    # 매출 3년 양의 추세
    if len(rev_hist) >= 3:
        if not _is_positive_trend(rev_hist):
            return False

    # EPS 3년 양의 추세
    if len(eps_hist) >= 3:
        if not _is_positive_trend(eps_hist):
            return False

    return True


def filter_phase3(stock: dict) -> bool:
    """Phase 3: 지속가능성 필터.

    Args:
        stock: {
            'payout_ratio': float,    # 배당성향 (%)
            'de_ratio': float,        # 부채비율 (%)
            'current_ratio': float,   # 유동비율
        }
    Returns:
        True if stock passes Phase 3
    """
    payout = stock.get('payout_ratio', 100)
    de_ratio = stock.get('de_ratio', 200)
    current_ratio = stock.get('current_ratio', 0)

    if payout >= PHASE3_MAX_PAYOUT:
        return False
    if de_ratio >= PHASE3_MAX_DE_RATIO:
        return False
    if current_ratio < PHASE3_MIN_CURRENT_RATIO:
        return False
    return True


def filter_all_phases(stock: dict) -> dict:
    """3-Phase 필터 전체 실행.

    Returns:
        {
            'passed': bool,
            'phase1': bool,
            'phase2': bool,
            'phase3': bool,
            'failed_at': str or None,
        }
    """
    p1 = filter_phase1(stock)
    if not p1:
        return {'passed': False, 'phase1': False, 'phase2': False, 'phase3': False, 'failed_at': 'phase1'}

    p2 = filter_phase2(stock)
    if not p2:
        return {'passed': False, 'phase1': True, 'phase2': False, 'phase3': False, 'failed_at': 'phase2'}

    p3 = filter_phase3(stock)
    if not p3:
        return {'passed': False, 'phase1': True, 'phase2': True, 'phase3': False, 'failed_at': 'phase3'}

    return {'passed': True, 'phase1': True, 'phase2': True, 'phase3': True, 'failed_at': None}


def _is_positive_trend(values: list) -> bool:
    """3개 이상의 값이 양의 추세(점진적 증가)인지 확인.

    최소 조건: 마지막 값 > 첫 값 (전체 기간 증가).
    """
    if len(values) < 2:
        return True
    return values[-1] > values[0]
