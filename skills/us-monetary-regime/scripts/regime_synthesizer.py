"""us-monetary-regime: 종합 레짐 판정 + 한국 오버레이."""

from fed_stance_analyzer import analyze_fed_stance
from rate_trend_classifier import classify_rate_trend
from liquidity_tracker import track_liquidity
from kr_transmission_scorer import score_kr_transmission


# --- Regime Weights (sum = 1.00) ---

REGIME_WEIGHTS = {
    'stance': 0.35,
    'rate': 0.30,
    'liquidity': 0.35,
}

# --- Regime Labels ---

REGIME_LABELS = {
    'tightening': (0, 35),
    'hold': (35, 65),
    'easing': (65, 100),
}

REGIME_DESCRIPTIONS = {
    'tightening': 'US 긴축 환경. 달러 강세, EM 자본유출 압력, 성장주 불리.',
    'hold': 'US 정책 관망기. 방향 불확실, 선택적 접근 필요.',
    'easing': 'US 완화 환경. 달러 약세, EM 자본유입 기대, 성장주 유리.',
}


def _normalize_stance_to_0_100(stance_score):
    """stance_score (-100~+100) -> 0~100."""
    return max(0, min(100, (stance_score + 100) / 2))


def _classify_regime(score):
    """점수 -> 레짐 라벨."""
    for label, (low, high) in REGIME_LABELS.items():
        if low <= score < high:
            return label
    if score >= 65:
        return 'easing'
    return 'tightening'


def synthesize_regime(fomc_tone='neutral', dot_plot='stable',
                      qt_qe='neutral', speaker_tone=0.0,
                      current_ffr=5.50, ffr_6m_ago=5.50,
                      ffr_12m_ago=5.50, last_change_bp=0,
                      next_meeting_cut_prob=0.0,
                      next_meeting_hike_prob=0.0,
                      yield_curve_2y10y=0.0,
                      fed_bs_change_pct=0.0, m2_growth_yoy=0.0,
                      dxy_change_3m=0.0, rrp_change_pct=0.0,
                      kr_rate=3.50, usdkrw_change_3m=0.0,
                      foreign_flow_5d=0, bok_direction='hold'):
    """US 통화정책 레짐 종합 분석 + 한국 오버레이.

    Returns:
        dict: {us_regime, kr_impact, overlay, sector_overlays,
               summary, data_inputs}
    """
    # Sub-module 1: Fed 기조
    stance = analyze_fed_stance(
        fomc_tone=fomc_tone,
        dot_plot=dot_plot,
        qt_qe=qt_qe,
        speaker_tone=speaker_tone,
    )

    # Sub-module 2: 금리 트렌드
    rate = classify_rate_trend(
        current_ffr=current_ffr,
        ffr_6m_ago=ffr_6m_ago,
        ffr_12m_ago=ffr_12m_ago,
        last_change_bp=last_change_bp,
        next_meeting_cut_prob=next_meeting_cut_prob,
        next_meeting_hike_prob=next_meeting_hike_prob,
        yield_curve_2y10y=yield_curve_2y10y,
    )

    # Sub-module 3: 유동성
    liquidity = track_liquidity(
        fed_bs_change_pct=fed_bs_change_pct,
        m2_growth_yoy=m2_growth_yoy,
        dxy_change_3m=dxy_change_3m,
        rrp_change_pct=rrp_change_pct,
    )

    # 종합 레짐 점수
    stance_normalized = _normalize_stance_to_0_100(stance['stance_score'])
    regime_score = round(
        stance_normalized * REGIME_WEIGHTS['stance'] +
        rate['rate_score'] * REGIME_WEIGHTS['rate'] +
        liquidity['liquidity_score'] * REGIME_WEIGHTS['liquidity'],
        1,
    )
    regime_score = max(0, min(100, regime_score))
    regime_label = _classify_regime(regime_score)

    # Sub-module 4: 한국 전이
    kr_impact = score_kr_transmission(
        us_regime_score=regime_score,
        kr_rate=kr_rate,
        us_rate=current_ffr,
        usdkrw_change_3m=usdkrw_change_3m,
        foreign_flow_5d=foreign_flow_5d,
        bok_direction=bok_direction,
    )

    # Summary
    summary = (
        f"US Monetary Regime: {regime_label.upper()} "
        f"(score {regime_score}/100). "
        f"Fed stance: {stance['stance_label']}, "
        f"Rate trend: {rate['rate_regime']}, "
        f"Liquidity: {liquidity['liquidity_trend']}. "
        f"KR impact: {kr_impact['impact_label']}, "
        f"Overlay: {kr_impact['overlay']:+.1f}pts. "
        f"{REGIME_DESCRIPTIONS.get(regime_label, '')}"
    )

    return {
        'us_regime': {
            'regime_score': regime_score,
            'regime_label': regime_label,
            'stance': stance,
            'rate': rate,
            'liquidity': liquidity,
        },
        'kr_impact': kr_impact,
        'overlay': kr_impact['overlay'],
        'sector_overlays': kr_impact['sector_overlays'],
        'summary': summary,
        'data_inputs': {
            'fomc_tone': fomc_tone,
            'dot_plot': dot_plot,
            'qt_qe': qt_qe,
            'speaker_tone': speaker_tone,
            'current_ffr': current_ffr,
            'ffr_6m_ago': ffr_6m_ago,
            'ffr_12m_ago': ffr_12m_ago,
            'last_change_bp': last_change_bp,
            'next_meeting_cut_prob': next_meeting_cut_prob,
            'next_meeting_hike_prob': next_meeting_hike_prob,
            'yield_curve_2y10y': yield_curve_2y10y,
            'fed_bs_change_pct': fed_bs_change_pct,
            'm2_growth_yoy': m2_growth_yoy,
            'dxy_change_3m': dxy_change_3m,
            'rrp_change_pct': rrp_change_pct,
            'kr_rate': kr_rate,
            'usdkrw_change_3m': usdkrw_change_3m,
            'foreign_flow_5d': foreign_flow_5d,
            'bok_direction': bok_direction,
        },
    }
