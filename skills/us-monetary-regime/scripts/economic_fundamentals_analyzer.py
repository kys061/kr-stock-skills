"""us-monetary-regime: 경제 펀더멘털 분석 (Fed 금리 결정의 근본 원인).

Fed Dual Mandate + 경기 상태를 분석하여
금리 인상/인하 압력을 예측한다.

4-Component:
  1. 인플레이션 (35%) - CPI/PCE, 방향성
  2. 고용/노동시장 (30%) - 실업률, 비농업고용, 임금
  3. 경기 성장 (25%) - GDP, ISM, 선행지표
  4. 외생적 충격 (10%) - 지정학, 팬데믹, 금융위기
"""


# --- Component Weights (sum = 1.00) ---

FUNDAMENTALS_WEIGHTS = {
    'inflation': 0.35,
    'labor': 0.30,
    'growth': 0.25,
    'shock': 0.10,
}

# --- Inflation Scoring ---
# 높은 인플레이션 = 금리 인상 압력 = 낮은 점수 (easing 불리)
# 낮은 인플레이션 = 금리 인하 여유 = 높은 점수 (easing 유리)

INFLATION_TARGET = 2.0  # Fed's target (%)

CPI_THRESHOLDS = {
    'very_high': (6.0, 5),       # 6%+ → 극단적 인상 압력
    'high': (4.0, 15),           # 4-6% → 강한 인상 압력
    'above_target': (3.0, 30),   # 3-4% → 인상 압력
    'slightly_above': (2.5, 40), # 2.5-3% → 약한 인상 압력
    'at_target': (1.5, 60),      # 1.5-2.5% → 목표 근처
    'below_target': (0.5, 75),   # 0.5-1.5% → 인하 여유
    'deflation': (-999, 90),     # <0.5% → 디플레이션 우려 → 강한 인하 여유
}

INFLATION_DIRECTION_ADJ = {
    'accelerating': -15,   # 물가 가속 상승 → 인상 압력 강화
    'stable': 0,           # 안정
    'decelerating': 10,    # 물가 둔화 → 인하 여유 증가
    'falling': 15,         # 물가 하락 → 인하 압력
}


def _score_inflation(cpi_yoy, core_pce_yoy=None, direction='stable'):
    """인플레이션 점수 산출.

    Args:
        cpi_yoy: float, CPI YoY (%).
        core_pce_yoy: float or None, Core PCE YoY (%). Fed 선호 지표.
        direction: str, 인플레이션 방향.
            Options: 'accelerating', 'stable', 'decelerating', 'falling'

    Returns:
        dict: {score, components, interpretation}
    """
    # Core PCE가 있으면 우선 사용 (Fed 선호), 없으면 CPI
    ref_rate = core_pce_yoy if core_pce_yoy is not None else cpi_yoy

    # 기본 점수
    base_score = 50  # default
    for label, (threshold, score) in CPI_THRESHOLDS.items():
        if ref_rate >= threshold:
            base_score = score
            break

    # 방향 보정
    dir_adj = INFLATION_DIRECTION_ADJ.get(direction, 0)
    final_score = max(0, min(100, base_score + dir_adj))

    # 목표 대비 갭
    gap = ref_rate - INFLATION_TARGET

    if gap > 2.0:
        interpretation = f'물가 {ref_rate:.1f}% (목표+{gap:.1f}%p) — 강한 인상 압력'
    elif gap > 0.5:
        interpretation = f'물가 {ref_rate:.1f}% (목표+{gap:.1f}%p) — 인상 압력'
    elif gap > -0.5:
        interpretation = f'물가 {ref_rate:.1f}% (목표 근처) — 중립'
    else:
        interpretation = f'물가 {ref_rate:.1f}% (목표-{abs(gap):.1f}%p) — 인하 여유'

    return {
        'score': round(final_score, 1),
        'components': {
            'cpi_yoy': cpi_yoy,
            'core_pce_yoy': core_pce_yoy,
            'reference_rate': ref_rate,
            'direction': direction,
            'gap_from_target': round(gap, 2),
        },
        'interpretation': interpretation,
    }


# --- Labor Market Scoring ---
# 노동시장 과열 = 인상 압력 = 낮은 점수
# 노동시장 냉각 = 인하 여유 = 높은 점수

UNEMPLOYMENT_THRESHOLDS = {
    'very_tight': (0, 3.5, 20),      # <3.5% → 극도로 타이트
    'tight': (3.5, 4.0, 35),         # 3.5-4.0% → 타이트
    'balanced': (4.0, 4.5, 55),      # 4.0-4.5% → 균형
    'softening': (4.5, 5.5, 70),     # 4.5-5.5% → 냉각
    'weak': (5.5, 100, 85),          # 5.5%+ → 약화
}

NFP_THRESHOLDS = {
    'very_strong': (300, 15),      # 300K+ → 과열
    'strong': (200, 30),           # 200-300K → 강함
    'moderate': (100, 50),         # 100-200K → 적정
    'weak': (50, 70),              # 50-100K → 약화
    'very_weak': (-999, 85),       # <50K → 약세
}

WAGE_THRESHOLDS = {
    'hot': (5.0, 15),         # 5%+ → 임금-물가 스파이럴 우려
    'warm': (4.0, 30),        # 4-5% → 인상 압력
    'normal': (3.0, 55),      # 3-4% → 적정
    'cool': (2.0, 70),        # 2-3% → 냉각
    'cold': (-999, 85),       # <2% → 약화
}


def _score_labor(unemployment_rate, nfp_thousands=150,
                 wage_growth_yoy=3.5):
    """노동시장 점수 산출.

    Args:
        unemployment_rate: float, 실업률 (%).
        nfp_thousands: float, 비농업고용 변동 (천명).
        wage_growth_yoy: float, 평균시간당임금 YoY (%).

    Returns:
        dict: {score, components, interpretation}
    """
    # 실업률 점수 (40%)
    unemp_score = 55
    for label, (low, high, score) in UNEMPLOYMENT_THRESHOLDS.items():
        if low <= unemployment_rate < high:
            unemp_score = score
            break

    # 비농업고용 점수 (35%)
    nfp_score = 50
    for label, (threshold, score) in NFP_THRESHOLDS.items():
        if nfp_thousands >= threshold:
            nfp_score = score
            break

    # 임금상승률 점수 (25%)
    wage_score = 55
    for label, (threshold, score) in WAGE_THRESHOLDS.items():
        if wage_growth_yoy >= threshold:
            wage_score = score
            break

    # 가중 합산
    final = (unemp_score * 0.40 + nfp_score * 0.35 + wage_score * 0.25)
    final = max(0, min(100, final))

    if final < 30:
        interpretation = f'노동시장 과열 (실업률 {unemployment_rate}%) — 강한 인상 압력'
    elif final < 45:
        interpretation = f'노동시장 타이트 (실업률 {unemployment_rate}%) — 인상 압력'
    elif final < 60:
        interpretation = f'노동시장 균형 (실업률 {unemployment_rate}%) — 중립'
    elif final < 75:
        interpretation = f'노동시장 냉각 (실업률 {unemployment_rate}%) — 인하 여유'
    else:
        interpretation = f'노동시장 약화 (실업률 {unemployment_rate}%) — 강한 인하 압력'

    return {
        'score': round(final, 1),
        'components': {
            'unemployment': {'rate': unemployment_rate, 'score': unemp_score},
            'nfp': {'thousands': nfp_thousands, 'score': nfp_score},
            'wages': {'yoy': wage_growth_yoy, 'score': wage_score},
        },
        'interpretation': interpretation,
    }


# --- Economic Growth Scoring ---
# 강한 성장 = 인상 압력 = 낮은 점수
# 약한 성장/침체 = 인하 압력 = 높은 점수

GDP_THRESHOLDS = {
    'overheating': (4.0, 15),      # 4%+ → 과열
    'strong': (3.0, 30),           # 3-4% → 강한 성장
    'moderate': (2.0, 50),         # 2-3% → 적정 성장
    'slow': (1.0, 65),            # 1-2% → 둔화
    'stagnation': (0.0, 80),      # 0-1% → 정체
    'recession': (-999, 95),      # 마이너스 → 침체
}

ISM_THRESHOLDS = {
    'strong_expansion': (57, 20),    # 57+ → 강한 확장
    'expansion': (53, 35),           # 53-57 → 확장
    'mild_expansion': (50, 50),      # 50-53 → 약한 확장
    'mild_contraction': (47, 65),    # 47-50 → 약한 수축
    'contraction': (43, 80),         # 43-47 → 수축
    'deep_contraction': (-999, 95),  # <43 → 심각한 수축
}


def _score_growth(gdp_growth_annualized, ism_manufacturing=50.0,
                  ism_services=50.0, lei_change_6m=0.0):
    """경기 성장 점수 산출.

    Args:
        gdp_growth_annualized: float, GDP 연율화 성장률 (%).
        ism_manufacturing: float, ISM 제조업 PMI.
        ism_services: float, ISM 서비스업 PMI.
        lei_change_6m: float, 선행경제지표 6M 변화율 (%).

    Returns:
        dict: {score, components, interpretation}
    """
    # GDP 점수 (40%)
    gdp_score = 50
    for label, (threshold, score) in GDP_THRESHOLDS.items():
        if gdp_growth_annualized >= threshold:
            gdp_score = score
            break

    # ISM 제조업 점수 (25%)
    ism_mfg_score = 50
    for label, (threshold, score) in ISM_THRESHOLDS.items():
        if ism_manufacturing >= threshold:
            ism_mfg_score = score
            break

    # ISM 서비스 점수 (20%)
    ism_svc_score = 50
    for label, (threshold, score) in ISM_THRESHOLDS.items():
        if ism_services >= threshold:
            ism_svc_score = score
            break

    # 선행지표 점수 (15%)
    if lei_change_6m < -5.0:
        lei_score = 90  # 급락 → 침체 선행
    elif lei_change_6m < -2.0:
        lei_score = 75
    elif lei_change_6m < 0:
        lei_score = 60
    elif lei_change_6m < 2.0:
        lei_score = 45
    else:
        lei_score = 25  # 상승 → 확장 선행

    # 가중 합산
    final = (
        gdp_score * 0.40 +
        ism_mfg_score * 0.25 +
        ism_svc_score * 0.20 +
        lei_score * 0.15
    )
    final = max(0, min(100, final))

    if final < 30:
        interpretation = f'경기 과열 (GDP {gdp_growth_annualized}%) — 인상 압력'
    elif final < 50:
        interpretation = f'경기 확장 (GDP {gdp_growth_annualized}%) — 중립~인상'
    elif final < 70:
        interpretation = f'경기 둔화 (GDP {gdp_growth_annualized}%) — 인하 여유'
    elif final < 85:
        interpretation = f'경기 약세 (GDP {gdp_growth_annualized}%) — 인하 압력'
    else:
        interpretation = f'경기 침체 (GDP {gdp_growth_annualized}%) — 강한 인하 압력'

    return {
        'score': round(final, 1),
        'components': {
            'gdp': {'growth': gdp_growth_annualized, 'score': gdp_score},
            'ism_manufacturing': {'value': ism_manufacturing, 'score': ism_mfg_score},
            'ism_services': {'value': ism_services, 'score': ism_svc_score},
            'lei': {'change_6m': lei_change_6m, 'score': lei_score},
        },
        'interpretation': interpretation,
    }


# --- Exogenous Shock Scoring ---
# 심각한 충격 = 긴급 인하 = 높은 점수
# 충격 없음 = 정상 = 중립 (50)

SHOCK_LEVELS = {
    'none': 50,           # 충격 없음 → 중립
    'minor': 55,          # 약한 충격 → 약간 인하 유리
    'moderate': 65,       # 중간 충격 → 인하 여유
    'severe': 80,         # 심각한 충격 (코로나, 금융위기) → 강한 인하
    'crisis': 95,         # 극단적 위기 → 긴급 인하
}

SHOCK_TYPES = {
    'pandemic': '팬데믹/전염병',
    'war': '전쟁/무력분쟁',
    'financial_crisis': '금융위기/은행위기',
    'trade_war': '무역전쟁/관세분쟁',
    'energy_crisis': '에너지위기/유가급등',
    'geopolitical': '지정학적 긴장',
    'natural_disaster': '자연재해',
    'supply_chain': '공급망 교란',
    'other': '기타',
}


def _score_shock(shock_level='none', shock_type='other',
                 duration_months=0, is_inflationary=False):
    """외생적 충격 점수 산출.

    Args:
        shock_level: str, 충격 수준.
            Options: 'none', 'minor', 'moderate', 'severe', 'crisis'
        shock_type: str, 충격 유형.
        duration_months: int, 충격 지속 기간 (월).
        is_inflationary: bool, 충격이 인플레이션을 유발하는지.
            True: 에너지위기, 공급망교란 → 인상 압력 (점수 하락)
            False: 팬데믹, 금융위기 → 인하 압력 (점수 상승)

    Returns:
        dict: {score, components, interpretation}
    """
    base_score = SHOCK_LEVELS.get(shock_level, 50)

    # 인플레이션 유발형 충격은 반대 방향
    # (물가 올리는 충격 → 금리 인하가 어려움 → 점수 낮춤)
    if is_inflationary and shock_level not in ('none',):
        base_score = 100 - base_score

    # 장기 충격 보정 (6개월+ → 추가 영향)
    if duration_months > 12:
        duration_adj = 10 if not is_inflationary else -10
    elif duration_months > 6:
        duration_adj = 5 if not is_inflationary else -5
    else:
        duration_adj = 0

    final = max(0, min(100, base_score + duration_adj))

    shock_desc = SHOCK_TYPES.get(shock_type, '기타')
    if shock_level == 'none':
        interpretation = '외생적 충격 없음 — 정상 정책 운영'
    elif is_inflationary:
        interpretation = (
            f'{shock_desc} ({shock_level}) — '
            f'인플레이션 유발형 → 인하 제약'
        )
    else:
        interpretation = (
            f'{shock_desc} ({shock_level}, {duration_months}M) — '
            f'경기 위축형 → 인하 압력'
        )

    return {
        'score': round(final, 1),
        'components': {
            'shock_level': shock_level,
            'shock_type': shock_type,
            'duration_months': duration_months,
            'is_inflationary': is_inflationary,
        },
        'interpretation': interpretation,
    }


# --- Fundamentals Pressure Labels ---

PRESSURE_LABELS = {
    'strong_hike': (0, 25),
    'hike': (25, 40),
    'neutral': (40, 60),
    'cut': (60, 75),
    'strong_cut': (75, 100),
}

PRESSURE_DESCRIPTIONS = {
    'strong_hike': '경제 펀더멘털이 강한 금리 인상을 지지. 물가↑ 고용↑ 성장↑.',
    'hike': '경제 펀더멘털이 금리 인상을 시사. 물가 목표 초과 또는 과열.',
    'neutral': '경제 펀더멘털 중립. 물가 목표 근처, 고용 균형.',
    'cut': '경제 펀더멘털이 금리 인하 여유 제공. 성장 둔화 또는 고용 냉각.',
    'strong_cut': '경제 펀더멘털이 강한 금리 인하를 지지. 침체 위험 또는 위기.',
}


def _classify_pressure(score):
    """점수 -> 금리 압력 분류."""
    for label, (low, high) in PRESSURE_LABELS.items():
        if low <= score < high:
            return label
    if score >= 75:
        return 'strong_cut'
    return 'strong_hike'


def analyze_fundamentals(cpi_yoy=3.0, core_pce_yoy=None,
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
    """경제 펀더멘털 종합 분석.

    Fed의 금리 결정 근본 원인이 되는 경제 지표를 분석하여
    금리 인상/인하 압력 점수를 산출한다.

    Args:
        cpi_yoy: float, CPI YoY (%).
        core_pce_yoy: float or None, Core PCE YoY (%).
        inflation_direction: str, 인플레이션 방향.
        unemployment_rate: float, 실업률 (%).
        nfp_thousands: float, 비농업고용 변동 (천명).
        wage_growth_yoy: float, 평균시간당임금 YoY (%).
        gdp_growth_annualized: float, GDP 연율화 성장률 (%).
        ism_manufacturing: float, ISM 제조업 PMI.
        ism_services: float, ISM 서비스업 PMI.
        lei_change_6m: float, 선행경제지표 6M 변화율 (%).
        shock_level: str, 외생적 충격 수준.
        shock_type: str, 충격 유형.
        shock_duration_months: int, 충격 지속 기간 (월).
        shock_is_inflationary: bool, 인플레이션 유발형 충격 여부.

    Returns:
        dict: {fundamentals_score, pressure_label, pressure_description,
               components, dual_mandate_assessment}
    """
    # 4개 컴포넌트 분석
    inflation = _score_inflation(cpi_yoy, core_pce_yoy, inflation_direction)
    labor = _score_labor(unemployment_rate, nfp_thousands, wage_growth_yoy)
    growth = _score_growth(
        gdp_growth_annualized, ism_manufacturing,
        ism_services, lei_change_6m,
    )
    shock = _score_shock(
        shock_level, shock_type,
        shock_duration_months, shock_is_inflationary,
    )

    # 가중 합산
    weighted = (
        inflation['score'] * FUNDAMENTALS_WEIGHTS['inflation'] +
        labor['score'] * FUNDAMENTALS_WEIGHTS['labor'] +
        growth['score'] * FUNDAMENTALS_WEIGHTS['growth'] +
        shock['score'] * FUNDAMENTALS_WEIGHTS['shock']
    )
    fundamentals_score = round(max(0, min(100, weighted)), 1)

    # 분류
    pressure_label = _classify_pressure(fundamentals_score)

    # Dual Mandate 평가
    inflation_ok = 1.5 <= (core_pce_yoy or cpi_yoy) <= 2.5
    employment_ok = 3.5 <= unemployment_rate <= 5.0

    if inflation_ok and employment_ok:
        dual_mandate = 'Both mandates satisfied — policy flexibility'
    elif not inflation_ok and not employment_ok:
        dual_mandate = 'Both mandates challenged — difficult tradeoffs'
    elif not inflation_ok:
        dual_mandate = 'Price stability challenged — inflation focus'
    else:
        dual_mandate = 'Employment challenged — growth support focus'

    return {
        'fundamentals_score': fundamentals_score,
        'pressure_label': pressure_label,
        'pressure_description': PRESSURE_DESCRIPTIONS.get(pressure_label, ''),
        'dual_mandate_assessment': dual_mandate,
        'components': {
            'inflation': inflation,
            'labor': labor,
            'growth': growth,
            'shock': shock,
        },
    }
