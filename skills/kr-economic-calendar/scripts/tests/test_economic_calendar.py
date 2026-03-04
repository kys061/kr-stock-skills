"""kr-economic-calendar 테스트 (~15 tests).

TestEcosFetcher:       ECOS 코드 매핑 + 값 조회
TestStaticCalendar:    정적 캘린더 생성 + 월별 이벤트
TestImpactClassifier:  H/M/L 분류 검증
TestReportGenerator:   JSON/Markdown 리포트
TestConstants:         지표 목록 + 금통위 일정 검증
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ecos_fetcher import (
    build_static_calendar, get_upcoming_events, classify_impact,
    _nth_weekday_of_month,
    KR_INDICATORS, BOK_RATE_DECISION_MONTHS,
    IMPACT_HIGH, IMPACT_MEDIUM, IMPACT_LOW,
    DEFAULT_LOOKAHEAD_DAYS, MAX_LOOKAHEAD_DAYS,
    STATIC_RELEASE_DAYS, GDP_RELEASE_MONTHS, GDP_RELEASE_DAY,
    BOK_RATE_WEEK, BOK_RATE_WEEKDAY,
)
from report_generator import EconomicCalendarReportGenerator


# ═══════════════════════════════════════════════════════════
# 1. TestEcosFetcher (4 tests)
# ═══════════════════════════════════════════════════════════
class TestEcosFetcher(unittest.TestCase):
    """ECOS 코드 매핑 + API 테스트."""

    def test_indicator_count(self):
        """11개 경제지표 등록 확인."""
        self.assertEqual(len(KR_INDICATORS), 11)

    def test_all_indicators_have_code(self):
        """모든 지표에 ECOS 코드 존재."""
        for ind in KR_INDICATORS:
            self.assertIn('code', ind)
            self.assertTrue(len(ind['code']) > 0, f"{ind['name']} has empty code")

    def test_all_indicators_have_impact(self):
        """모든 지표에 임팩트 레벨 존재."""
        valid_impacts = {IMPACT_HIGH, IMPACT_MEDIUM, IMPACT_LOW}
        for ind in KR_INDICATORS:
            self.assertIn(ind['impact'], valid_impacts,
                          f"{ind['name']} has invalid impact: {ind['impact']}")

    def test_high_impact_count(self):
        """High Impact 지표 5개 확인."""
        high = [i for i in KR_INDICATORS if i['impact'] == IMPACT_HIGH]
        self.assertEqual(len(high), 5)


# ═══════════════════════════════════════════════════════════
# 2. TestStaticCalendar (4 tests)
# ═══════════════════════════════════════════════════════════
class TestStaticCalendar(unittest.TestCase):
    """정적 캘린더 생성 테스트."""

    def test_january_has_bok_rate(self):
        """1월 = 금통위 개최 월 → 금통위 이벤트 포함."""
        events = build_static_calendar(2026, 1)
        bok_events = [e for e in events if '금통위' in e['name']]
        self.assertEqual(len(bok_events), 1)
        self.assertEqual(bok_events[0]['impact'], IMPACT_HIGH)

    def test_march_no_bok_rate(self):
        """3월 = 금통위 미개최 월 → 금통위 이벤트 없음."""
        events = build_static_calendar(2026, 3)
        bok_events = [e for e in events if '금통위' in e['name']]
        self.assertEqual(len(bok_events), 0)

    def test_january_has_gdp(self):
        """1월 = GDP 발표 월 → GDP 이벤트 포함."""
        events = build_static_calendar(2026, 1)
        gdp_events = [e for e in events if 'GDP' in e['name']]
        self.assertEqual(len(gdp_events), 1)
        self.assertEqual(gdp_events[0]['date'], '2026-01-25')

    def test_february_no_gdp(self):
        """2월 = GDP 비발표 월."""
        events = build_static_calendar(2026, 2)
        gdp_events = [e for e in events if 'GDP' in e['name']]
        self.assertEqual(len(gdp_events), 0)


# ═══════════════════════════════════════════════════════════
# 3. TestImpactClassifier (3 tests)
# ═══════════════════════════════════════════════════════════
class TestImpactClassifier(unittest.TestCase):
    """임팩트 분류 테스트."""

    def test_high_impact(self):
        """기준금리 → H."""
        self.assertEqual(classify_impact('기준금리'), IMPACT_HIGH)

    def test_medium_impact(self):
        """산업생산지수 → M."""
        self.assertEqual(classify_impact('산업생산지수'), IMPACT_MEDIUM)

    def test_unknown_impact(self):
        """미등록 지표 → unknown."""
        self.assertEqual(classify_impact('없는지표'), 'unknown')


# ═══════════════════════════════════════════════════════════
# 4. TestReportGenerator (2 tests)
# ═══════════════════════════════════════════════════════════
class TestReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_json_report(self):
        events = [
            {'date': '2026-01-03', 'name': 'CPI', 'impact': 'H',
             'source': '통계청', 'frequency': 'monthly', 'code': '901Y009'},
        ]
        gen = EconomicCalendarReportGenerator(self.tmpdir)
        path = gen.generate_json(events)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-economic-calendar')
        self.assertEqual(data['summary']['high_impact'], 1)
        self.assertEqual(data['summary']['total'], 1)

    def test_markdown_report(self):
        events = [
            {'date': '2026-01-03', 'name': 'CPI', 'impact': 'H',
             'source': '통계청', 'frequency': 'monthly', 'code': '901Y009'},
        ]
        gen = EconomicCalendarReportGenerator(self.tmpdir)
        path = gen.generate_markdown(events)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('한국 경제 캘린더 리포트', content)
        self.assertIn('CPI', content)


# ═══════════════════════════════════════════════════════════
# 5. TestConstants (2 tests)
# ═══════════════════════════════════════════════════════════
class TestConstants(unittest.TestCase):
    """지표 목록 + 금통위 일정 검증."""

    def test_bok_rate_months(self):
        """금통위 8회/연 확인."""
        self.assertEqual(len(BOK_RATE_DECISION_MONTHS), 8)
        # 3, 6, 9, 12월은 미개최
        self.assertNotIn(3, BOK_RATE_DECISION_MONTHS)
        self.assertNotIn(6, BOK_RATE_DECISION_MONTHS)
        self.assertNotIn(9, BOK_RATE_DECISION_MONTHS)
        self.assertNotIn(12, BOK_RATE_DECISION_MONTHS)

    def test_lookahead_limits(self):
        """기본/최대 조회 기간 검증."""
        self.assertEqual(DEFAULT_LOOKAHEAD_DAYS, 7)
        self.assertEqual(MAX_LOOKAHEAD_DAYS, 90)


# ═══════════════════════════════════════════════════════════
# 6. TestUpcomingEvents (3 bonus tests)
# ═══════════════════════════════════════════════════════════
class TestUpcomingEvents(unittest.TestCase):
    """향후 이벤트 조회 테스트."""

    def test_get_upcoming_events_returns_list(self):
        """이벤트 목록 반환 확인."""
        base = datetime(2026, 1, 1)
        events = get_upcoming_events(days_ahead=31, base_date=base)
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

    def test_impact_filter(self):
        """임팩트 필터 적용 확인."""
        base = datetime(2026, 1, 1)
        events = get_upcoming_events(days_ahead=31, impact_filter=['H'],
                                     base_date=base)
        for ev in events:
            self.assertEqual(ev['impact'], 'H')

    def test_nth_weekday(self):
        """2026년 1월 둘째주 목요일 = 1/8."""
        day = _nth_weekday_of_month(2026, 1, 3, 2)  # 목(3), 둘째(2)
        self.assertEqual(day, 8)


if __name__ == '__main__':
    unittest.main()
