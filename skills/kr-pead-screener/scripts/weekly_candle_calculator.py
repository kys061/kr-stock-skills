"""
kr-pead-screener: 주봉 캔들 분석.
갭업 감지, 적색/녹색 캔들 분류, 패턴 품질 평가.
"""

# ── 갭 크기 임계값 ────────────────────────────────────────
MIN_GAP_PCT = 3.0  # 최소 갭 3%

# ── 갭 점수 테이블 ────────────────────────────────────────
GAP_SCORE_TABLE = [
    (15, 100),  # ≥ 15%
    (10,  85),  # 10-14%
    (7,   70),  # 7-9%
    (5,   55),  # 5-6%
    (3,   40),  # 3-4%
]


def detect_gap(prev_close: float, curr_open: float) -> dict:
    """갭업 감지.

    Args:
        prev_close: 전주 종가
        curr_open: 당주 시가
    Returns:
        {'gap_pct': float, 'is_gap_up': bool}
    """
    if prev_close <= 0:
        return {'gap_pct': 0.0, 'is_gap_up': False}

    gap_pct = ((curr_open - prev_close) / prev_close) * 100
    return {
        'gap_pct': gap_pct,
        'is_gap_up': gap_pct >= MIN_GAP_PCT,
    }


def classify_candle(open_price: float, close: float) -> str:
    """캔들 분류.

    Returns:
        'green' (종가 > 시가), 'red' (종가 < 시가), 'doji' (동일)
    """
    if close > open_price:
        return 'green'
    elif close < open_price:
        return 'red'
    else:
        return 'doji'


def analyze_weekly_candles(weekly_data: list) -> dict:
    """주봉 캔들 시퀀스 분석.

    Args:
        weekly_data: [
            {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float},
            ...
        ] 갭업 주봉 이후 최대 5주
    Returns:
        {
            'red_candle_found': bool,
            'red_candle_index': int or None,
            'red_candle_high': float or None,
            'red_candle_low': float or None,
            'breakout_found': bool,
            'volume_declining': bool,
            'weeks_since_gap': int,
        }
    """
    result = {
        'red_candle_found': False,
        'red_candle_index': None,
        'red_candle_high': None,
        'red_candle_low': None,
        'breakout_found': False,
        'volume_declining': False,
        'weeks_since_gap': len(weekly_data),
    }

    if not weekly_data:
        return result

    # 적색 캔들 탐색
    for i, candle in enumerate(weekly_data):
        color = classify_candle(candle['open'], candle['close'])
        if color == 'red':
            result['red_candle_found'] = True
            result['red_candle_index'] = i
            result['red_candle_high'] = candle['high']
            result['red_candle_low'] = candle['low']

            # 거래량 감소 확인 (이전 캔들 대비)
            if i > 0 and candle['volume'] < weekly_data[i - 1]['volume']:
                result['volume_declining'] = True

            # 브레이크아웃 확인 (적색 이후 녹색 캔들)
            for j in range(i + 1, len(weekly_data)):
                next_candle = weekly_data[j]
                next_color = classify_candle(next_candle['open'], next_candle['close'])
                if next_color == 'green' and next_candle['close'] > candle['high']:
                    result['breakout_found'] = True
                    break
            break  # 첫 번째 적색 캔들만 분석

    return result


def score_gap_size(gap_pct: float) -> int:
    """갭 크기 점수."""
    if gap_pct < MIN_GAP_PCT:
        return 0
    for threshold, score in GAP_SCORE_TABLE:
        if gap_pct >= threshold:
            return score
    return 0


def score_pattern_quality(red_found: bool, volume_declining: bool,
                          gap_maintained: bool) -> int:
    """패턴 품질 점수.

    Args:
        red_found: 적색 캔들 형성 여부
        volume_declining: 거래량 감소 여부
        gap_maintained: 갭 유지 여부 (적색 캔들 저가 > 갭 시작 수준)
    """
    if red_found and volume_declining and gap_maintained:
        return 100
    elif red_found and volume_declining:
        return 80
    elif red_found:
        return 60
    else:
        return 40  # MONITORING 상태
