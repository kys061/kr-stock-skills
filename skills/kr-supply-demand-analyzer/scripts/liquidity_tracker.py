"""kr-supply-demand-analyzer: 유동성 지표 분석."""


# ─── 유동성 지표 ───

LIQUIDITY_CONFIG = {
    'volume_ma_periods': [5, 20, 60],   # 거래대금 이동평균
    'turnover_warning': 0.5,            # 회전율 경고: 0.5% 이하 (저유동성)
    'turnover_high': 2.0,               # 회전율 과열: 2.0% 이상
    'concentration_warning': 0.30,      # 상위 10종목 비중 30% 이상
    'concentration_critical': 0.50,     # 상위 10종목 비중 50% 이상
}

LIQUIDITY_GRADES = {
    'ABUNDANT': {'min_score': 80, 'label': '풍부'},
    'NORMAL': {'min_score': 60, 'label': '보통'},
    'TIGHT': {'min_score': 40, 'label': '위축'},
    'DRIED': {'min_score': 0, 'label': '고갈'},
}


def calc_volume_ratio(daily_volumes, ma_periods=None):
    """거래대금 이동평균 대비 비율 계산.

    Args:
        daily_volumes: list of float (최근순, 예: [today, yesterday, ...])
        ma_periods: list of int (기본: [5, 20, 60])

    Returns:
        dict: {'5d_ratio': float, '20d_ratio': float, '60d_ratio': float}
              비율 1.0 = 평균과 동일, 2.0 = 평균의 2배
    """
    if ma_periods is None:
        ma_periods = LIQUIDITY_CONFIG['volume_ma_periods']

    if not daily_volumes:
        return {f'{p}d_ratio': 1.0 for p in ma_periods}

    current = daily_volumes[0] if daily_volumes else 0
    result = {}

    for period in ma_periods:
        if len(daily_volumes) >= period:
            ma = sum(daily_volumes[:period]) / period
        elif daily_volumes:
            ma = sum(daily_volumes) / len(daily_volumes)
        else:
            ma = 0

        ratio = current / ma if ma > 0 else 1.0
        result[f'{period}d_ratio'] = round(ratio, 4)

    return result


def _volume_ratio_to_score(ratios):
    """거래대금 비율 → 0-100 점수.

    높은 거래대금(1.5+) = 유동성 풍부 → 높은 점수
    낮은 거래대금(0.5-) = 유동성 부족 → 낮은 점수
    """
    if not ratios:
        return 50.0

    # 5일 평균 비율 기준 (가장 단기)
    ratio_5d = ratios.get('5d_ratio', 1.0)
    ratio_20d = ratios.get('20d_ratio', 1.0)

    # 단기(5일) 70% + 중기(20일) 30%
    avg_ratio = ratio_5d * 0.7 + ratio_20d * 0.3

    if avg_ratio >= 2.0:
        return 95.0
    elif avg_ratio >= 1.5:
        return round(75 + (avg_ratio - 1.5) * 40, 1)
    elif avg_ratio >= 1.0:
        return round(60 + (avg_ratio - 1.0) * 30, 1)
    elif avg_ratio >= 0.7:
        return round(40 + (avg_ratio - 0.7) * 66.7, 1)
    elif avg_ratio >= 0.5:
        return round(25 + (avg_ratio - 0.5) * 75, 1)
    else:
        return round(max(5, avg_ratio * 50), 1)


def calc_turnover_rate(volume, market_cap):
    """회전율 계산.

    Args:
        volume: 거래대금 (원).
        market_cap: 시가총액 (원).

    Returns:
        float: 회전율 (%), 예: 1.5 = 1.5%
    """
    if not market_cap or market_cap <= 0:
        return 0.0
    return round((volume / market_cap) * 100, 4)


def _turnover_to_score(turnover):
    """회전율 → 0-100 점수.

    적정 회전율(0.5~2.0%) = 높은 점수
    과열(2.0%+) = 중간 점수 (과열 경고)
    저유동성(0.5%-) = 낮은 점수
    """
    if turnover >= LIQUIDITY_CONFIG['turnover_high']:
        # 과열: 2.0% → 60, 3.0%+ → 50
        return round(max(50, 70 - (turnover - LIQUIDITY_CONFIG['turnover_high']) * 20), 1)
    elif turnover >= 1.0:
        # 활발: 1.0~2.0% → 80~75
        return round(80 - (turnover - 1.0) * 5, 1)
    elif turnover >= LIQUIDITY_CONFIG['turnover_warning']:
        # 보통: 0.5~1.0% → 60~80
        ratio = (turnover - LIQUIDITY_CONFIG['turnover_warning']) / (
            1.0 - LIQUIDITY_CONFIG['turnover_warning']
        )
        return round(60 + ratio * 20, 1)
    elif turnover > 0:
        # 저유동성: 0~0.5% → 15~60
        ratio = turnover / LIQUIDITY_CONFIG['turnover_warning']
        return round(15 + ratio * 45, 1)
    return 10.0


def _concentration_to_score(concentration):
    """상위 10종목 거래 집중도 → 0-100 점수 (분산이 건전할수록 높은 점수)."""
    if concentration >= LIQUIDITY_CONFIG['concentration_critical']:
        return 10.0
    elif concentration >= LIQUIDITY_CONFIG['concentration_warning']:
        # 0.30~0.50 → 45~10
        ratio = (concentration - LIQUIDITY_CONFIG['concentration_warning']) / (
            LIQUIDITY_CONFIG['concentration_critical'] - LIQUIDITY_CONFIG['concentration_warning']
        )
        return round(45 - ratio * 35, 1)
    elif concentration >= 0.15:
        # 0.15~0.30 → 80~45
        ratio = (concentration - 0.15) / 0.15
        return round(80 - ratio * 35, 1)
    else:
        return 90.0


def _classify_grade(score):
    """점수 → 유동성 등급."""
    for grade, cfg in LIQUIDITY_GRADES.items():
        if score >= cfg['min_score']:
            return grade
    return 'DRIED'


def analyze_liquidity(volume_data, market_cap_data=None, top10_volume=None,
                      total_volume=None):
    """유동성 종합 분석.

    Args:
        volume_data: list of float (일별 거래대금, 최근순)
        market_cap_data: float (시가총액, optional)
        top10_volume: float (상위 10종목 거래대금, optional)
        total_volume: float (전체 거래대금, optional)

    Returns:
        dict: {volume_ratio, turnover, concentration, grade, score}
    """
    # 거래대금 비율
    volume_ratio = calc_volume_ratio(volume_data)
    volume_score = _volume_ratio_to_score(volume_ratio)

    # 회전율
    turnover = 0.0
    turnover_score = 50.0
    if volume_data and market_cap_data:
        turnover = calc_turnover_rate(volume_data[0], market_cap_data)
        turnover_score = _turnover_to_score(turnover)

    # 상위 10종목 집중도
    concentration = 0.0
    concentration_score = 70.0
    if top10_volume and total_volume and total_volume > 0:
        concentration = round(top10_volume / total_volume, 4)
        concentration_score = _concentration_to_score(concentration)

    # 유동성 종합 (거래대금비율 40% + 회전율 30% + 집중도 30%)
    total_score = round(
        volume_score * 0.40 + turnover_score * 0.30 + concentration_score * 0.30,
        1,
    )

    grade = _classify_grade(total_score)

    return {
        'volume_ratio': volume_ratio,
        'volume_score': volume_score,
        'turnover': turnover,
        'turnover_score': turnover_score,
        'concentration': concentration,
        'concentration_score': concentration_score,
        'grade': grade,
        'score': total_score,
    }
