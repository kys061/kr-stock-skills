"""kr-institutional-flow: 4팩터 종합 수급 스코어링.

외국인(40%) + 기관(30%) + 일관성(20%) + 거래량(10%).
한국 특화: Retail-Counter 보너스.
"""

# ─── 가중치 ───
WEIGHTS = {
    'foreign_flow': 0.40,
    'institutional_flow': 0.30,
    'flow_consistency': 0.20,
    'volume_confirmation': 0.10,
}

# ─── 등급 ───
RATING_BANDS = [
    {'min': 85, 'max': 100, 'name': 'Strong Accumulation',
     'desc': '강력 축적 — 외국인+기관 동반 매수'},
    {'min': 70, 'max': 84, 'name': 'Accumulation',
     'desc': '축적 중 — 모니터링'},
    {'min': 55, 'max': 69, 'name': 'Mild Positive',
     'desc': '약한 긍정 — 추가 확인 필요'},
    {'min': 40, 'max': 54, 'name': 'Neutral',
     'desc': '중립 — 수급 방향 불명'},
    {'min': 0, 'max': 39, 'name': 'Distribution',
     'desc': '이탈 중 — 주의'},
]

# ─── 수급 일관성 점수 테이블 ───
CONSISTENCY_SCORE_TABLE = [
    (80, 100),   # ≥ 80% 순매수일 → 100점
    (60, 80),    # ≥ 60% → 80점
    (50, 60),    # ≥ 50% → 60점
    (40, 40),    # ≥ 40% → 40점
    (0, 20),     # < 40% → 20점
]

# ─── 거래량 확인 점수 테이블 ───
VOLUME_CONFIRM_TABLE = [
    (1.5, 100),  # ≥ 1.5x → 100점
    (1.2, 75),   # ≥ 1.2x → 75점
    (1.0, 50),   # ≥ 1.0x → 50점
    (0, 25),     # < 1.0x → 25점
]

# ─── 시총 필터 ───
MARKET_CAP_MIN = 500_000_000_000   # 5,000억원


def calc_flow_consistency(daily_net_buys: list) -> dict:
    """수급 일관성 점수 계산.

    20일 중 순매수 일수 비율 기반.

    Args:
        daily_net_buys: 일별 순매수 리스트

    Returns:
        {'score': int, 'ratio': float, 'buy_days': int, 'total_days': int}
    """
    if not daily_net_buys:
        return {'score': 20, 'ratio': 0.0, 'buy_days': 0, 'total_days': 0}

    total = len(daily_net_buys)
    buy_days = sum(1 for x in daily_net_buys if x > 0)
    ratio = (buy_days / total) * 100 if total > 0 else 0

    score = CONSISTENCY_SCORE_TABLE[-1][1]
    for threshold, s in CONSISTENCY_SCORE_TABLE:
        if ratio >= threshold:
            score = s
            break

    return {
        'score': score,
        'ratio': round(ratio, 1),
        'buy_days': buy_days,
        'total_days': total,
    }


def calc_volume_confirmation(daily_net_buys: list,
                              daily_volumes: list) -> dict:
    """거래량 동반 확인 점수 계산.

    순매수일 평균거래량 / 순매도일 평균거래량 비율.

    Args:
        daily_net_buys: 일별 순매수 리스트
        daily_volumes: 일별 거래량 리스트

    Returns:
        {'score': int, 'ratio': float}
    """
    if not daily_net_buys or not daily_volumes:
        return {'score': 25, 'ratio': 0.0}

    min_len = min(len(daily_net_buys), len(daily_volumes))
    buy_vols = []
    sell_vols = []

    for i in range(min_len):
        if daily_net_buys[i] > 0:
            buy_vols.append(daily_volumes[i])
        elif daily_net_buys[i] < 0:
            sell_vols.append(daily_volumes[i])

    if not buy_vols or not sell_vols:
        return {'score': 25, 'ratio': 0.0}

    buy_avg = sum(buy_vols) / len(buy_vols)
    sell_avg = sum(sell_vols) / len(sell_vols)

    if sell_avg <= 0:
        return {'score': 25, 'ratio': 0.0}

    ratio = buy_avg / sell_avg

    score = VOLUME_CONFIRM_TABLE[-1][1]
    for threshold, s in VOLUME_CONFIRM_TABLE:
        if ratio >= threshold:
            score = s
            break

    return {'score': score, 'ratio': round(ratio, 2)}


def calc_composite_score(components: dict) -> dict:
    """4팩터 종합 점수 계산.

    Args:
        components: {
            'foreign_flow': int,
            'institutional_flow': int,
            'flow_consistency': int,
            'volume_confirmation': int,
        }

    Returns:
        {'composite_score': int, 'rating': str, 'rating_name': str, ...}
    """
    total = 0
    for key, weight in WEIGHTS.items():
        total += components.get(key, 0) * weight

    score = round(total)

    rating = 'Distribution'
    rating_name = 'Distribution'
    rating_desc = '이탈 중 — 주의'
    for band in RATING_BANDS:
        if band['min'] <= score <= band['max']:
            rating = band['name']
            rating_name = band['name']
            rating_desc = band['desc']
            break

    weakest = min(components, key=lambda k: components[k])
    strongest = max(components, key=lambda k: components[k])

    return {
        'composite_score': score,
        'rating': rating,
        'rating_name': rating_name,
        'rating_desc': rating_desc,
        'weakest_component': weakest,
        'weakest_score': components[weakest],
        'strongest_component': strongest,
        'strongest_score': components[strongest],
        'component_breakdown': {
            k: {'score': components[k], 'weight': WEIGHTS[k],
                'weighted': round(components[k] * WEIGHTS[k], 1)}
            for k in WEIGHTS
        },
    }


def get_rating(score: float) -> dict:
    """점수 → 등급 분류.

    Args:
        score: 종합 점수 (0-100)

    Returns:
        {'rating': str, 'desc': str}
    """
    for band in RATING_BANDS:
        if band['min'] <= score <= band['max']:
            return {'rating': band['name'], 'desc': band['desc']}
    return {'rating': 'Distribution', 'desc': '이탈 중 — 주의'}
