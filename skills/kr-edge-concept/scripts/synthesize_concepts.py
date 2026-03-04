"""kr-edge-concept: 엣지 힌트/티켓 → 재사용 가능 컨셉 합성.

Usage:
    python synthesize_concepts.py --hints hints.yaml --output edge_concepts.yaml
"""

import argparse
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

try:
    import yaml
except ImportError:
    yaml = None

# ─── 상수 ───

MIN_TICKET_SUPPORT = 2

EXPORTABLE_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}

HYPOTHESIS_TYPES = {
    'breakout': '참여 확대 기반 추세 돌파',
    'earnings_drift': '이벤트 기반 지속 드리프트',
    'news_reaction': '뉴스 과반응 드리프트',
    'futures_trigger': '교차 자산 전파',
    'calendar_anomaly': '계절성 수요 불균형',
    'panic_reversal': '충격 과도 반전',
    'regime_shift': '레짐 전환 기회',
    'sector_x_stock': '리더-래거드 섹터 릴레이',
}

HYPOTHESIS_THESIS = {
    'breakout': '외국인/기관 참여 확대 → 주요 저항선 돌파 시 추세 가속',
    'earnings_drift': '실적 서프라이즈 후 가격 조정 지연 → 드리프트 지속',
    'news_reaction': '뉴스 과반응 → 초기 움직임 방향으로 지속 드리프트',
    'futures_trigger': '선물/옵션 시장 시그널 → 현물 시장 전파',
    'calendar_anomaly': '계절적 패턴(배당 시즌, 결산 시즌) → 수요 불균형',
    'panic_reversal': '공포 과도 반응 → 평균 회귀',
    'regime_shift': '매크로 레짐 전환 → 신규 추세 시작',
    'sector_x_stock': '섹터 리더 모멘텀 → 래거드 종목 따라잡기',
}

HYPOTHESIS_INVALIDATIONS = {
    'breakout': [
        '돌파 후 거래량 급감',
        '외국인/기관 순매도 전환',
        '시장 전체 분배일 발생',
    ],
    'earnings_drift': [
        '후속 분기 실적 하향',
        '섹터 전체 하락',
        '외국인 이탈',
    ],
    'news_reaction': [
        '반대 뉴스 발생',
        '시장 레짐 전환',
        '거래량 소멸',
    ],
    'futures_trigger': [
        '선물-현물 괴리율 정상화',
        '프로그램 매매 방향 전환',
    ],
    'calendar_anomaly': [
        '이벤트 날짜 변경/취소',
        '시장 레짐 급변',
    ],
    'panic_reversal': [
        '추가 악재 발생',
        '신용 경색 지속',
        'VIX/VKOSPI 추가 상승',
    ],
    'regime_shift': [
        '레짐 전환 미확인 (일시적)',
        '반대 매크로 시그널',
    ],
    'sector_x_stock': [
        '섹터 리더 모멘텀 붕괴',
        '래거드 종목 펀더멘탈 훼손',
    ],
}

HYPOTHESIS_PLAYBOOKS = {
    'breakout': ['pivot_breakout: 52주 신고가 + 거래량 확인 진입'],
    'earnings_drift': ['gap_up_continuation: 실적 갭업 후 눌림목 진입'],
    'news_reaction': ['gap_up_continuation: 뉴스 갭업 후 지지 확인 진입'],
    'futures_trigger': ['pivot_breakout: 선물 시그널 확인 후 현물 진입'],
    'calendar_anomaly': ['pivot_breakout: 이벤트 전 포지션 구축'],
    'panic_reversal': ['연구용: 과매도 반전 패턴 관찰'],
    'regime_shift': ['연구용: 레짐 전환 초기 포지션'],
    'sector_x_stock': ['연구용: 섹터 릴레이 패턴'],
}


def load_data(filepath: str) -> dict | list | None:
    """YAML 또는 JSON 파일 로드."""
    if not filepath or not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        if yaml and filepath.endswith(('.yaml', '.yml')):
            return yaml.safe_load(f)
        return json.load(f)


def cluster_key(item: dict) -> tuple:
    """클러스터링 키 생성: (hypothesis_type, regime).

    Args:
        item: 힌트 또는 티켓 dict

    Returns:
        (hypothesis_type, regime) 튜플
    """
    hypothesis = item.get('hypothesis', item.get('hypothesis_type', ''))
    regime = item.get('regime', 'Neutral')
    return (hypothesis, regime)


def cluster_items(hints: list, tickets: list = None) -> dict:
    """힌트와 티켓을 (hypothesis, regime) 기준으로 클러스터링.

    Args:
        hints: 힌트 리스트
        tickets: 티켓 리스트 (선택)

    Returns:
        {(hypothesis, regime): {'hints': [...], 'tickets': [...]}}
    """
    clusters = defaultdict(lambda: {'hints': [], 'tickets': []})

    for h in (hints or []):
        key = cluster_key(h)
        if key[0]:
            clusters[key]['hints'].append(h)

    for t in (tickets or []):
        key = cluster_key(t)
        if key[0]:
            clusters[key]['tickets'].append(t)

    return dict(clusters)


def determine_entry_family(items: list) -> str:
    """아이템 리스트에서 가장 빈번한 entry_family 결정.

    Args:
        items: 힌트/티켓 리스트

    Returns:
        entry_family 문자열 또는 빈 문자열
    """
    family_counts = defaultdict(int)
    for item in items:
        fam = item.get('entry_family', '')
        if fam:
            family_counts[fam] += 1

    if not family_counts:
        return ''
    return max(family_counts, key=family_counts.get)


def build_concept(concept_id: str, hypothesis: str, regime: str,
                  cluster: dict) -> dict:
    """클러스터에서 엣지 컨셉 생성.

    Args:
        concept_id: 컨셉 고유 ID
        hypothesis: 가설 유형
        regime: 시장 레짐
        cluster: {'hints': [...], 'tickets': [...]}

    Returns:
        엣지 컨셉 dict
    """
    all_items = cluster['hints'] + cluster['tickets']
    entry_family = determine_entry_family(all_items)
    export_ready = entry_family in EXPORTABLE_FAMILIES

    concept = {
        'id': concept_id,
        'hypothesis_type': hypothesis,
        'title': HYPOTHESIS_TYPES.get(hypothesis, hypothesis),
        'thesis': HYPOTHESIS_THESIS.get(hypothesis, ''),
        'invalidation': HYPOTHESIS_INVALIDATIONS.get(hypothesis, []),
        'playbooks': HYPOTHESIS_PLAYBOOKS.get(hypothesis, []),
        'support': {
            'ticket_count': len(cluster['tickets']),
            'hint_count': len(cluster['hints']),
        },
        'regime': regime,
        'export_ready': export_ready,
    }

    if entry_family:
        concept['entry_family'] = entry_family

    # 관련 종목 수집
    symbols = set()
    for item in all_items:
        sym = item.get('symbol', '')
        if sym:
            symbols.add(sym)
    if symbols:
        concept['related_symbols'] = sorted(symbols)

    return concept


def synthesize_concepts(hints: list = None,
                        tickets: list = None,
                        regime: str = 'Neutral') -> dict:
    """모든 힌트/티켓에서 엣지 컨셉을 합성.

    Args:
        hints: 힌트 리스트
        tickets: 티켓 리스트
        regime: 기본 레짐 (힌트에 레짐 없을 때 사용)

    Returns:
        {'concepts': [...], 'meta': {...}}
    """
    # 힌트에 레짐 주입
    enriched_hints = []
    for h in (hints or []):
        enriched = dict(h)
        if 'regime' not in enriched:
            enriched['regime'] = regime
        enriched_hints.append(enriched)

    enriched_tickets = []
    for t in (tickets or []):
        enriched = dict(t)
        if 'regime' not in enriched:
            enriched['regime'] = regime
        enriched_tickets.append(enriched)

    clusters = cluster_items(enriched_hints, enriched_tickets)

    concepts = []
    idx = 0
    for (hypothesis, clust_regime), cluster in sorted(clusters.items()):
        total_support = len(cluster['hints']) + len(cluster['tickets'])
        if total_support < MIN_TICKET_SUPPORT:
            continue

        idx += 1
        concept_id = f'concept-{idx:03d}'
        concept = build_concept(concept_id, hypothesis, clust_regime, cluster)
        concepts.append(concept)

    exportable = sum(1 for c in concepts if c.get('export_ready'))

    return {
        'concepts': concepts,
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'total_concepts': len(concepts),
            'exportable_concepts': exportable,
            'total_hints': len(enriched_hints),
            'total_tickets': len(enriched_tickets),
            'min_ticket_support': MIN_TICKET_SUPPORT,
        },
    }


def write_output(data: dict, filepath: str) -> str:
    """결과 출력."""
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    if yaml and filepath.endswith(('.yaml', '.yml')):
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def main():
    parser = argparse.ArgumentParser(description='한국 엣지 컨셉 합성기')
    parser.add_argument('--hints', default=None)
    parser.add_argument('--tickets', default=None)
    parser.add_argument('--output', default='edge_concepts.yaml')
    args = parser.parse_args()

    hints_data = load_data(args.hints)
    hints = []
    regime = 'Neutral'
    if isinstance(hints_data, dict):
        hints = hints_data.get('hints', [])
        regime = hints_data.get('meta', {}).get('regime', 'Neutral')
    elif isinstance(hints_data, list):
        hints = hints_data

    tickets = load_data(args.tickets) or []

    result = synthesize_concepts(hints, tickets, regime)
    outpath = write_output(result, args.output)
    print(f'[EdgeConcept] {len(result["concepts"])}개 컨셉 합성 → {outpath}')


if __name__ == '__main__':
    main()
