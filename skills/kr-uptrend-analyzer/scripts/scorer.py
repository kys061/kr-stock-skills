"""5-컴포넌트 업트렌드 스코어 계산기.

US uptrend-analyzer의 스코어링 로직 보존.
가중치: Breadth(30%) + Participation(25%) + Rotation(15%) + Momentum(20%) + Historical(10%)
"""

import numpy as np

# 가중치
WEIGHTS = {
    'breadth': 0.30,
    'participation': 0.25,
    'rotation': 0.15,
    'momentum': 0.20,
    'historical': 0.10,
}

# Uptrend Zone 정의: (min_score, max_score, zone_name, zone_kr, exposure)
UPTREND_ZONES = [
    (80, 100, 'Strong Bull', '강세장', '90-100%'),
    (60, 79, 'Bull-Lower', '약강세', '80-100%'),
    (40, 59, 'Neutral', '중립', '60-80%'),
    (20, 39, 'Bear-Lower', '약약세', '40-60%'),
    (0, 19, 'Strong Bear', '약세장', '25-40%'),
]

# 경고 정의
WARNINGS = {
    'late_cycle': {
        'description': '후기 사이클 경고 (Late Cycle)',
        'penalty': -5,
    },
    'high_spread': {
        'description': '높은 업종 편차 경고 (High Spread)',
        'penalty': -3,
    },
    'divergence': {
        'description': '그룹 내 다이버전스 경고',
        'penalty': -3,
    },
}


class UptrendScorer:
    """5-컴포넌트 업트렌드 스코어 계산."""

    WEIGHTS = WEIGHTS

    def score(self, data: dict) -> dict:
        """종합 스코어 계산.

        Args:
            data: {
                'overall_ratio': float,        # 전체 업트렌드 비율 (0~100)
                'sector_data': dict,           # 업종별 데이터
                'group_averages': dict,        # 그룹별 평균
                'sector_spread': float,        # 업종간 스프레드
                'group_std': dict,             # 그룹 내 표준편차
                'history': list,               # 최근 점수 히스토리
                'prev_ratio': float,           # 3일 전 비율 (모멘텀 계산용)
            }

        Returns:
            {
                'composite_score': float,
                'uptrend_zone': str,
                'uptrend_zone_kr': str,
                'equity_exposure': str,
                'components': {...},
                'warnings': [...],
                'strongest_component': str,
                'weakest_component': str,
            }
        """
        components = {}

        # 1. Market Breadth (30%)
        breadth_score = self._score_breadth(
            data.get('overall_ratio', 0),
            data.get('prev_ratio'),
        )
        components['breadth'] = {
            'score': breadth_score,
            'weight': self.WEIGHTS['breadth'],
            'weighted': round(breadth_score * self.WEIGHTS['breadth'], 1),
            'detail': f"전체 업트렌드 {data.get('overall_ratio', 0):.1f}%",
        }

        # 2. Sector Participation (25%)
        participation_score = self._score_participation(
            data.get('sector_data', {}),
        )
        sector_count = sum(
            1 for s in data.get('sector_data', {}).values() if s['ratio'] > 50
        )
        total_sectors = len(data.get('sector_data', {}))
        components['participation'] = {
            'score': participation_score,
            'weight': self.WEIGHTS['participation'],
            'weighted': round(participation_score * self.WEIGHTS['participation'], 1),
            'detail': f"참여 업종 {sector_count}/{total_sectors}",
        }

        # 3. Sector Rotation (15%)
        rotation_score = self._score_rotation(data.get('group_averages', {}))
        components['rotation'] = {
            'score': rotation_score,
            'weight': self.WEIGHTS['rotation'],
            'weighted': round(rotation_score * self.WEIGHTS['rotation'], 1),
            'detail': self._rotation_detail(data.get('group_averages', {})),
        }

        # 4. Momentum (20%)
        momentum_score = self._score_momentum(
            data.get('overall_ratio', 0),
            data.get('prev_ratio'),
        )
        components['momentum'] = {
            'score': momentum_score,
            'weight': self.WEIGHTS['momentum'],
            'weighted': round(momentum_score * self.WEIGHTS['momentum'], 1),
            'detail': self._momentum_detail(
                data.get('overall_ratio', 0),
                data.get('prev_ratio'),
            ),
        }

        # 5. Historical Context (10%)
        historical_score = self._score_historical(
            data.get('overall_ratio', 0),
            data.get('history', []),
        )
        components['historical'] = {
            'score': historical_score,
            'weight': self.WEIGHTS['historical'],
            'weighted': round(historical_score * self.WEIGHTS['historical'], 1),
            'detail': f"백분위 {historical_score}%",
        }

        # 종합 점수
        raw_score = sum(c['weighted'] for c in components.values())

        # 경고 시스템
        warnings = self._check_warnings(data)
        total_penalty = sum(w['penalty'] for w in warnings)
        if len(warnings) > 1:
            total_penalty += 1  # 복수 경고 할인

        composite = max(0, min(100, round(raw_score + total_penalty)))

        # Zone 결정
        zone, zone_kr, exposure = self._get_zone(composite)

        # 강/약 컴포넌트
        strongest = max(components, key=lambda k: components[k]['score'])
        weakest = min(components, key=lambda k: components[k]['score'])

        return {
            'composite_score': composite,
            'uptrend_zone': zone,
            'uptrend_zone_kr': zone_kr,
            'equity_exposure': exposure,
            'components': components,
            'warnings': warnings,
            'strongest_component': strongest,
            'weakest_component': weakest,
        }

    def _score_breadth(self, overall_ratio: float, prev_ratio: float = None) -> float:
        """Market Breadth (30%)."""
        if overall_ratio >= 70:
            base = 90
        elif overall_ratio >= 55:
            base = 70
        elif overall_ratio >= 40:
            base = 50
        elif overall_ratio >= 25:
            base = 30
        else:
            base = 10

        # 3일 변화량 보정
        if prev_ratio is not None:
            delta = overall_ratio - prev_ratio
            if delta > 0:
                base = min(100, base + 10)
            elif delta < 0:
                base = max(0, base - 10)

        return base

    def _score_participation(self, sector_data: dict) -> float:
        """Sector Participation (25%)."""
        if not sector_data:
            return 50

        total = len(sector_data)
        participating = sum(1 for s in sector_data.values() if s['ratio'] > 50)

        if total == 0:
            return 50

        pct = participating / total * 100
        if pct >= 80:
            base = 90
        elif pct >= 60:
            base = 70
        elif pct >= 40:
            base = 50
        elif pct >= 20:
            base = 30
        else:
            base = 10

        # 편차 보정
        ratios = [s['ratio'] for s in sector_data.values()]
        if len(ratios) > 1 and np.std(ratios) > 20:
            base = max(0, base - 10)

        return base

    def _score_rotation(self, group_averages: dict) -> float:
        """Sector Rotation (15%)."""
        cyclical = group_averages.get('Cyclical', 50)
        defensive = group_averages.get('Defensive', 50)
        diff = cyclical - defensive

        if diff > 20:
            return 80  # 성장 국면
        elif diff > 0:
            return 70
        elif diff > -10:
            return 50  # 비슷
        elif diff > -20:
            return 30
        else:
            return 20  # 방어 국면

    def _score_momentum(self, current: float, prev: float = None) -> float:
        """Momentum (20%)."""
        if prev is None:
            return 50

        delta = current - prev
        if delta > 5:
            return 90  # 급상승
        elif delta > 0:
            return 70  # 상승
        elif delta > -2:
            return 50  # 횡보
        elif delta > -5:
            return 30  # 하락
        else:
            return 10  # 급하락

    def _score_historical(self, current: float, history: list) -> float:
        """Historical Context (10%)."""
        if not history or len(history) < 3:
            return 50

        # percentile
        below = sum(1 for h in history if h <= current)
        pct = below / len(history) * 100
        return round(min(100, max(0, pct)))

    def _check_warnings(self, data: dict) -> list:
        """경고 시스템."""
        warnings = []
        group_avg = data.get('group_averages', {})
        sector_spread = data.get('sector_spread', 0)
        group_std = data.get('group_std', {})

        # Late Cycle: 원자재/에너지 > 경기민감 AND 방어 (Financial을 Commodity proxy로 사용)
        cyclical = group_avg.get('Cyclical', 0)
        defensive = group_avg.get('Defensive', 0)
        financial = group_avg.get('Financial', 0)
        if financial > cyclical and financial > defensive:
            warnings.append({
                'type': 'late_cycle',
                'penalty': WARNINGS['late_cycle']['penalty'],
                'description': WARNINGS['late_cycle']['description'],
            })

        # High Spread
        if sector_spread > 40:
            warnings.append({
                'type': 'high_spread',
                'penalty': WARNINGS['high_spread']['penalty'],
                'description': WARNINGS['high_spread']['description'],
            })

        # Divergence: 그룹 내 표준편차 > 20
        for group, std in group_std.items():
            if std > 20:
                warnings.append({
                    'type': 'divergence',
                    'penalty': WARNINGS['divergence']['penalty'],
                    'description': f"{group} {WARNINGS['divergence']['description']} (σ={std})",
                })
                break  # 1개만

        return warnings

    def _get_zone(self, score: float) -> tuple:
        """점수 → Zone 매핑."""
        for low, high, zone, zone_kr, exposure in UPTREND_ZONES:
            if low <= score <= high:
                return zone, zone_kr, exposure
        return 'Unknown', '미정', '50%'

    def _rotation_detail(self, group_averages: dict) -> str:
        """Rotation 상세 설명."""
        cyclical = group_averages.get('Cyclical', 0)
        defensive = group_averages.get('Defensive', 0)
        return f"경기민감 {cyclical:.0f}% vs 방어 {defensive:.0f}%"

    def _momentum_detail(self, current: float, prev: float = None) -> str:
        """Momentum 상세 설명."""
        if prev is None:
            return "이전 데이터 없음"
        delta = current - prev
        direction = "상승" if delta > 0 else "하락" if delta < 0 else "횡보"
        return f"{direction} ({delta:+.1f}pp/3d)"
