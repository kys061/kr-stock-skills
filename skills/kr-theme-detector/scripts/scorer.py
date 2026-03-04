"""3D 테마 스코어링: Heat × Lifecycle × Confidence.

US theme-detector의 3D 스코어링 모델을 한국 시장에 맞게 구현.
"""

import logging

logger = logging.getLogger(__name__)

# Heat 컴포넌트 가중치
HEAT_WEIGHTS = {
    'momentum': 0.40,
    'volume': 0.20,
    'uptrend': 0.25,
    'breadth': 0.15,
}


def calculate_theme_heat(stats: dict) -> float:
    """Theme Heat (0-100) 계산.

    Args:
        stats: ThemeClassifier의 테마 통계

    Returns:
        0~100 Heat 점수
    """
    # 1. Momentum (40%) - 시총가중 1주 수익률 기반
    change_1w = stats.get('weighted_change_1w', 0)
    if change_1w >= 5:
        momentum = 95
    elif change_1w >= 3:
        momentum = 80
    elif change_1w >= 1:
        momentum = 65
    elif change_1w >= 0:
        momentum = 50
    elif change_1w >= -1:
        momentum = 35
    elif change_1w >= -3:
        momentum = 20
    else:
        momentum = 5

    # 2. Volume (20%) - 거래량 비율
    vol_ratio = stats.get('avg_volume_ratio', 1.0)
    if vol_ratio >= 2.0:
        volume = 90
    elif vol_ratio >= 1.5:
        volume = 70
    elif vol_ratio >= 1.2:
        volume = 55
    elif vol_ratio >= 0.8:
        volume = 40
    else:
        volume = 20

    # 3. Uptrend Ratio (25%) - 200MA 위 비율
    uptrend = stats.get('uptrend_ratio', 0)
    if uptrend >= 80:
        uptrend_score = 90
    elif uptrend >= 60:
        uptrend_score = 70
    elif uptrend >= 40:
        uptrend_score = 50
    elif uptrend >= 20:
        uptrend_score = 30
    else:
        uptrend_score = 10

    # 4. Breadth (15%) - 5일 양봉 비율
    breadth = stats.get('breadth_5d', 0)
    if breadth >= 80:
        breadth_score = 90
    elif breadth >= 60:
        breadth_score = 70
    elif breadth >= 40:
        breadth_score = 50
    elif breadth >= 20:
        breadth_score = 30
    else:
        breadth_score = 10

    heat = (
        momentum * HEAT_WEIGHTS['momentum']
        + volume * HEAT_WEIGHTS['volume']
        + uptrend_score * HEAT_WEIGHTS['uptrend']
        + breadth_score * HEAT_WEIGHTS['breadth']
    )

    return round(min(100, max(0, heat)), 1)


def classify_lifecycle(stats: dict) -> str:
    """Lifecycle 단계 분류.

    Returns:
        'Early' | 'Mid' | 'Late' | 'Exhaustion'
    """
    change_1w = stats.get('weighted_change_1w', 0)
    change_1m = stats.get('weighted_change_1m', 0)
    vol_ratio = stats.get('avg_volume_ratio', 1.0)
    uptrend = stats.get('uptrend_ratio', 0)

    # Exhaustion: 1주 하락 but 1개월 높음 + 거래량 감소
    if change_1w < 0 and change_1m > 10 and vol_ratio < 1.0:
        return 'Exhaustion'

    # Late: 1개월 > 15%, 거래량 급증, 업트렌드 80%+
    if change_1m > 15 and vol_ratio > 2.0 and uptrend >= 80:
        return 'Late'

    # Mid: 1개월 > 5%, 거래량 안정, 업트렌드 50%+
    if change_1m > 5 and vol_ratio >= 1.0 and uptrend >= 50:
        return 'Mid'

    # Early: 1주 > 0, 1개월 ≤ 5%
    if change_1w > 0 and change_1m <= 5:
        return 'Early'

    # Default (하락 중이면 Exhaustion, 아니면 Early)
    if change_1w < 0 and change_1m < 0:
        return 'Exhaustion'

    return 'Early'


def assess_confidence(stats: dict) -> str:
    """Confidence 평가.

    Returns:
        'High' | 'Medium' | 'Low'
    """
    uptrend = stats.get('uptrend_ratio', 0)
    vol_ratio = stats.get('avg_volume_ratio', 1.0)

    quant_high = uptrend > 60 and vol_ratio > 1.2
    quant_low = uptrend < 40 or vol_ratio < 0.8

    if quant_high:
        return 'High'
    elif quant_low:
        return 'Low'
    return 'Medium'


def detect_direction(stats: dict) -> str:
    """테마 방향 판정.

    Returns:
        'Bullish' | 'Bearish' | 'Neutral'
    """
    w_change = stats.get('weighted_change_1w', 0)
    uptrend = stats.get('uptrend_ratio', 0)
    vol_ratio = stats.get('avg_volume_ratio', 1.0)

    if w_change > 0 and (uptrend > 50 or vol_ratio > 1.3):
        return 'Bullish'
    elif w_change < 0 and (uptrend < 50 or vol_ratio < 0.8):
        return 'Bearish'
    return 'Neutral'


class ThemeScorer:
    """전체 테마 스코어링 통합."""

    def score_all(self, classified_data: dict) -> dict:
        """모든 테마 3D 스코어 계산.

        Args:
            classified_data: ThemeClassifier.classify()의 결과

        Returns:
            {
                'ai_semiconductor': {
                    'name': 'AI/반도체',
                    'heat': 82.0,
                    'lifecycle': 'Mid',
                    'confidence': 'High',
                    'direction': 'Bullish',
                    'stats': {...},
                },
                ...
            }
        """
        results = {}

        for theme_id, stats in classified_data.items():
            heat = calculate_theme_heat(stats)
            lifecycle = classify_lifecycle(stats)
            confidence = assess_confidence(stats)
            direction = detect_direction(stats)

            results[theme_id] = {
                'name': stats['name'],
                'heat': heat,
                'lifecycle': lifecycle,
                'confidence': confidence,
                'direction': direction,
                'stats': stats,
            }

        return results
