"""monthly_calendar 단위 테스트."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monthly_calendar import (
    get_recurring_date, load_static_events,
    merge_events, format_calendar,
)


class TestGetRecurringDate:

    def test_3rd_friday_march_2026(self):
        result = get_recurring_date(2026, 3, '3rd_friday')
        assert result == '2026-03-20'

    def test_2nd_thursday_march_2026(self):
        result = get_recurring_date(2026, 3, '2nd_thursday')
        assert result == '2026-03-12'

    def test_1st_monday(self):
        result = get_recurring_date(2026, 3, '1st_monday')
        assert result == '2026-03-02'

    def test_invalid_rule(self):
        assert get_recurring_date(2026, 3, 'invalid') is None

    def test_5th_friday_may_not_exist(self):
        # 2026년 3월에는 5번째 금요일 없음
        result = get_recurring_date(2026, 3, '5th_friday')
        assert result is None


class TestLoadStaticEvents:

    def test_march_has_fomc(self):
        events = load_static_events(2026, 3)
        descriptions = [e['event'] for e in events]
        assert any('FOMC' in d for d in descriptions)

    def test_march_no_bok(self):
        events = load_static_events(2026, 3)
        descriptions = [e['event'] for e in events]
        assert not any('금통위' in d for d in descriptions)

    def test_march_has_quad_witching(self):
        events = load_static_events(2026, 3)
        descriptions = [e['event'] for e in events]
        assert any('동시만기' in d for d in descriptions)

    def test_march_has_special_events(self):
        events = load_static_events(2026, 3)
        descriptions = [e['event'] for e in events]
        assert any('인터배터리' in d for d in descriptions)

    def test_events_sorted_by_date(self):
        events = load_static_events(2026, 3)
        dates = [e['date'] for e in events]
        assert dates == sorted(dates)

    def test_all_events_have_required_keys(self):
        events = load_static_events(2026, 3)
        for e in events:
            assert 'date' in e
            assert 'event' in e
            assert 'category' in e
            assert 'source' in e

    def test_nonexistent_year(self):
        events = load_static_events(2099, 3)
        # recurring 이벤트는 있어야 함
        assert len(events) > 0


class TestMergeEvents:

    def test_static_only(self):
        static = [
            {'date': '2026-03-10', 'event': 'Event A', 'category': '정책', 'source': 'static'},
        ]
        result = merge_events(static, None)
        assert len(result) == 1

    def test_merge_dedup(self):
        static = [
            {'date': '2026-03-10', 'event': 'Event AAAA', 'category': '정책', 'source': 'static'},
        ]
        dynamic = [
            {'date': '2026-03-10', 'event': 'Event AAAA추가정보', 'category': '정책'},
        ]
        result = merge_events(static, dynamic)
        # 같은 날짜 + 앞 10글자 같으면 중복 제거
        assert len(result) == 1

    def test_merge_different_events(self):
        static = [
            {'date': '2026-03-10', 'event': 'Event A', 'category': '정책', 'source': 'static'},
        ]
        dynamic = [
            {'date': '2026-03-15', 'event': 'Event B', 'category': '산업'},
        ]
        result = merge_events(static, dynamic)
        assert len(result) == 2

    def test_sorted_output(self):
        static = [
            {'date': '2026-03-20', 'event': 'Late', 'category': '기타', 'source': 'static'},
        ]
        dynamic = [
            {'date': '2026-03-05', 'event': 'Early', 'category': '기타'},
        ]
        result = merge_events(static, dynamic)
        assert result[0]['date'] < result[1]['date']


class TestFormatCalendar:

    def test_basic_format(self):
        events = [
            {'date': '2026-03-10', 'event': 'Test Event', 'category': '정책'},
        ]
        result = format_calendar(events, 3)
        assert '3월 주요일정 체크리스트' in result
        assert '3/10 Test Event' in result

    def test_empty_events(self):
        result = format_calendar([], 3)
        assert '일정 없음' in result

    def test_day_zero_padding_removed(self):
        events = [
            {'date': '2026-03-05', 'event': 'Test', 'category': '기타'},
        ]
        result = format_calendar(events, 3)
        assert '3/5 Test' in result
