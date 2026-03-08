"""kr-stock-analysis: 기술적 분석 엔진."""


# ─── 기술적 지표 ───

TECHNICAL_INDICATORS = {
    'trend': {
        'ma20': {'period': 20, 'label': '20일 이동평균'},
        'ma60': {'period': 60, 'label': '60일 이동평균'},
        'ma120': {'period': 120, 'label': '120일 이동평균'},
    },
    'momentum': {
        'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},
    },
    'volatility': {
        'bollinger': {'period': 20, 'std': 2},
    },
    'volume': {
        'avg_volume_20': {'period': 20, 'label': '20일 평균 거래량'},
        'volume_ratio': {'label': '거래량 비율 (당일/20일평균)'},
    },
}


def calc_moving_averages(prices, periods=(20, 60, 120)):
    """이동평균선 계산.

    Args:
        prices: list of closing prices (oldest first).
        periods: tuple of MA periods.

    Returns:
        dict: {ma20: value, ma60: value, ...}
    """
    result = {}
    for p in periods:
        key = f'ma{p}'
        if len(prices) >= p:
            result[key] = round(sum(prices[-p:]) / p, 2)
        else:
            result[key] = None
    return result


def calc_rsi(prices, period=14):
    """RSI (Relative Strength Index) 계산.

    Args:
        prices: list of closing prices (oldest first).
        period: RSI period (default 14).

    Returns:
        float: RSI value (0-100), or None if insufficient data.
    """
    if len(prices) < period + 1:
        return None

    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = changes[-(period):]

    gains = [c for c in recent if c > 0]
    losses = [-c for c in recent if c < 0]

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calc_macd(prices, fast=12, slow=26, signal_period=9):
    """MACD 계산.

    Args:
        prices: list of closing prices (oldest first).
        fast: fast EMA period.
        slow: slow EMA period.
        signal_period: signal line EMA period.

    Returns:
        dict: {macd, signal, histogram} or None if insufficient data.
    """
    if len(prices) < slow + signal_period:
        return None

    def _ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_values.append(price * multiplier + ema_values[-1] * (1 - multiplier))
        return ema_values

    fast_ema = _ema(prices, fast)
    slow_ema = _ema(prices, slow)

    # Align lengths: fast_ema is longer, trim to match slow_ema length
    offset = len(fast_ema) - len(slow_ema)
    macd_line = [f - s for f, s in zip(fast_ema[offset:], slow_ema)]

    if len(macd_line) < signal_period:
        return None

    signal_line = _ema(macd_line, signal_period)
    # Align
    macd_offset = len(macd_line) - len(signal_line)
    macd_val = macd_line[-1]
    signal_val = signal_line[-1]

    return {
        'macd': round(macd_val, 2),
        'signal': round(signal_val, 2),
        'histogram': round(macd_val - signal_val, 2),
    }


def calc_bollinger_bands(prices, period=20, std_mult=2):
    """볼린저 밴드 계산.

    Args:
        prices: list of closing prices (oldest first).
        period: 이동평균 기간.
        std_mult: 표준편차 배수.

    Returns:
        dict: {upper, middle, lower, bandwidth, percent_b} or None.
    """
    if len(prices) < period:
        return None

    recent = prices[-period:]
    middle = sum(recent) / period
    variance = sum((p - middle) ** 2 for p in recent) / period
    std = variance ** 0.5

    upper = middle + std_mult * std
    lower = middle - std_mult * std
    current = prices[-1]

    bandwidth = (upper - lower) / middle * 100 if middle != 0 else 0
    percent_b = (current - lower) / (upper - lower) * 100 if (upper - lower) != 0 else 50

    return {
        'upper': round(upper, 2),
        'middle': round(middle, 2),
        'lower': round(lower, 2),
        'bandwidth': round(bandwidth, 2),
        'percent_b': round(percent_b, 2),
    }


def _score_trend(current_price, ma_data):
    """추세 점수. 가격이 이평선 위일수록 높은 점수."""
    if not ma_data or current_price is None:
        return 50.0

    scores = []
    for key in ('ma20', 'ma60', 'ma120'):
        ma = ma_data.get(key)
        if ma is None or ma == 0:
            continue
        ratio = (current_price - ma) / ma * 100
        if ratio > 10:
            scores.append(90)
        elif ratio > 5:
            scores.append(75)
        elif ratio > 0:
            scores.append(60)
        elif ratio > -5:
            scores.append(40)
        elif ratio > -10:
            scores.append(25)
        else:
            scores.append(10)

    # MA 배열도 (20 > 60 > 120 = 정배열)
    ma20 = ma_data.get('ma20')
    ma60 = ma_data.get('ma60')
    ma120 = ma_data.get('ma120')
    if ma20 and ma60 and ma120:
        if ma20 > ma60 > ma120:
            scores.append(90)  # 정배열
        elif ma20 < ma60 < ma120:
            scores.append(10)  # 역배열
        else:
            scores.append(50)  # 혼합

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_momentum(rsi, macd_data):
    """모멘텀 점수."""
    scores = []
    if rsi is not None:
        if rsi >= 70:
            scores.append(40)  # 과매수 = 조정 가능
        elif rsi >= 50:
            scores.append(70)  # 강세
        elif rsi >= 30:
            scores.append(50)  # 중립~약세
        else:
            scores.append(60)  # 과매도 = 반등 가능

    if macd_data:
        hist = macd_data.get('histogram', 0)
        if hist > 0:
            scores.append(70)
        elif hist > -50:
            scores.append(45)
        else:
            scores.append(25)

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_volatility(bb_data):
    """변동성 점수."""
    if not bb_data:
        return 50.0
    pctb = bb_data.get('percent_b', 50)
    if pctb > 100:
        return 35.0  # 상단 돌파 (과열)
    elif pctb > 80:
        return 45.0
    elif pctb > 50:
        return 65.0
    elif pctb > 20:
        return 55.0
    elif pctb > 0:
        return 60.0  # 하단 근접 (반등 가능)
    else:
        return 65.0  # 하단 이탈 (과매도)


def _score_volume(volume_ratio):
    """거래량 점수."""
    if volume_ratio is None:
        return 50.0
    if volume_ratio > 3.0:
        return 80.0  # 폭발적 거래량
    elif volume_ratio > 1.5:
        return 70.0  # 강한 거래
    elif volume_ratio > 0.8:
        return 55.0  # 보통
    elif volume_ratio > 0.5:
        return 40.0  # 약한 거래
    else:
        return 30.0  # 극소 거래


def calc_support_resistance(current_price, ma_data, bb_data, week52_high, week52_low):
    """지지선/저항선 산출.

    Args:
        current_price: 현재가
        ma_data: {'ma20': float, 'ma60': float, 'ma120': float}
        bb_data: {'upper': float, 'lower': float, ...} or None
        week52_high: 52주 최고가 (None 허용)
        week52_low: 52주 최저가 (None 허용)

    Returns:
        {
            'supports': [float, ...],    # 현재가 아래 지지선 (내림차순)
            'resistances': [float, ...], # 현재가 위 저항선 (오름차순)
        }
    """
    levels = []

    # 이동평균선
    for key in ('ma20', 'ma60', 'ma120'):
        val = ma_data.get(key)
        if val is not None and val > 0:
            levels.append(val)

    # 볼린저 밴드
    if bb_data:
        if bb_data.get('lower'):
            levels.append(bb_data['lower'])
        if bb_data.get('upper'):
            levels.append(bb_data['upper'])

    # 52주 고/저
    if week52_high and week52_high > 0:
        levels.append(week52_high)
    if week52_low and week52_low > 0:
        levels.append(week52_low)

    # 분류
    supports = sorted(
        [lv for lv in levels if lv < current_price],
        reverse=True,
    )
    resistances = sorted(
        [lv for lv in levels if lv > current_price],
    )

    return {
        'supports': supports,
        'resistances': resistances,
    }


def analyze_technicals(ohlcv_data):
    """종합 기술적 분석.

    Args:
        ohlcv_data: dict with keys:
            prices: list of closing prices (oldest first)
            volumes: list of volumes (oldest first, optional)
            current_price: current price (optional, defaults to last price)

    Returns:
        dict: {trend, momentum, volatility, volume, score}
    """
    prices = ohlcv_data.get('prices', [])
    volumes = ohlcv_data.get('volumes', [])
    current_price = ohlcv_data.get('current_price', prices[-1] if prices else None)

    # 이동평균
    ma_data = calc_moving_averages(prices)

    # RSI
    rsi = calc_rsi(prices)

    # MACD
    macd_data = calc_macd(prices)

    # 볼린저 밴드
    bb_data = calc_bollinger_bands(prices)

    # 거래량 비율
    volume_ratio = None
    if len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        if avg_vol > 0:
            volume_ratio = round(volumes[-1] / avg_vol, 2)

    # 각 카테고리 점수
    trend_score = _score_trend(current_price, ma_data)
    momentum_score = _score_momentum(rsi, macd_data)
    volatility_score = _score_volatility(bb_data)
    volume_score = _score_volume(volume_ratio)

    # 기술적 종합: 추세 40% + 모멘텀 25% + 변동성 15% + 거래량 20%
    total = (trend_score * 0.40 + momentum_score * 0.25
             + volatility_score * 0.15 + volume_score * 0.20)

    return {
        'trend': {
            'moving_averages': ma_data,
            'current_price': current_price,
            'score': trend_score,
        },
        'momentum': {
            'rsi': rsi,
            'macd': macd_data,
            'score': momentum_score,
        },
        'volatility': {
            'bollinger': bb_data,
            'score': volatility_score,
        },
        'volume': {
            'volume_ratio': volume_ratio,
            'score': volume_score,
        },
        'score': round(total, 1),
    }
