"""report_generator.py 테스트."""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from report_generator import (
    build_header, build_dashboard_section, build_regime_section,
    build_impact_section, build_calendar_section,
    build_footer, generate_report, save_report,
    _format_value, _format_change,
)
from regime_classifier import Regime


def _sample_indicators():
    """테스트용 지표 샘플."""
    return [
        {'id': 'gdp', 'name_kr': 'GDP', 'category': 'growth',
         'value': 2.3, 'prev_value': 3.1, 'change': -0.8,
         'direction': '↓', 'trend_label': '하락', 'unit': '%'},
        {'id': 'fed_rate', 'name_kr': '기준금리', 'category': 'rates',
         'value': 4.5, 'prev_value': 4.5, 'change': 0,
         'direction': '→', 'trend_label': '보합', 'unit': '%'},
        {'id': 'cpi', 'name_kr': 'CPI', 'category': 'inflation',
         'value': 2.9, 'prev_value': 3.0, 'change': -0.1,
         'direction': '↓', 'trend_label': '둔화', 'unit': '%'},
    ]


def _sample_regime():
    """테스트용 레짐 결과."""
    return {
        'regime': Regime.GOLDILOCKS,
        'regime_kr': '골디락스 (적정 성장 + 물가 안정)',
        'composite_score': 55.0,
        'kr_impact': '위험자산 강세, 한국 시장 유리',
        'components': {
            'inflation': {'score': 65, 'weight': 0.30, 'weighted': 19.5},
            'growth': {'score': 55, 'weight': 0.25, 'weighted': 13.75},
            'employment': {'score': 45, 'weight': 0.25, 'weighted': 11.25},
            'sentiment': {'score': 60, 'weight': 0.10, 'weighted': 6.0},
            'external': {'score': 40, 'weight': 0.10, 'weighted': 4.0},
        },
        'component_details': {
            'inflation': {'score': 65, 'level': 'moderate'},
            'growth': {'score': 55, 'level': 'moderate'},
            'employment': {'score': 45, 'level': 'cooling'},
            'sentiment': {'score': 60, 'level': 'neutral'},
            'external': {'score': 40, 'level': 'moderate'},
        },
    }


def _sample_impact():
    """테스트용 영향 결과."""
    return {
        'positive': [{'reason': 'CPI 둔화 → 인하 기대'}],
        'negative': [{'reason': '임금 가속 → 인플레 우려'}],
        'neutral': [],
        'summary': '긍정(1): CPI 둔화 / 부정(1): 임금 가속',
        'net_impact': 'neutral',
    }


class TestFormatValue:
    """값 포맷팅 테스트."""

    def test_percent(self):
        assert _format_value(2.95, '%') == '2.95%'

    def test_thousands(self):
        assert _format_value(220, 'K') == '220K'

    def test_billions(self):
        assert _format_value(-200.5, '$B') == '$-200.5B'

    def test_none(self):
        assert _format_value(None, '%') == 'N/A'

    def test_index(self):
        assert _format_value(52.3, 'index') == '52.3'


class TestFormatChange:
    """변화량 포맷팅 테스트."""

    def test_positive_change(self):
        result = _format_change(0.2, '%', '↑')
        assert '+' in result

    def test_negative_change(self):
        result = _format_change(-0.3, '%', '↓')
        assert '-' in result

    def test_none_change(self):
        assert _format_change(None, '%', '→') == '-'


class TestBuildHeader:
    """헤더 빌드 테스트."""

    def test_header_content(self):
        stats = {'total': 21, 'collected': 18, 'rate': 85.7}
        regime = {'regime': Regime.GOLDILOCKS, 'regime_kr': '골디락스'}
        header = build_header(stats, regime)
        assert '미국 경제지표 대시보드' in header
        assert '18/21' in header


class TestBuildDashboardSection:
    """대시보드 섹션 테스트."""

    def test_dashboard_has_categories(self):
        indicators = _sample_indicators()
        section = build_dashboard_section(indicators)
        assert '성장' in section or '금리' in section or '물가' in section

    def test_dashboard_has_table(self):
        indicators = _sample_indicators()
        section = build_dashboard_section(indicators)
        assert '| 지표 |' in section


class TestBuildRegimeSection:
    """레짐 섹션 테스트."""

    def test_regime_section(self):
        regime = _sample_regime()
        section = build_regime_section(regime)
        assert '종합 진단' in section
        assert '5-컴포넌트 스코어' in section
        assert '물가' in section


class TestBuildImpactSection:
    """영향 섹션 테스트."""

    def test_impact_section(self):
        impact = _sample_impact()
        section = build_impact_section(impact)
        assert '한국 시장 영향 분석' in section


class TestBuildCalendarSection:
    """캘린더 섹션 테스트."""

    def test_calendar_section(self):
        events = [{
            'date': '2026-03-12', 'indicator_id': 'cpi',
            'name_kr': 'CPI', 'forecast': '2.8%',
            'previous': '2.9%', 'importance': 5, 'stars': '★★★★★',
        }]
        section = build_calendar_section(events)
        assert '발표 일정' in section


class TestGenerateReport:
    """전체 리포트 생성 테스트."""

    def test_report_has_all_sections(self):
        indicators = _sample_indicators()
        regime = _sample_regime()
        impact = _sample_impact()
        upcoming = []
        stats = {'total': 3, 'collected': 3, 'rate': 100.0}

        report = generate_report(indicators, regime, impact, upcoming, stats)
        assert '미국 경제지표 대시보드' in report
        assert 'Section 1' in report
        assert 'Section 2' in report
        assert '한국 시장 영향 분석' in report


class TestSaveReport:
    """리포트 저장 테스트."""

    def test_save_report(self):
        content = '# 테스트 리포트'
        path = save_report(content, '20260310')
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8') as f:
            assert f.read() == content
        # cleanup
        os.remove(path)
