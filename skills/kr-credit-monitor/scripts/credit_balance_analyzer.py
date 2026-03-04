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
