"""kr-short-sale-tracker: 공매도 비율 분석."""


# ─── 공매도 비율 분석 ───

SHORT_RATIO_CONFIG = {
    'ma_periods': [5, 20, 60],  # 이동평균 기간
    'percentile_lookback': 252,  # 퍼센타일 계산: 1년 (영업일)
}

# 잔고비율 수준 (공매도 잔고 / 상장주식수)
SHORT_BALANCE_LEVELS = {
    'extreme': 0.10,     # 10% 이상: 극단적
    'high': 0.05,        # 5% 이상: 높음
    'moderate': 0.02,    # 2% 이상: 보통
    'low': 0.01,         # 1% 이상: 낮음
    'minimal': 0.0,      # 1% 미만: 미미
}

# 거래비율 수준 (공매도 거래량 / 총 거래량)
SHORT_TRADE_LEVELS = {
    'extreme': 0.20,     # 20% 이상: 극단적
    'high': 0.10,        # 10% 이상: 높음
    'moderate': 0.05,    # 5% 이상: 보통
    'low': 0.0,          # 5% 미만: 낮음
}


def _classify_balance_level(ratio):
    """잔고비율 수준 분류."""
    if ratio >= SHORT_BALANCE_LEVELS['extreme']:
        return 'extreme'
    elif ratio >= SHORT_BALANCE_LEVELS['high']:
        return 'high'
    elif ratio >= SHORT_BALANCE_LEVELS['moderate']:
        return 'moderate'
    elif ratio >= SHORT_BALANCE_LEVELS['low']:
        return 'low'
    return 'minimal'


def _classify_trade_level(ratio):
    """거래비율 수준 분류."""
    if ratio >= SHORT_TRADE_LEVELS['extreme']:
        return 'extreme'
    elif ratio >= SHORT_TRADE_LEVELS['high']:
        return 'high'
    elif ratio >= SHORT_TRADE_LEVELS['moderate']:
        return 'moderate'
    return 'low'


def calc_short_percentile(current_ratio, historical_ratios):
    """현재 공매도 비율의 퍼센타일 계산.

    Args:
        current_ratio: 현재 잔고비율.
        historical_ratios: list of float (과거 비율들).

    Returns:
        float: 0-100 퍼센타일.
    """
    if not historical_ratios:
        return 50.0

    count_below = sum(1 for r in historical_ratios if r < current_ratio)
    return round((count_below / len(historical_ratios)) * 100, 1)


def _calc_ma_ratios(short_data, ma_periods=None):
    """공매도 잔고비율 이동평균 계산.

    Args:
        short_data: list of dict [{date, balance_ratio, ...}] (최근순)
        ma_periods: list of int

    Returns:
        dict: {'5d_ma': float, '20d_ma': float, '60d_ma': float}
    """
    if ma_periods is None:
        ma_periods = SHORT_RATIO_CONFIG['ma_periods']

    ratios = [d.get('balance_ratio', 0) for d in short_data if d.get('balance_ratio') is not None]
    result = {}

    for period in ma_periods:
        if len(ratios) >= period:
            ma = sum(ratios[:period]) / period
        elif ratios:
            ma = sum(ratios) / len(ratios)
        else:
            ma = 0
        result[f'{period}d_ma'] = round(ma, 6)

    return result


def analyze_short_ratio(short_data, shares_outstanding):
    """공매도 비율 종합 분석.

    Args:
        short_data: list of dict [{date, short_balance, short_volume, total_volume}]
                    최근순 정렬.
        shares_outstanding: 상장주식수.

    Returns:
        dict: {balance_ratio, trade_ratio, ma_ratios, percentile, level}
    """
    if not short_data or not shares_outstanding:
        return {
            'balance_ratio': 0.0,
            'trade_ratio': 0.0,
            'balance_level': 'minimal',
            'trade_level': 'low',
            'ma_ratios': {},
            'percentile': 50.0,
        }

    latest = short_data[0]

    # 잔고비율
    short_balance = latest.get('short_balance', 0) or 0
    balance_ratio = short_balance / shares_outstanding if shares_outstanding > 0 else 0.0

    # 거래비율
    short_volume = latest.get('short_volume', 0) or 0
    total_volume = latest.get('total_volume', 0) or 0
    trade_ratio = short_volume / total_volume if total_volume > 0 else 0.0

    # 잔고비율 시계열 (이동평균, 퍼센타일용)
    enriched_data = []
    for d in short_data:
        sb = d.get('short_balance', 0) or 0
        br = sb / shares_outstanding if shares_outstanding > 0 else 0.0
        enriched_data.append({**d, 'balance_ratio': br})

    ma_ratios = _calc_ma_ratios(enriched_data)

    # 퍼센타일 (1년)
    lookback = SHORT_RATIO_CONFIG['percentile_lookback']
    historical = [e['balance_ratio'] for e in enriched_data[:lookback]]
    percentile = calc_short_percentile(balance_ratio, historical)

    return {
        'balance_ratio': round(balance_ratio, 6),
        'trade_ratio': round(trade_ratio, 6),
        'balance_level': _classify_balance_level(balance_ratio),
        'trade_level': _classify_trade_level(trade_ratio),
        'ma_ratios': ma_ratios,
        'percentile': percentile,
    }


def analyze_sector_concentration(sector_short_data):
    """섹터별 공매도 집중도 분석.

    Args:
        sector_short_data: dict {sector: {short_balance, total_volume}}

    Returns:
        dict: {sector_ratios, anomalies, hhi}
    """
    if not sector_short_data:
        return {'sector_ratios': {}, 'anomalies': [], 'hhi': 0.0}

    sector_ratios = {}
    total_short = 0
    for sector, data in sector_short_data.items():
        sb = data.get('short_balance', 0) or 0
        total_short += sb
        sector_ratios[sector] = sb

    # 섹터별 비중
    if total_short > 0:
        for sector in sector_ratios:
            sector_ratios[sector] = round(sector_ratios[sector] / total_short, 4)
    else:
        for sector in sector_ratios:
            sector_ratios[sector] = 0.0

    # HHI 집중도
    hhi = sum(share ** 2 for share in sector_ratios.values())

    # 이상치: 단일 섹터 30% 이상
    anomalies = [
        sector for sector, share in sector_ratios.items()
        if share >= 0.30
    ]

    return {
        'sector_ratios': sector_ratios,
        'anomalies': anomalies,
        'hhi': round(hhi, 4),
    }
