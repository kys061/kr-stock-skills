"""kr-edge-strategy 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from design_strategy_drafts import (
    RISK_PROFILES, VARIANT_OVERRIDES, KR_STRATEGY_COSTS,
    MAX_SECTOR_EXPOSURE, TIME_STOP_BREAKOUT, TIME_STOP_DEFAULT,
    EXPORTABLE_FAMILIES, ENTRY_TEMPLATES,
    resolve_variants, resolve_entry, build_draft,
    build_export_ticket, design_all_drafts,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_risk_profiles_count(self):
        assert len(RISK_PROFILES) == 3
        assert 'conservative' in RISK_PROFILES
        assert 'balanced' in RISK_PROFILES
        assert 'aggressive' in RISK_PROFILES

    def test_conservative_profile(self):
        p = RISK_PROFILES['conservative']
        assert p['risk_per_trade'] == 0.005
        assert p['max_positions'] == 3
        assert p['stop_loss_pct'] == 0.05
        assert p['take_profit_rr'] == 2.2

    def test_balanced_profile(self):
        p = RISK_PROFILES['balanced']
        assert p['risk_per_trade'] == 0.01
        assert p['max_positions'] == 5
        assert p['stop_loss_pct'] == 0.07
        assert p['take_profit_rr'] == 3.0

    def test_aggressive_profile(self):
        p = RISK_PROFILES['aggressive']
        assert p['risk_per_trade'] == 0.015
        assert p['max_positions'] == 7
        assert p['stop_loss_pct'] == 0.09
        assert p['take_profit_rr'] == 3.5

    def test_variant_overrides(self):
        assert VARIANT_OVERRIDES['core']['risk_multiplier'] == 1.0
        assert VARIANT_OVERRIDES['conservative']['risk_multiplier'] == 0.75
        assert VARIANT_OVERRIDES['research_probe']['risk_multiplier'] == 0.5

    def test_kr_strategy_costs(self):
        assert KR_STRATEGY_COSTS['round_trip_cost'] == 0.0053
        assert KR_STRATEGY_COSTS['holding_cost_daily'] == 0.0

    def test_sector_exposure(self):
        assert MAX_SECTOR_EXPOSURE == 0.30

    def test_time_stops(self):
        assert TIME_STOP_BREAKOUT == 20
        assert TIME_STOP_DEFAULT == 10

    def test_exportable_families(self):
        assert EXPORTABLE_FAMILIES == {'pivot_breakout',
                                        'gap_up_continuation'}

    def test_entry_templates(self):
        assert 'pivot_breakout' in ENTRY_TEMPLATES
        assert 'gap_up_continuation' in ENTRY_TEMPLATES


# ─── 변형 결정 ───

class TestResolveVariants:

    def test_exportable_concept_3_variants(self):
        concept = {'export_ready': True}
        variants = resolve_variants(concept)
        assert variants == ['core', 'conservative', 'research_probe']

    def test_non_exportable_concept_1_variant(self):
        concept = {'export_ready': False}
        variants = resolve_variants(concept)
        assert variants == ['research_probe']


# ─── 진입 조건 ───

class TestResolveEntry:

    def test_pivot_breakout_entry(self):
        concept = {'entry_family': 'pivot_breakout'}
        entry = resolve_entry(concept)
        assert len(entry['conditions']) >= 2
        assert entry['trend_filter'] != ''

    def test_gap_up_entry(self):
        concept = {'entry_family': 'gap_up_continuation'}
        entry = resolve_entry(concept)
        assert len(entry['conditions']) >= 2

    def test_unknown_family(self):
        concept = {'entry_family': 'unknown'}
        entry = resolve_entry(concept)
        assert '연구 대상' in entry['conditions'][0]


# ─── 드래프트 빌드 ───

class TestBuildDraft:

    def test_core_variant(self):
        concept = {
            'id': 'concept-001',
            'hypothesis_type': 'breakout',
            'title': '추세 돌파',
            'entry_family': 'pivot_breakout',
            'export_ready': True,
        }
        draft = build_draft(concept, 'core')
        assert draft['id'] == 'concept-001-core'
        assert draft['variant'] == 'core'
        assert draft['risk']['risk_per_trade'] == 0.01
        assert draft['exit']['time_stop_days'] == TIME_STOP_BREAKOUT
        assert draft['cost_model']['round_trip_cost'] == 0.0053

    def test_research_probe_risk_halved(self):
        concept = {
            'id': 'concept-002',
            'hypothesis_type': 'panic_reversal',
            'title': '충격 반전',
        }
        draft = build_draft(concept, 'research_probe')
        assert draft['risk']['risk_per_trade'] == 0.005  # 0.01 × 0.5

    def test_default_time_stop(self):
        concept = {
            'id': 'concept-003',
            'hypothesis_type': 'news_reaction',
            'entry_family': 'gap_up_continuation',
        }
        draft = build_draft(concept, 'core')
        assert draft['exit']['time_stop_days'] == TIME_STOP_DEFAULT

    def test_sector_constraint(self):
        concept = {'id': 'c-001', 'hypothesis_type': 'breakout'}
        draft = build_draft(concept, 'core')
        assert draft['constraints']['max_sector_exposure'] == 0.30


# ─── 내보내기 티켓 ───

class TestBuildExportTicket:

    def test_exportable_core_draft(self):
        draft = {
            'id': 'concept-001-core',
            'variant': 'core',
            'entry_family': 'pivot_breakout',
            'hypothesis_type': 'breakout',
            'title': '테스트',
            'entry': {'conditions': ['test']},
            'risk': {'risk_per_trade': 0.01},
            'exit': {'time_stop_days': 20},
            'cost_model': KR_STRATEGY_COSTS,
        }
        ticket = build_export_ticket(draft)
        assert ticket is not None
        assert ticket['source'] == 'kr-edge-strategy'
        assert ticket['entry_family'] == 'pivot_breakout'

    def test_non_exportable_family(self):
        draft = {'id': 'x', 'variant': 'core', 'entry_family': 'unknown'}
        assert build_export_ticket(draft) is None

    def test_non_core_variant(self):
        draft = {'id': 'x', 'variant': 'research_probe',
                 'entry_family': 'pivot_breakout'}
        assert build_export_ticket(draft) is None


# ─── 통합 ───

class TestDesignAllDrafts:

    def test_exportable_concept_generates_3_drafts_1_ticket(self):
        concepts = [{
            'id': 'concept-001',
            'hypothesis_type': 'breakout',
            'title': '추세 돌파',
            'entry_family': 'pivot_breakout',
            'export_ready': True,
        }]
        result = design_all_drafts(concepts)
        assert result['meta']['total_drafts'] == 3
        assert result['meta']['total_export_tickets'] == 1

    def test_non_exportable_concept(self):
        concepts = [{
            'id': 'concept-002',
            'hypothesis_type': 'panic_reversal',
            'title': '충격 반전',
            'export_ready': False,
        }]
        result = design_all_drafts(concepts)
        assert result['meta']['total_drafts'] == 1
        assert result['meta']['total_export_tickets'] == 0

    def test_empty_concepts(self):
        result = design_all_drafts([])
        assert result['meta']['total_drafts'] == 0

    def test_meta_has_cost_model(self):
        result = design_all_drafts([])
        assert 'cost_model' in result['meta']
        assert result['meta']['cost_model']['round_trip_cost'] == 0.0053
