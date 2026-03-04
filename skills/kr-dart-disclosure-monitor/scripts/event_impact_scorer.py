"""kr-dart-disclosure-monitor: 이벤트 영향도 평가."""

from .disclosure_classifier import DISCLOSURE_TYPES


# ─── 이벤트 영향도 (1-5) ───

EVENT_IMPACT_LEVELS = {
    5: {
        'label': 'Critical',
        'korean': '매우 심각',
        'events': [
            'delisting', 'reduction', 'management_issue', 'trading_halt',
        ],
        'action': '즉시 확인 필요',
    },
    4: {
        'label': 'High',
        'korean': '높음',
        'events': [
            'merger', 'acquisition', 'rights_offering', 'ceo_change',
            'decrease',  # 감배
            'spin_off',
        ],
        'action': '당일 내 확인',
    },
    3: {
        'label': 'Medium',
        'korean': '보통',
        'events': [
            'preliminary', 'confirmed',  # 실적
            'major_holder',  # 5% 보유변동
            'increase',  # 증배
            'convertible',  # CB/BW
        ],
        'action': '주간 리뷰 시 확인',
    },
    2: {
        'label': 'Low',
        'korean': '낮음',
        'events': [
            'treasury_stock', 'articles', 'bonus_issue',
            'contract', 'patent',
        ],
        'action': '참고',
    },
    1: {
        'label': 'Info',
        'korean': '정보',
        'events': [
            'guidance', 'board', 'facility',
            'record_date',
        ],
        'action': '기록',
    },
}

# 영향도 보정 요인
IMPACT_ADJUSTMENTS = {
    'market_cap_large': 1.0,        # 시총 10조+ → 가중치 유지
    'market_cap_mid': 0.8,          # 시총 1-10조 → 0.8배
    'market_cap_small': 0.6,        # 시총 1조 미만 → 0.6배
    'after_hours': 1.2,             # 장후 공시 → 1.2배
    'consecutive_disclosure': 1.5,  # 연속 공시 → 1.5배
}

# 공시 빈도 이상 탐지
FREQUENCY_ANOMALY = {
    'normal_daily': 2,     # 일 2건 이하: 정상
    'elevated_daily': 5,   # 일 5건 이상: 상승
    'anomaly_daily': 10,   # 일 10건 이상: 이상
}

# ─── 공시 리스크 스코어 ───

DISCLOSURE_RISK_WEIGHTS = {
    'event_severity': {'weight': 0.35, 'label': '이벤트 심각도'},
    'frequency': {'weight': 0.20, 'label': '공시 빈도 이상'},
    'stake_change': {'weight': 0.25, 'label': '지분 변동 방향'},
    'governance': {'weight': 0.20, 'label': '지배구조 안정성'},
}
# 가중치 합계: 0.35 + 0.20 + 0.25 + 0.20 = 1.00

DISCLOSURE_RISK_GRADES = {
    'NORMAL': {'min_score': 0, 'max_score': 25, 'label': '정상'},
    'ATTENTION': {'min_score': 25, 'max_score': 50, 'label': '주의'},
    'WARNING': {'min_score': 50, 'max_score': 75, 'label': '경고'},
    'CRITICAL': {'min_score': 75, 'max_score': 100, 'label': '위험'},
}


def _get_event_impact_level(subtype):
    """서브타입 → 영향도 레벨 (1-5)."""
    if not subtype:
        return 1
    for level, info in EVENT_IMPACT_LEVELS.items():
        if subtype in info['events']:
            return level
    return 1


def _get_market_cap_adjustment(market_cap):
    """시총 → 보정 배수."""
    if market_cap is None:
        return 1.0
    if market_cap >= 10_000_000_000_000:  # 10조
        return IMPACT_ADJUSTMENTS['market_cap_large']
    elif market_cap >= 1_000_000_000_000:  # 1조
        return IMPACT_ADJUSTMENTS['market_cap_mid']
    return IMPACT_ADJUSTMENTS['market_cap_small']


def score_event_impact(disclosure_type, subtype, market_cap=None, timing=None):
    """이벤트 영향도 스코어 계산.

    Args:
        disclosure_type: 공시 유형 (EARNINGS, DIVIDEND, ...).
        subtype: 세부 유형.
        market_cap: 시가총액 (원, optional).
        timing: 'after_hours' 등 (optional).

    Returns:
        dict: {level, label, action, adjusted_level, score}
    """
    base_level = _get_event_impact_level(subtype)
    info = EVENT_IMPACT_LEVELS.get(base_level, EVENT_IMPACT_LEVELS[1])

    # 보정
    adjustment = _get_market_cap_adjustment(market_cap)
    if timing == 'after_hours':
        adjustment *= IMPACT_ADJUSTMENTS['after_hours']

    adjusted_level = round(base_level * adjustment, 1)

    # 영향도 → 0-100 점수 (5단계 → 0-100)
    score = round(min(100, (base_level / 5) * 100 * adjustment), 1)

    return {
        'level': base_level,
        'label': info['label'],
        'korean': info['korean'],
        'action': info['action'],
        'adjusted_level': adjusted_level,
        'score': score,
    }


def detect_frequency_anomaly(disclosures, corp_code=None, lookback_days=30):
    """공시 빈도 이상 탐지.

    Args:
        disclosures: list of dict (분류된 공시 목록).
        corp_code: 특정 기업 코드 (optional, 필터링용).
        lookback_days: 분석 기간 (일).

    Returns:
        dict: {total_count, daily_avg, is_anomaly, anomaly_score}
    """
    if not disclosures:
        return {
            'total_count': 0,
            'daily_avg': 0.0,
            'is_anomaly': False,
            'anomaly_score': 0,
        }

    # 기업 필터링
    filtered = disclosures
    if corp_code:
        filtered = [d for d in disclosures if d.get('corp_code') == corp_code]

    total = len(filtered)
    daily_avg = total / max(lookback_days, 1)

    # 이상 여부
    anomaly_cfg = FREQUENCY_ANOMALY
    is_anomaly = daily_avg >= anomaly_cfg['anomaly_daily']

    # 점수: normal(0) → anomaly(100)
    if daily_avg >= anomaly_cfg['anomaly_daily']:
        anomaly_score = 90
    elif daily_avg >= anomaly_cfg['elevated_daily']:
        ratio = (daily_avg - anomaly_cfg['elevated_daily']) / (
            anomaly_cfg['anomaly_daily'] - anomaly_cfg['elevated_daily']
        )
        anomaly_score = round(50 + ratio * 40, 1)
    elif daily_avg >= anomaly_cfg['normal_daily']:
        ratio = (daily_avg - anomaly_cfg['normal_daily']) / (
            anomaly_cfg['elevated_daily'] - anomaly_cfg['normal_daily']
        )
        anomaly_score = round(10 + ratio * 40, 1)
    else:
        anomaly_score = 5

    return {
        'total_count': total,
        'daily_avg': round(daily_avg, 2),
        'is_anomaly': is_anomaly,
        'anomaly_score': round(anomaly_score, 1),
    }


def _severity_to_risk(events):
    """이벤트 심각도 → 리스크 점수."""
    if not events:
        return 10

    max_level = max(e.get('level', 1) for e in events) if events else 1
    avg_level = sum(e.get('level', 1) for e in events) / len(events) if events else 1

    # max 70% + avg 30%
    score = round((max_level / 5) * 100 * 0.7 + (avg_level / 5) * 100 * 0.3, 1)
    return min(100, score)


def _governance_to_risk(governance_events):
    """지배구조 관련 이벤트 → 리스크 점수."""
    if not governance_events:
        return 10  # 이벤트 없음 → 안정

    # CEO 변경, 이사회 이벤트 등
    ceo_changes = sum(1 for e in governance_events if e.get('subtype') == 'ceo_change')
    board_events = sum(1 for e in governance_events if e.get('subtype') == 'board')

    score = 10
    score += ceo_changes * 30
    score += board_events * 10
    return min(100, score)


def _classify_risk_grade(score):
    """리스크 점수 → 등급."""
    for grade, cfg in DISCLOSURE_RISK_GRADES.items():
        if cfg['min_score'] <= score < cfg['max_score']:
            return grade
    if score >= 75:
        return 'CRITICAL'
    return 'NORMAL'


def calc_disclosure_risk_score(events, stake_data=None, governance_data=None,
                                frequency_data=None):
    """공시 리스크 스코어 계산.

    Args:
        events: list of dict (score_event_impact 결과들).
        stake_data: dict (track_stake_changes 결과, optional).
        governance_data: list of dict (지배구조 이벤트, optional).
        frequency_data: dict (detect_frequency_anomaly 결과, optional).

    Returns:
        dict: {score, grade, label, components}
    """
    # 심각도
    severity_risk = _severity_to_risk(events)

    # 빈도
    freq_risk = 10
    if frequency_data:
        freq_risk = frequency_data.get('anomaly_score', 10)

    # 지분 변동
    stake_risk = 20  # 기본: 변동 없음
    if stake_data:
        signal = stake_data.get('signal', 'NEUTRAL')
        signal_scores = {
            'ACCUMULATION': 15,   # 축적 → 안정적 → 낮은 리스크
            'DISPOSAL': 70,       # 매각 → 불안 → 높은 리스크
            'TREASURY_BUY': 10,   # 자사주 매입 → 긍정
            'TREASURY_SELL': 55,  # 자사주 매각 → 부정
            'NEUTRAL': 20,
        }
        stake_risk = signal_scores.get(signal, 20)

    # 지배구조
    gov_risk = _governance_to_risk(governance_data or [])

    # 가중 합산
    weights = DISCLOSURE_RISK_WEIGHTS
    total = (
        severity_risk * weights['event_severity']['weight']
        + freq_risk * weights['frequency']['weight']
        + stake_risk * weights['stake_change']['weight']
        + gov_risk * weights['governance']['weight']
    )
    total = round(max(0, min(100, total)), 1)

    grade = _classify_risk_grade(total)
    label = DISCLOSURE_RISK_GRADES[grade]['label']

    return {
        'score': total,
        'grade': grade,
        'label': label,
        'components': {
            'event_severity': {'score': severity_risk, 'weight': weights['event_severity']['weight']},
            'frequency': {'score': freq_risk, 'weight': weights['frequency']['weight']},
            'stake_change': {'score': stake_risk, 'weight': weights['stake_change']['weight']},
            'governance': {'score': gov_risk, 'weight': weights['governance']['weight']},
        },
    }
