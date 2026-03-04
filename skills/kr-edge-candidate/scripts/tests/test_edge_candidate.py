"""kr-edge-candidate 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from candidate_contract import (
    INTERFACE_VERSION, CANDIDATE_REQUIRED_KEYS,
    SUPPORTED_ENTRY_FAMILIES, VALIDATION_RULES,
    validate_ticket_payload, validate_interface_contract,
)
from auto_detect_candidates import (
    KR_UNIVERSES, REQUIRED_OHLCV_COLUMNS,
    ENTRY_FAMILY_TO_HYPOTHESIS, RESEARCH_ONLY_HYPOTHESES,
    score_breakout_candidate, score_gap_candidate,
    build_ticket_payload, detect_candidates,
)
from export_candidate import (
    DEFAULT_UNIVERSE, DEFAULT_RISK, DEFAULT_COST_MODEL,
    DEFAULT_PROMOTION_GATES,
    build_strategy_spec, build_metadata, export_candidate,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_interface_version(self):
        assert INTERFACE_VERSION == 'edge-finder-candidate/v1'

    def test_required_keys(self):
        assert len(CANDIDATE_REQUIRED_KEYS) == 8
        assert 'id' in CANDIDATE_REQUIRED_KEYS
        assert 'promotion_gates' in CANDIDATE_REQUIRED_KEYS

    def test_supported_families(self):
        assert SUPPORTED_ENTRY_FAMILIES == {'pivot_breakout',
                                             'gap_up_continuation'}

    def test_kr_universes(self):
        assert 'kospi200' in KR_UNIVERSES
        assert 'kosdaq150' in KR_UNIVERSES
        assert len(KR_UNIVERSES) == 4

    def test_research_only_hypotheses(self):
        assert 'panic_reversal' in RESEARCH_ONLY_HYPOTHESES
        assert 'breakout' not in RESEARCH_ONLY_HYPOTHESES


# ─── 계약 검증 ───

class TestValidateTicketPayload:

    def _make_valid_ticket(self):
        return {
            'id': 'test-001',
            'name': 'Test',
            'universe': {'market': 'KRX'},
            'signals': {'entry_family': 'pivot_breakout'},
            'risk': {'risk_per_trade': 0.01, 'max_positions': 5},
            'cost_model': {'round_trip_cost': 0.0053},
            'validation': {'method': 'full_sample'},
            'promotion_gates': {'min_score': 70},
        }

    def test_valid_ticket(self):
        result = validate_ticket_payload(self._make_valid_ticket())
        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_missing_required_key(self):
        ticket = self._make_valid_ticket()
        del ticket['id']
        result = validate_ticket_payload(ticket)
        assert result['valid'] is False

    def test_excessive_risk(self):
        ticket = self._make_valid_ticket()
        ticket['risk']['risk_per_trade'] = 0.15
        result = validate_ticket_payload(ticket)
        assert result['valid'] is False

    def test_unsupported_entry_family_warning(self):
        ticket = self._make_valid_ticket()
        ticket['signals']['entry_family'] = 'unknown_family'
        result = validate_ticket_payload(ticket)
        assert len(result['warnings']) >= 1


class TestValidateInterfaceContract:

    def test_full_validation(self):
        ticket = {
            'id': 'test-001',
            'name': 'Test',
            'universe': {},
            'signals': {},
            'risk': {'risk_per_trade': 0.01, 'max_positions': 5},
            'cost_model': {},
            'validation': {'method': 'full_sample'},
            'promotion_gates': {'min_score': 70, 'min_profit_factor': 1.5},
        }
        result = validate_interface_contract(ticket)
        assert result['valid'] is True

    def test_non_full_sample_warning(self):
        ticket = {
            'id': 'x', 'name': 'x', 'universe': {},
            'signals': {}, 'risk': {'risk_per_trade': 0.01,
                                     'max_positions': 5},
            'cost_model': {}, 'validation': {'method': 'walk_forward'},
            'promotion_gates': {},
        }
        result = validate_interface_contract(ticket)
        assert any('full_sample' in w for w in result['warnings'])


# ─── 후보 스코어링 ───

class TestScoreBreakoutCandidate:

    def test_high_score(self):
        data = {
            'rs_rank': 95,
            'rel_volume': 3.0,
            'close_pos': 0.95,
            'atr_rank': 80,
            'regime': 'RiskOn',
        }
        score = score_breakout_candidate(data)
        assert score >= 80

    def test_low_score(self):
        data = {
            'rs_rank': 10,
            'rel_volume': 0.5,
            'close_pos': 0.2,
            'atr_rank': 10,
            'regime': 'RiskOff',
        }
        score = score_breakout_candidate(data)
        assert score < 40

    def test_score_bounds(self):
        score = score_breakout_candidate({})
        assert 0 <= score <= 100


class TestScoreGapCandidate:

    def test_large_gap(self):
        data = {
            'gap_pct': 8.0,
            'rel_volume': 2.5,
            'close_pos': 0.9,
            'trend_strength': 0.8,
        }
        score = score_gap_candidate(data)
        assert score >= 70

    def test_small_gap(self):
        data = {
            'gap_pct': 1.0,
            'rel_volume': 0.5,
            'close_pos': 0.3,
            'trend_strength': 0.2,
        }
        score = score_gap_candidate(data)
        assert score < 40


# ─── 후보 탐지 ───

class TestDetectCandidates:

    def test_detect_with_data(self):
        ohlcv = [
            {'symbol': '005930', 'rs_rank': 95, 'rel_volume': 2.5,
             'close_pos': 0.95, 'atr_rank': 80, 'regime': 'RiskOn',
             'gap_pct': 5.0, 'trend_strength': 0.8},
        ]
        result = detect_candidates(ohlcv, 'kospi200')
        assert result['meta']['universe'] == 'kospi200'
        assert result['meta']['total_candidates'] >= 1

    def test_detect_empty_data(self):
        result = detect_candidates([], 'kospi200')
        assert result['meta']['total_candidates'] == 0

    def test_below_threshold_filtered(self):
        ohlcv = [
            {'symbol': '000001', 'rs_rank': 5, 'rel_volume': 0.3,
             'close_pos': 0.1, 'atr_rank': 5, 'regime': 'RiskOff',
             'gap_pct': 0.5, 'trend_strength': 0.1},
        ]
        result = detect_candidates(ohlcv)
        assert result['meta']['exportable_count'] == 0


# ─── 티켓 빌드 ───

class TestBuildTicketPayload:

    def test_exportable_ticket(self):
        candidate = {'symbol': '005930', 'score': 85, 'universe': 'kospi200'}
        ticket = build_ticket_payload(candidate, 'pivot_breakout')
        assert ticket['research_only'] is False
        assert ticket['signals']['entry_family'] == 'pivot_breakout'

    def test_research_only_ticket(self):
        candidate = {'symbol': '005930', 'score': 70}
        ticket = build_ticket_payload(candidate, 'pivot_breakout')
        # pivot_breakout maps to 'breakout', not research-only
        assert ticket['research_only'] is False


# ─── 내보내기 ───

class TestExport:

    def test_build_strategy_spec(self):
        candidate = {
            'id': 'test-001',
            'name': 'Test Strategy',
            'signals': {'entry_family': 'pivot_breakout'},
        }
        spec = build_strategy_spec(candidate)
        assert spec['version'] == 'edge-finder-candidate/v1'
        assert spec['id'] == 'test-001'
        assert 'risk' in spec
        assert 'cost_model' in spec

    def test_build_metadata(self):
        candidate = {'id': 'test-001', 'score': 85}
        meta = build_metadata(candidate)
        assert meta['interface_version'] == 'edge-finder-candidate/v1'
        assert meta['source'] == 'kr-edge-candidate'
        assert 'exported_at' in meta

    def test_export_candidate(self, tmp_path):
        candidate = {
            'id': 'test-export-001',
            'name': 'Export Test',
            'signals': {'entry_family': 'pivot_breakout'},
            'score': 80,
        }
        result = export_candidate(candidate, str(tmp_path))
        assert os.path.exists(result['metadata_path'])
