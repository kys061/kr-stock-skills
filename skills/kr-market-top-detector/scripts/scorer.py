"""
kr-market-top-detector: 7-컴포넌트 천장 리스크 스코어러.
"""


COMPONENT_WEIGHTS = {
    'distribution': 0.20,
    'leading_stock': 0.15,
    'defensive_rotation': 0.12,
    'breadth_divergence': 0.13,
    'index_technical': 0.13,
    'sentiment': 0.12,
    'foreign_flow': 0.15,
}

COMPONENT_NAMES = {
    'distribution': '분배일 카운트',
    'leading_stock': '선도주 건전성',
    'defensive_rotation': '방어 섹터 로테이션',
    'breadth_divergence': '시장폭 다이버전스',
    'index_technical': '지수 기술적 조건',
    'sentiment': '센티먼트 & 투기',
    'foreign_flow': '외국인 수급',
}

RISK_ZONES = [
    {'name': 'Green',    'label': '정상',       'min': 0,  'max': 20,
     'budget': '100%',   'action': '정상 운영, 신규 진입 가능'},
    {'name': 'Yellow',   'label': '초기 경고',   'min': 21, 'max': 40,
     'budget': '80-90%', 'action': '손절 강화, 신규 진입 축소'},
    {'name': 'Orange',   'label': '위험 상승',   'min': 41, 'max': 60,
     'budget': '60-75%', 'action': '약한 포지션 이익실현'},
    {'name': 'Red',      'label': '고확률 천장', 'min': 61, 'max': 80,
     'budget': '40-55%', 'action': '적극적 이익실현'},
    {'name': 'Critical', 'label': '천장 형성',   'min': 81, 'max': 100,
     'budget': '20-35%', 'action': '최대 방어, 헤지'},
]


def classify_risk_zone(score: float) -> dict:
    """점수 → 리스크 존 매핑."""
    clamped = max(0, min(100, score))
    for zone in RISK_ZONES:
        if zone['min'] <= clamped <= zone['max']:
            return {
                'name': zone['name'],
                'label': zone['label'],
                'budget': zone['budget'],
                'action': zone['action'],
            }
    return RISK_ZONES[-1]  # fallback Critical


def score_index_technical(signals: dict) -> float:
    """기술적 조건 신호 → 점수 (0-100).

    Args:
        signals: {
            'ma10_below_ma21': bool,     # +15
            'ma21_below_ma50': bool,     # +15
            'ma50_below_ma200': bool,    # +25 (데드크로스)
            'failed_rally': bool,        # +20
            'lower_low': bool,           # +15
            'declining_volume_rise': bool, # +10
        }
    Returns:
        0-100
    """
    pts = 0
    if signals.get('ma10_below_ma21'):
        pts += 15
    if signals.get('ma21_below_ma50'):
        pts += 15
    if signals.get('ma50_below_ma200'):
        pts += 25
    if signals.get('failed_rally'):
        pts += 20
    if signals.get('lower_low'):
        pts += 15
    if signals.get('declining_volume_rise'):
        pts += 10
    return min(pts, 100)


def score_sentiment(vkospi: float, credit_yoy: float = 0.0) -> float:
    """VKOSPI + 신용잔고 → 점수 (0-100).

    VKOSPI: <13 → +40, 13-18 → +20, 18-25 → 0, >25 → -10
    신용잔고 YoY: +15%+ → +30, +5~15% → +15, -5~+5% → 0, <-5% → -10
    """
    # VKOSPI 점수
    if vkospi < 13:
        v_score = 40
    elif vkospi < 18:
        v_score = 20
    elif vkospi <= 25:
        v_score = 0
    else:
        v_score = -10

    # 신용잔고 점수
    if credit_yoy >= 0.15:
        c_score = 30
    elif credit_yoy >= 0.05:
        c_score = 15
    elif credit_yoy >= -0.05:
        c_score = 0
    else:
        c_score = -10

    return max(0.0, min(100.0, float(v_score + c_score)))


def score_breadth_divergence(is_near_high: bool,
                             breadth_ratio: float) -> float:
    """시장폭 다이버전스 → 점수 (0-100).

    Args:
        is_near_high: KOSPI가 52주 고점의 5% 이내인지
        breadth_ratio: 200MA 위 종목 비율 (0-1)
    """
    if not is_near_high:
        return 10.0  # 이미 조정 중이면 낮은 점수

    if breadth_ratio >= 0.70:
        return 10.0
    elif breadth_ratio >= 0.60:
        return 25.0
    elif breadth_ratio >= 0.45:
        return 50.0
    elif breadth_ratio >= 0.40:
        return 70.0
    else:
        return 90.0


class MarketTopScorer:
    """7-컴포넌트 천장 리스크 스코어러."""

    def score(self, components: dict) -> dict:
        """가중 합계 → 복합 점수.

        Args:
            components: {
                'distribution': float (0-100),
                'leading_stock': float (0-100),
                'defensive_rotation': float (0-100),
                'breadth_divergence': float (0-100),
                'index_technical': float (0-100),
                'sentiment': float (0-100),
                'foreign_flow': float (0-100),
            }
        Returns:
            {
                'composite_score': float (0-100),
                'risk_zone': dict,
                'components': dict,
                'weights': dict,
            }
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for key, weight in COMPONENT_WEIGHTS.items():
            val = components.get(key)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight

        # 가용 가중치로 정규화
        if total_weight > 0 and total_weight < 1.0:
            composite = weighted_sum / total_weight
        else:
            composite = weighted_sum

        composite = max(0.0, min(100.0, composite))
        zone = classify_risk_zone(composite)

        return {
            'composite_score': round(composite, 1),
            'risk_zone': zone,
            'components': components,
            'weights': dict(COMPONENT_WEIGHTS),
        }
