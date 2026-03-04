"""VCP 패턴 탐지기 (Volatility Contraction Pattern).

한국 적응:
- T1 깊이: 10-30% (US 8-35%, ±30% 가격제한폭 반영)
- 수축 비율: <= 0.75
- 최소 수축: 2회
"""

# ── VCP 파라미터 (한국) ───────────────────────────────────────
T1_MIN_DEPTH = 10       # T1 최소 깊이 (%)
T1_MAX_DEPTH_LARGE = 30  # T1 최대 깊이 (대형주, %)
T1_MAX_DEPTH_SMALL = 40  # T1 최대 깊이 (소형주, %)
CONTRACTION_RATIO = 0.75  # 수축 비율 (T2/T1 <= 0.75)
MIN_CONTRACTIONS = 2     # 최소 수축 횟수
IDEAL_CONTRACTIONS = (3, 4)  # 이상적 수축 횟수
PATTERN_MIN_DAYS = 15    # 패턴 최소 기간
PATTERN_MAX_DAYS = 325   # 패턴 최대 기간

# ── Contraction Quality 스코어 테이블 ──────────────────────────
CONTRACTION_SCORES = [
    {'count': 4, 'ratio_ok': True,  'score': 90},
    {'count': 3, 'ratio_ok': True,  'score': 80},
    {'count': 2, 'ratio_ok': True,  'score': 60},
    {'count': 2, 'ratio_ok': False, 'score': 40},
]
CONTRACTION_DEFAULT = 20

TIGHT_BONUS = 10          # 마지막 수축 깊이 < 10% → +10
DEEP_PENALTY = -10        # 마지막 수축 깊이 > 20% → -10


def detect_contractions(swing_highs: list, swing_lows: list) -> list:
    """스윙 고저점에서 수축(Contraction) 목록 탐지.

    Args:
        swing_highs: [(index, price), ...] 스윙 고점 (시간순)
        swing_lows: [(index, price), ...]  스윙 저점 (시간순)
    Returns:
        [{'high': float, 'low': float, 'depth_pct': float, 'high_idx': int, 'low_idx': int}, ...]
    """
    if not swing_highs or not swing_lows:
        return []

    contractions = []
    used_lows = set()

    for h_idx, h_price in swing_highs:
        # 해당 고점 이후 가장 가까운 저점 찾기
        best_low = None
        for l_idx, l_price in swing_lows:
            if l_idx > h_idx and l_idx not in used_lows:
                best_low = (l_idx, l_price)
                break

        if best_low and h_price > 0:
            l_idx, l_price = best_low
            depth = ((h_price - l_price) / h_price) * 100
            if depth >= T1_MIN_DEPTH:
                contractions.append({
                    'high': h_price,
                    'low': l_price,
                    'depth_pct': round(depth, 2),
                    'high_idx': h_idx,
                    'low_idx': l_idx,
                })
                used_lows.add(l_idx)

    return contractions


def check_contraction_progression(contractions: list) -> bool:
    """수축 진행 검사: 각 수축이 이전보다 얕아야 함 (ratio <= 0.75).

    Args:
        contractions: detect_contractions() 결과
    Returns:
        True if 모든 연속 수축 비율이 CONTRACTION_RATIO 이하
    """
    if len(contractions) < 2:
        return False

    for i in range(1, len(contractions)):
        prev_depth = contractions[i - 1]['depth_pct']
        curr_depth = contractions[i]['depth_pct']
        if prev_depth <= 0:
            return False
        ratio = curr_depth / prev_depth
        if ratio > CONTRACTION_RATIO:
            return False
    return True


def calc_pivot_point(contractions: list) -> dict:
    """마지막 수축의 피봇 포인트 계산.

    Args:
        contractions: detect_contractions() 결과
    Returns:
        {'pivot': float, 'stop_loss': float, 'last_depth': float}
    """
    if not contractions:
        return {'pivot': 0, 'stop_loss': 0, 'last_depth': 0}

    last = contractions[-1]
    pivot = last['high']
    stop_loss = round(last['low'] * 0.98, 2)  # -2%
    return {
        'pivot': pivot,
        'stop_loss': stop_loss,
        'last_depth': last['depth_pct'],
    }


def score_contraction_quality(contractions: list) -> dict:
    """Contraction Quality 점수 계산.

    Args:
        contractions: detect_contractions() 결과
    Returns:
        {'score': int, 'count': int, 'ratio_ok': bool, 'adjustments': dict}
    """
    count = len(contractions)
    ratio_ok = check_contraction_progression(contractions)

    base = CONTRACTION_DEFAULT
    for entry in CONTRACTION_SCORES:
        if count >= entry['count']:
            if entry['ratio_ok'] and not ratio_ok:
                continue
            base = entry['score']
            break

    # 수축 2회 + 축소 불충분
    if count >= 2 and not ratio_ok and base == CONTRACTION_DEFAULT:
        base = 40

    adjustments = {}
    if contractions:
        last_depth = contractions[-1]['depth_pct']
        if last_depth < 10:
            adjustments['tight_bonus'] = TIGHT_BONUS
        elif last_depth > 20:
            adjustments['deep_penalty'] = DEEP_PENALTY

    score = max(0, min(100, base + sum(adjustments.values())))
    return {
        'score': score,
        'count': count,
        'ratio_ok': ratio_ok,
        'adjustments': adjustments,
    }
