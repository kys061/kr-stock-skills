"""M 컴포넌트: 시장 방향 (Market Direction)."""

# ── 임계값 ────────────────────────────────────────────────
M_STRONG_BULL = 100    # 강한 상승장
M_BULL = 80            # 상승장
M_WEAK = 40            # 약세
M_BEAR = 0             # 약세장 (매수 금지)

VKOSPI_DANGER = 25     # VKOSPI > 25 → 약세장
BREADTH_HEALTHY = 60   # breadth ≥ 60 → 건강
BREADTH_WEAK = 40      # breadth ≥ 40 → 약세


def calc_market_direction(kospi_above_ema50: bool,
                          vkospi: float = None,
                          breadth_score: float = None,
                          regime: str = None,
                          risk_zone: str = None) -> dict:
    """시장 방향 점수 계산.

    Phase 3 크로스레퍼런스 우선 사용.
    크로스레퍼런스 미존재 시 KOSPI 50 EMA + VKOSPI로 자체 계산.

    Args:
        kospi_above_ema50: KOSPI > 50 EMA 여부
        vkospi: VKOSPI 수준 (선택)
        breadth_score: kr-market-breadth 점수 (선택)
        regime: kr-macro-regime 레짐 (선택)
        risk_zone: kr-market-top-detector 위험 존 (선택)
    Returns:
        {'score': int, 'is_critical_gate': bool, 'details': dict}
    """
    details = {
        'kospi_above_ema50': kospi_above_ema50,
        'vkospi': vkospi,
        'breadth_score': breadth_score,
        'regime': regime,
        'risk_zone': risk_zone,
    }

    # M = 0 (CRITICAL GATE): KOSPI < 50 EMA + VKOSPI > 25
    if not kospi_above_ema50 and vkospi is not None and vkospi > VKOSPI_DANGER:
        return {'score': M_BEAR, 'is_critical_gate': True, 'details': details}

    # 크로스레퍼런스 사용 시
    if breadth_score is not None and regime is not None:
        if kospi_above_ema50 and breadth_score >= BREADTH_HEALTHY and regime != 'Contraction':
            return {'score': M_STRONG_BULL, 'is_critical_gate': False, 'details': details}

    # 리스크존 사용 시
    if risk_zone is not None:
        if kospi_above_ema50 and risk_zone in ('Green', 'Yellow'):
            return {'score': M_BULL, 'is_critical_gate': False, 'details': details}

    # 기본 EMA 판단
    if kospi_above_ema50:
        if breadth_score is not None and breadth_score >= BREADTH_WEAK:
            return {'score': M_BULL, 'is_critical_gate': False, 'details': details}
        return {'score': M_BULL, 'is_critical_gate': False, 'details': details}
    else:
        if breadth_score is not None and breadth_score >= BREADTH_WEAK:
            return {'score': M_WEAK, 'is_critical_gate': False, 'details': details}
        return {'score': M_WEAK, 'is_critical_gate': False, 'details': details}
