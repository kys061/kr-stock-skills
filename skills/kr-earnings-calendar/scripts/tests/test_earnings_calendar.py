"""kr-earnings-calendar 테스트 (~20 tests).

TestDartEarningsFetcher:    공시 조회 + 필터링 + 시간 분류
TestEarningsSeason:         월별 실적 시즌 매핑
TestReportGenerator:        JSON/Markdown 리포트 생성
TestConstants:              DART 코드 + 시총 필터 + 시즌맵 검증
TestCalendarOrchestrator:   메인 플로우 + 에러 처리
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dart_earnings_fetcher import (
    classify_disclosure_timing, get_current_earnings_season,
    filter_earnings_disclosures, _classify_report_type,
    DART_REPORT_CODES, CONFIRMED_CODES, PRELIMINARY_CODES,
    MARKET_CAP_MIN, LOOKBACK_DAYS, LOOKAHEAD_DAYS,
    EARNINGS_SEASON_MAP, MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR,
)
from report_generator import EarningsCalendarReportGenerator
from kr_earnings_calendar import run_earnings_calendar


# ═══════════════════════════════════════════════════════════
# 1. TestDartEarningsFetcher (5 tests)
# ═══════════════════════════════════════════════════════════
class TestDartEarningsFetcher(unittest.TestCase):
    """공시 조회 + 필터링 + 시간 분류."""

    def test_classify_before_open(self):
        """08:00 이전 → before_open."""
        disc = {'disclosure_time': '07:30:00'}
        self.assertEqual(classify_disclosure_timing(disc), 'before_open')

    def test_classify_during_market(self):
        """09:00 → during_market."""
        disc = {'disclosure_time': '09:00:00'}
        self.assertEqual(classify_disclosure_timing(disc), 'during_market')

    def test_classify_after_close(self):
        """16:00 → after_close."""
        disc = {'disclosure_time': '16:00:00'}
        self.assertEqual(classify_disclosure_timing(disc), 'after_close')

    def test_classify_market_close_boundary(self):
        """15:30 → after_close (장 마감 시간)."""
        disc = {'disclosure_time': '15:30:00'}
        self.assertEqual(classify_disclosure_timing(disc), 'after_close')

    def test_classify_unknown(self):
        """시간 없음 → unknown."""
        disc = {}
        self.assertEqual(classify_disclosure_timing(disc), 'unknown')


# ═══════════════════════════════════════════════════════════
# 2. TestEarningsSeason (4 tests)
# ═══════════════════════════════════════════════════════════
class TestEarningsSeason(unittest.TestCase):
    """월별 실적 시즌 매핑."""

    def test_january_4q_preliminary(self):
        """1월 = 4Q 잠정실적 시즌."""
        season = get_current_earnings_season(1)
        self.assertEqual(season['quarter'], '4Q')
        self.assertEqual(season['type'], 'preliminary')

    def test_march_4q_confirmed(self):
        """3월 = 4Q 확정실적 시즌."""
        season = get_current_earnings_season(3)
        self.assertEqual(season['quarter'], '4Q')
        self.assertEqual(season['type'], 'confirmed')

    def test_june_off_season(self):
        """6월 = 비시즌."""
        season = get_current_earnings_season(6)
        self.assertIsNone(season['quarter'])
        self.assertEqual(season['type'], 'off_season')

    def test_october_3q_preliminary(self):
        """10월 = 3Q 잠정실적 시즌."""
        season = get_current_earnings_season(10)
        self.assertEqual(season['quarter'], '3Q')
        self.assertEqual(season['type'], 'preliminary')


# ═══════════════════════════════════════════════════════════
# 3. TestReportGenerator (3 tests)
# ═══════════════════════════════════════════════════════════
class TestReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _sample_disclosures(self):
        return [
            {'date': '2026-01-15', 'ticker': '005930', 'name': '삼성전자',
             'report_code': 'D002', 'report_type': '영업(잠정)실적',
             'is_confirmed': False, 'is_preliminary': True,
             'market_cap': 400_000_000_000_000, 'timing': 'after_close'},
            {'date': '2026-01-16', 'ticker': '000660', 'name': 'SK하이닉스',
             'report_code': 'D002', 'report_type': '영업(잠정)실적',
             'is_confirmed': False, 'is_preliminary': True,
             'market_cap': 100_000_000_000_000, 'timing': 'during_market'},
        ]

    def test_json_report(self):
        gen = EarningsCalendarReportGenerator(self.tmpdir)
        path = gen.generate_json(self._sample_disclosures())
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-earnings-calendar')
        self.assertEqual(data['summary']['total'], 2)
        self.assertEqual(data['summary']['preliminary'], 2)

    def test_markdown_report(self):
        gen = EarningsCalendarReportGenerator(self.tmpdir)
        path = gen.generate_markdown(self._sample_disclosures())
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('한국 실적 캘린더 리포트', content)
        self.assertIn('삼성전자', content)

    def test_empty_report(self):
        gen = EarningsCalendarReportGenerator(self.tmpdir)
        path = gen.generate_markdown([])
        with open(path) as f:
            content = f.read()
        self.assertIn('공시가 없습니다', content)


# ═══════════════════════════════════════════════════════════
# 4. TestConstants (3 tests)
# ═══════════════════════════════════════════════════════════
class TestConstants(unittest.TestCase):
    """DART 코드 + 시총 필터 + 시즌맵 검증."""

    def test_dart_report_codes(self):
        """5개 DART 공시 코드 확인."""
        self.assertEqual(len(DART_REPORT_CODES), 5)
        self.assertEqual(DART_REPORT_CODES['annual'], 'A001')
        self.assertEqual(DART_REPORT_CODES['preliminary'], 'D002')

    def test_market_cap_min(self):
        """시총 필터 = 1조원."""
        self.assertEqual(MARKET_CAP_MIN, 1_000_000_000_000)

    def test_earnings_season_coverage(self):
        """실적 시즌 9개월 커버 확인 (6, 9, 12월 제외)."""
        self.assertEqual(len(EARNINGS_SEASON_MAP), 9)
        self.assertNotIn(6, EARNINGS_SEASON_MAP)
        self.assertNotIn(9, EARNINGS_SEASON_MAP)
        self.assertNotIn(12, EARNINGS_SEASON_MAP)


# ═══════════════════════════════════════════════════════════
# 5. TestCalendarOrchestrator (5 tests)
# ═══════════════════════════════════════════════════════════
class TestCalendarOrchestrator(unittest.TestCase):
    """메인 플로우 + 에러 처리."""

    def test_no_client_returns_error(self):
        """client=None → 에러 반환."""
        result = run_earnings_calendar(client=None)
        self.assertIn('error', result)
        self.assertEqual(result['summary']['total'], 0)

    def test_result_has_season(self):
        """결과에 시즌 정보 포함."""
        result = run_earnings_calendar(client=None)
        self.assertIn('season', result)
        self.assertIn('type', result['season'])

    def test_report_type_classification(self):
        """DART 코드 → 보고서 유형명 변환."""
        self.assertEqual(_classify_report_type('A001'), '사업보고서')
        self.assertEqual(_classify_report_type('D002'), '영업(잠정)실적')

    def test_confirmed_vs_preliminary_codes(self):
        """확정/잠정 코드 집합 분리."""
        self.assertEqual(CONFIRMED_CODES, {'A001', 'A002', 'A003'})
        self.assertEqual(PRELIMINARY_CODES, {'D001', 'D002'})
        # 교집합 없음
        self.assertEqual(len(CONFIRMED_CODES & PRELIMINARY_CODES), 0)

    def test_filter_empty_list(self):
        """빈 공시 목록 필터링 → 빈 결과."""
        result = filter_earnings_disclosures([], client=None)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
