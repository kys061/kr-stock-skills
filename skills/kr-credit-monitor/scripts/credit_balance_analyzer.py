"""kr-credit-monitor: 신용잔고 분석."""


# ─── 신용잔고 분석 ───

CREDIT_BALANCE_CONFIG = {
    'lookback_years': 3,        # 퍼센타일 계산: 3년
    'yoy_warning': 0.15,        # YoY +15% 이상: 경고
    'yoy_critical': 0.30,       # YoY +30% 이상: 위험
    'mom_warning': 0.05,        # MoM +5% 이상: 경고
    'mom_critical': 0.10,       # MoM +10% 이상: 위험
}

# 시총 대비 신용잔고 비율 기준
CREDIT_MARKET_RATIO_LEVELS = {
    'critical': 0.030,   # 3.0% 이상: 위험 (역사적 고점 수준)
    'high': 0.025,       # 2.5% 이상: 높음
    'elevated': 0.020,   # 2.0% 이상: 상승
    'normal': 0.015,     # 1.5% 이상: 보통
    'safe': 0.0,         # 1.5% 미만: 안전
}

# ─── 레버리지 사이클 ───

LEVERAGE_CYCLE_PHASES = {
    'EXPANSION': {
        'label': '확장기',
        'condition': 'credit_mom > 0 AND credit_yoy > 0',
        'risk': 'increasing',
    },
    'PEAK': {
        'label': '정점',
        'condition': 'credit_percentile >= 90',
        'risk': 'high',
    },
    'CONTRACTION': {
        'label': '수축기',
        'condition': 'credit_mom < 0 AND credit_yoy > 0',
        'risk': 'decreasing',
    },
    'TROUGH': {
        'label': '저점',
        'condition': 'credit_percentile <= 20',
        'risk': 'low',
    },
}

# --- 고객 예탁금(투자자예수금) 수준 ---

DEPOSIT_LEVEL_THRESHOLDS = {
    'very_high': 60.0,    # 60조원+: 대기 자금 풍부
    'high': 50.0,         # 50조원+
    'normal': 40.0,       # 40조원+
    'low': 30.0,          # 30조원+
    'very_low': 0.0,      # 30조원 미만: 자금 이탈
}

DEPOSIT_CHANGE_SIGNALS = {
    'surge': 0.10,        # MoM +10%+: 대기 자금 급증
    'increase': 0.03,     # MoM +3%~+10%
    'stable_upper': -0.03,  # MoM -3%~+3%
    'decrease': -0.10,    # MoM -3%~-10%
    'exodus': -0.10,      # MoM < -10%: 자금 이탈
}

DEPOSIT_LEVEL_SCORES = {
    'very_high': 90,
    'high': 70,
    'normal': 50,
    'low': 30,
    'very_low': 10,
}

DEPOSIT_SIGNAL_SCORES = {
    'surge': 90,
    'increase': 70,
    'stable': 50,
    'decrease': 30,
    'exodus': 10,
}

# 예탁금 대비 신용잔고 비율
DEPOSIT_CREDIT_RATIO = {
    'overheated': 0.80,   # 80% 이상: 과열
    'high': 0.60,         # 60% 이상
    'normal': 0.40,       # 40% 이상
    'healthy': 0.0,       # 40% 미만: 건전
}


def _classify_market_ratio(ratio):
    """시총 대비 신용잔고 비율 수준 분류."""
    if ratio >= CREDIT_MARKET_RATIO_LEVELS['critical']:
        return 'critical'
    elif ratio >= CREDIT_MARKET_RATIO_LEVELS['high']:
        return 'high'
    elif ratio >= CREDIT_MARKET_RATIO_LEVELS['elevated']:
        return 'elevated'
    elif ratio >= CREDIT_MARKET_RATIO_LEVELS['normal']:
        return 'normal'
    return 'safe'


def calc_credit_percentile(current, historical):
    """신용잔고의 퍼센타일 계산.

    Args:
        current: 현재 신용잔고 금액.
        historical: list of float (과거 신용잔고 금액).

    Returns:
        float: 0-100 퍼센타일.
    """
    if not historical:
        return 50.0
    count_below = sum(1 for h in historical if h < current)
    return round((count_below / len(historical)) * 100, 1)


def _calc_growth_rates(credit_data):
    """YoY/MoM 성장률 계산.

    Args:
        credit_data: list of dict [{date, total}] (최근순).

    Returns:
        dict: {yoy, yoy_level, mom, mom_level}
    """
    if not credit_data or len(credit_data) < 2:
        return {'yoy': 0.0, 'yoy_level': 'normal', 'mom': 0.0, 'mom_level': 'normal'}

    current = credit_data[0].get('total', 0)

    # MoM: 약 20영업일 전
    mom_idx = min(20, len(credit_data) - 1)
    mom_base = credit_data[mom_idx].get('total', 0)
    mom = (current - mom_base) / mom_base if mom_base > 0 else 0.0

    # YoY: 약 252영업일 전
    yoy_idx = min(252, len(credit_data) - 1)
    yoy_base = credit_data[yoy_idx].get('total', 0)
    yoy = (current - yoy_base) / yoy_base if yoy_base > 0 else 0.0

    # 수준 분류
    cfg = CREDIT_BALANCE_CONFIG
    yoy_level = 'normal'
    if yoy >= cfg['yoy_critical']:
        yoy_level = 'critical'
    elif yoy >= cfg['yoy_warning']:
        yoy_level = 'warning'

    mom_level = 'normal'
    if mom >= cfg['mom_critical']:
        mom_level = 'critical'
    elif mom >= cfg['mom_warning']:
        mom_level = 'warning'

    return {
        'yoy': round(yoy, 4),
        'yoy_level': yoy_level,
        'mom': round(mom, 4),
        'mom_level': mom_level,
    }


def classify_leverage_cycle(credit_data):
    """레버리지 사이클 위치 분류.

    Args:
        credit_data: list of dict [{date, total}] (최근순).

    Returns:
        str: 'EXPANSION' / 'PEAK' / 'CONTRACTION' / 'TROUGH'
    """
    if not credit_data:
        return 'TROUGH'

    growth = _calc_growth_rates(credit_data)
    totals = [d.get('total', 0) for d in credit_data]
    percentile = calc_credit_percentile(totals[0], totals) if totals else 50

    # PEAK: 퍼센타일 90%+
    if percentile >= 90:
        return 'PEAK'

    # TROUGH: 퍼센타일 20%-
    if percentile <= 20:
        return 'TROUGH'

    # EXPANSION: MoM > 0 AND YoY > 0
    if growth['mom'] > 0 and growth['yoy'] > 0:
        return 'EXPANSION'

    # CONTRACTION: MoM < 0 AND YoY > 0
    if growth['mom'] < 0 and growth['yoy'] > 0:
        return 'CONTRACTION'

    # 기타: MoM ≤ 0 AND YoY ≤ 0 → TROUGH에 가까움
    if growth['mom'] <= 0 and growth['yoy'] <= 0:
        return 'TROUGH'

    return 'EXPANSION'


def calc_deposit_credit_ratio(credit_balance, deposit_balance):
    """예탁금 대비 신용잔고 비율 계산.

    Args:
        credit_balance: 신용잔고 (원).
        deposit_balance: 투자자예탁금 (원).

    Returns:
        dict: {ratio, level, label}
    """
    if not deposit_balance or deposit_balance <= 0:
        return {'ratio': 0.0, 'level': 'healthy', 'label': '건전'}

    ratio = credit_balance / deposit_balance
    ratio = round(ratio, 4)

    if ratio >= DEPOSIT_CREDIT_RATIO['overheated']:
        level = 'overheated'
        label = '과열'
    elif ratio >= DEPOSIT_CREDIT_RATIO['high']:
        level = 'high'
        label = '높음'
    elif ratio >= DEPOSIT_CREDIT_RATIO['normal']:
        level = 'normal'
        label = '보통'
    else:
        level = 'healthy'
        label = '건전'

    return {'ratio': ratio, 'level': level, 'label': label}


def analyze_credit_balance(credit_data, market_cap):
    """신용잔고 종합 분석.

    Args:
        credit_data: list of dict [{date, margin_loan, margin_short, total}]
                     최근순 정렬.
        market_cap: 시가총액 (원).

    Returns:
        dict: {total, market_ratio, market_ratio_level, yoy, mom,
               percentile, cycle_phase, growth}
    """
    if not credit_data:
        return {
            'total': 0,
            'market_ratio': 0.0,
            'market_ratio_level': 'safe',
            'growth': {'yoy': 0.0, 'yoy_level': 'normal', 'mom': 0.0, 'mom_level': 'normal'},
            'percentile': 50.0,
            'cycle_phase': 'TROUGH',
        }

    latest = credit_data[0]
    total = latest.get('total', 0) or 0

    # 시총 대비 비율
    market_ratio = total / market_cap if market_cap and market_cap > 0 else 0.0
    market_ratio_level = _classify_market_ratio(market_ratio)

    # 성장률
    growth = _calc_growth_rates(credit_data)

    # 퍼센타일
    lookback = CREDIT_BALANCE_CONFIG['lookback_years'] * 252
    totals = [d.get('total', 0) for d in credit_data[:lookback]]
    percentile = calc_credit_percentile(total, totals)

    # 사이클
    cycle_phase = classify_leverage_cycle(credit_data)

    return {
        'total': total,
        'market_ratio': round(market_ratio, 6),
        'market_ratio_level': market_ratio_level,
        'growth': growth,
        'percentile': percentile,
        'cycle_phase': cycle_phase,
    }


def _classify_deposit_level(balance_t):
    """예탁금 잔고(조원) -> 수준 분류."""
    if balance_t >= DEPOSIT_LEVEL_THRESHOLDS['very_high']:
        return 'very_high'
    elif balance_t >= DEPOSIT_LEVEL_THRESHOLDS['high']:
        return 'high'
    elif balance_t >= DEPOSIT_LEVEL_THRESHOLDS['normal']:
        return 'normal'
    elif balance_t >= DEPOSIT_LEVEL_THRESHOLDS['low']:
        return 'low'
    return 'very_low'


def _classify_deposit_signal(change_1m_pct):
    """예탁금 1개월 변화율(%) -> 시그널 분류."""
    change_ratio = change_1m_pct / 100.0
    if change_ratio >= DEPOSIT_CHANGE_SIGNALS['surge']:
        return 'surge'
    elif change_ratio >= DEPOSIT_CHANGE_SIGNALS['increase']:
        return 'increase'
    elif change_ratio >= DEPOSIT_CHANGE_SIGNALS['stable_upper']:
        return 'stable'
    elif change_ratio >= DEPOSIT_CHANGE_SIGNALS['decrease']:
        return 'decrease'
    return 'exodus'


def _deposit_interpretation(level, signal):
    """예탁금 해석 문장 생성."""
    level_labels = {
        'very_high': '대기 자금 매우 풍부',
        'high': '대기 자금 양호',
        'normal': '대기 자금 보통',
        'low': '대기 자금 부족',
        'very_low': '대기 자금 극히 부족',
    }
    signal_labels = {
        'surge': '급증 중 (매수 대기 자금 급격 유입)',
        'increase': '증가 중',
        'stable': '안정적',
        'decrease': '감소 중',
        'exodus': '급감 중 (자금 이탈 경고)',
    }
    return f"{level_labels.get(level, level)}, {signal_labels.get(signal, signal)}"


def analyze_investor_deposits(deposit_balance_t, deposit_change_1m_pct=0.0):
    """고객 예탁금(투자자예수금) 독립 분석.

    Args:
        deposit_balance_t: float, 현재 예탁금 (조원).
        deposit_change_1m_pct: float, 1개월 변화율 (%, e.g. 5.0 = +5%).

    Returns:
        dict: {balance_t, level, change_pct, signal, interpretation,
               buying_power_score}
    """
    level = _classify_deposit_level(deposit_balance_t)
    signal = _classify_deposit_signal(deposit_change_1m_pct)

    level_score = DEPOSIT_LEVEL_SCORES.get(level, 50)
    signal_score = DEPOSIT_SIGNAL_SCORES.get(signal, 50)
    buying_power_score = round(level_score * 0.5 + signal_score * 0.5, 1)
    buying_power_score = max(0, min(100, buying_power_score))

    return {
        'balance_t': deposit_balance_t,
        'level': level,
        'change_pct': deposit_change_1m_pct,
        'signal': signal,
        'interpretation': _deposit_interpretation(level, signal),
        'buying_power_score': buying_power_score,
    }
