"""Tests for kr-news-tone-analyzer tone_classifier.py

Test coverage:
  TestClassifyHeadline (8): fear_ko, fear_en, stable_ko, stable_en, neutral_ko,
                            neutral_default, mixed_tiebreak, multi_keyword
  TestClassifyHeadlines (3): normal, string_list, empty
  TestCalculateToneRatio (4): normal, all_fear, all_stable, empty
  TestJudgeTransition (4): stable, transitioning, fear, edge_case
  TestAnalyzeNewsTone (2): demo, minimal
  TestLoadToneKeywords (2): existing, missing
  Total: 23 tests
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tone_classifier import (
    classify_headline,
    classify_headlines,
    calculate_tone_ratio,
    judge_transition,
    analyze_news_tone,
    load_tone_keywords,
    TONE_LABEL_KO,
    DEMO_HEADLINES,
)


# ---------------------------------------------------------------------------
# TestClassifyHeadline
# ---------------------------------------------------------------------------

class TestClassifyHeadline:
    """T-01 ~ T-08: Single headline classification tests."""

    def test_fear_korean(self):
        """T-01: Korean fear headline → fear."""
        result = classify_headline("코스피 역대급 폭락, 서킷브레이커 발동")
        assert result['tone'] == 'fear'
        assert '폭락' in result['matched_keywords'] or '서킷브레이커' in result['matched_keywords']

    def test_fear_english(self):
        """T-02: English fear headline → fear."""
        result = classify_headline("Panic Sweeps South Korea Stocks in Crash")
        assert result['tone'] == 'fear'

    def test_stable_korean(self):
        """T-03: Korean stable headline → stable."""
        result = classify_headline("코스피 역대급 반등, 외국인 순매수 전환")
        assert result['tone'] == 'stable'

    def test_stable_english(self):
        """T-04: English stable headline → stable."""
        result = classify_headline("KOSPI soars 12% in historic rebound rally")
        assert result['tone'] == 'stable'

    def test_neutral_korean(self):
        """T-05: Korean neutral headline → neutral."""
        result = classify_headline("코스피 보합 마감, 혼조세 지속")
        assert result['tone'] == 'neutral'

    def test_neutral_default(self):
        """T-06: No keyword match → neutral (default)."""
        result = classify_headline("삼성전자 신제품 발표")
        assert result['tone'] == 'neutral'
        assert result['confidence'] == 'low'

    def test_mixed_tiebreak(self):
        """T-07: Mixed keywords → first-position tiebreak."""
        # "반등" (stable) comes before "급락" (fear) in this headline
        result = classify_headline("반등 후 다시 급락한 코스피")
        assert result['tone'] == 'stable'  # "반등" appears first

    def test_multi_keyword_confidence(self):
        """T-08: Multiple matching keywords → high confidence."""
        result = classify_headline("코스피 폭락 패닉 서킷브레이커 발동 위기")
        assert result['tone'] == 'fear'
        assert result['confidence'] == 'high'
        assert len(result['matched_keywords']) >= 2


# ---------------------------------------------------------------------------
# TestClassifyHeadlines
# ---------------------------------------------------------------------------

class TestClassifyHeadlines:
    """T-09 ~ T-11: Multiple headline classification tests."""

    def test_normal(self):
        """T-09: Classify list of headline dicts."""
        headlines = [
            {'headline': '코스피 폭락', 'source': '한경'},
            {'headline': 'KOSPI rebounds strongly', 'source': 'CNBC'},
        ]
        results = classify_headlines(headlines)
        assert len(results) == 2
        assert results[0]['tone'] == 'fear'
        assert results[1]['tone'] == 'stable'

    def test_string_list(self):
        """T-10: Classify list of plain strings."""
        results = classify_headlines(["시장 폭락", "반등 기대감"])
        assert len(results) == 2
        assert results[0]['source'] == ''

    def test_empty(self):
        """T-11: Empty list returns empty."""
        results = classify_headlines([])
        assert results == []


# ---------------------------------------------------------------------------
# TestCalculateToneRatio
# ---------------------------------------------------------------------------

class TestCalculateToneRatio:
    """T-12 ~ T-15: Tone ratio calculation tests."""

    def test_normal(self):
        """T-12: Normal ratio calculation."""
        classified = [
            {'tone': 'fear'}, {'tone': 'fear'},
            {'tone': 'stable'}, {'tone': 'stable'}, {'tone': 'stable'},
            {'tone': 'neutral'},
        ]
        ratio = calculate_tone_ratio(classified)
        assert ratio['total'] == 6
        assert ratio['fear']['count'] == 2
        assert ratio['stable']['count'] == 3
        assert ratio['neutral']['count'] == 1
        assert abs(ratio['fear']['pct'] - 33.3) < 0.5

    def test_all_fear(self):
        """T-13: 100% fear."""
        classified = [{'tone': 'fear'}] * 5
        ratio = calculate_tone_ratio(classified)
        assert ratio['fear']['pct'] == 100.0
        assert ratio['stable']['pct'] == 0.0

    def test_all_stable(self):
        """T-14: 100% stable."""
        classified = [{'tone': 'stable'}] * 4
        ratio = calculate_tone_ratio(classified)
        assert ratio['stable']['pct'] == 100.0

    def test_empty(self):
        """T-15: Empty list → zero counts."""
        ratio = calculate_tone_ratio([])
        assert ratio['total'] == 0
        assert ratio['fear']['pct'] == 0


# ---------------------------------------------------------------------------
# TestJudgeTransition
# ---------------------------------------------------------------------------

class TestJudgeTransition:
    """T-16 ~ T-19: Transition judgment tests."""

    def test_stable(self):
        """T-16: stable ≥ 70% & fear < 20% → 안정."""
        ratio = {
            'fear': {'count': 1, 'pct': 10},
            'neutral': {'count': 1, 'pct': 10},
            'stable': {'count': 8, 'pct': 80},
            'total': 10,
        }
        result = judge_transition(ratio)
        assert result['status'] == 'stable'
        assert result['label_ko'] == '안정'

    def test_transitioning(self):
        """T-17: stable ≥ 50% but fear ≥ 20% → 전환 중."""
        ratio = {
            'fear': {'count': 4, 'pct': 40},
            'neutral': {'count': 0, 'pct': 0},
            'stable': {'count': 6, 'pct': 60},
            'total': 10,
        }
        result = judge_transition(ratio)
        assert result['status'] == 'transitioning'
        assert result['label_ko'] == '전환 중'

    def test_fear(self):
        """T-18: stable < 50% → 공포."""
        ratio = {
            'fear': {'count': 6, 'pct': 60},
            'neutral': {'count': 2, 'pct': 20},
            'stable': {'count': 2, 'pct': 20},
            'total': 10,
        }
        result = judge_transition(ratio)
        assert result['status'] == 'fear'
        assert result['label_ko'] == '공포'

    def test_edge_70_20(self):
        """T-19: Exactly 70% stable, 20% fear → transitioning (fear not < 20)."""
        ratio = {
            'fear': {'count': 2, 'pct': 20},
            'neutral': {'count': 1, 'pct': 10},
            'stable': {'count': 7, 'pct': 70},
            'total': 10,
        }
        result = judge_transition(ratio)
        # stable >= 70% BUT fear = 20% (not < 20%) → transitioning
        assert result['status'] == 'transitioning'


# ---------------------------------------------------------------------------
# TestAnalyzeNewsTone
# ---------------------------------------------------------------------------

class TestAnalyzeNewsTone:
    """T-20 ~ T-21: Full analysis pipeline tests."""

    def test_demo_headlines(self):
        """T-20: Demo headlines produce valid analysis."""
        analysis = analyze_news_tone(DEMO_HEADLINES)
        assert 'classified' in analysis
        assert 'tone_ratio' in analysis
        assert 'transition' in analysis
        assert 'summary' in analysis
        assert analysis['tone_ratio']['total'] == len(DEMO_HEADLINES)
        assert analysis['transition']['status'] in ('fear', 'transitioning', 'stable')

    def test_minimal(self):
        """T-21: Single headline analysis works."""
        analysis = analyze_news_tone([{'headline': '코스피 반등', 'source': 'test'}])
        assert analysis['tone_ratio']['total'] == 1
        assert analysis['tone_ratio']['stable']['count'] == 1


# ---------------------------------------------------------------------------
# TestLoadToneKeywords
# ---------------------------------------------------------------------------

class TestLoadToneKeywords:
    """T-22 ~ T-23: Keyword loading tests."""

    def test_load_existing(self):
        """T-22: Load actual tone_keywords.json from references/."""
        keywords = load_tone_keywords()
        assert isinstance(keywords, dict)
        assert 'fear' in keywords
        assert 'neutral' in keywords
        assert 'stable' in keywords
        assert len(keywords['fear']['ko']) >= 5

    def test_load_missing(self, tmp_path, monkeypatch):
        """T-23: Missing file returns default keywords."""
        import tone_classifier as mod
        monkeypatch.setattr(mod, '_KEYWORDS_PATH', str(tmp_path / 'nonexistent.json'))
        result = mod.load_tone_keywords()
        assert 'fear' in result
        assert 'stable' in result
