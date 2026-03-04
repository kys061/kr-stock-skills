"""
kr-vcp-screener: 5-컴포넌트 가중합 스코어러.
Trend Template(25%) + Contraction Quality(25%) + Volume Pattern(20%)
+ Pivot Proximity(15%) + Relative Strength(15%) = 100%.
"""

# ── 가중치 ────────────────────────────────────────────────────
WEIGHTS = {
    'trend_template':       0.25,
    'contraction_quality':  0.25,
    'volume_pattern':       0.20,
    'pivot_proximity':      0.15,
    'relative_strength':    0.15,
}

# ── 등급 ──────────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Textbook VCP', 'min': 90, 'max': 100, 'action': '피봇에서 매수 (1.5-2x 사이징)'},
    {'name': 'Strong VCP',   'min': 80, 'max': 89,  'action': '피봇에서 매수 (표준 사이징)'},
    {'name': 'Good VCP',     'min': 70, 'max': 79,  'action': '거래량 확인 후 매수'},
    {'name': 'Developing',   'min': 60, 'max': 69,  'action': '관찰 리스트'},
    {'name': 'No VCP',       'min': 0,  'max': 59,  'action': '패스'},
]

# ── Stage 2 통과 필수 ────────────────────────────────────────
STAGE2_MIN_POINTS = 6  # 7점 중 6점 이상 필수


def calc_vcp_total(components: dict, stage2_points: int = 7) -> dict:
    """5-컴포넌트 VCP 종합 스코어 계산.

    Args:
        components: {
            'trend_template': int (0-100),
            'contraction_quality': int (0-100),
            'volume_pattern': int (0-100),
            'pivot_proximity': int (0-100),
            'relative_strength': int (0-100),
        }
        stage2_points: Stage 2 템플릿 통과 점수 (0-7)
    Returns:
        {
            'total_score': int,
            'rating': str,
            'action': str,
            'stage2_passed': bool,
            'components': dict,
            'weights': dict,
        }
    """
    stage2_passed = stage2_points >= STAGE2_MIN_POINTS

    # Stage 2 미통과 시 자동 No VCP
    if not stage2_passed:
        return {
            'total_score': 0,
            'rating': 'No VCP',
            'action': 'Stage 2 미충족 — 패스',
            'stage2_passed': False,
            'components': components,
            'weights': WEIGHTS,
        }

    # 가중합 계산
    total = 0
    for comp, weight in WEIGHTS.items():
        total += components.get(comp, 0) * weight
    total = round(max(0, min(100, total)))

    rating = 'No VCP'
    action = '패스'
    for band in RATING_BANDS:
        if band['min'] <= total <= band['max']:
            rating = band['name']
            action = band['action']
            break

    return {
        'total_score': total,
        'rating': rating,
        'action': action,
        'stage2_passed': True,
        'components': components,
        'weights': WEIGHTS,
    }
