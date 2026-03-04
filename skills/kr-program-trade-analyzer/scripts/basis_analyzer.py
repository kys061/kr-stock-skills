"""kr-program-trade-analyzer: 선물 베이시스 분석."""

import math


# kr-options-advisor 참조: KOSPI200_MULTIPLIER = 250_000
KOSPI200_MULTIPLIER = 250_000

BASIS_CONFIG = {
    'normal_range_pct': 0.003,       # 정상 베이시스: ±0.3%
    'warning_range_pct': 0.007,      # 경고 베이시스: ±0.7%
    'critical_range_pct': 0.015,     # 위험 베이시스: ±1.5%
    'risk_free_rate': 0.035,         # 무위험이자율: 3.5% (BOK 기준금리)
}

BASIS_STATES = {
    'DEEP_CONTANGO': {'label': '강한 콘탱고', 'implication': '차익 매도 가능'},
    'CONTANGO': {'label': '콘탱고', 'implication': '선물 프리미엄'},
    'FAIR': {'label': '적정', 'implication': '이론가 근접'},
    'BACKWARDATION': {'label': '백워데이션', 'implication': '선물 할인'},
    'DEEP_BACKWARDATION': {'label': '강한 백워데이션', 'implication': '차익 매수 가능'},
}

# 미결제약정 (Open Interest)
OI_CONFIG = {
    'change_significant': 0.05,   # OI 5% 이상 변화: 유의미
    'change_large': 0.10,         # OI 10% 이상 변화: 대규모
}


def calc_theoretical_basis(spot, rate=None, days=None):
    """이론 선물가격 계산 (Cost of Carry 모델).

    F = S × (1 + r × t/365)

    Args:
        spot: 현물 지수.
        rate: 무위험이자율 (default: 3.5%).
        days: 잔존 일수.

    Returns:
        float: 이론 선물가격.
    """
    if rate is None:
        rate = BASIS_CONFIG['risk_free_rate']
    if days is None:
        days = 30  # 기본 1개월

    if spot is None or spot <= 0:
        return 0.0

    return round(spot * (1 + rate * days / 365), 2)


def _classify_basis_state(basis_pct):
    """베이시스 비율 → 상태 분류."""
    cfg = BASIS_CONFIG
    if basis_pct >= cfg['critical_range_pct']:
        return 'DEEP_CONTANGO'
    elif basis_pct >= cfg['warning_range_pct']:
        return 'CONTANGO'
    elif basis_pct >= -cfg['normal_range_pct']:
        return 'FAIR'
    elif basis_pct >= -cfg['warning_range_pct']:
        return 'BACKWARDATION'
    return 'DEEP_BACKWARDATION'


def _basis_to_score(basis_pct, state):
    """베이시스 → 0-100 점수.

    FAIR(적정) = 70점 (안정적)
    콘탱고 = 60-50점 (약간 불안정)
    백워데이션 = 40-30점 (불안정)
    극단 = 20-10점 (매우 불안정)
    """
    scores = {
        'FAIR': 70,
        'CONTANGO': 55,
        'DEEP_CONTANGO': 35,
        'BACKWARDATION': 45,
        'DEEP_BACKWARDATION': 25,
    }
    return scores.get(state, 50)


def analyze_basis(futures_price, spot_price, days_to_expiry=None, risk_free_rate=None):
    """선물 베이시스 분석.

    Args:
        futures_price: 선물 가격.
        spot_price: 현물 지수.
        days_to_expiry: 만기까지 잔존일 (default: 30).
        risk_free_rate: 무위험이자율 (default: 3.5%).

    Returns:
        dict: {basis, basis_pct, theoretical_basis, state, deviation, score}
    """
    if not futures_price or not spot_price or spot_price <= 0:
        return {
            'basis': 0,
            'basis_pct': 0.0,
            'theoretical_basis': 0,
            'state': 'FAIR',
            'deviation': 0.0,
            'score': 70,
        }

    if risk_free_rate is None:
        risk_free_rate = BASIS_CONFIG['risk_free_rate']
    if days_to_expiry is None:
        days_to_expiry = 30

    basis = futures_price - spot_price
    basis_pct = basis / spot_price

    theoretical = calc_theoretical_basis(spot_price, risk_free_rate, days_to_expiry)
    deviation = (futures_price - theoretical) / theoretical if theoretical > 0 else 0.0

    state = _classify_basis_state(basis_pct)
    score = _basis_to_score(basis_pct, state)

    return {
        'basis': round(basis, 2),
        'basis_pct': round(basis_pct, 6),
        'theoretical_basis': theoretical,
        'state': state,
        'deviation': round(deviation, 6),
        'score': score,
    }


def analyze_open_interest(oi_data):
    """미결제약정 분석.

    Args:
        oi_data: list of float (최근순, 일별 OI).

    Returns:
        dict: {current, change_pct, trend, significance}
    """
    if not oi_data or len(oi_data) < 2:
        return {
            'current': oi_data[0] if oi_data else 0,
            'change_pct': 0.0,
            'trend': 'stable',
            'significance': 'none',
        }

    current = oi_data[0]
    previous = oi_data[1]

    change_pct = (current - previous) / previous if previous > 0 else 0.0

    # 추세
    if len(oi_data) >= 5:
        recent_avg = sum(oi_data[:3]) / 3
        older_avg = sum(oi_data[3:6]) / min(len(oi_data[3:6]), 3) if len(oi_data) > 3 else recent_avg
        if recent_avg > older_avg * 1.02:
            trend = 'increasing'
        elif recent_avg < older_avg * 0.98:
            trend = 'decreasing'
        else:
            trend = 'stable'
    else:
        trend = 'increasing' if change_pct > 0.01 else ('decreasing' if change_pct < -0.01 else 'stable')

    # 유의미성
    abs_change = abs(change_pct)
    if abs_change >= OI_CONFIG['change_large']:
        significance = 'large'
    elif abs_change >= OI_CONFIG['change_significant']:
        significance = 'significant'
    else:
        significance = 'none'

    return {
        'current': current,
        'change_pct': round(change_pct, 4),
        'trend': trend,
        'significance': significance,
    }
