"""kr-earnings-trade: 5팩터 종합 스코어링.

US earnings-trade-analyzer와 동일한 가중치/등급 시스템.
한국 특화: 외국인 순매수 보너스.
"""

# ─── 가중치 ───
WEIGHTS = {
    'gap_size': 0.25,
    'pre_earnings_trend': 0.30,
    'volume_trend': 0.20,
    'ma200_position': 0.15,
    'ma50_position': 0.10,
}

# ─── 등급 ───
GRADE_THRESHOLDS = [
    {'min': 85, 'max': 100, 'grade': 'A', 'name': 'Strong Setup',
     'desc': '강한 실적 반응 + 기관 축적 — 진입 고려'},
    {'min': 70, 'max': 84, 'grade': 'B', 'name': 'Good Setup',
     'desc': '양호한 실적 반응 — 모니터링'},
    {'min': 55, 'max': 69, 'grade': 'C', 'name': 'Mixed Setup',
     'desc': '혼합 시그널 — 추가 분석 필요'},
    {'min': 0, 'max': 54, 'grade': 'D', 'name': 'Weak Setup',
     'desc': '약한 셋업 — 회피'},
]

# ─── 한국 특화: 외국인 순매수 보너스 ───
FOREIGN_BUY_BONUS_DAYS = 5           # 실적 후 5일 연속 순매수
FOREIGN_BUY_BONUS_SCORE = 5          # 보너스 점수
FOREIGN_BUY_MIN_AMOUNT = 1_000_000_000  # 10억원 이상

# ─── 시총 필터 ───
MARKET_CAP_MIN = 500_000_000_000     # 5,000억원

# ─── 실적 조회 ───
LOOKBACK_DAYS = 14                    # 최근 14일 실적 공시 조회


def calc_composite_score(components: dict) -> dict:
    """5팩터 종합 점수 계산.

    Args:
        components: {
            'gap_size': int,
            'pre_earnings_trend': int,
            'volume_trend': int,
            'ma200_position': int,
            'ma50_position': int,
        }

    Returns:
        {'composite_score': int, 'grade': str, 'grade_name': str, ...}
    """
    total = 0
    for key, weight in WEIGHTS.items():
        total += components.get(key, 0) * weight

    score = round(total)

    # 등급 결정
    grade = 'D'
    grade_name = 'Weak Setup'
    grade_desc = '약한 셋업 — 회피'
    for band in GRADE_THRESHOLDS:
        if band['min'] <= score <= band['max']:
            grade = band['grade']
            grade_name = band['name']
            grade_desc = band['desc']
            break

    # 최약/최강 컴포넌트
    weakest = min(components, key=lambda k: components[k])
    strongest = max(components, key=lambda k: components[k])

    return {
        'composite_score': score,
        'grade': grade,
        'grade_name': grade_name,
        'grade_desc': grade_desc,
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


def apply_foreign_bonus(composite_score: int,
                         daily_foreign_net_buys: list) -> dict:
    """외국인 순매수 보너스 적용.

    Args:
        composite_score: 기본 종합 점수
        daily_foreign_net_buys: 실적 후 일별 외국인 순매수 금액 리스트

    Returns:
        {'final_score': int, 'bonus_applied': bool, 'consecutive_days': int}
    """
    if not daily_foreign_net_buys:
        return {
            'final_score': composite_score,
            'bonus_applied': False,
            'consecutive_days': 0,
        }

    # 연속 순매수 일수 계산
    consecutive = 0
    for amount in daily_foreign_net_buys[:FOREIGN_BUY_BONUS_DAYS]:
        if amount >= FOREIGN_BUY_MIN_AMOUNT:
            consecutive += 1
        else:
            break

    bonus_applied = consecutive >= FOREIGN_BUY_BONUS_DAYS
    final_score = composite_score
    if bonus_applied:
        final_score = min(composite_score + FOREIGN_BUY_BONUS_SCORE, 100)

    return {
        'final_score': final_score,
        'bonus_applied': bonus_applied,
        'consecutive_days': consecutive,
    }
