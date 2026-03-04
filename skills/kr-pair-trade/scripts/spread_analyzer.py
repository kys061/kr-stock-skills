"""Z-Score 스프레드 분석기: 진입/청산 시그널."""

import math

# ── Z-Score 시그널 ────────────────────────────────────────────
ZSCORE_STOP = 3.0           # 스탑로스
ZSCORE_ENTRY = 2.0          # 진입 시그널
ZSCORE_WATCH = 1.5          # 관찰
ZSCORE_EXIT = 0.0           # 청산 (평균 회귀)
ZSCORE_PARTIAL = 1.0        # 부분 청산 (50%)
MAX_HOLDING_DAYS = 90       # 최대 보유 기간

# ── Z-Score 스코어 ────────────────────────────────────────────
ZSCORE_SCORES = [
    # (min_abs_z, max_abs_z, score, signal)
    (2.0, 3.0, 100, 'ENTRY'),      # 진입 시그널
    (1.5, 2.0, 70,  'WATCH'),      # 관찰
    (0.0, 1.5, 40,  'NORMAL'),     # 정상 범위
]
ZSCORE_STOP_SCORE = 20             # |Z| > 3.0: 스탑로스


def calc_zscore(spread: list, lookback: int = 252) -> dict:
    """현재 Z-Score 계산.

    Z = (현재_Spread - 평균) / 표준편차

    Args:
        spread: 스프레드 리스트 (최신이 마지막)
        lookback: 통계 계산 기간 (기본 252거래일)
    Returns:
        {'zscore': float, 'mean': float, 'std': float, 'current': float}
    """
    if len(spread) < 30:
        return {'zscore': 0, 'mean': 0, 'std': 0, 'current': 0}

    window = spread[-min(lookback, len(spread)):]
    mean = sum(window) / len(window)
    std = math.sqrt(sum((x - mean) ** 2 for x in window) / len(window))

    current = spread[-1]

    if std == 0:
        return {'zscore': 0, 'mean': mean, 'std': 0, 'current': current}

    zscore = (current - mean) / std
    return {
        'zscore': round(zscore, 4),
        'mean': round(mean, 4),
        'std': round(std, 4),
        'current': round(current, 4),
    }


def classify_signal(zscore: float) -> dict:
    """Z-Score 기반 시그널 분류.

    Args:
        zscore: 현재 Z-Score
    Returns:
        {'signal': str, 'direction': str, 'action': str}
    """
    abs_z = abs(zscore)

    if abs_z > ZSCORE_STOP:
        direction = 'LONG_A' if zscore < 0 else 'SHORT_A'
        return {
            'signal': 'STOP',
            'direction': direction,
            'action': '스탑로스/퇴출',
        }

    if abs_z >= ZSCORE_ENTRY:
        if zscore < 0:
            return {
                'signal': 'ENTRY',
                'direction': 'LONG_A_SHORT_B',
                'action': 'A 매수, B 매도 (Z < -2.0)',
            }
        else:
            return {
                'signal': 'ENTRY',
                'direction': 'SHORT_A_LONG_B',
                'action': 'A 매도, B 매수 (Z > +2.0)',
            }

    if abs_z >= ZSCORE_WATCH:
        return {
            'signal': 'WATCH',
            'direction': 'NEUTRAL',
            'action': '관찰 대기 (1.5 ≤ |Z| < 2.0)',
        }

    if abs_z <= 0.5:
        return {
            'signal': 'EXIT',
            'direction': 'CLOSE',
            'action': '평균 회귀 — 청산 (이익 실현)',
        }

    return {
        'signal': 'NORMAL',
        'direction': 'NEUTRAL',
        'action': '정상 범위 — 보유/관망',
    }


def score_zscore(zscore: float) -> dict:
    """Z-Score 점수 계산.

    Args:
        zscore: 현재 Z-Score
    Returns:
        {'score': int, 'zscore': float, 'signal': str}
    """
    abs_z = abs(zscore)
    signal_data = classify_signal(zscore)

    if abs_z > ZSCORE_STOP:
        return {'score': ZSCORE_STOP_SCORE, 'zscore': round(zscore, 4),
                'signal': signal_data['signal']}

    for min_z, max_z, score, signal in ZSCORE_SCORES:
        if min_z <= abs_z < max_z:
            return {'score': score, 'zscore': round(zscore, 4),
                    'signal': signal}

    return {'score': 40, 'zscore': round(zscore, 4), 'signal': 'NORMAL'}


def calc_risk_reward(zscore: float, spread_std: float) -> dict:
    """리스크/리워드 비율 계산.

    Args:
        zscore: 현재 Z-Score
        spread_std: 스프레드 표준편차
    Returns:
        {'ratio': float, 'target': float, 'stop': float}
    """
    if spread_std <= 0 or abs(zscore) < ZSCORE_ENTRY:
        return {'ratio': 0, 'target': 0, 'stop': 0}

    # 목표: Z = 0 (평균 회귀), 스탑: |Z| = 3.0
    target_distance = abs(zscore) * spread_std      # Z → 0
    stop_distance = (ZSCORE_STOP - abs(zscore)) * spread_std  # Z → ±3.0

    if stop_distance <= 0:
        return {'ratio': 0, 'target': target_distance, 'stop': 0}

    ratio = target_distance / stop_distance
    return {
        'ratio': round(ratio, 2),
        'target': round(target_distance, 2),
        'stop': round(stop_distance, 2),
    }
