"""us-monetary-regime: 종합 레짐 판정 + 한국 오버레이.

4-Component Regime Score:
  stance     × 0.25  (Fed 기조 — FOMC, 점도표, QT/QE)
  rate       × 0.20  (금리 트렌드 — FFR 수준/방향/시장기대)
  liquidity  × 0.25  (유동성 — Fed B/S, M2, DXY, RRP)
  fundamentals × 0.30 (경제 펀더멘털 — 물가, 고용, 성장, 충격)
"""

from fed_stance_analyzer import analyze_fed_stance
from rate_trend_classifier import classify_rate_trend
from liquidity_tracker import track_liquidity
from economic_fundamentals_analyzer import analyze_fundamentals
from kr_transmission_scorer import score_kr_transmission


# --- Regime Weights (sum = 1.00) ---

REGIME_WEIGHTS = {
    'stance': 0.25,
    'rate': 0.20,
    'liquidity': 0.25,
    'fundamentals': 0.30,
}

# --- Legacy 3-component weights (backward compatibility) ---

REGIME_WEIGHTS_LEGACY = {
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


# --- Rate Outlook ---

RATE_OUTLOOK_LABELS = {
    'hike_likely': '금리 인상 가능성 높음',
    'hike_lean': '금리 인상 쪽으로 기울어짐',
    'hold_hawkish': '동결 유지 (매파적 기조)',
    'hold_neutral': '동결 유지 (중립)',
    'hold_dovish': '동결 유지 (비둘기파적 기조)',
    'cut_lean': '금리 인하 쪽으로 기울어짐',
    'cut_likely': '금리 인하 가능성 높음',
}


def _generate_rate_outlook(regime_score, stance, rate, fundamentals):
    """4-컴포넌트 종합 결과를 바탕으로 금리 방향 판단 요약 생성.

    Args:
        regime_score: float, 종합 레짐 점수 (0-100).
        stance: dict, Fed 기조 분석 결과.
        rate: dict, 금리 트렌드 분석 결과.
        fundamentals: dict, 경제 펀더멘털 분석 결과.

    Returns:
        dict: {direction, label, confidence, reasoning, key_factors}
    """
    pressure = fundamentals['pressure_label']
    stance_label = stance['stance_label']
    rate_regime = rate['rate_regime']
    fund_score = fundamentals['fundamentals_score']

    # --- 방향 판단 ---
    # 펀더멘털 압력(30%) + 레짐 점수 기반 종합 판단
    if regime_score < 20:
        direction = 'hike_likely'
        confidence = 'high'
    elif regime_score < 35:
        direction = 'hike_lean'
        confidence = 'medium'
    elif regime_score < 45:
        direction = 'hold_hawkish'
        confidence = 'medium'
    elif regime_score < 55:
        direction = 'hold_neutral'
        confidence = 'low'
    elif regime_score < 65:
        direction = 'hold_dovish'
        confidence = 'medium'
    elif regime_score < 80:
        direction = 'cut_lean'
        confidence = 'medium'
    else:
        direction = 'cut_likely'
        confidence = 'high'

    # --- 핵심 요인 수집 ---
    key_factors = []

    # 인플레이션
    infl = fundamentals['components']['inflation']
    infl_ref = infl['components']['reference_rate']
    infl_dir = infl['components']['direction']
    if infl_ref > 3.0:
        key_factors.append(f'물가 {infl_ref:.1f}% (목표 2% 초과) → 인상 압력')
    elif infl_ref < 1.5:
        key_factors.append(f'물가 {infl_ref:.1f}% (목표 하회) → 인하 여유')
    else:
        key_factors.append(f'물가 {infl_ref:.1f}% (목표 근처)')
    if infl_dir == 'accelerating':
        key_factors.append('인플레이션 가속 중 → 인하 제약')
    elif infl_dir == 'decelerating':
        key_factors.append('인플레이션 둔화 중 → 인하 여유 확대')

    # 고용
    labor = fundamentals['components']['labor']
    unemp = labor['components']['unemployment']['rate']
    if unemp < 3.5:
        key_factors.append(f'실업률 {unemp}% (극도로 타이트) → 인상 압력')
    elif unemp > 5.0:
        key_factors.append(f'실업률 {unemp}% (약화) → 인하 압력')
    else:
        key_factors.append(f'실업률 {unemp}%')

    # 성장
    growth = fundamentals['components']['growth']
    gdp = growth['components']['gdp']['growth']
    if gdp < 1.0:
        key_factors.append(f'GDP {gdp}% (정체/침체) → 인하 압력')
    elif gdp > 4.0:
        key_factors.append(f'GDP {gdp}% (과열) → 인상 압력')

    # 외생적 충격
    shock = fundamentals['components']['shock']
    shock_lvl = shock['components']['shock_level']
    if shock_lvl not in ('none', 'minor'):
        shock_inf = shock['components']['is_inflationary']
        if shock_inf:
            key_factors.append(
                f'{shock["interpretation"]} → 스태그플레이션 우려, 인하 제약')
        else:
            key_factors.append(f'{shock["interpretation"]}')

    # --- 요약 문장 생성 ---
    label = RATE_OUTLOOK_LABELS.get(direction, direction)
    dual = fundamentals['dual_mandate_assessment']

    if direction in ('hike_likely', 'hike_lean'):
        reasoning = (
            f'펀더멘털 압력이 {pressure}로 금리 인상을 시사. '
            f'{dual}. '
            f'Fed 기조 {stance_label}, 금리 트렌드 {rate_regime}.'
        )
    elif direction in ('cut_likely', 'cut_lean'):
        reasoning = (
            f'펀더멘털 압력이 {pressure}로 금리 인하 여유 존재. '
            f'{dual}. '
            f'Fed 기조 {stance_label}, 금리 트렌드 {rate_regime}.'
        )
    else:
        reasoning = (
            f'펀더멘털 압력 {pressure}, 금리 변동보다 동결 유지 가능성 높음. '
            f'{dual}. '
            f'Fed 기조 {stance_label}, 금리 트렌드 {rate_regime}.'
        )

    return {
        'direction': direction,
        'label': label,
        'confidence': confidence,
        'reasoning': reasoning,
        'key_factors': key_factors,
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
                      tga_change_1m_pct=None,
                      kr_rate=3.50, usdkrw_change_3m=0.0,
                      foreign_flow_5d=0, bok_direction='hold',
                      # --- New: Economic Fundamentals ---
                      cpi_yoy=3.0, core_pce_yoy=None,
                      inflation_direction='stable',
                      unemployment_rate=4.0,
                      nfp_thousands=150,
                      wage_growth_yoy=3.5,
                      gdp_growth_annualized=2.5,
                      ism_manufacturing=50.0,
                      ism_services=52.0,
                      lei_change_6m=0.0,
                      shock_level='none',
                      shock_type='other',
                      shock_duration_months=0,
                      shock_is_inflationary=False):
    """US 통화정책 레짐 종합 분석 + 한국 오버레이.

    4-Component: stance(0.25) + rate(0.20) + liquidity(0.25) + fundamentals(0.30)

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
        tga_change_1m_pct=tga_change_1m_pct,
    )

    # Sub-module 4: 경제 펀더멘털 (NEW)
    fundamentals = analyze_fundamentals(
        cpi_yoy=cpi_yoy,
        core_pce_yoy=core_pce_yoy,
        inflation_direction=inflation_direction,
        unemployment_rate=unemployment_rate,
        nfp_thousands=nfp_thousands,
        wage_growth_yoy=wage_growth_yoy,
        gdp_growth_annualized=gdp_growth_annualized,
        ism_manufacturing=ism_manufacturing,
        ism_services=ism_services,
        lei_change_6m=lei_change_6m,
        shock_level=shock_level,
        shock_type=shock_type,
        shock_duration_months=shock_duration_months,
        shock_is_inflationary=shock_is_inflationary,
    )

    # 종합 레짐 점수 (4-component)
    stance_normalized = _normalize_stance_to_0_100(stance['stance_score'])
    regime_score = round(
        stance_normalized * REGIME_WEIGHTS['stance'] +
        rate['rate_score'] * REGIME_WEIGHTS['rate'] +
        liquidity['liquidity_score'] * REGIME_WEIGHTS['liquidity'] +
        fundamentals['fundamentals_score'] * REGIME_WEIGHTS['fundamentals'],
        1,
    )
    regime_score = max(0, min(100, regime_score))
    regime_label = _classify_regime(regime_score)

    # Sub-module 5: 한국 전이
    kr_impact = score_kr_transmission(
        us_regime_score=regime_score,
        kr_rate=kr_rate,
        us_rate=current_ffr,
        usdkrw_change_3m=usdkrw_change_3m,
        foreign_flow_5d=foreign_flow_5d,
        bok_direction=bok_direction,
    )

    # Rate Outlook (금리 방향 판단 요약)
    rate_outlook = _generate_rate_outlook(
        regime_score, stance, rate, fundamentals,
    )

    # Summary
    summary = (
        f"US Monetary Regime: {regime_label.upper()} "
        f"(score {regime_score}/100). "
        f"Fed stance: {stance['stance_label']}, "
        f"Rate trend: {rate['rate_regime']}, "
        f"Liquidity: {liquidity['liquidity_trend']}, "
        f"Fundamentals: {fundamentals['pressure_label']}. "
        f"▶ 금리 방향: {rate_outlook['label']} "
        f"(확신도: {rate_outlook['confidence']}). "
        f"KR impact: {kr_impact['impact_label']}, "
        f"Overlay: {kr_impact['overlay']:+.1f}pts. "
        f"{REGIME_DESCRIPTIONS.get(regime_label, '')}"
    )

    return {
        'us_regime': {
            'regime_score': regime_score,
            'regime_label': regime_label,
            'rate_outlook': rate_outlook,
            'stance': stance,
            'rate': rate,
            'liquidity': liquidity,
            'fundamentals': fundamentals,
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
            'tga_change_1m_pct': tga_change_1m_pct,
            'kr_rate': kr_rate,
            'usdkrw_change_3m': usdkrw_change_3m,
            'foreign_flow_5d': foreign_flow_5d,
            'bok_direction': bok_direction,
            # Fundamentals inputs
            'cpi_yoy': cpi_yoy,
            'core_pce_yoy': core_pce_yoy,
            'inflation_direction': inflation_direction,
            'unemployment_rate': unemployment_rate,
            'nfp_thousands': nfp_thousands,
            'wage_growth_yoy': wage_growth_yoy,
            'gdp_growth_annualized': gdp_growth_annualized,
            'ism_manufacturing': ism_manufacturing,
            'ism_services': ism_services,
            'lei_change_6m': lei_change_6m,
            'shock_level': shock_level,
            'shock_type': shock_type,
            'shock_duration_months': shock_duration_months,
            'shock_is_inflationary': shock_is_inflationary,
        },
    }
