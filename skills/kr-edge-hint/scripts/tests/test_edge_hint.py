"""kr-edge-hint 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_hints import (
    RISK_ON_OFF_THRESHOLD, SUPPORTED_ENTRY_FAMILIES, KR_HINT_SOURCES,
    VALID_DIRECTIONS, VALID_HYPOTHESES,
    FOREIGN_CONSECUTIVE_HINT, INST_CONSECUTIVE_HINT,
    FOREIGN_STRONG_CONSECUTIVE, SHORT_INTEREST_SPIKE,
    infer_regime, normalize_hint, build_flow_hints,
    build_anomaly_hints, build_news_hints, dedupe_hints,
    build_all_hints,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_risk_on_off_threshold(self):
        assert RISK_ON_OFF_THRESHOLD == 10

    def test_supported_entry_families(self):
        assert SUPPORTED_ENTRY_FAMILIES == {'pivot_breakout',
                                             'gap_up_continuation'}

    def test_kr_hint_sources(self):
        assert 'foreign_flow' in KR_HINT_SOURCES
        assert 'institutional_flow' in KR_HINT_SOURCES
        assert 'program_trading' in KR_HINT_SOURCES
        assert 'short_interest' in KR_HINT_SOURCES
        assert 'credit_balance' in KR_HINT_SOURCES
        assert len(KR_HINT_SOURCES) == 5

    def test_valid_hypotheses_count(self):
        assert len(VALID_HYPOTHESES) == 8

    def test_foreign_consecutive_hint(self):
        assert FOREIGN_CONSECUTIVE_HINT == 5

    def test_inst_consecutive_hint(self):
        assert INST_CONSECUTIVE_HINT == 5


# ─── 레짐 추론 ───

class TestInferRegime:

    def test_risk_on(self):
        summary = {'risk_on': 15, 'risk_off': 3}
        assert infer_regime(summary) == 'RiskOn'

    def test_risk_off(self):
        summary = {'risk_on': 2, 'risk_off': 15}
        assert infer_regime(summary) == 'RiskOff'

    def test_neutral(self):
        summary = {'risk_on': 8, 'risk_off': 5}
        assert infer_regime(summary) == 'Neutral'

    def test_exact_threshold_risk_on(self):
        summary = {'risk_on': 15, 'risk_off': 5}
        assert infer_regime(summary) == 'RiskOn'

    def test_none_input(self):
        assert infer_regime(None) == 'Neutral'

    def test_empty_dict(self):
        assert infer_regime({}) == 'Neutral'


# ─── 힌트 정규화 ───

class TestNormalizeHint:

    def test_valid_hint(self):
        raw = {
            'symbol': '005930',
            'direction': 'bullish',
            'hypothesis': 'breakout',
            'source': 'rule:foreign_flow',
            'confidence': 0.8,
            'memo': '외국인 매수',
        }
        result = normalize_hint(raw)
        assert result is not None
        assert result['symbol'] == '005930'
        assert result['direction'] == 'bullish'
        assert result['confidence'] == 0.8

    def test_missing_symbol(self):
        raw = {'direction': 'bullish', 'hypothesis': 'breakout'}
        assert normalize_hint(raw) is None

    def test_missing_hypothesis(self):
        raw = {'symbol': '005930', 'direction': 'bullish'}
        assert normalize_hint(raw) is None

    def test_invalid_hypothesis(self):
        raw = {'symbol': '005930', 'hypothesis': 'unknown_type',
               'direction': 'bullish'}
        assert normalize_hint(raw) is None

    def test_invalid_direction_defaults_neutral(self):
        raw = {'symbol': '005930', 'hypothesis': 'breakout',
               'direction': 'invalid', 'source': 'test'}
        result = normalize_hint(raw)
        assert result['direction'] == 'neutral'

    def test_confidence_clamped(self):
        raw = {'symbol': '005930', 'hypothesis': 'breakout',
               'confidence': 1.5, 'source': 'test'}
        result = normalize_hint(raw)
        assert result['confidence'] == 1.0

        raw2 = {'symbol': '005930', 'hypothesis': 'breakout',
                'confidence': -0.5, 'source': 'test'}
        result2 = normalize_hint(raw2)
        assert result2['confidence'] == 0.0

    def test_invalid_entry_family_removed(self):
        raw = {'symbol': '005930', 'hypothesis': 'breakout',
               'entry_family': 'invalid_family', 'source': 'test'}
        result = normalize_hint(raw)
        assert 'entry_family' not in result

    def test_valid_entry_family_kept(self):
        raw = {'symbol': '005930', 'hypothesis': 'breakout',
               'entry_family': 'pivot_breakout', 'source': 'test'}
        result = normalize_hint(raw)
        assert result['entry_family'] == 'pivot_breakout'


# ─── 수급 힌트 생성 ───

class TestBuildFlowHints:

    def test_foreign_consecutive_buy(self):
        summary = {
            'flow_data': [{
                'symbol': '005930',
                'foreign_consecutive_buy': 7,
            }]
        }
        hints = build_flow_hints(summary)
        assert len(hints) >= 1
        foreign_hint = [h for h in hints
                        if h['source'] == 'rule:foreign_flow'
                        and h['direction'] == 'bullish']
        assert len(foreign_hint) == 1
        assert foreign_hint[0]['confidence'] == 0.6

    def test_foreign_strong_consecutive(self):
        summary = {
            'flow_data': [{
                'symbol': '005930',
                'foreign_consecutive_buy': 12,
            }]
        }
        hints = build_flow_hints(summary)
        foreign_hint = [h for h in hints
                        if h['source'] == 'rule:foreign_flow'
                        and h['direction'] == 'bullish']
        assert foreign_hint[0]['confidence'] == 0.8

    def test_inst_consecutive_buy(self):
        summary = {
            'flow_data': [{
                'symbol': '000660',
                'inst_consecutive_buy': 6,
            }]
        }
        hints = build_flow_hints(summary)
        inst_hint = [h for h in hints
                     if h['source'] == 'rule:institutional_flow']
        assert len(inst_hint) == 1

    def test_foreign_consecutive_sell(self):
        summary = {
            'flow_data': [{
                'symbol': '005930',
                'foreign_consecutive_sell': 7,
            }]
        }
        hints = build_flow_hints(summary)
        sell_hint = [h for h in hints if h['direction'] == 'bearish']
        assert len(sell_hint) == 1

    def test_short_interest_spike(self):
        summary = {
            'flow_data': [{
                'symbol': '035420',
                'short_interest_change': 0.25,
            }]
        }
        hints = build_flow_hints(summary)
        short_hint = [h for h in hints
                      if h['source'] == 'rule:short_interest']
        assert len(short_hint) == 1
        assert short_hint[0]['direction'] == 'bearish'

    def test_below_threshold_no_hint(self):
        summary = {
            'flow_data': [{
                'symbol': '005930',
                'foreign_consecutive_buy': 3,
            }]
        }
        hints = build_flow_hints(summary)
        assert len(hints) == 0

    def test_empty_flow_data(self):
        hints = build_flow_hints({'flow_data': []})
        assert len(hints) == 0

    def test_no_flow_data(self):
        hints = build_flow_hints({})
        assert len(hints) == 0


# ─── 이상 탐지 힌트 ───

class TestBuildAnomalyHints:

    def test_volume_spike(self):
        anomalies = [{
            'symbol': '005930',
            'type': 'volume_spike',
            'direction': 'bullish',
            'confidence': 0.7,
            'description': '거래량 3배 급증',
        }]
        hints = build_anomaly_hints(anomalies)
        assert len(hints) == 1
        assert hints[0]['hypothesis'] == 'breakout'
        assert hints[0]['entry_family'] == 'pivot_breakout'

    def test_price_gap_bullish(self):
        anomalies = [{
            'symbol': '000660',
            'type': 'price_gap',
            'direction': 'bullish',
            'confidence': 0.6,
        }]
        hints = build_anomaly_hints(anomalies)
        assert hints[0]['entry_family'] == 'gap_up_continuation'

    def test_correlation_break(self):
        anomalies = [{
            'symbol': '035420',
            'type': 'correlation_break',
            'direction': 'neutral',
            'confidence': 0.5,
        }]
        hints = build_anomaly_hints(anomalies)
        assert hints[0]['hypothesis'] == 'regime_shift'

    def test_empty_anomalies(self):
        assert build_anomaly_hints([]) == []
        assert build_anomaly_hints(None) == []


# ─── 뉴스 반응 힌트 ───

class TestBuildNewsHints:

    def test_positive_news_large_move(self):
        news = [{
            'symbol': '005930',
            'reaction': 'positive',
            'headline': '삼성전자 AI 칩 수주',
            'price_change_pct': 5.0,
        }]
        hints = build_news_hints(news)
        assert len(hints) == 1
        assert hints[0]['direction'] == 'bullish'
        assert hints[0]['hypothesis'] == 'news_reaction'

    def test_small_move_filtered(self):
        news = [{
            'symbol': '005930',
            'reaction': 'positive',
            'headline': '테스트',
            'price_change_pct': 1.5,
        }]
        hints = build_news_hints(news)
        assert len(hints) == 0

    def test_negative_news(self):
        news = [{
            'symbol': '035420',
            'reaction': 'negative',
            'headline': '실적 부진',
            'price_change_pct': -4.0,
        }]
        hints = build_news_hints(news)
        assert len(hints) == 1
        assert hints[0]['direction'] == 'bearish'

    def test_empty_news(self):
        assert build_news_hints([]) == []
        assert build_news_hints(None) == []


# ─── 중복 제거 ───

class TestDedupeHints:

    def test_dedup_keeps_higher_confidence(self):
        hints = [
            {'symbol': '005930', 'direction': 'bullish',
             'hypothesis': 'breakout', 'confidence': 0.6, 'source': 'a',
             'memo': 'low'},
            {'symbol': '005930', 'direction': 'bullish',
             'hypothesis': 'breakout', 'confidence': 0.9, 'source': 'b',
             'memo': 'high'},
        ]
        result = dedupe_hints(hints)
        assert len(result) == 1
        assert result[0]['confidence'] == 0.9

    def test_different_symbols_kept(self):
        hints = [
            {'symbol': '005930', 'direction': 'bullish',
             'hypothesis': 'breakout', 'confidence': 0.6, 'source': 'a',
             'memo': ''},
            {'symbol': '000660', 'direction': 'bullish',
             'hypothesis': 'breakout', 'confidence': 0.7, 'source': 'b',
             'memo': ''},
        ]
        result = dedupe_hints(hints)
        assert len(result) == 2

    def test_empty_list(self):
        assert dedupe_hints([]) == []


# ─── 통합 빌드 ───

class TestBuildAllHints:

    def test_combined_build(self):
        market_summary = {
            'risk_on': 15, 'risk_off': 3,
            'flow_data': [{
                'symbol': '005930',
                'foreign_consecutive_buy': 8,
            }],
        }
        anomalies = [{
            'symbol': '000660',
            'type': 'volume_spike',
            'direction': 'bullish',
            'confidence': 0.7,
            'description': '거래량 급증',
        }]
        result = build_all_hints(market_summary, anomalies)
        assert 'hints' in result
        assert 'meta' in result
        assert result['meta']['regime'] == 'RiskOn'
        assert len(result['hints']) >= 2

    def test_empty_inputs(self):
        result = build_all_hints()
        assert result['hints'] == []
        assert result['meta']['regime'] == 'Neutral'
        assert result['meta']['total_hints'] == 0

    def test_meta_fields(self):
        result = build_all_hints({'risk_on': 0, 'risk_off': 0})
        meta = result['meta']
        assert 'generated_at' in meta
        assert 'rule_hints' in meta
        assert 'total_hints' in meta
        assert 'regime' in meta
