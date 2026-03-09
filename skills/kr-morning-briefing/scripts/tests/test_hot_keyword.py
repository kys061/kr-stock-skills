"""hot_keyword_analyzer 단위 테스트."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hot_keyword_analyzer import (
    THEME_STOCK_MAP, KEYWORD_THEME_HINTS,
    map_related_stocks, extract_keywords_from_news,
    analyze_hot_keywords,
)


class TestThemeStockMap:

    def test_theme_count(self):
        assert len(THEME_STOCK_MAP) == 10

    def test_each_theme_has_stocks(self):
        for theme, stocks in THEME_STOCK_MAP.items():
            assert len(stocks) >= 3, f"{theme}: only {len(stocks)} stocks"


class TestMapRelatedStocks:

    def test_direct_theme(self):
        result = map_related_stocks('', '방산')
        assert '한화에어로스페이스' in result
        assert len(result) == 4

    def test_keyword_hint(self):
        result = map_related_stocks('이란 전쟁 위기 고조', '')
        assert '한화에어로스페이스' in result

    def test_ai_keyword(self):
        result = map_related_stocks('AI 반도체 수요 폭증', '')
        assert 'SK하이닉스' in result

    def test_unknown_keyword(self):
        result = map_related_stocks('알 수 없는 카테고리', '')
        assert result == []


class TestExtractKeywords:

    def test_empty_headlines(self):
        assert extract_keywords_from_news([]) == []

    def test_basic_extraction(self):
        headlines = [
            '이란 전쟁 위기 고조로 방산주 강세',
            'AI 반도체 수요 폭증 전망',
            '금리 동결 예상에 은행주 약세',
        ]
        result = extract_keywords_from_news(headlines, max_keywords=3)
        assert len(result) <= 3
        for kw in result:
            assert 'headline' in kw
            assert 'category' in kw

    def test_dedup_headlines(self):
        headlines = ['같은 뉴스', '같은 뉴스', '다른 뉴스']
        result = extract_keywords_from_news(headlines, max_keywords=3)
        assert len(result) == 2

    def test_max_keywords_limit(self):
        headlines = [f'뉴스 {i}' for i in range(10)]
        result = extract_keywords_from_news(headlines, max_keywords=2)
        assert len(result) <= 2


class TestAnalyzeHotKeywords:

    def test_empty_context(self):
        result = analyze_hot_keywords(None)
        assert result['keyword_count'] == 0
        assert result['keywords'] == []
        assert result['one_liner'] == ''

    def test_structured_context(self):
        ctx = {
            'keywords': [
                {'headline': '이란 전쟁', 'summary': '요약', 'impact': '방산주 강세'},
            ],
            'one_liner': '테스트 한줄평',
        }
        result = analyze_hot_keywords(ctx)
        assert result['keyword_count'] == 1
        assert result['one_liner'] == '테스트 한줄평'
        assert result['keywords'][0]['rank'] == 1

    def test_headlines_context(self):
        ctx = {
            'headlines': [
                '이란 전쟁 위기 고조',
                'AI 반도체 급등',
            ],
        }
        result = analyze_hot_keywords(ctx)
        assert result['keyword_count'] >= 1
        assert len(result['keywords']) >= 1

    def test_structured_adds_related_stocks(self):
        ctx = {
            'keywords': [
                {'headline': 'AI 반도체 수요 폭증', 'category': 'AI반도체'},
            ],
        }
        result = analyze_hot_keywords(ctx)
        stocks = result['keywords'][0]['related_stocks']
        assert len(stocks) > 0
