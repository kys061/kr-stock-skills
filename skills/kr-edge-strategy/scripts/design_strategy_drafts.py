"""kr-edge-strategy: 엣지 컨셉 → 전략 드래프트 변환.

Usage:
    python design_strategy_drafts.py --concepts edge_concepts.yaml \
                                      --output-dir strategy_drafts/
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

# ─── 리스크 프로파일 ───

RISK_PROFILES = {
    'conservative': {
        'risk_per_trade': 0.005,
        'max_positions': 3,
        'stop_loss_pct': 0.05,
        'take_profit_rr': 2.2,
    },
    'balanced': {
        'risk_per_trade': 0.01,
        'max_positions': 5,
        'stop_loss_pct': 0.07,
        'take_profit_rr': 3.0,
    },
    'aggressive': {
        'risk_per_trade': 0.015,
        'max_positions': 7,
        'stop_loss_pct': 0.09,
        'take_profit_rr': 3.5,
    },
}

# ─── 변형 오버라이드 ───

VARIANT_OVERRIDES = {
    'core': {'risk_multiplier': 1.0},
    'conservative': {'risk_multiplier': 0.75},
    'research_probe': {'risk_multiplier': 0.5},
}

# ─── 한국 비용 모델 ───

KR_STRATEGY_COSTS = {
    'round_trip_cost': 0.0053,
    'holding_cost_daily': 0.0,
    'margin_rate': 0.0,
}

# ─── 전략 제약 ───

MAX_SECTOR_EXPOSURE = 0.30
TIME_STOP_BREAKOUT = 20
TIME_STOP_DEFAULT = 10

# ─── 내보내기 가능 패밀리 ───

EXPORTABLE_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}

# ─── 진입 조건 템플릿 ───

ENTRY_TEMPLATES = {
    'pivot_breakout': {
        'conditions': [
            '52주 신고가 돌파 또는 주요 저항선 돌파',
            '거래량 20일 평균 대비 1.5배 이상',
        ],
        'trend_filter': '20일 이동평균선 위',
    },
    'gap_up_continuation': {
        'conditions': [
            '갭업 발생 (전일 종가 대비 +3% 이상)',
            '장중 갭 메우지 않음',
        ],
        'trend_filter': '50일 이동평균선 위',
    },
}


def load_concepts(filepath: str) -> list:
    """컨셉 YAML/JSON 파일 로드.

    Args:
        filepath: 컨셉 파일 경로

    Returns:
        컨셉 리스트
    """
    if not filepath or not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        if yaml and filepath.endswith(('.yaml', '.yml')):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    if isinstance(data, dict):
        return data.get('concepts', [])
    return data if isinstance(data, list) else []


def resolve_variants(concept: dict) -> list:
    """컨셉의 export_ready에 따라 변형 결정.

    Args:
        concept: 엣지 컨셉

    Returns:
        변형 이름 리스트
    """
    if concept.get('export_ready'):
        return ['core', 'conservative', 'research_probe']
    return ['research_probe']


def resolve_entry(concept: dict) -> dict:
    """컨셉에서 진입 조건 결정.

    Args:
        concept: 엣지 컨셉

    Returns:
        {'conditions': [...], 'trend_filter': str}
    """
    family = concept.get('entry_family', '')
    if family in ENTRY_TEMPLATES:
        return dict(ENTRY_TEMPLATES[family])
    return {
        'conditions': ['연구 대상 — 구체적 진입 조건 미정'],
        'trend_filter': '',
    }


def build_draft(concept: dict, variant: str,
                profile_name: str = 'balanced') -> dict:
    """컨셉 + 변형으로 전략 드래프트 생성.

    Args:
        concept: 엣지 컨셉
        variant: 변형 이름 (core, conservative, research_probe)
        profile_name: 리스크 프로파일 이름

    Returns:
        전략 드래프트 dict
    """
    concept_id = concept.get('id', 'unknown')
    draft_id = f'{concept_id}-{variant}'

    profile = dict(RISK_PROFILES.get(profile_name, RISK_PROFILES['balanced']))
    multiplier = VARIANT_OVERRIDES.get(variant, {}).get('risk_multiplier', 1.0)

    adjusted_risk = profile['risk_per_trade'] * multiplier

    entry_family = concept.get('entry_family', '')
    time_stop = (TIME_STOP_BREAKOUT
                 if entry_family == 'pivot_breakout'
                 else TIME_STOP_DEFAULT)

    entry = resolve_entry(concept)

    draft = {
        'id': draft_id,
        'concept_id': concept_id,
        'variant': variant,
        'hypothesis_type': concept.get('hypothesis_type', ''),
        'title': concept.get('title', ''),
        'entry': entry,
        'risk': {
            'profile': profile_name,
            'risk_per_trade': round(adjusted_risk, 4),
            'max_positions': profile['max_positions'],
            'stop_loss_pct': profile['stop_loss_pct'],
            'take_profit_rr': profile['take_profit_rr'],
        },
        'exit': {
            'time_stop_days': time_stop,
            'trailing_stop': True,
        },
        'cost_model': dict(KR_STRATEGY_COSTS),
        'constraints': {
            'max_sector_exposure': MAX_SECTOR_EXPOSURE,
        },
    }

    if entry_family:
        draft['entry_family'] = entry_family

    return draft


def build_export_ticket(draft: dict) -> dict | None:
    """드래프트 → 내보내기 가능 티켓 변환.

    Args:
        draft: 전략 드래프트

    Returns:
        내보내기 티켓 dict 또는 내보내기 불가 시 None
    """
    entry_family = draft.get('entry_family', '')
    if entry_family not in EXPORTABLE_FAMILIES:
        return None
    if draft.get('variant') != 'core':
        return None

    return {
        'id': f'ticket-{draft["id"]}',
        'name': draft.get('title', ''),
        'hypothesis_type': draft.get('hypothesis_type', ''),
        'entry_family': entry_family,
        'entry': draft.get('entry', {}),
        'risk': draft.get('risk', {}),
        'exit': draft.get('exit', {}),
        'cost_model': draft.get('cost_model', {}),
        'source': 'kr-edge-strategy',
    }


def design_all_drafts(concepts: list) -> dict:
    """모든 컨셉에서 전략 드래프트 및 내보내기 티켓 생성.

    Args:
        concepts: 엣지 컨셉 리스트

    Returns:
        {
            'drafts': [...],
            'export_tickets': [...],
            'meta': {...},
        }
    """
    drafts = []
    export_tickets = []

    for concept in concepts:
        variants = resolve_variants(concept)
        for variant in variants:
            draft = build_draft(concept, variant)
            drafts.append(draft)

            ticket = build_export_ticket(draft)
            if ticket:
                export_tickets.append(ticket)

    return {
        'drafts': drafts,
        'export_tickets': export_tickets,
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'total_drafts': len(drafts),
            'total_export_tickets': len(export_tickets),
            'cost_model': KR_STRATEGY_COSTS,
        },
    }


def write_output(data: dict, output_dir: str) -> str:
    """결과 출력."""
    os.makedirs(output_dir, exist_ok=True)

    drafts_path = os.path.join(output_dir, 'strategy_drafts.json')
    with open(drafts_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return drafts_path


def main():
    parser = argparse.ArgumentParser(description='한국 전략 드래프트 생성기')
    parser.add_argument('--concepts', required=True)
    parser.add_argument('--output-dir', default='strategy_drafts')
    args = parser.parse_args()

    concepts = load_concepts(args.concepts)
    result = design_all_drafts(concepts)
    outpath = write_output(result, args.output_dir)

    print(f'[EdgeStrategy] {len(result["drafts"])}개 드래프트, '
          f'{len(result["export_tickets"])}개 티켓 → {outpath}')


if __name__ == '__main__':
    main()
