"""
kr-bubble-detector: 한국 시장 버블 스코어러.
Minsky/Kindleberger v2.1 프레임워크 한국 적용.
6개 정량 지표 (max 12) + 3개 정성 조정 (max 3) = 최대 15점.
"""

# ── 지표 정의 ──────────────────────────────────────────
INDICATOR_NAMES = [
    'vkospi_market',       # 지표 1: VKOSPI + 시장 위치
    'credit_balance',      # 지표 2: 신용잔고 변화
    'ipo_heat',            # 지표 3: IPO 과열도
    'breadth_anomaly',     # 지표 4: 시장폭 이상
    'price_acceleration',  # 지표 5: 가격 가속화
    'per_band',            # 지표 6: KOSPI PER 밴드
]

ADJUSTMENT_NAMES = [
    'social_penetration',   # 조정 A: 사회적 침투도
    'media_trend',          # 조정 B: 미디어/검색 트렌드
    'valuation_disconnect', # 조정 C: 밸류에이션 괴리
]

# ── 리스크 존 ──────────────────────────────────────────
RISK_ZONES = [
    {'name': 'Normal',        'min': 0,  'max': 4,  'label': '정상',     'budget': '100%'},
    {'name': 'Caution',       'min': 5,  'max': 7,  'label': '주의',     'budget': '70-80%'},
    {'name': 'Elevated_Risk', 'min': 8,  'max': 9,  'label': '위험 상승', 'budget': '50-70%'},
    {'name': 'Euphoria',      'min': 10, 'max': 12, 'label': '유포리아', 'budget': '40-50%'},
    {'name': 'Critical',      'min': 13, 'max': 15, 'label': '위기',     'budget': '20-30%'},
]


# ── 개별 지표 스코어링 함수 ────────────────────────────

def score_vkospi_market(vkospi: float, pct_from_high: float) -> int:
    """지표 1: VKOSPI + 시장 위치.

    Args:
        vkospi: VKOSPI 수준
        pct_from_high: KOSPI 52주 고점 대비 하락률 (0.0 = 고점, -0.05 = 5% 하락)
    Returns:
        0, 1, 또는 2
    """
    if vkospi < 13 and pct_from_high > -0.05:
        return 2
    elif vkospi <= 18 and pct_from_high > -0.10:
        return 1
    else:
        return 0


def score_credit_balance(credit_yoy: float, is_ath: bool) -> int:
    """지표 2: 신용잔고 변화.

    Args:
        credit_yoy: 신용잔고 전년 대비 변화율 (0.20 = +20%)
        is_ath: 신용잔고가 역대 최고인지 여부
    Returns:
        0, 1, 또는 2
    """
    if credit_yoy >= 0.20 and is_ath:
        return 2
    elif credit_yoy >= 0.10:
        return 1
    else:
        return 0


def score_ipo_heat(quarterly_ipo_count: int, avg_5y: float,
                   avg_competition: float) -> int:
    """지표 3: IPO 과열도.

    Args:
        quarterly_ipo_count: 분기 IPO 건수
        avg_5y: 5년 평균 분기 IPO 건수
        avg_competition: 평균 청약 경쟁률 (500.0 = 500:1)
    Returns:
        0, 1, 또는 2
    """
    if avg_5y <= 0:
        return 0
    ratio = quarterly_ipo_count / avg_5y
    if ratio > 2.0 and avg_competition > 500:
        return 2
    elif ratio > 1.5:
        return 1
    else:
        return 0


def score_breadth_anomaly(is_new_high: bool, breadth_200ma: float) -> int:
    """지표 4: 시장폭 이상.

    Args:
        is_new_high: KOSPI가 52주 신고가인지 여부
        breadth_200ma: 200MA 위 종목 비율 (0.0-1.0, 0.52 = 52%)
    Returns:
        0, 1, 또는 2
    """
    if is_new_high and breadth_200ma < 0.45:
        return 2
    elif breadth_200ma < 0.60:
        return 1
    else:
        return 0


def score_price_acceleration(return_3m: float, percentile: float) -> int:
    """지표 5: 가격 가속화.

    Args:
        return_3m: KOSPI 3개월 수익률 (0.15 = +15%)
        percentile: 10년 역사 대비 백분위 (0.0-1.0, 0.95 = 95th)
    Returns:
        0, 1, 또는 2
    """
    if percentile >= 0.95:
        return 2
    elif percentile >= 0.85:
        return 1
    else:
        return 0


def score_per_band(kospi_per: float) -> int:
    """지표 6: KOSPI PER 밴드.

    Args:
        kospi_per: KOSPI 12개월 선행 PER
    Returns:
        0, 1, 또는 2
    """
    if kospi_per >= 14.0:
        return 2
    elif kospi_per >= 12.0:
        return 1
    else:
        return 0


# ── 리스크 존 분류 ─────────────────────────────────────

def classify_risk_zone(total_score: int) -> dict:
    """총점으로 리스크 존 분류.

    Args:
        total_score: 정량 + 정성 합산 (0-15)
    Returns:
        {'name': str, 'label': str, 'budget': str}
    """
    clamped = max(0, min(total_score, 15))
    for zone in RISK_ZONES:
        if zone['min'] <= clamped <= zone['max']:
            return {
                'name': zone['name'],
                'label': zone['label'],
                'budget': zone['budget'],
            }
    return {'name': 'Normal', 'label': '정상', 'budget': '100%'}


# ── 통합 스코어러 클래스 ──────────────────────────────

class BubbleScorer:
    """6 정량 + 3 정성 한국 시장 버블 스코어러."""

    # 정량 스코어링 함수 매핑
    SCORE_FUNCTIONS = {
        'vkospi_market': score_vkospi_market,
        'credit_balance': score_credit_balance,
        'ipo_heat': score_ipo_heat,
        'breadth_anomaly': score_breadth_anomaly,
        'price_acceleration': score_price_acceleration,
        'per_band': score_per_band,
    }

    def score_quantitative(self, indicators: dict) -> dict:
        """정량 6개 지표 스코어링.

        Args:
            indicators: {
                'vkospi_market': {'vkospi': 12.0, 'pct_from_high': -0.02},
                'credit_balance': {'credit_yoy': 0.25, 'is_ath': True},
                'ipo_heat': {'quarterly_ipo_count': 40, 'avg_5y': 18.0,
                             'avg_competition': 600.0},
                'breadth_anomaly': {'is_new_high': True, 'breadth_200ma': 0.42},
                'price_acceleration': {'return_3m': 0.20, 'percentile': 0.96},
                'per_band': {'kospi_per': 14.5},
            }
        Returns:
            {'scores': {name: int}, 'total': int}
        """
        scores = {}
        for name in INDICATOR_NAMES:
            params = indicators.get(name, {})
            func = self.SCORE_FUNCTIONS[name]
            scores[name] = func(**params) if params else 0
        total = sum(scores.values())
        return {'scores': scores, 'total': total}

    def score_qualitative(self, adjustments: dict) -> dict:
        """정성 3개 조정 스코어링.

        Args:
            adjustments: {
                'social_penetration': bool,  # 요건 충족 여부
                'media_trend': bool,
                'valuation_disconnect': bool,
            }
        Returns:
            {'adjustments': {name: int}, 'total': int}
        """
        adj_scores = {}
        for name in ADJUSTMENT_NAMES:
            adj_scores[name] = 1 if adjustments.get(name, False) else 0
        total = min(sum(adj_scores.values()), 3)  # 최대 3점
        return {'adjustments': adj_scores, 'total': total}

    def calculate_final(self, quant: dict, qual: dict) -> dict:
        """최종 버블 점수 계산.

        Args:
            quant: score_quantitative() 결과
            qual: score_qualitative() 결과
        Returns:
            {
                'quantitative_total': int,
                'qualitative_total': int,
                'final_score': int,
                'risk_zone': dict,
                'max_possible': 15,
            }
        """
        final_score = quant['total'] + qual['total']
        final_score = max(0, min(final_score, 15))
        risk_zone = classify_risk_zone(final_score)

        return {
            'quantitative_total': quant['total'],
            'qualitative_total': qual['total'],
            'final_score': final_score,
            'risk_zone': risk_zone,
            'max_possible': 15,
        }
