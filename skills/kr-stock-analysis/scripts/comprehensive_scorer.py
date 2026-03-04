"""kr-stock-analysis: 종합 스코어링 엔진."""


# ─── 종합 분석 스코어링 ───

COMPREHENSIVE_SCORING = {
    'fundamental': {'weight': 0.35, 'label': '펀더멘털'},
    'technical': {'weight': 0.25, 'label': '기술적'},
    'supply_demand': {'weight': 0.25, 'label': '수급'},
    'valuation': {'weight': 0.15, 'label': '밸류에이션'},
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
                             supply_demand=None, valuation_score=None):
    """종합 분석 점수 계산.

    Args:
        fundamental: dict from analyze_fundamentals() with 'score' key.
        technical: dict from analyze_technicals() with 'score' key.
        supply_demand: dict from analyze_supply_demand() with 'score' key.
        valuation_score: float, valuation sub-score (0-100).
            If None, uses fundamental's valuation score.

    Returns:
        dict: {score, grade, components, recommendation}
    """
    components = {}
    weighted_sum = 0
    total_weight = 0

    # 펀더멘털
    if fundamental and 'score' in fundamental:
        f_score = fundamental['score']
        components['fundamental'] = {'score': f_score, 'weight': 0.35}
        weighted_sum += f_score * 0.35
        total_weight += 0.35

    # 기술적
    if technical and 'score' in technical:
        t_score = technical['score']
        components['technical'] = {'score': t_score, 'weight': 0.25}
        weighted_sum += t_score * 0.25
        total_weight += 0.25

    # 수급
    if supply_demand and 'score' in supply_demand:
        s_score = supply_demand['score']
        components['supply_demand'] = {'score': s_score, 'weight': 0.25}
        weighted_sum += s_score * 0.25
        total_weight += 0.25

    # 밸류에이션
    v_score = valuation_score
    if v_score is None and fundamental:
        val_data = fundamental.get('valuation', {})
        v_score = val_data.get('score') if isinstance(val_data, dict) else None
    if v_score is not None:
        components['valuation'] = {'score': v_score, 'weight': 0.15}
        weighted_sum += v_score * 0.15
        total_weight += 0.15

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
