"""6-컴포넌트 시장폭 스코어 계산기.

US market-breadth-analyzer의 스코어링 로직을 보존.
가중치: Breadth(25%) + Crossover(20%) + Cycle(20%) + Bearish(15%) + Percentile(10%) + Divergence(10%)
"""

import logging

logger = logging.getLogger(__name__)

# Health Zone 정의
HEALTH_ZONES = [
    (80, 100, 'Strong', '강세', '90-100%'),
    (60, 79, 'Healthy', '건강', '75-90%'),
    (40, 59, 'Neutral', '중립', '60-75%'),
    (20, 39, 'Weakening', '약화', '40-60%'),
    (0, 19, 'Critical', '위험', '25-40%'),
]


class BreadthScorer:
    """시장폭 스코어 계산기."""

    WEIGHTS = {
        'breadth_level': 0.25,
        'crossover': 0.20,
        'cycle': 0.20,
        'bearish': 0.15,
        'percentile': 0.10,
        'divergence': 0.10,
    }

    def score(self, breadth_data: dict) -> dict:
        """종합 점수 계산.

        Args:
            breadth_data: BreadthCalculator.calculate() 결과

        Returns:
            {
                'composite_score': float,
                'health_zone': str,
                'health_zone_kr': str,
                'equity_exposure': str,
                'components': dict,
                'strongest_component': str,
                'weakest_component': str,
            }
        """
        raw = breadth_data.get('breadth_raw', 0)
        ma8 = breadth_data.get('breadth_8ma', raw)
        ma200 = breadth_data.get('breadth_200ma', raw)
        trend = breadth_data.get('trend', 'flat')
        is_peak = breadth_data.get('is_peak', False)
        is_trough = breadth_data.get('is_trough', False)
        bearish = breadth_data.get('bearish_signal', False)
        history = breadth_data.get('breadth_history', [])
        index_history = breadth_data.get('index_history', [])

        # 이전 8MA-200MA 갭 (히스토리에서 추정)
        prev_gap = 0.0
        if len(history) >= 2:
            prev_gap = history[-2] - ma200

        # 각 컴포넌트 점수 계산
        components = {}
        components['breadth_level'] = self._score_breadth_level(raw, ma8, ma200, trend)
        components['crossover'] = self._score_crossover(ma8, ma200, prev_gap)
        components['cycle'] = self._score_cycle(is_peak, is_trough, trend)
        components['bearish'] = self._score_bearish(bearish)
        components['percentile'] = self._score_percentile(raw, history)
        components['divergence'] = self._score_divergence(index_history, history)

        # 가중 합산
        composite = 0.0
        for key, weight in self.WEIGHTS.items():
            score = components[key]['score']
            composite += score * weight
            components[key]['weight'] = weight
            components[key]['weighted'] = round(score * weight, 1)

        composite = round(min(max(composite, 0), 100), 1)

        # Health Zone 판정
        zone, zone_kr, exposure = self._classify_zone(composite)

        # 최강/최약 컴포넌트
        sorted_comp = sorted(components.items(), key=lambda x: x[1]['score'], reverse=True)
        strongest = sorted_comp[0][0] if sorted_comp else ''
        weakest = sorted_comp[-1][0] if sorted_comp else ''

        return {
            'composite_score': composite,
            'health_zone': zone,
            'health_zone_kr': zone_kr,
            'equity_exposure': exposure,
            'components': components,
            'strongest_component': strongest,
            'weakest_component': weakest,
        }

    def _score_breadth_level(self, raw: float, ma8: float, ma200: float,
                              trend: str) -> dict:
        """Breadth Level & Trend (25%)."""
        if ma8 >= 70:
            base = 80
        elif ma8 >= 50:
            base = 60
        elif ma8 >= 30:
            base = 40
        else:
            base = 20

        bonus = 0
        if trend == 'up':
            bonus += 10
        if ma8 > ma200:
            bonus += 10

        score = min(base + bonus, 100)
        return {'score': score, 'detail': f'8MA={ma8:.1f}, trend={trend}'}

    def _score_crossover(self, ma8: float, ma200: float, prev_gap: float) -> dict:
        """8MA vs 200MA Crossover (20%)."""
        gap = ma8 - ma200
        expanding = gap > prev_gap

        if gap > 0 and expanding:
            score = 90
            detail = f'갭 +{gap:.1f}, 확대중'
        elif gap > 0 and not expanding:
            score = 60
            detail = f'갭 +{gap:.1f}, 축소중'
        elif gap <= 0 and not expanding:
            score = 40
            detail = f'갭 {gap:.1f}, 수렴중'
        else:
            score = 10
            detail = f'갭 {gap:.1f}, 발산중'

        return {'score': score, 'detail': detail}

    def _score_cycle(self, is_peak: bool, is_trough: bool, trend: str) -> dict:
        """Peak/Trough Cycle (20%)."""
        if is_trough and trend == 'up':
            score = 80
            detail = '저점 후 상승'
        elif is_peak and trend == 'down':
            score = 30
            detail = '고점 후 하락'
        elif is_peak:
            score = 60
            detail = '고점 근처'
        elif is_trough:
            score = 50
            detail = '저점 근처'
        elif trend == 'up':
            score = 70
            detail = '상승 구간'
        elif trend == 'down':
            score = 35
            detail = '하락 구간'
        else:
            score = 50
            detail = '횡보'

        return {'score': score, 'detail': detail}

    def _score_bearish(self, bearish_signal: bool) -> dict:
        """Bearish Signal (15%)."""
        if bearish_signal:
            return {'score': 0, 'detail': '약세 신호 활성'}
        return {'score': 100, 'detail': '약세 신호 없음'}

    def _score_percentile(self, raw: float, history: list) -> dict:
        """Historical Percentile (10%)."""
        if not history or len(history) < 2:
            return {'score': 50, 'detail': '히스토리 부족'}

        rank = sum(1 for v in history if v < raw)
        percentile = (rank / len(history)) * 100
        score = round(percentile)
        return {'score': score, 'detail': f'상위 {100 - percentile:.0f}%'}

    def _score_divergence(self, index_history: list, breadth_history: list) -> dict:
        """지수 Divergence (10%)."""
        if not index_history or not breadth_history or len(index_history) < 2:
            return {'score': 50, 'detail': '데이터 부족'}

        # 간단한 방향 비교
        idx_dir = 1 if index_history[-1] > index_history[0] else -1
        brd_dir = 1 if breadth_history[-1] > breadth_history[0] else -1

        if idx_dir == brd_dir:
            score = 80
            detail = '동일 방향 (확인)'
        elif idx_dir > 0 and brd_dir < 0:
            score = 30
            detail = '지수↑ 시장폭↓ (위험 괴리)'
        else:
            score = 70
            detail = '지수↓ 시장폭↑ (긍정 신호)'

        return {'score': score, 'detail': detail}

    @staticmethod
    def _classify_zone(score: float) -> tuple:
        """점수 → Health Zone 분류."""
        for low, high, zone, zone_kr, exposure in HEALTH_ZONES:
            if low <= score <= high:
                return zone, zone_kr, exposure
        return 'Unknown', '미정', '50%'
