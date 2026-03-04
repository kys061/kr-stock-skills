"""
kr-macro-regime: 레짐 분류 스코어러.
가중 투표 방식으로 6개 컴포넌트의 레짐 시그널 집계.
"""


COMPONENT_WEIGHTS = {
    'concentration': 0.25,
    'yield_curve': 0.20,
    'credit': 0.15,
    'size_factor': 0.15,
    'equity_bond': 0.15,
    'sector_rotation': 0.10,
}

COMPONENT_NAMES = {
    'concentration': '시장 집중도',
    'yield_curve': '금리 곡선',
    'credit': '신용 환경',
    'size_factor': '사이즈 팩터',
    'equity_bond': '주식-채권 관계',
    'sector_rotation': '섹터 로테이션',
}

REGIME_TYPES = [
    'Concentration', 'Broadening', 'Contraction',
    'Inflationary', 'Transitional',
]

REGIME_STRATEGIES = {
    'Concentration': '대형 성장주 유지, 소형주 회피',
    'Broadening': '소형/가치주 비중 확대, 업종 분산',
    'Contraction': '현금 비중 확대, 방어 섹터 집중',
    'Inflationary': '실물자산, 에너지/원자재 비중',
    'Transitional': '포지션 축소, 관망, 유동성 확보',
}

TRANSITIONAL_THRESHOLD = 0.40  # 40% 미만이면 Transitional


def classify_regime(components: dict) -> dict:
    """6개 컴포넌트의 레짐 시그널을 가중 투표로 집계.

    Args:
        components: {
            'concentration': {'regime_signal': str, ...},
            'yield_curve': {'regime_signal': str, ...},
            ...
        }
    Returns:
        {
            'regime': str,
            'confidence': float (0-1),
            'votes': dict,
            'strategic_implication': str,
        }
    """
    votes = {r: 0.0 for r in REGIME_TYPES}
    total_weight = 0.0

    for key, weight in COMPONENT_WEIGHTS.items():
        comp = components.get(key, {})
        signal = comp.get('regime_signal', 'Transitional')
        if signal in votes:
            votes[signal] += weight
            total_weight += weight

    # 정규화
    if total_weight > 0:
        for r in votes:
            votes[r] /= total_weight

    # 최다 득표 레짐
    max_regime = max(votes, key=votes.get)
    confidence = votes[max_regime]

    # 40% 미만이면 Transitional
    if confidence < TRANSITIONAL_THRESHOLD:
        regime = 'Transitional'
        confidence = votes.get('Transitional', 0.0)
    else:
        regime = max_regime

    return {
        'regime': regime,
        'confidence': round(confidence, 3),
        'votes': {k: round(v, 3) for k, v in votes.items()},
        'strategic_implication': REGIME_STRATEGIES.get(regime, ''),
    }


def calculate_transition_probability(current_regime: str,
                                     votes: dict) -> dict:
    """현재 레짐에서 다른 레짐으로의 전환 확률.

    Args:
        current_regime: 현재 레짐명
        votes: 컴포넌트 투표 결과 (정규화됨)
    Returns:
        {'Broadening': 0.25, 'Contraction': 0.15, ...}
    """
    probs = {}
    for regime, vote_share in votes.items():
        if regime == current_regime:
            continue
        probs[regime] = round(vote_share, 3)
    return probs


class MacroRegimeScorer:
    """레짐 분류 스코어러."""

    def classify(self, components: dict) -> dict:
        """6개 컴포넌트 → 레짐 분류.

        Returns:
            {
                'regime': str,
                'confidence': float,
                'votes': dict,
                'transition_probs': dict,
                'strategic_implication': str,
                'components': dict,
            }
        """
        result = classify_regime(components)
        result['transition_probs'] = calculate_transition_probability(
            result['regime'], result['votes']
        )
        result['components'] = components
        return result
