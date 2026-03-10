"""kr_impact_analyzer.py 테스트."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kr_impact_analyzer import (
    Impact, IMPACT_RULES, NET_IMPACT_KR,
    analyze_impact, format_impact_section,
)


class TestImpactRules:
    """임팩트 룰 테스트."""

    def test_rule_count(self):
        """42개 룰 확인."""
        assert len(IMPACT_RULES) == 42

    def test_gdp_up_positive(self):
        """GDP 상승 → 긍정."""
        impact, reason = IMPACT_RULES[('gdp', '↑')]
        assert impact == Impact.POSITIVE

    def test_cpi_down_positive(self):
        """CPI 하락 → 긍정."""
        impact, reason = IMPACT_RULES[('cpi', '↓')]
        assert impact == Impact.POSITIVE

    def test_fed_rate_up_negative(self):
        """기준금리 인상 → 부정."""
        impact, reason = IMPACT_RULES[('fed_rate', '↑')]
        assert impact == Impact.NEGATIVE

    def test_current_account_neutral(self):
        """경상수지 → 중립."""
        impact, _ = IMPACT_RULES[('current_account', '↓')]
        assert impact == Impact.NEUTRAL


class TestAnalyzeImpact:
    """영향 분석 테스트."""

    def test_mostly_positive(self):
        """긍정 요인 많을 때."""
        indicators = [
            {'id': 'cpi', 'value': 2.5, 'direction': '↓', 'name_kr': 'CPI'},
            {'id': 'pce', 'value': 2.3, 'direction': '↓', 'name_kr': 'PCE'},
            {'id': 'gdp', 'value': 3.0, 'direction': '↑', 'name_kr': 'GDP'},
            {'id': 'ism_pmi', 'value': 52.0, 'direction': '↑', 'name_kr': 'ISM PMI'},
            {'id': 'fed_rate', 'value': 4.5, 'direction': '↓', 'name_kr': '기준금리'},
        ]
        result = analyze_impact(indicators)
        assert len(result['positive']) >= 4
        assert result['net_impact'] in ('strongly_positive', 'mildly_positive')

    def test_mostly_negative(self):
        """부정 요인 많을 때."""
        indicators = [
            {'id': 'cpi', 'value': 3.5, 'direction': '↑', 'name_kr': 'CPI'},
            {'id': 'pce', 'value': 3.0, 'direction': '↑', 'name_kr': 'PCE'},
            {'id': 'fed_rate', 'value': 5.0, 'direction': '↑', 'name_kr': '기준금리'},
            {'id': 'hourly_earnings', 'value': 0.5, 'direction': '↑', 'name_kr': '시간당소득'},
            {'id': 'ism_pmi', 'value': 48.0, 'direction': '↓', 'name_kr': 'ISM PMI'},
        ]
        result = analyze_impact(indicators)
        assert len(result['negative']) >= 4
        assert result['net_impact'] in ('strongly_negative', 'mildly_negative')

    def test_skip_none_value(self):
        """value=None 항목 제외."""
        indicators = [
            {'id': 'gdp', 'value': None, 'direction': '↑', 'name_kr': 'GDP'},
        ]
        result = analyze_impact(indicators)
        assert len(result['positive']) == 0
        assert len(result['negative']) == 0

    def test_flat_direction_neutral(self):
        """변화 없음 → 중립."""
        indicators = [
            {'id': 'gdp', 'value': 2.5, 'direction': '→', 'name_kr': 'GDP'},
        ]
        result = analyze_impact(indicators)
        assert len(result['neutral']) == 1

    def test_net_impact_strongly_positive(self):
        """strongly_positive 판정 (diff >= 4)."""
        indicators = [
            {'id': f'ind_{i}', 'value': 1, 'direction': '↑', 'name_kr': f'지표{i}'}
            for i in range(5)
        ]
        # 룰에 없는 지표이므로 neutral 처리됨 — 실제 룰 있는 지표 사용
        indicators = [
            {'id': 'cpi', 'value': 2.5, 'direction': '↓', 'name_kr': 'CPI'},
            {'id': 'pce', 'value': 2.3, 'direction': '↓', 'name_kr': 'PCE'},
            {'id': 'ppi', 'value': 2.0, 'direction': '↓', 'name_kr': 'PPI'},
            {'id': 'gdp', 'value': 3.0, 'direction': '↑', 'name_kr': 'GDP'},
        ]
        result = analyze_impact(indicators)
        assert result['net_impact'] == 'strongly_positive'

    def test_summary_generation(self):
        """summary 생성."""
        indicators = [
            {'id': 'cpi', 'value': 2.5, 'direction': '↓', 'name_kr': 'CPI'},
            {'id': 'fed_rate', 'value': 5.0, 'direction': '↑', 'name_kr': '기준금리'},
        ]
        result = analyze_impact(indicators)
        assert '긍정' in result['summary']
        assert '부정' in result['summary']

    def test_empty_indicators(self):
        """빈 지표 리스트."""
        result = analyze_impact([])
        assert result['net_impact'] == 'neutral'
        assert result['summary'] == '분석 데이터 부족'


class TestFormatImpactSection:
    """포맷팅 테스트."""

    def test_format_output(self):
        """마크다운 포맷 확인."""
        impact = {
            'positive': [{'reason': 'CPI 둔화'}],
            'negative': [{'reason': '금리 인상'}],
            'neutral': [],
            'net_impact': 'neutral',
        }
        output = format_impact_section(impact)
        assert '## 한국 시장 영향 분석' in output
        assert '긍정 요인' in output
        assert '부정 요인' in output

    def test_net_impact_kr_mapping(self):
        """NET_IMPACT_KR 매핑 확인."""
        assert 'strongly_positive' in NET_IMPACT_KR
        assert 'strongly_negative' in NET_IMPACT_KR
        assert len(NET_IMPACT_KR) == 5
