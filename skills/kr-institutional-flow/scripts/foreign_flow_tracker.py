"""kr-institutional-flow: 외국인 수급 심화 분석.

외국인 지분율 추세와 매수→매도 전환점을 감지한다.
"""


def calc_ownership_trend(ownership_history: list) -> dict:
    """외국인 지분율 추세 분석.

    Args:
        ownership_history: [{date, ratio}, ...] 시간순 정렬

    Returns:
        {
            'trend_direction': 'up' | 'down' | 'sideways',
            'change_rate': float (기간 내 변화폭 %p),
            'start_ratio': float,
            'end_ratio': float
        }
    """
    if not ownership_history or len(ownership_history) < 2:
        return {
            'trend_direction': 'sideways',
            'change_rate': 0.0,
            'start_ratio': 0.0,
            'end_ratio': 0.0,
        }

    start = ownership_history[0].get('ratio', 0)
    end = ownership_history[-1].get('ratio', 0)
    change = end - start

    if change > 0.5:
        direction = 'up'
    elif change < -0.5:
        direction = 'down'
    else:
        direction = 'sideways'

    return {
        'trend_direction': direction,
        'change_rate': round(change, 2),
        'start_ratio': round(start, 2),
        'end_ratio': round(end, 2),
    }


def detect_turning_point(daily_net_buys: list, window: int = 5) -> dict:
    """외국인 순매수→순매도 또는 역방향 전환점 감지.

    최근 window일과 그 이전 window일의 방향을 비교한다.

    Args:
        daily_net_buys: 일별 순매수 리스트 (시간순)
        window: 비교 윈도우 크기

    Returns:
        {
            'turning_point': bool,
            'direction': 'buy_to_sell' | 'sell_to_buy' | 'none',
            'recent_sum': float,
            'previous_sum': float
        }
    """
    if not daily_net_buys or len(daily_net_buys) < window * 2:
        return {
            'turning_point': False,
            'direction': 'none',
            'recent_sum': 0,
            'previous_sum': 0,
        }

    recent = daily_net_buys[-window:]
    previous = daily_net_buys[-(window * 2):-window]

    recent_sum = sum(recent)
    previous_sum = sum(previous)

    turning = False
    direction = 'none'

    if previous_sum > 0 and recent_sum < 0:
        turning = True
        direction = 'buy_to_sell'
    elif previous_sum < 0 and recent_sum > 0:
        turning = True
        direction = 'sell_to_buy'

    return {
        'turning_point': turning,
        'direction': direction,
        'recent_sum': recent_sum,
        'previous_sum': previous_sum,
    }
