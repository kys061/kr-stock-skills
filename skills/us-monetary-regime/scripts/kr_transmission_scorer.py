"""us-monetary-regime: 한국 전이 메커니즘 스코어링."""


# --- Transmission Weights (sum = 1.00) ---

TRANSMISSION_WEIGHTS = {
    'interest_rate_diff': 0.30,
    'fx_impact': 0.25,
    'risk_appetite': 0.20,
    'sector_rotation': 0.15,
    'bok_policy_lag': 0.10,
}

# --- Rate Differential Scoring ---

RATE_DIFF_SCORING = {
    'kr_much_higher': 80,     # KR > US +1.5%p+
    'kr_higher': 65,          # KR > US +0.5~1.5%p
    'similar': 50,            # +-0.5%p
    'us_higher': 35,          # US > KR +0.5~1.5%p
    'us_much_higher': 20,     # US > KR +1.5%p+
}

# --- FX Scoring ---

FX_SCORING = {
    'won_strong_appreciation': 80,  # 원화 3M > +5% 강세
    'won_appreciation': 65,         # 3M +1~5%
    'stable': 50,                   # +-1%
    'won_depreciation': 35,         # 3M -1~-5%
    'won_strong_depreciation': 20,  # 3M < -5%
}

# --- BOK Policy Lag ---

BOK_LAG_MONTHS = (6, 12)

# --- 14 Sector Sensitivities ---

SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,
    'secondary_battery': 1.3,
    'bio': 1.2,
    'it': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'construction': 0.8,
    'finance': 0.7,
    'insurance': 0.6,
    'retail': 0.5,
    'defense': 0.4,
    'food': 0.3,
}

DEFAULT_SENSITIVITY = 0.7

# --- Overlay Limits ---

OVERLAY_MULTIPLIER = 0.30
OVERLAY_MAX = 15
OVERLAY_MIN = -15


def _score_rate_diff(kr_rate, us_rate):
    """한미 금리차 -> 점수."""
    diff = kr_rate - us_rate  # KR - US
    if diff >= 1.5:
        return RATE_DIFF_SCORING['kr_much_higher']
    elif diff >= 0.5:
        return RATE_DIFF_SCORING['kr_higher']
    elif diff >= -0.5:
        return RATE_DIFF_SCORING['similar']
    elif diff >= -1.5:
        return RATE_DIFF_SCORING['us_higher']
    return RATE_DIFF_SCORING['us_much_higher']


def _score_fx(usdkrw_change_3m):
    """원달러 3M 변화율 -> 점수.

    usdkrw_change_3m > 0 → 원화 약세 (부정적)
    usdkrw_change_3m < 0 → 원화 강세 (긍정적)
    """
    if usdkrw_change_3m < -5.0:
        return FX_SCORING['won_strong_appreciation']
    elif usdkrw_change_3m < -1.0:
        return FX_SCORING['won_appreciation']
    elif usdkrw_change_3m <= 1.0:
        return FX_SCORING['stable']
    elif usdkrw_change_3m <= 5.0:
        return FX_SCORING['won_depreciation']
    return FX_SCORING['won_strong_depreciation']


def _score_risk_appetite(us_regime_score):
    """US 레짐 점수 -> 위험선호도 점수.

    US 완화(높은 점수) → Risk-on → EM 유입 → 긍정적.
    """
    return max(0, min(100, us_regime_score))


def _score_sector_rotation(us_regime_score):
    """US 레짐 -> 섹터 회전 효과."""
    # US 완화 → 성장주 선호, US 긴축 → 가치주 선호
    return max(0, min(100, us_regime_score))


def _score_bok_lag(bok_direction, us_regime_score):
    """BOK 정책 후행 효과."""
    bok_scores = {
        'cutting': 70,
        'hold': 50,
        'hiking': 30,
    }
    bok_score = bok_scores.get(bok_direction, 50)

    # US와 같은 방향이면 보너스, 반대면 페널티
    alignment = 1.0 - abs(us_regime_score - bok_score) / 100
    return max(0, min(100, bok_score * 0.7 + us_regime_score * 0.3 * alignment))


def _calc_overlay(us_regime_score):
    """오버레이 계산: (score - 50) * 0.30, clamped to +-15."""
    raw = (us_regime_score - 50) * OVERLAY_MULTIPLIER
    return round(max(OVERLAY_MIN, min(OVERLAY_MAX, raw)), 1)


def _get_impact_label(score):
    """전이 점수 -> 영향 라벨."""
    if score >= 60:
        return 'positive'
    elif score <= 40:
        return 'negative'
    return 'neutral'


def get_sector_overlay(overlay, sector='default'):
    """섹터별 오버레이 계산.

    Args:
        overlay: float, base overlay (-15~+15).
        sector: str, 한국 섹터명.

    Returns:
        float: sector-adjusted overlay.
    """
    sensitivity = SECTOR_SENSITIVITY.get(sector, DEFAULT_SENSITIVITY)
    return round(overlay * sensitivity, 1)


def score_kr_transmission(us_regime_score=50, kr_rate=3.50,
                          us_rate=4.50, usdkrw_change_3m=0.0,
                          foreign_flow_5d=0, bok_direction='hold'):
    """한국 전이 스코어 계산.

    Args:
        us_regime_score: float (0~100), US 통화정책 레짐 점수.
        kr_rate: float, 한국 기준금리 (%).
        us_rate: float, US FFR 상단 (%).
        usdkrw_change_3m: float, 원달러 3개월 변화율 (%).
        foreign_flow_5d: float, 외국인 5일 순매수 (억원).
        bok_direction: str, BOK 정책 방향.

    Returns:
        dict: {kr_impact_score, impact_label, overlay, channels,
               sector_overlays, favored_sectors, unfavored_sectors}
    """
    # 5채널 점수
    rd_score = _score_rate_diff(kr_rate, us_rate)
    fx_score = _score_fx(usdkrw_change_3m)
    ra_score = _score_risk_appetite(us_regime_score)
    sr_score = _score_sector_rotation(us_regime_score)
    bl_score = _score_bok_lag(bok_direction, us_regime_score)

    # 외국인 수급 보너스 (+-5점)
    if foreign_flow_5d > 5000:
        flow_adj = 5
    elif foreign_flow_5d > 1000:
        flow_adj = 2
    elif foreign_flow_5d < -5000:
        flow_adj = -5
    elif foreign_flow_5d < -1000:
        flow_adj = -2
    else:
        flow_adj = 0

    # 가중 합산
    weighted = (
        rd_score * TRANSMISSION_WEIGHTS['interest_rate_diff'] +
        fx_score * TRANSMISSION_WEIGHTS['fx_impact'] +
        ra_score * TRANSMISSION_WEIGHTS['risk_appetite'] +
        sr_score * TRANSMISSION_WEIGHTS['sector_rotation'] +
        bl_score * TRANSMISSION_WEIGHTS['bok_policy_lag']
    )

    kr_impact_score = round(max(0, min(100, weighted + flow_adj)), 1)

    # 오버레이
    overlay = _calc_overlay(us_regime_score)

    # 섹터별 오버레이
    sector_overlays = {}
    for sector in SECTOR_SENSITIVITY:
        sector_overlays[sector] = get_sector_overlay(overlay, sector)

    # Favored / Unfavored 섹터
    if overlay > 0:
        # 완화기 → 고민감 섹터 유리
        favored = [s for s, v in SECTOR_SENSITIVITY.items() if v >= 1.1]
        unfavored = [s for s, v in SECTOR_SENSITIVITY.items() if v <= 0.5]
    elif overlay < 0:
        # 긴축기 → 저민감(방어) 섹터 유리
        favored = [s for s, v in SECTOR_SENSITIVITY.items() if v <= 0.5]
        unfavored = [s for s, v in SECTOR_SENSITIVITY.items() if v >= 1.1]
    else:
        favored = []
        unfavored = []

    # 채널별 상세
    rate_diff = kr_rate - us_rate
    channels = {
        'interest_rate_diff': {
            'score': rd_score,
            'weight': TRANSMISSION_WEIGHTS['interest_rate_diff'],
            'detail': f'KR-US 금리차: {rate_diff:+.2f}%p',
        },
        'fx_impact': {
            'score': fx_score,
            'weight': TRANSMISSION_WEIGHTS['fx_impact'],
            'detail': f'원달러 3M 변화: {usdkrw_change_3m:+.1f}%',
        },
        'risk_appetite': {
            'score': ra_score,
            'weight': TRANSMISSION_WEIGHTS['risk_appetite'],
            'detail': f'US regime {us_regime_score} → Risk {"On" if us_regime_score > 50 else "Off"}',
        },
        'sector_rotation': {
            'score': sr_score,
            'weight': TRANSMISSION_WEIGHTS['sector_rotation'],
            'detail': f'{"성장주 선호" if us_regime_score > 50 else "가치주 선호"}',
        },
        'bok_policy_lag': {
            'score': bl_score,
            'weight': TRANSMISSION_WEIGHTS['bok_policy_lag'],
            'detail': f'BOK {bok_direction}, 6-12M 후행',
        },
    }

    return {
        'kr_impact_score': kr_impact_score,
        'impact_label': _get_impact_label(kr_impact_score),
        'overlay': overlay,
        'channels': channels,
        'sector_overlays': sector_overlays,
        'favored_sectors': favored,
        'unfavored_sectors': unfavored,
    }
