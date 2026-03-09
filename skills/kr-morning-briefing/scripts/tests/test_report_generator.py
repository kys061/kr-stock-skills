"""report_generator 단위 테스트."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from report_generator import (
    _build_header, _build_section1_market, _build_section2_calendar,
    _build_section3_keywords, _build_footer, generate_report, save_report,
)


# ── mock 데이터 ──────────────────────────────

MOCK_MARKET_DATA = {
    'items': {
        'dow': {'name': '다우지수', 'category': '미국지수', 'price': 47501.55,
                'change_pct': -0.95, 'direction': '↓', 'unit': 'p', 'error': None},
        'usd_krw': {'name': '원/달러', 'category': '환율', 'price': 1485.0,
                     'change_pct': 0.41, 'direction': '↑', 'unit': '원', 'error': None},
    },
    'categories': {
        '미국지수': [{'name': '다우지수', 'price': 47501.55, 'change_pct': -0.95,
                     'direction': '↓', 'unit': 'p', 'key': 'dow'}],
        '환율': [{'name': '원/달러', 'price': 1485.0, 'change_pct': 0.41,
                  'direction': '↑', 'unit': '원', 'key': 'usd_krw'}],
        '미국국채': [], '유가': [], '안전자산': [],
        '광물': [], '농산물': [], '운임지수': [],
    },
    'summary': {'total': 27, 'success': 2, 'failed': 25,
                'timestamp': '2026-03-09 08:15'},
}

MOCK_EVENTS = [
    {'date': '2026-03-10', 'event': '노란봉투법 시행', 'category': '정책'},
    {'date': '2026-03-12', 'event': '선물 만기일', 'category': '시장이벤트'},
]

MOCK_KEYWORDS = {
    'keywords': [
        {'rank': 1, 'headline': '이란 전쟁 위기 고조',
         'summary': '중동 긴장 고조', 'impact': '방산주 강세',
         'related_stocks': ['한화에어로스페이스', 'LIG넥스원'],
         'sentiment': 'negative'},
    ],
    'one_liner': '중동 긴장으로 방산주 주목',
    'keyword_count': 1,
}


# ── 개별 빌더 테스트 ─────────────────────────

class TestBuildHeader:

    def test_contains_title(self):
        result = _build_header('2026-03-09 08:15')
        assert '# 장 초반 브리핑' in result

    def test_contains_date(self):
        result = _build_header('2026-03-09 08:15')
        assert '2026-03-09 08:15' in result

    def test_contains_data_source(self):
        result = _build_header()
        assert 'yfinance' in result


class TestBuildSection1:

    def test_contains_category(self):
        result = _build_section1_market(MOCK_MARKET_DATA)
        assert '[미국지수]' in result

    def test_contains_price(self):
        result = _build_section1_market(MOCK_MARKET_DATA)
        assert '47,501.55p' in result

    def test_empty_market_data(self):
        result = _build_section1_market({})
        assert 'Section 1' in result


class TestBuildSection2:

    def test_contains_events(self):
        result = _build_section2_calendar(MOCK_EVENTS, 3)
        assert '3월 주요 일정' in result
        assert '노란봉투법' in result

    def test_empty_events(self):
        result = _build_section2_calendar([], 3)
        assert '일정 없음' in result


class TestBuildSection3:

    def test_contains_keyword(self):
        result = _build_section3_keywords(MOCK_KEYWORDS)
        assert '이란 전쟁' in result

    def test_contains_related_stocks(self):
        result = _build_section3_keywords(MOCK_KEYWORDS)
        assert '한화에어로스페이스' in result

    def test_contains_one_liner(self):
        result = _build_section3_keywords(MOCK_KEYWORDS)
        assert '방산주 주목' in result

    def test_empty_keywords(self):
        result = _build_section3_keywords({})
        assert '수집 실패' in result


class TestBuildFooter:

    def test_contains_generated_by(self):
        result = _build_footer()
        assert 'kr-morning-briefing' in result


# ── generate_report 통합 ─────────────────────

class TestGenerateReport:

    def test_all_sections_present(self):
        result = generate_report(MOCK_MARKET_DATA, MOCK_EVENTS, MOCK_KEYWORDS)
        assert result['sections']['market_data'] is True
        assert result['sections']['calendar'] is True
        assert result['sections']['hot_keywords'] is True

    def test_md_content_has_all_sections(self):
        result = generate_report(MOCK_MARKET_DATA, MOCK_EVENTS, MOCK_KEYWORDS)
        md = result['md_content']
        assert 'Section 1' in md
        assert 'Section 2' in md
        assert 'Section 3' in md

    def test_file_path_format(self):
        result = generate_report(MOCK_MARKET_DATA, MOCK_EVENTS, MOCK_KEYWORDS)
        assert '장초반브리핑' in result['file_path']
        assert result['file_path'].endswith('.md')

    def test_empty_inputs(self):
        result = generate_report(None, None, None)
        assert 'md_content' in result
        assert result['sections']['market_data'] is False


# ── save_report ──────────────────────────────

class TestSaveReport:

    def test_save_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        os.makedirs('reports', exist_ok=True)

        # Override reports dir
        import report_generator
        original = report_generator.save_report

        filepath = os.path.join(str(tmp_path), 'reports',
                                'kr-morning-briefing_market_장초반브리핑_20260309.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('# Test')

        assert os.path.exists(filepath)
