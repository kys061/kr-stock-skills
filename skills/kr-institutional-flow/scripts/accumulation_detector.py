"""kr-institutional-flow: 수급 축적/이탈 패턴 감지.

외국인+기관 동반 매수 & 개인 매도 = Accumulation
외국인+기관 동반 매도 & 개인 매수 = Distribution
"""

# ─── 상수 ───
RETAIL_COUNTER_BONUS = 10
RETAIL_COUNTER_MIN_DAYS = 5


def detect_accumulation(foreign_net: list, inst_net: list,
                         retail_net: list) -> dict:
    """수급 축적/이탈 패턴 감지.

    최근부터 역방향으로 외국인+기관 매수 & 개인 매도가
    동시에 나타나는 연속 일수를 계산한다.

    Args:
        foreign_net: 외국인 일별 순매수 리스트
        inst_net: 기관 일별 순매수 리스트
        retail_net: 개인 일별 순매수 리스트

    Returns:
        {
            'pattern': 'accumulation' | 'distribution' | 'neutral',
            'days': int,
            'strength': float (0-1)
        }
    """
    if not foreign_net or not inst_net or not retail_net:
        return {'pattern': 'neutral', 'days': 0, 'strength': 0.0}

    min_len = min(len(foreign_net), len(inst_net), len(retail_net))

    # 최근부터 연속 accumulation 일수
    acc_days = 0
    for i in range(1, min_len + 1):
        fi = foreign_net[-i]
        ii = inst_net[-i]
        ri = retail_net[-i]
        if fi > 0 and ii > 0 and ri < 0:
            acc_days += 1
        else:
            break

    # 최근부터 연속 distribution 일수
    dist_days = 0
    for i in range(1, min_len + 1):
        fi = foreign_net[-i]
        ii = inst_net[-i]
        ri = retail_net[-i]
        if fi < 0 and ii < 0 and ri > 0:
            dist_days += 1
        else:
            break

    if acc_days >= 3:
        strength = min(acc_days / 10.0, 1.0)
        return {'pattern': 'accumulation', 'days': acc_days,
                'strength': round(strength, 2)}
    elif dist_days >= 3:
        strength = min(dist_days / 10.0, 1.0)
        return {'pattern': 'distribution', 'days': dist_days,
                'strength': round(strength, 2)}
    else:
        return {'pattern': 'neutral', 'days': 0, 'strength': 0.0}


def detect_retail_counter(retail_net: list, smart_money_net: list) -> dict:
    """개인-스마트머니(외국인+기관) 역방향 패턴 감지.

    Args:
        retail_net: 개인 일별 순매수 리스트
        smart_money_net: (외국인+기관) 합계 일별 순매수 리스트

    Returns:
        {
            'counter_pattern': bool,
            'consecutive_days': int,
            'bonus_applicable': bool
        }
    """
    if not retail_net or not smart_money_net:
        return {'counter_pattern': False, 'consecutive_days': 0,
                'bonus_applicable': False}

    min_len = min(len(retail_net), len(smart_money_net))
    consecutive = 0

    for i in range(1, min_len + 1):
        r = retail_net[-i]
        s = smart_money_net[-i]
        if r < 0 and s > 0:
            consecutive += 1
        else:
            break

    bonus = consecutive >= RETAIL_COUNTER_MIN_DAYS
    return {
        'counter_pattern': consecutive >= 3,
        'consecutive_days': consecutive,
        'bonus_applicable': bonus,
    }


def apply_retail_counter_bonus(composite_score: int,
                                retail_counter: dict) -> dict:
    """Retail-Counter 보너스 적용.

    Args:
        composite_score: 기본 종합 점수
        retail_counter: detect_retail_counter 결과

    Returns:
        {'final_score': int, 'bonus_applied': bool}
    """
    if retail_counter.get('bonus_applicable', False):
        final = min(composite_score + RETAIL_COUNTER_BONUS, 100)
        return {'final_score': final, 'bonus_applied': True}
    return {'final_score': composite_score, 'bonus_applied': False}
