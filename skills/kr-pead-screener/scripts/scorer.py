"""
kr-pead-screener: 스테이지 분류 + 4-컴포넌트 스코어링.
Gap Size(30%) + Pattern Quality(25%) + Earnings Surprise(25%) + Risk/Reward(20%) = 100%.
"""

# ── 스테이지 정의 ─────────────────────────────────────────
STAGES = ['MONITORING', 'SIGNAL_READY', 'BREAKOUT', 'EXPIRED']
MAX_WEEKS = 5  # 만료 주기

# ── 가중치 ────────────────────────────────────────────────
WEIGHTS = {
    'gap_size': 0.30,
    'pattern_quality': 0.25,
    'earnings_surprise': 0.25,
    'risk_reward': 0.20,
}

# ── 등급 ──────────────────────────────────────────────────
RATING_BANDS = [
    {'name': 'Strong Signal', 'min': 80, 'max': 100, 'action': '즉시 진입 (브레이크아웃 확인)'},
    {'name': 'Good Signal',   'min': 65, 'max': 79,  'action': '브레이크아웃 대기'},
    {'name': 'Weak Signal',   'min': 50, 'max': 64,  'action': '관찰'},
    {'name': 'No Signal',     'min': 0,  'max': 49,  'action': '패스'},
]

# ── Earnings Surprise 임계값 ──────────────────────────────
SURPRISE_THRESHOLDS = [
    (50, 100),  # ≥ 50% 서프라이즈
    (30,  85),  # 30-49%
    (20,  70),  # 20-29%
    (10,  55),  # 10-19%
    (0,   40),  # 0-9%
]


def classify_stage(weeks_since_gap: int, red_candle_found: bool,
                   breakout_found: bool) -> str:
    """4-Stage 분류.

    Args:
        weeks_since_gap: 갭업 이후 주수
        red_candle_found: 적색 캔들 형성 여부
        breakout_found: 브레이크아웃 발생 여부
    """
    if weeks_since_gap > MAX_WEEKS:
        return 'EXPIRED'
    if breakout_found:
        return 'BREAKOUT'
    if red_candle_found:
        return 'SIGNAL_READY'
    return 'MONITORING'


def score_earnings_surprise(surprise_pct: float) -> int:
    """실적 서프라이즈 점수.

    Args:
        surprise_pct: 실적 서프라이즈 비율 (%) — 컨센서스 대비 초과
    """
    if surprise_pct < 0:
        return 0
    for threshold, score in SURPRISE_THRESHOLDS:
        if surprise_pct >= threshold:
            return score
    return 0


def calc_total_score(gap_score: int, pattern_score: int,
                     surprise_score: int, rr_score: int) -> dict:
    """4-컴포넌트 종합 스코어.

    Returns:
        {'total_score': int, 'rating': str, 'action': str, 'components': dict}
    """
    total = round(
        gap_score * WEIGHTS['gap_size'] +
        pattern_score * WEIGHTS['pattern_quality'] +
        surprise_score * WEIGHTS['earnings_surprise'] +
        rr_score * WEIGHTS['risk_reward']
    )
    total = max(0, min(100, total))

    rating = 'No Signal'
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
        'components': {
            'gap_size': gap_score,
            'pattern_quality': pattern_score,
            'earnings_surprise': surprise_score,
            'risk_reward': rr_score,
        },
        'weights': WEIGHTS,
    }
