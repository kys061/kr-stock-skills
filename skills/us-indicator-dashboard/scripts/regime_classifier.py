"""미국 경제 레짐 분류 모듈.

5-컴포넌트(물가/경기/고용/심리/대외) 스코어로 4-레짐 판정.
"""

from enum import Enum
from typing import Optional


class Regime(Enum):
    GOLDILOCKS = 'Goldilocks'
    OVERHEATING = 'Overheating'
    STAGFLATION = 'Stagflation'
    RECESSION = 'Recession'


REGIME_DESCRIPTIONS = {
    Regime.GOLDILOCKS: {
        'kr': '골디락스 (적정 성장 + 물가 안정)',
        'kr_impact': '위험자산 강세, 한국 시장 유리',
    },
    Regime.OVERHEATING: {
        'kr': '과열 (강한 성장 + 물가 상승)',
        'kr_impact': '금리 인상 우려, 한국 시장 부정적',
    },
    Regime.STAGFLATION: {
        'kr': '스태그플레이션 (성장 둔화 + 물가 상승)',
        'kr_impact': '최악 시나리오, 위험자산 급락',
    },
    Regime.RECESSION: {
        'kr': '침체 (역성장 + 물가 안정)',
        'kr_impact': '긴급 인하 기대, 초기 부정 → 후반 긍정',
    },
}

COMPONENT_WEIGHTS = {
    'inflation': 0.30,
    'growth': 0.25,
    'employment': 0.25,
    'sentiment': 0.10,
    'external': 0.10,
}


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _linear_score(value: float, low: float, high: float) -> float:
    """low→0, high→100 선형 매핑."""
    if high == low:
        return 50.0
    return _clamp((value - low) / (high - low) * 100)


def calc_inflation_score(cpi: float = None, pce: float = None,
                          ppi: float = None,
                          inflation_exp: float = None) -> dict:
    """물가 컴포넌트 스코어 (0~100). 높을수록 물가 안정."""
    target = 2.0
    scores = {}
    values = {'cpi': cpi, 'pce': pce, 'ppi': ppi, 'inflation_exp': inflation_exp}

    for name, val in values.items():
        if val is None:
            continue
        gap = abs(val - target)
        # gap 0 → 100, gap 1 → 60, gap 2 → 30, gap 3+ → 0
        s = _clamp(100 - gap * 35)
        scores[name] = {'value': val, 'gap_from_target': round(gap, 2), 'score': round(s, 1)}

    if not scores:
        return {'score': 50.0, 'level': 'unknown', 'detail': {}}

    avg = sum(d['score'] for d in scores.values()) / len(scores)

    if avg >= 70:
        level = 'low'
    elif avg >= 45:
        level = 'moderate'
    elif avg >= 25:
        level = 'high'
    else:
        level = 'very_high'

    return {'score': round(avg, 1), 'level': level, 'detail': scores}


def calc_growth_score(gdp: float = None, ism_pmi: float = None,
                       retail_sales: float = None,
                       housing_starts: float = None,
                       business_inventories: float = None) -> dict:
    """경기 컴포넌트 스코어 (0~100). 높을수록 경기 강세."""
    components = {}
    weights = {}

    if gdp is not None:
        # GDP: -2% → 0, 0% → 25, 2% → 50, 3% → 75, 4%+ → 100
        s = _clamp((gdp + 2) / 6 * 100)
        components['gdp'] = {'value': gdp, 'score': round(s, 1)}
        weights['gdp'] = 0.35

    if ism_pmi is not None:
        # ISM: 35 → 0, 50 → 50, 60 → 100
        s = _linear_score(ism_pmi, 35, 60)
        components['ism_pmi'] = {'value': ism_pmi, 'score': round(s, 1)}
        weights['ism_pmi'] = 0.30

    if retail_sales is not None:
        # Retail: -2% → 0, 0% → 50, +1% → 100
        s = _clamp((retail_sales + 2) / 3 * 100)
        components['retail_sales'] = {'value': retail_sales, 'score': round(s, 1)}
        weights['retail_sales'] = 0.20

    if housing_starts is not None:
        s = _clamp((housing_starts + 5) / 15 * 100)
        components['housing_starts'] = {'value': housing_starts, 'score': round(s, 1)}
        weights['housing_starts'] = 0.10

    if business_inventories is not None:
        # 재고 0% → 60 (적정), 높으면 과잉
        s = _clamp(60 - abs(business_inventories) * 30)
        components['business_inventories'] = {'value': business_inventories, 'score': round(s, 1)}
        weights['business_inventories'] = 0.05

    if not components:
        return {'score': 50.0, 'level': 'unknown', 'detail': {}}

    total_w = sum(weights.values())
    avg = sum(components[k]['score'] * weights[k] for k in components) / total_w

    if avg >= 75:
        level = 'strong'
    elif avg >= 55:
        level = 'moderate'
    elif avg >= 35:
        level = 'weak'
    else:
        level = 'recession'

    return {'score': round(avg, 1), 'level': level, 'detail': components}


def calc_employment_score(unemployment: float = None,
                           weekly_hours: float = None,
                           hourly_earnings: float = None,
                           jobless_claims: float = None) -> dict:
    """고용 컴포넌트 스코어 (0~100). 높을수록 고용 과열."""
    components = {}
    weights = {}

    if unemployment is not None:
        # 실업: 3.0% → 100(과열), 4.0% → 65, 5.0% → 30, 6%+ → 0
        s = _clamp((6.5 - unemployment) / 3.5 * 100)
        components['unemployment'] = {'value': unemployment, 'score': round(s, 1)}
        weights['unemployment'] = 0.35

    if weekly_hours is not None:
        # 근무시간: 33.0 → 0, 34.0 → 50, 35.0 → 100
        s = _linear_score(weekly_hours, 33.0, 35.0)
        components['weekly_hours'] = {'value': weekly_hours, 'score': round(s, 1)}
        weights['weekly_hours'] = 0.20

    if hourly_earnings is not None:
        # 시간당소득 MoM: 높을수록 과열 (역방향 점수 — 높으면 인하 제약)
        # 0.1% → 80, 0.3% → 50, 0.5%+ → 20
        s = _clamp(100 - hourly_earnings * 150)
        components['hourly_earnings'] = {'value': hourly_earnings, 'score': round(s, 1)}
        weights['hourly_earnings'] = 0.20

    if jobless_claims is not None:
        # 실업수당: 180K → 90, 220K → 65, 300K → 20, 350K+ → 0
        s = _clamp((380 - jobless_claims) / 200 * 100)
        components['jobless_claims'] = {'value': jobless_claims, 'score': round(s, 1)}
        weights['jobless_claims'] = 0.25

    if not components:
        return {'score': 50.0, 'level': 'unknown', 'detail': {}}

    total_w = sum(weights.values())
    avg = sum(components[k]['score'] * weights[k] for k in components) / total_w

    if avg >= 70:
        level = 'tight'
    elif avg >= 50:
        level = 'balanced'
    elif avg >= 30:
        level = 'cooling'
    else:
        level = 'weak'

    return {'score': round(avg, 1), 'level': level, 'detail': components}


def calc_sentiment_score(consumer_sentiment: float = None,
                          consumer_confidence: float = None) -> dict:
    """심리 컴포넌트 스코어 (0~100)."""
    components = {}

    if consumer_sentiment is not None:
        # UMich: 50 → 0, 75 → 40, 100 → 70, 110+ → 90
        s = _linear_score(consumer_sentiment, 50, 120)
        components['consumer_sentiment'] = {'value': consumer_sentiment, 'score': round(s, 1)}

    if consumer_confidence is not None:
        # CB: 60 → 0, 80 → 30, 100 → 60, 130+ → 100
        s = _linear_score(consumer_confidence, 60, 130)
        components['consumer_confidence'] = {'value': consumer_confidence, 'score': round(s, 1)}

    if not components:
        return {'score': 50.0, 'level': 'unknown', 'detail': {}}

    avg = sum(d['score'] for d in components.values()) / len(components)

    if avg >= 70:
        level = 'optimistic'
    elif avg >= 45:
        level = 'neutral'
    elif avg >= 25:
        level = 'cautious'
    else:
        level = 'pessimistic'

    return {'score': round(avg, 1), 'level': level, 'detail': components}


def calc_external_score(current_account: float = None) -> dict:
    """대외 컴포넌트 스코어 (0~100)."""
    if current_account is None:
        return {'score': 50.0, 'level': 'unknown', 'detail': {}}

    # 경상수지 (음수가 정상): -100B → 80, -200B → 50, -300B+ → 20
    s = _clamp((current_account + 350) / 300 * 100)

    if s >= 65:
        level = 'healthy'
    elif s >= 40:
        level = 'moderate'
    else:
        level = 'deficit_widening'

    return {
        'score': round(s, 1),
        'level': level,
        'detail': {'current_account': {'value': current_account, 'score': round(s, 1)}},
    }


def classify_regime(inflation_score: float, growth_score: float,
                     employment_score: float, sentiment_score: float,
                     external_score: float) -> dict:
    """5-컴포넌트로 4-레짐 판정."""
    composite = (
        inflation_score * COMPONENT_WEIGHTS['inflation']
        + growth_score * COMPONENT_WEIGHTS['growth']
        + employment_score * COMPONENT_WEIGHTS['employment']
        + sentiment_score * COMPONENT_WEIGHTS['sentiment']
        + external_score * COMPONENT_WEIGHTS['external']
    )

    inflation_low = inflation_score >= 50
    growth_strong = growth_score >= 50

    if inflation_low and growth_strong:
        regime = Regime.GOLDILOCKS
    elif not inflation_low and growth_strong:
        regime = Regime.OVERHEATING
    elif not inflation_low and not growth_strong:
        regime = Regime.STAGFLATION
    else:
        regime = Regime.RECESSION

    # 경계값 tie-break (45~55 구간)
    if 45 <= inflation_score <= 55 and 45 <= growth_score <= 55:
        if sentiment_score >= 55:
            regime = Regime.GOLDILOCKS
        elif sentiment_score <= 35:
            regime = Regime.STAGFLATION

    desc = REGIME_DESCRIPTIONS[regime]

    components = {
        'inflation': {'score': inflation_score, 'weight': COMPONENT_WEIGHTS['inflation'],
                      'weighted': round(inflation_score * COMPONENT_WEIGHTS['inflation'], 1)},
        'growth': {'score': growth_score, 'weight': COMPONENT_WEIGHTS['growth'],
                   'weighted': round(growth_score * COMPONENT_WEIGHTS['growth'], 1)},
        'employment': {'score': employment_score, 'weight': COMPONENT_WEIGHTS['employment'],
                       'weighted': round(employment_score * COMPONENT_WEIGHTS['employment'], 1)},
        'sentiment': {'score': sentiment_score, 'weight': COMPONENT_WEIGHTS['sentiment'],
                      'weighted': round(sentiment_score * COMPONENT_WEIGHTS['sentiment'], 1)},
        'external': {'score': external_score, 'weight': COMPONENT_WEIGHTS['external'],
                     'weighted': round(external_score * COMPONENT_WEIGHTS['external'], 1)},
    }

    return {
        'regime': regime,
        'regime_kr': desc['kr'],
        'composite_score': round(composite, 1),
        'kr_impact': desc['kr_impact'],
        'components': components,
    }


def _extract_value(indicators: list, ind_id: str) -> Optional[float]:
    """indicators 리스트에서 특정 ID의 value 추출."""
    for ind in indicators:
        if ind.get('id') == ind_id:
            return ind.get('value')
    return None


def analyze_regime(indicators: list) -> dict:
    """지표 리스트에서 레짐 분석 전체 수행."""
    infl = calc_inflation_score(
        cpi=_extract_value(indicators, 'cpi'),
        pce=_extract_value(indicators, 'pce'),
        ppi=_extract_value(indicators, 'ppi'),
        inflation_exp=_extract_value(indicators, 'inflation_exp'),
    )
    growth = calc_growth_score(
        gdp=_extract_value(indicators, 'gdp'),
        ism_pmi=_extract_value(indicators, 'ism_pmi'),
        retail_sales=_extract_value(indicators, 'retail_sales'),
        housing_starts=_extract_value(indicators, 'housing_starts'),
        business_inventories=_extract_value(indicators, 'business_inventories'),
    )
    empl = calc_employment_score(
        unemployment=_extract_value(indicators, 'unemployment'),
        weekly_hours=_extract_value(indicators, 'weekly_hours'),
        hourly_earnings=_extract_value(indicators, 'hourly_earnings'),
        jobless_claims=_extract_value(indicators, 'jobless_claims'),
    )
    sent = calc_sentiment_score(
        consumer_sentiment=_extract_value(indicators, 'consumer_sentiment'),
        consumer_confidence=_extract_value(indicators, 'consumer_confidence'),
    )
    ext = calc_external_score(
        current_account=_extract_value(indicators, 'current_account'),
    )

    result = classify_regime(
        infl['score'], growth['score'], empl['score'],
        sent['score'], ext['score'],
    )
    result['component_details'] = {
        'inflation': infl,
        'growth': growth,
        'employment': empl,
        'sentiment': sent,
        'external': ext,
    }
    return result
