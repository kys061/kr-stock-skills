"""
kr-pead-screener: 브레이크아웃 판정.
적색 캔들 고가 돌파 + 거래량 확인.
"""


def check_breakout(current_close: float, current_open: float,
                   red_candle_high: float, current_volume: float = 0,
                   avg_volume: float = 0) -> dict:
    """브레이크아웃 판정.

    Args:
        current_close: 현재 주봉 종가
        current_open: 현재 주봉 시가
        red_candle_high: 적색 캔들 고가
        current_volume: 현재 거래량
        avg_volume: 평균 거래량
    Returns:
        {'is_breakout': bool, 'volume_confirmed': bool, 'pct_above': float}
    """
    is_green = current_close > current_open
    above_red = current_close > red_candle_high

    is_breakout = is_green and above_red
    pct_above = ((current_close - red_candle_high) / red_candle_high * 100) if red_candle_high > 0 else 0

    volume_confirmed = False
    if avg_volume > 0 and current_volume > 0:
        volume_confirmed = current_volume >= avg_volume * 1.2

    return {
        'is_breakout': is_breakout,
        'volume_confirmed': volume_confirmed,
        'pct_above': pct_above,
    }


def calc_risk_reward(entry_price: float, stop_price: float,
                     target_pct: float = 10.0) -> dict:
    """Risk/Reward 계산.

    Args:
        entry_price: 진입가 (적색 캔들 고가)
        stop_price: 스탑가 (적색 캔들 저가)
        target_pct: 목표 수익률 (%)
    Returns:
        {'risk_pct': float, 'reward_pct': float, 'rr_ratio': float, 'score': int}
    """
    if entry_price <= 0 or stop_price <= 0:
        return {'risk_pct': 0, 'reward_pct': 0, 'rr_ratio': 0, 'score': 0}

    risk_pct = ((entry_price - stop_price) / entry_price) * 100
    reward_pct = target_pct

    rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

    # R/R 점수
    if rr_ratio >= 4.0:
        score = 100
    elif rr_ratio >= 3.0:
        score = 85
    elif rr_ratio >= 2.0:
        score = 70
    elif rr_ratio >= 1.5:
        score = 55
    elif rr_ratio >= 1.0:
        score = 40
    else:
        score = 20

    return {
        'risk_pct': round(risk_pct, 2),
        'reward_pct': round(reward_pct, 2),
        'rr_ratio': round(rr_ratio, 2),
        'score': score,
    }
