"""kr-strategy-pivot: 피벗 제안 생성기.

Usage:
    python generate_pivots.py --diagnosis diagnosis.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ─── 아키타입 카탈로그 ───

ARCHETYPE_CATALOG = {
    'trend_following_breakout': {
        'hypothesis_type': 'breakout',
        'entry_family': 'pivot_breakout',
        'compatible_pivots': ['mean_reversion_pullback',
                              'volatility_contraction'],
    },
    'mean_reversion_pullback': {
        'hypothesis_type': 'panic_reversal',
        'entry_family': '',
        'compatible_pivots': ['trend_following_breakout',
                              'statistical_pairs'],
    },
    'earnings_drift_pead': {
        'hypothesis_type': 'earnings_drift',
        'entry_family': 'gap_up_continuation',
        'compatible_pivots': ['event_driven_fade',
                              'sector_rotation_momentum'],
    },
    'volatility_contraction': {
        'hypothesis_type': 'breakout',
        'entry_family': 'pivot_breakout',
        'compatible_pivots': ['trend_following_breakout',
                              'regime_conditional_carry'],
    },
    'regime_conditional_carry': {
        'hypothesis_type': 'regime_shift',
        'entry_family': '',
        'compatible_pivots': ['trend_following_breakout',
                              'sector_rotation_momentum'],
    },
    'sector_rotation_momentum': {
        'hypothesis_type': 'sector_x_stock',
        'entry_family': '',
        'compatible_pivots': ['earnings_drift_pead',
                              'trend_following_breakout'],
    },
    'event_driven_fade': {
        'hypothesis_type': 'news_reaction',
        'entry_family': '',
        'compatible_pivots': ['earnings_drift_pead',
                              'mean_reversion_pullback'],
    },
    'statistical_pairs': {
        'hypothesis_type': 'sector_x_stock',
        'entry_family': '',
        'compatible_pivots': ['mean_reversion_pullback',
                              'regime_conditional_carry'],
    },
}

# ─── 가정 반전 맵 ───

INVERSION_MAP = {
    'cost_defeat': ['보유 기간 단축', '고유동성 종목으로 전환'],
    'tail_risk_elevation': ['리스크 제약 강화', '시장 중립 전환'],
    'improvement_plateau': ['거래량 기반 시그널', '진입 타이밍 변경'],
    'overfitting_proxy': ['모델 복잡도 축소', '검증 기간 연장'],
}

# ─── 목적 리프레이밍 맵 ───

REFRAME_MAP = {
    'tail_risk_elevation': {
        'new_objective': 'max_drawdown_pct < 25, expected_value > 0',
        'description': '리스크 제한 우선 목적함수',
    },
    'cost_defeat': {
        'new_objective': 'win_rate > 55%, expected_value > 0',
        'description': '승률 우선 목적함수',
    },
    'improvement_plateau': {
        'new_objective': 'risk_adjusted_return_per_exposure > 0.5',
        'description': '리스크 대비 수익 목적함수',
    },
    'overfitting_proxy': {
        'new_objective': 'expected_value > 0, 레짐 안정성',
        'description': '안정성 우선 목적함수',
    },
}


def generate_inversions(fired_triggers: list) -> list:
    """가정 반전 제안 생성.

    Args:
        fired_triggers: 발화된 트리거 리스트

    Returns:
        반전 제안 리스트
    """
    proposals = []
    for trigger in fired_triggers:
        trigger_name = trigger.get('trigger', '')
        inversions = INVERSION_MAP.get(trigger_name, [])
        for inv in inversions:
            proposals.append({
                'technique': 'assumption_inversion',
                'source_trigger': trigger_name,
                'proposal': inv,
                'severity': trigger.get('severity', 'MEDIUM'),
            })
    return proposals


def generate_archetype_switches(current_archetype: str) -> list:
    """아키타입 전환 제안 생성.

    Args:
        current_archetype: 현재 전략 아키타입

    Returns:
        전환 제안 리스트
    """
    catalog = ARCHETYPE_CATALOG.get(current_archetype, {})
    compatible = catalog.get('compatible_pivots', [])

    proposals = []
    for target in compatible:
        target_info = ARCHETYPE_CATALOG.get(target, {})
        proposals.append({
            'technique': 'archetype_switch',
            'from_archetype': current_archetype,
            'to_archetype': target,
            'hypothesis_type': target_info.get('hypothesis_type', ''),
            'entry_family': target_info.get('entry_family', ''),
        })
    return proposals


def generate_reframes(fired_triggers: list) -> list:
    """목적 리프레이밍 제안 생성.

    Args:
        fired_triggers: 발화된 트리거 리스트

    Returns:
        리프레이밍 제안 리스트
    """
    proposals = []
    for trigger in fired_triggers:
        trigger_name = trigger.get('trigger', '')
        reframe = REFRAME_MAP.get(trigger_name)
        if reframe:
            proposals.append({
                'technique': 'objective_reframe',
                'source_trigger': trigger_name,
                'new_objective': reframe['new_objective'],
                'description': reframe['description'],
            })
    return proposals


def identify_current_archetype(draft: dict) -> str:
    """현재 드래프트에서 아키타입 식별.

    Args:
        draft: 전략 드래프트 dict

    Returns:
        아키타입 이름
    """
    hypothesis = draft.get('hypothesis_type', '')
    entry_family = draft.get('entry_family', '')

    for name, info in ARCHETYPE_CATALOG.items():
        if (info.get('hypothesis_type') == hypothesis
                and info.get('entry_family') == entry_family):
            return name

    # 가설 유형 기반 폴백
    for name, info in ARCHETYPE_CATALOG.items():
        if info.get('hypothesis_type') == hypothesis:
            return name

    return 'trend_following_breakout'


def generate_all_pivots(diagnosis: dict, draft: dict = None) -> dict:
    """모든 피벗 제안 생성.

    Args:
        diagnosis: 정체 진단 결과
        draft: 현재 전략 드래프트 (선택)

    Returns:
        {
            'inversions': [...],
            'archetype_switches': [...],
            'reframes': [...],
            'recommendation': str,
            'meta': {...},
        }
    """
    fired_triggers = diagnosis.get('fired_triggers', [])
    recommendation = diagnosis.get('recommendation', 'continue')

    inversions = generate_inversions(fired_triggers)
    reframes = generate_reframes(fired_triggers)

    archetype_switches = []
    if draft:
        current = identify_current_archetype(draft)
        archetype_switches = generate_archetype_switches(current)

    total_proposals = len(inversions) + len(archetype_switches) + len(reframes)

    return {
        'inversions': inversions,
        'archetype_switches': archetype_switches,
        'reframes': reframes,
        'recommendation': recommendation,
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'total_proposals': total_proposals,
            'fired_triggers_count': len(fired_triggers),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='피벗 제안 생성기')
    parser.add_argument('--diagnosis', required=True)
    parser.add_argument('--draft', default=None)
    parser.add_argument('--output', default='pivot_proposals.json')
    args = parser.parse_args()

    with open(args.diagnosis, 'r', encoding='utf-8') as f:
        diagnosis = json.load(f)

    draft = None
    if args.draft:
        with open(args.draft, 'r', encoding='utf-8') as f:
            draft = json.load(f)

    result = generate_all_pivots(diagnosis, draft)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'[StrategyPivot] {result["meta"]["total_proposals"]}개 피벗 제안 생성')


if __name__ == '__main__':
    main()
