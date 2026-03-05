"""kr-stock-analysis: 종합 스코어링 엔진."""


# ─── 종합 분석 스코어링 ───

COMPREHENSIVE_SCORING = {
    'fundamental': {'weight': 0.30, 'label': '펀더멘털'},
    'technical': {'weight': 0.22, 'label': '기술적'},
    'supply_demand': {'weight': 0.22, 'label': '수급'},
    'valuation': {'weight': 0.13, 'label': '밸류에이션'},
    'growth': {'weight': 0.13, 'label': '성장성'},
}

# ─── 분석 유형 ───

ANALYSIS_TYPES = [
    'BASIC',          # 기본 정보
    'FUNDAMENTAL',    # 펀더멘털
    'TECHNICAL',      # 기술적 분석
    'SUPPLY_DEMAND',  # 수급 분석 (KR 고유)
    'COMPREHENSIVE',  # 종합 리포트
]

# ─── 투자 등급 ───

ANALYSIS_GRADES = {
    'STRONG_BUY': 80,
    'BUY': 65,
    'HOLD': 50,
    'SELL': 35,
    'STRONG_SELL': 0,
}


def _get_grade(score):
    """점수 → 등급 변환."""
    if score >= ANALYSIS_GRADES['STRONG_BUY']:
        return 'STRONG_BUY'
    elif score >= ANALYSIS_GRADES['BUY']:
        return 'BUY'
    elif score >= ANALYSIS_GRADES['HOLD']:
        return 'HOLD'
    elif score >= ANALYSIS_GRADES['SELL']:
        return 'SELL'
    else:
        return 'STRONG_SELL'


def _generate_recommendation(grade, components):
    """등급 및 컴포넌트에 기반한 추천 생성."""
    recommendations = {
        'STRONG_BUY': '적극 매수 권장. 펀더멘털과 수급이 모두 긍정적.',
        'BUY': '매수 고려. 다수 지표가 긍정적.',
        'HOLD': '보유 유지. 추가 시그널 대기.',
        'SELL': '매도 고려. 부정적 지표 다수.',
        'STRONG_SELL': '적극 매도 권장. 대부분 지표가 부정적.',
    }

    rec = recommendations.get(grade, '분석 데이터 부족.')

    # 강점/약점 식별
    strengths = []
    weaknesses = []
    for name, data in components.items():
        score = data.get('score', 50)
        label = COMPREHENSIVE_SCORING.get(name, {}).get('label', name)
        if score >= 70:
            strengths.append(label)
        elif score < 40:
            weaknesses.append(label)

    return {
        'summary': rec,
        'strengths': strengths,
        'weaknesses': weaknesses,
    }


def calc_comprehensive_score(fundamental=None, technical=None,
                             supply_demand=None, valuation_score=None,
                             growth_quick=None):
    """종합 분석 점수 계산.

    Args:
        fundamental: dict from analyze_fundamentals() with 'score' key.
        technical: dict from analyze_technicals() with 'score' key.
        supply_demand: dict from analyze_supply_demand() with 'score' key.
        valuation_score: float, valuation sub-score (0-100).
            If None, uses fundamental's valuation score.
        growth_quick: dict from calc_growth_quick_score() with 'score' key.

    Returns:
        dict: {score, grade, components, recommendation}
    """
    components = {}
    weighted_sum = 0
    total_weight = 0

    # 펀더멘털
    if fundamental and 'score' in fundamental:
        f_score = fundamental['score']
        components['fundamental'] = {'score': f_score, 'weight': 0.30}
        weighted_sum += f_score * 0.30
        total_weight += 0.30

    # 기술적
    if technical and 'score' in technical:
        t_score = technical['score']
        components['technical'] = {'score': t_score, 'weight': 0.22}
        weighted_sum += t_score * 0.22
        total_weight += 0.22

    # 수급
    if supply_demand and 'score' in supply_demand:
        s_score = supply_demand['score']
        components['supply_demand'] = {'score': s_score, 'weight': 0.22}
        weighted_sum += s_score * 0.22
        total_weight += 0.22

    # 밸류에이션
    v_score = valuation_score
    if v_score is None and fundamental:
        val_data = fundamental.get('valuation', {})
        v_score = val_data.get('score') if isinstance(val_data, dict) else None
    if v_score is not None:
        components['valuation'] = {'score': v_score, 'weight': 0.13}
        weighted_sum += v_score * 0.13
        total_weight += 0.13

    # 성장성 (Growth Quick Score)
    if growth_quick and 'score' in growth_quick:
        g_score = growth_quick['score']
        components['growth'] = {'score': g_score, 'weight': 0.13}
        weighted_sum += g_score * 0.13
        total_weight += 0.13

    # 가중 합산 (가용 컴포넌트만으로 정규화)
    if total_weight > 0:
        score = round(weighted_sum / total_weight * 1.0, 1)
    else:
        score = 50.0

    grade = _get_grade(score)
    recommendation = _generate_recommendation(grade, components)

    return {
        'score': score,
        'grade': grade,
        'components': components,
        'recommendation': recommendation,
    }


# --- US Monetary Regime Overlay (B방식) ---

_SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,
    'secondary_battery': 1.3,
    'bio': 1.2,
    'it': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'construction': 0.8,
    'finance': 0.7,
    'insurance': 0.6,
    'retail': 0.5,
    'defense': 0.4,
    'food': 0.3,
}

_DEFAULT_SENSITIVITY = 0.7


def apply_monetary_overlay(base_score, overlay=None, sector='default'):
    """통화정책 오버레이 적용.

    기존 calc_comprehensive_score() 결과에 us-monetary-regime
    오버레이를 섹터 민감도에 따라 적용한다.
    overlay=None이면 base_score를 그대로 반환.

    Args:
        base_score: float (0~100), calc_comprehensive_score() score.
        overlay: float or None, us-monetary-regime 오버레이 (-15~+15).
        sector: str, 한국 섹터명.

    Returns:
        dict: {original_score, overlay_applied, sector, sector_sensitivity,
               adjusted_overlay, final_score, final_grade, overlay_impact}
    """
    if overlay is None:
        return {
            'original_score': base_score,
            'overlay_applied': None,
            'sector': sector,
            'sector_sensitivity': _SECTOR_SENSITIVITY.get(sector, _DEFAULT_SENSITIVITY),
            'adjusted_overlay': 0,
            'final_score': base_score,
            'final_grade': _get_grade(base_score),
            'overlay_impact': 'neutral',
        }

    sensitivity = _SECTOR_SENSITIVITY.get(sector, _DEFAULT_SENSITIVITY)
    adjusted = round(overlay * sensitivity, 1)
    final = round(max(0, min(100, base_score + adjusted)), 1)

    if adjusted > 0.5:
        impact = 'positive'
    elif adjusted < -0.5:
        impact = 'negative'
    else:
        impact = 'neutral'

    return {
        'original_score': base_score,
        'overlay_applied': overlay,
        'sector': sector,
        'sector_sensitivity': sensitivity,
        'adjusted_overlay': adjusted,
        'final_score': final,
        'final_grade': _get_grade(final),
        'overlay_impact': impact,
    }
