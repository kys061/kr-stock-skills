"""kr-scenario-analyzer 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kr_scenario_analyzer import (
    SCENARIO_STRUCTURE, TIME_HORIZON_MONTHS, IMPACT_ORDERS,
    RECOMMENDATION_COUNT, KR_SECTORS, KR_EVENT_TYPES,
    EVENT_SECTOR_IMPACT, EVENT_KEYWORDS,
    classify_event, get_sector_impact, build_impact_chain,
    build_scenarios, build_recommendations, analyze_scenario,
    generate_report,
)


# ─── 상수 검증 ───

class TestConstants:

    def test_scenario_structure_count(self):
        assert len(SCENARIO_STRUCTURE) == 3
        assert 'base' in SCENARIO_STRUCTURE
        assert 'bull' in SCENARIO_STRUCTURE
        assert 'bear' in SCENARIO_STRUCTURE

    def test_time_horizon(self):
        assert TIME_HORIZON_MONTHS == 18

    def test_impact_orders(self):
        assert IMPACT_ORDERS == ['1차 영향', '2차 영향', '3차 영향']

    def test_kr_sectors_count(self):
        assert len(KR_SECTORS) == 14

    def test_kr_event_types_count(self):
        assert len(KR_EVENT_TYPES) == 7

    def test_event_sector_impact_keys(self):
        for event_type in KR_EVENT_TYPES:
            assert event_type in EVENT_SECTOR_IMPACT

    def test_event_keywords_keys(self):
        for event_type in KR_EVENT_TYPES:
            assert event_type in EVENT_KEYWORDS


# ─── 이벤트 분류 ───

class TestClassifyEvent:

    def test_bok_rate(self):
        assert classify_event('BOK 기준금리 0.25%p 인하') == 'bok_rate_decision'

    def test_north_korea(self):
        assert classify_event('북한 미사일 발사') == 'north_korea_geopolitical'

    def test_semiconductor(self):
        assert classify_event('DRAM 가격 반등') == 'semiconductor_cycle'

    def test_exchange_rate(self):
        assert classify_event('원/달러 환율 급등') == 'exchange_rate_shock'

    def test_government_policy(self):
        assert classify_event('부동산 규제 강화 법안') == 'government_policy'

    def test_china_trade(self):
        assert classify_event('중국 수출규제 확대') == 'china_trade_policy'

    def test_earnings(self):
        assert classify_event('삼성전자 영업이익 서프라이즈') == 'earnings_surprise'

    def test_empty_headline(self):
        assert classify_event('') == 'earnings_surprise'


# ─── 섹터 영향 ───

class TestGetSectorImpact:

    def test_bok_rate_impact(self):
        impact = get_sector_impact('bok_rate_decision')
        assert '금융/은행' in impact['positive']

    def test_north_korea_impact(self):
        impact = get_sector_impact('north_korea_geopolitical')
        assert '방산' in impact['positive']
        assert '건설/부동산' in impact['negative']

    def test_unknown_event(self):
        impact = get_sector_impact('unknown')
        assert 'description' in impact


# ─── 영향 체인 ───

class TestBuildImpactChain:

    def test_chain_has_3_orders(self):
        impact = get_sector_impact('bok_rate_decision')
        chain = build_impact_chain('bok_rate_decision', impact)
        assert len(chain) == 3
        assert chain[0]['order'] == '1차 영향'
        assert chain[1]['order'] == '2차 영향'
        assert chain[2]['order'] == '3차 영향'


# ─── 시나리오 빌드 ───

class TestBuildScenarios:

    def test_three_scenarios(self):
        impact = get_sector_impact('bok_rate_decision')
        scenarios = build_scenarios('금리 인하', 'bok_rate_decision', impact)
        assert len(scenarios) == 3

    def test_probability_sum_100(self):
        impact = get_sector_impact('bok_rate_decision')
        scenarios = build_scenarios('금리 인하', 'bok_rate_decision', impact)
        total_prob = sum(s['probability'] for s in scenarios)
        assert total_prob == 100

    def test_scenario_names(self):
        impact = get_sector_impact('bok_rate_decision')
        scenarios = build_scenarios('테스트', 'bok_rate_decision', impact)
        names = [s['name'] for s in scenarios]
        assert '기본 시나리오' in names
        assert '강세 시나리오' in names
        assert '약세 시나리오' in names


# ─── 종목 추천 ───

class TestBuildRecommendations:

    def test_bok_rate_recommendations(self):
        impact = get_sector_impact('bok_rate_decision')
        recs = build_recommendations(impact)
        assert 'positive' in recs
        assert 'negative' in recs
        assert len(recs['positive']) <= 5

    def test_north_korea_has_both(self):
        impact = get_sector_impact('north_korea_geopolitical')
        recs = build_recommendations(impact)
        assert len(recs['positive']) > 0
        assert len(recs['negative']) > 0


# ─── 통합 분석 ───

class TestAnalyzeScenario:

    def test_full_analysis(self):
        result = analyze_scenario('BOK 기준금리 0.25%p 인하')
        assert result['event_type'] == 'bok_rate_decision'
        assert len(result['scenarios']) == 3
        assert len(result['impact_chain']) == 3
        assert 'meta' in result
        assert result['meta']['time_horizon_months'] == 18

    def test_report_generation(self):
        result = analyze_scenario('반도체 DRAM 가격 반등')
        report = generate_report(result)
        assert '시나리오 분석' in report
        assert '기본 시나리오' in report
        assert '강세 시나리오' in report
        assert '약세 시나리오' in report
