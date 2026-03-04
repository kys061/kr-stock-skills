"""kr-short-sale-tracker: 숏커버 시그널 탐지."""


# ─── 숏커버 시그널 ───

SHORT_COVER_CONFIG = {
    'consecutive_decrease': {
        'strong': 7,     # 7일 연속 잔고 감소 → 강한 숏커버
        'moderate': 5,   # 5일 연속
        'mild': 3,       # 3일 연속
    },
    'sharp_decrease_pct': 0.10,  # 전일 대비 -10% 이상 급감
    'days_to_cover': {
        'critical': 10,  # 10일 이상: 위험 (숏스퀴즈 가능)
        'high': 5,       # 5일 이상: 높음
        'moderate': 3,   # 3일 이상: 보통
        'low': 0,        # 3일 미만: 낮음
    },
}

# 숏스퀴즈 확률 조건
SQUEEZE_CONDITIONS = {
    'high_balance': 0.05,           # 잔고비율 5% 이상
    'decreasing_balance': True,     # 잔고 감소 추세
    'price_rising': True,           # 주가 상승 중
    'high_days_to_cover': 5,        # DTC 5일 이상
}

SHORT_COVER_SIGNALS = {
    'STRONG_COVER': {'min_score': 80, 'label': '강한 숏커버'},
    'COVER': {'min_score': 60, 'label': '숏커버 진행'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'BUILDING': {'min_score': 20, 'label': '공매도 축적'},
    'HEAVY_SHORT': {'min_score': 0, 'label': '과도한 공매도'},
}

# ─── 공매도 리스크 스코어 ───

SHORT_RISK_WEIGHTS = {
    'short_ratio': {'weight': 0.30, 'label': '잔고비율 수준'},
    'trend': {'weight': 0.30, 'label': '증가/감소 추세'},
    'concentration': {'weight': 0.20, 'label': '집중도'},
    'days_to_cover': {'weight': 0.20, 'label': '커버 소요일'},
}
# 가중치 합계: 0.30 + 0.30 + 0.20 + 0.20 = 1.00

SHORT_RISK_GRADES = {
    'LOW': {'min_score': 0, 'max_score': 25, 'label': '낮음'},
    'MODERATE': {'min_score': 25, 'max_score': 50, 'label': '보통'},
    'HIGH': {'min_score': 50, 'max_score': 75, 'label': '높음'},
    'EXTREME': {'min_score': 75, 'max_score': 100, 'label': '극단적'},
}


def _count_consecutive_decrease(short_balances):
    """연속 잔고 감소 일수.

    Args:
        short_balances: list of float (최근순).

    Returns:
        int: 연속 감소 일수.
    """
    if len(short_balances) < 2:
        return 0

    count = 0
    for i in range(len(short_balances) - 1):
        if short_balances[i] < short_balances[i + 1]:
            count += 1
        else:
            break
    return count


def _classify_decrease_strength(days):
    """연속 감소 일수 → 강도."""
    thresholds = SHORT_COVER_CONFIG['consecutive_decrease']
    if days >= thresholds['strong']:
        return 'strong'
    elif days >= thresholds['moderate']:
        return 'moderate'
    elif days >= thresholds['mild']:
        return 'mild'
    return 'none'


def _check_sharp_decrease(current, previous):
    """전일 대비 급감 여부.

    Returns:
        tuple: (is_sharp, decrease_pct)
    """
    if not previous or previous == 0:
        return False, 0.0
    pct = (current - previous) / previous
    threshold = -SHORT_COVER_CONFIG['sharp_decrease_pct']
    return pct <= threshold, round(pct, 4)


def calc_days_to_cover(short_balance, avg_volume):
    """Days-to-Cover 계산.

    Args:
        short_balance: 공매도 잔고 (주).
        avg_volume: 평균 일 거래량 (주).

    Returns:
        float: DTC (일)
    """
    if not avg_volume or avg_volume <= 0:
        return 0.0
    return round(short_balance / avg_volume, 2)


def _classify_dtc(dtc):
    """DTC → 수준 분류."""
    thresholds = SHORT_COVER_CONFIG['days_to_cover']
    if dtc >= thresholds['critical']:
        return 'critical'
    elif dtc >= thresholds['high']:
        return 'high'
    elif dtc >= thresholds['moderate']:
        return 'moderate'
    return 'low'


def calc_squeeze_probability(balance_ratio, dtc, trend_decreasing, price_rising):
    """숏스퀴즈 확률 추정.

    Args:
        balance_ratio: 잔고비율 (0-1).
        dtc: Days-to-Cover.
        trend_decreasing: bool (잔고 감소 추세).
        price_rising: bool (주가 상승 중).

    Returns:
        float: 0.0-1.0 확률.
    """
    conditions_met = 0
    total_conditions = 4

    if balance_ratio >= SQUEEZE_CONDITIONS['high_balance']:
        conditions_met += 1
    if trend_decreasing:
        conditions_met += 1
    if price_rising:
        conditions_met += 1
    if dtc >= SQUEEZE_CONDITIONS['high_days_to_cover']:
        conditions_met += 1

    # 조건 충족 비율 기반 + 비선형 보너스
    base = conditions_met / total_conditions
    if conditions_met >= 4:
        return round(min(0.85, base + 0.15), 2)
    elif conditions_met >= 3:
        return round(min(0.65, base + 0.05), 2)
    return round(base, 2)


def _classify_cover_signal(score):
    """숏커버 점수 → 시그널."""
    for signal, cfg in SHORT_COVER_SIGNALS.items():
        if score >= cfg['min_score']:
            return signal
    return 'HEAVY_SHORT'


def detect_short_cover(short_data, price_data=None):
    """숏커버 시그널 탐지.

    Args:
        short_data: list of dict [{date, short_balance, short_volume, total_volume}]
                    최근순 정렬.
        price_data: list of float (종가, 최근순, optional).

    Returns:
        dict: {signal, consecutive_decrease, decrease_strength, sharp_decrease,
               days_to_cover, dtc_level, squeeze_probability}
    """
    if not short_data:
        return {
            'signal': 'NEUTRAL',
            'consecutive_decrease': 0,
            'decrease_strength': 'none',
            'sharp_decrease': False,
            'sharp_decrease_pct': 0.0,
            'days_to_cover': 0.0,
            'dtc_level': 'low',
            'squeeze_probability': 0.0,
        }

    # 잔고 시계열
    balances = [d.get('short_balance', 0) or 0 for d in short_data]

    # 연속 감소
    consec_decrease = _count_consecutive_decrease(balances)
    decrease_strength = _classify_decrease_strength(consec_decrease)

    # 급감
    sharp = False
    sharp_pct = 0.0
    if len(balances) >= 2:
        sharp, sharp_pct = _check_sharp_decrease(balances[0], balances[1])

    # DTC
    current_balance = balances[0] if balances else 0
    volumes = [d.get('total_volume', 0) or 0 for d in short_data]
    avg_vol = sum(volumes[:20]) / min(len(volumes), 20) if volumes else 0
    dtc = calc_days_to_cover(current_balance, avg_vol)
    dtc_level = _classify_dtc(dtc)

    # 숏커버 점수 (0-100)
    cover_score = 50  # 기본

    # 연속 감소 → 점수 상승
    if decrease_strength == 'strong':
        cover_score += 30
    elif decrease_strength == 'moderate':
        cover_score += 20
    elif decrease_strength == 'mild':
        cover_score += 10

    # 급감 → 추가
    if sharp:
        cover_score += 15

    # DTC 높으면 숏커버 가능성 ↑
    if dtc_level == 'critical':
        cover_score += 10
    elif dtc_level == 'high':
        cover_score += 5

    # 잔고 증가 중이면 점수 하락
    if consec_decrease == 0 and len(balances) >= 2:
        if balances[0] > balances[1]:
            cover_score -= 20

    cover_score = max(0, min(100, cover_score))
    signal = _classify_cover_signal(cover_score)

    # 숏스퀴즈 확률
    # 잔고비율은 short_data에서 추정 (shares_outstanding 없을 때 0)
    balance_ratio = 0.0
    if short_data[0].get('balance_ratio'):
        balance_ratio = short_data[0]['balance_ratio']

    trend_decreasing = consec_decrease >= SHORT_COVER_CONFIG['consecutive_decrease']['mild']
    price_rising = False
    if price_data and len(price_data) >= 5:
        price_rising = price_data[0] > price_data[4]

    squeeze_prob = calc_squeeze_probability(balance_ratio, dtc, trend_decreasing, price_rising)

    return {
        'signal': signal,
        'cover_score': cover_score,
        'consecutive_decrease': consec_decrease,
        'decrease_strength': decrease_strength,
        'sharp_decrease': sharp,
        'sharp_decrease_pct': sharp_pct,
        'days_to_cover': dtc,
        'dtc_level': dtc_level,
        'squeeze_probability': squeeze_prob,
    }


def _ratio_to_risk_score(balance_level, trade_level):
    """잔고/거래비율 수준 → 리스크 점수 (높을수록 위험)."""
    level_scores = {
        'extreme': 95,
        'high': 75,
        'moderate': 50,
        'low': 25,
        'minimal': 10,
    }
    balance_score = level_scores.get(balance_level, 30)
    trade_score = level_scores.get(trade_level, 30)
    return round(balance_score * 0.6 + trade_score * 0.4, 1)


def _trend_to_risk_score(consecutive_decrease, sharp_decrease):
    """추세 → 리스크 점수 (감소 = 낮은 리스크, 증가 = 높은 리스크).

    숏커버 진행(감소) → 리스크 낮음 → 낮은 점수
    공매도 축적(증가) → 리스크 높음 → 높은 점수
    """
    if consecutive_decrease >= 7:
        score = 15  # 강한 숏커버 → 낮은 리스크
    elif consecutive_decrease >= 5:
        score = 25
    elif consecutive_decrease >= 3:
        score = 35
    else:
        score = 65  # 감소 없음 → 중간~높은 리스크

    if sharp_decrease:
        score = max(10, score - 15)  # 급감 → 리스크 감소

    return score


def _dtc_to_risk_score(dtc):
    """DTC → 리스크 점수."""
    if dtc >= 10:
        return 90
    elif dtc >= 5:
        return 70
    elif dtc >= 3:
        return 50
    elif dtc >= 1:
        return 30
    return 15


def _classify_risk_grade(score):
    """리스크 점수 → 등급."""
    for grade, cfg in SHORT_RISK_GRADES.items():
        if cfg['min_score'] <= score < cfg['max_score']:
            return grade
    if score >= 75:
        return 'EXTREME'
    return 'LOW'


def calc_short_risk_score(ratio_data, cover_data, concentration_data=None):
    """공매도 리스크 스코어 계산.

    Args:
        ratio_data: analyze_short_ratio() 결과.
        cover_data: detect_short_cover() 결과.
        concentration_data: analyze_sector_concentration() 결과 (optional).

    Returns:
        dict: {score, grade, label, components}
    """
    # 잔고비율 리스크
    ratio_risk = _ratio_to_risk_score(
        ratio_data.get('balance_level', 'minimal'),
        ratio_data.get('trade_level', 'low'),
    )

    # 추세 리스크
    trend_risk = _trend_to_risk_score(
        cover_data.get('consecutive_decrease', 0),
        cover_data.get('sharp_decrease', False),
    )

    # 집중도 리스크
    conc_risk = 30  # 기본
    if concentration_data:
        hhi = concentration_data.get('hhi', 0)
        anomalies = len(concentration_data.get('anomalies', []))
        conc_risk = min(90, round(hhi * 100 + anomalies * 20, 1))

    # DTC 리스크
    dtc_risk = _dtc_to_risk_score(cover_data.get('days_to_cover', 0))

    # 가중 합산
    weights = SHORT_RISK_WEIGHTS
    total = (
        ratio_risk * weights['short_ratio']['weight']
        + trend_risk * weights['trend']['weight']
        + conc_risk * weights['concentration']['weight']
        + dtc_risk * weights['days_to_cover']['weight']
    )
    total = round(max(0, min(100, total)), 1)

    grade = _classify_risk_grade(total)
    label = SHORT_RISK_GRADES[grade]['label']

    return {
        'score': total,
        'grade': grade,
        'label': label,
        'components': {
            'short_ratio': {'score': ratio_risk, 'weight': weights['short_ratio']['weight']},
            'trend': {'score': trend_risk, 'weight': weights['trend']['weight']},
            'concentration': {'score': conc_risk, 'weight': weights['concentration']['weight']},
            'days_to_cover': {'score': dtc_risk, 'weight': weights['days_to_cover']['weight']},
        },
    }
