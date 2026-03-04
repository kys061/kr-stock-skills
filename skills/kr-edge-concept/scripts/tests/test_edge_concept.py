"""kr-edge-concept 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from synthesize_concepts import (
    MIN_TICKET_SUPPORT, EXPORTABLE_FAMILIES, HYPOTHESIS_TYPES,
    HYPOTHESIS_THESIS, HYPOTHESIS_INVALIDATIONS, HYPOTHESIS_PLAYBOOKS,
    cluster_key, cluster_items, determine_entry_family,
    build_concept, synthesize_concepts,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_min_ticket_support(self):
        assert MIN_TICKET_SUPPORT == 2

    def test_exportable_families(self):
        assert EXPORTABLE_FAMILIES == {'pivot_breakout',
                                        'gap_up_continuation'}

    def test_hypothesis_types_count(self):
        assert len(HYPOTHESIS_TYPES) == 8

    def test_all_hypotheses_have_thesis(self):
        for h in HYPOTHESIS_TYPES:
            assert h in HYPOTHESIS_THESIS

    def test_all_hypotheses_have_invalidations(self):
        for h in HYPOTHESIS_TYPES:
            assert h in HYPOTHESIS_INVALIDATIONS
            assert len(HYPOTHESIS_INVALIDATIONS[h]) >= 1

    def test_all_hypotheses_have_playbooks(self):
        for h in HYPOTHESIS_TYPES:
            assert h in HYPOTHESIS_PLAYBOOKS
            assert len(HYPOTHESIS_PLAYBOOKS[h]) >= 1


# ─── 클러스터링 ───

class TestClustering:

    def test_cluster_key_from_hint(self):
        hint = {'hypothesis': 'breakout', 'regime': 'RiskOn'}
        assert cluster_key(hint) == ('breakout', 'RiskOn')

    def test_cluster_key_default_regime(self):
        hint = {'hypothesis': 'breakout'}
        assert cluster_key(hint) == ('breakout', 'Neutral')

    def test_cluster_items_groups_correctly(self):
        hints = [
            {'hypothesis': 'breakout', 'regime': 'RiskOn', 'symbol': 'A'},
            {'hypothesis': 'breakout', 'regime': 'RiskOn', 'symbol': 'B'},
            {'hypothesis': 'panic_reversal', 'regime': 'RiskOff',
             'symbol': 'C'},
        ]
        clusters = cluster_items(hints)
        assert ('breakout', 'RiskOn') in clusters
        assert len(clusters[('breakout', 'RiskOn')]['hints']) == 2
        assert ('panic_reversal', 'RiskOff') in clusters

    def test_cluster_items_with_tickets(self):
        hints = [{'hypothesis': 'breakout', 'regime': 'RiskOn'}]
        tickets = [{'hypothesis': 'breakout', 'regime': 'RiskOn'}]
        clusters = cluster_items(hints, tickets)
        cluster = clusters[('breakout', 'RiskOn')]
        assert len(cluster['hints']) == 1
        assert len(cluster['tickets']) == 1

    def test_empty_inputs(self):
        clusters = cluster_items([], [])
        assert len(clusters) == 0


# ─── entry_family 결정 ───

class TestDetermineEntryFamily:

    def test_most_frequent_family(self):
        items = [
            {'entry_family': 'pivot_breakout'},
            {'entry_family': 'pivot_breakout'},
            {'entry_family': 'gap_up_continuation'},
        ]
        assert determine_entry_family(items) == 'pivot_breakout'

    def test_no_family(self):
        items = [{'symbol': 'A'}, {'symbol': 'B'}]
        assert determine_entry_family(items) == ''

    def test_empty_list(self):
        assert determine_entry_family([]) == ''


# ─── 컨셉 빌드 ───

class TestBuildConcept:

    def test_basic_concept(self):
        cluster = {
            'hints': [
                {'symbol': '005930', 'entry_family': 'pivot_breakout'},
                {'symbol': '000660', 'entry_family': 'pivot_breakout'},
            ],
            'tickets': [],
        }
        concept = build_concept('concept-001', 'breakout', 'RiskOn', cluster)
        assert concept['id'] == 'concept-001'
        assert concept['hypothesis_type'] == 'breakout'
        assert concept['title'] == '참여 확대 기반 추세 돌파'
        assert concept['export_ready'] is True
        assert concept['entry_family'] == 'pivot_breakout'
        assert concept['support']['hint_count'] == 2
        assert '005930' in concept['related_symbols']

    def test_non_exportable_concept(self):
        cluster = {
            'hints': [
                {'symbol': '035420'},
                {'symbol': '035720'},
            ],
            'tickets': [],
        }
        concept = build_concept('concept-002', 'panic_reversal', 'RiskOff',
                                cluster)
        assert concept['export_ready'] is False
        assert 'entry_family' not in concept


# ─── 통합 합성 ───

class TestSynthesizeConcepts:

    def test_synthesize_with_sufficient_support(self):
        hints = [
            {'symbol': '005930', 'hypothesis': 'breakout',
             'entry_family': 'pivot_breakout'},
            {'symbol': '000660', 'hypothesis': 'breakout',
             'entry_family': 'pivot_breakout'},
        ]
        result = synthesize_concepts(hints, regime='RiskOn')
        assert len(result['concepts']) == 1
        assert result['concepts'][0]['hypothesis_type'] == 'breakout'
        assert result['meta']['total_concepts'] == 1

    def test_below_min_support_filtered(self):
        hints = [
            {'symbol': '005930', 'hypothesis': 'breakout'},
        ]
        result = synthesize_concepts(hints)
        assert len(result['concepts']) == 0

    def test_multiple_clusters(self):
        hints = [
            {'symbol': 'A', 'hypothesis': 'breakout'},
            {'symbol': 'B', 'hypothesis': 'breakout'},
            {'symbol': 'C', 'hypothesis': 'panic_reversal'},
            {'symbol': 'D', 'hypothesis': 'panic_reversal'},
        ]
        result = synthesize_concepts(hints)
        assert len(result['concepts']) == 2

    def test_meta_fields(self):
        result = synthesize_concepts([])
        meta = result['meta']
        assert 'generated_at' in meta
        assert 'total_concepts' in meta
        assert 'exportable_concepts' in meta
        assert meta['min_ticket_support'] == MIN_TICKET_SUPPORT

    def test_regime_injection(self):
        hints = [
            {'symbol': 'A', 'hypothesis': 'breakout'},
            {'symbol': 'B', 'hypothesis': 'breakout'},
        ]
        result = synthesize_concepts(hints, regime='RiskOn')
        assert result['concepts'][0]['regime'] == 'RiskOn'
