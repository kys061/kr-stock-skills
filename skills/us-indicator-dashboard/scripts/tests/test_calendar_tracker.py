"""calendar_tracker.py 테스트."""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calendar_tracker import (
    IMPORTANCE_STARS, DEFAULT_RELEASE_PATTERNS,
    load_release_calendar, get_upcoming_releases,
    get_next_fomc, format_calendar_section,
)


class TestConstants:
    """상수 테스트."""

    def test_importance_stars(self):
        """중요도 별 매핑."""
        assert IMPORTANCE_STARS[5] == '★★★★★'
        assert IMPORTANCE_STARS[1] == '★'

    def test_default_patterns(self):
        """기본 패턴 15개."""
        assert len(DEFAULT_RELEASE_PATTERNS) == 15
        assert 'cpi' in DEFAULT_RELEASE_PATTERNS
        assert DEFAULT_RELEASE_PATTERNS['cpi']['importance'] == 5


class TestLoadCalendar:
    """캘린더 로드 테스트."""

    def test_load_release_calendar(self):
        """release_calendar.json 로드."""
        cal = load_release_calendar()
        assert isinstance(cal, dict)
        # 파일이 존재하면 2026-03 키가 있어야 함
        if cal:
            assert '2026-03' in cal or 'fomc_dates_2026' in cal


class TestGetUpcomingReleases:
    """향후 발표 일정 테스트."""

    def test_returns_list(self):
        """리스트 반환."""
        result = get_upcoming_releases(days=30)
        assert isinstance(result, list)

    def test_event_structure(self):
        """이벤트 구조 확인."""
        result = get_upcoming_releases(days=60)
        if result:
            evt = result[0]
            assert 'date' in evt
            assert 'indicator_id' in evt
            assert 'name_kr' in evt
            assert 'importance' in evt
            assert 'stars' in evt

    def test_sorted_by_date(self):
        """날짜순 정렬."""
        result = get_upcoming_releases(days=60)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i]['date'] <= result[i + 1]['date']

    def test_websearch_context_merge(self):
        """WebSearch 컨텍스트 병합."""
        # 미래 날짜로 테스트
        future = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        ctx = {
            'events': [{
                'date': future,
                'indicator': 'test_ind',
                'name': '테스트 지표',
                'forecast': '2.5%',
                'previous': '2.8%',
            }]
        }
        result = get_upcoming_releases(days=14, websearch_context=ctx)
        test_events = [e for e in result if e['indicator_id'] == 'test_ind']
        assert len(test_events) == 1
        assert test_events[0]['forecast'] == '2.5%'


class TestGetNextFomc:
    """FOMC 일정 테스트."""

    def test_next_fomc(self):
        """다음 FOMC."""
        result = get_next_fomc()
        assert 'date' in result
        assert 'days_until' in result
        assert 'label' in result

    def test_next_fomc_with_calendar(self):
        """캘린더 지정."""
        cal = {'fomc_dates_2026': ['2099-12-31']}
        result = get_next_fomc(cal)
        assert result['date'] == '2099-12-31'


class TestFormatCalendarSection:
    """포맷팅 테스트."""

    def test_empty_list(self):
        """빈 리스트."""
        output = format_calendar_section([])
        assert '향후 2주 발표 일정' in output
        assert '발표 일정이 없습니다' in output

    def test_with_events(self):
        """이벤트 포함."""
        events = [{
            'date': '2026-03-12',
            'indicator_id': 'cpi',
            'name_kr': 'CPI (2월)',
            'forecast': '2.8%',
            'previous': '2.9%',
            'importance': 5,
            'stars': '★★★★★',
            'source': 'BLS',
        }]
        output = format_calendar_section(events)
        assert '| 날짜 |' in output
        assert 'CPI (2월)' in output
        assert '★★★★★' in output
