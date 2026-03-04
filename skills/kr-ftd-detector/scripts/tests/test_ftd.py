"""
kr-ftd-detector 테스트.
상태 머신 + FTD 자격 + 품질 점수 + PostFTD 모니터 + 리포트.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rally_tracker import RallyTracker, RallyState
from ftd_qualifier import (
    FTDQualifier,
    QUALITY_WEIGHTS,
    EXPOSURE_LEVELS,
    FTD_MIN_GAIN,
    FTD_WINDOW_START,
    FTD_WINDOW_END,
    score_volume_surge,
    score_day_number,
    score_gain_size,
    score_breadth_confirmation,
    score_foreign_flow,
    get_exposure_level,
)
from post_ftd_monitor import PostFTDMonitor
from report_generator import ReportGenerator


# ── RallyState 테스트 ───────────────────────────────

class TestRallyState(unittest.TestCase):

    def test_enum_values(self):
        """7개 상태 존재."""
        states = list(RallyState)
        self.assertEqual(len(states), 7)

    def test_initial_state(self):
        """초기 상태 = NO_SIGNAL."""
        tracker = RallyTracker('KOSPI')
        self.assertEqual(tracker.state, RallyState.NO_SIGNAL)

    def test_index_name(self):
        """지수명 설정."""
        tracker = RallyTracker('KOSDAQ')
        self.assertEqual(tracker.index_name, 'KOSDAQ')


# ── RallyTracker 상태 전이 테스트 ────────────────────

class TestRallyTracker(unittest.TestCase):

    def test_correction_detection(self):
        """3%+ 하락, 3일 이상 → CORRECTION."""
        tracker = RallyTracker('KOSPI')
        # 시작: 2800
        tracker.correction_start = 2800
        # Day 1: -1.5%
        tracker.update('2026-01-02', 2758, 2800)
        # Day 2: -1.0%
        tracker.update('2026-01-03', 2730, 2758)
        # Day 3: -1.0% → 총 -3.6%
        tracker.update('2026-01-04', 2703, 2730)
        self.assertEqual(tracker.state, RallyState.CORRECTION)

    def test_rally_attempt_on_bounce(self):
        """조정 후 반등 → RALLY_ATTEMPT."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.CORRECTION
        tracker.swing_low = 2700
        tracker.swing_low_date = '2026-01-04'
        # 반등일
        tracker.update('2026-01-05', 2720, 2700)
        self.assertEqual(tracker.state, RallyState.RALLY_ATTEMPT)
        self.assertEqual(tracker.rally_day, 1)

    def test_rally_attempt_to_ftd_window(self):
        """Day 4 → FTD_WINDOW."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.RALLY_ATTEMPT
        tracker.swing_low = 2700
        tracker.rally_day = 3  # 이미 Day 3까지 진행
        # Day 4 진입
        tracker.update('2026-01-08', 2750, 2740, 100, 90)
        self.assertEqual(tracker.state, RallyState.FTD_WINDOW)

    def test_ftd_confirmed(self):
        """FTD 자격 조건 충족 → FTD_CONFIRMED."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.FTD_WINDOW
        tracker.swing_low = 2700
        tracker.rally_day = 4
        # +2% 상승, 거래량 증가
        close = 2800
        prev_close = 2745  # (2800-2745)/2745 ≈ +2.0%
        tracker.update('2026-01-09', close, prev_close, 1500000, 1000000)
        self.assertEqual(tracker.state, RallyState.FTD_CONFIRMED)
        self.assertEqual(tracker.ftd_close, 2800)

    def test_rally_failed_swing_low_break(self):
        """스윙 로우 이탈 → RALLY_FAILED."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.RALLY_ATTEMPT
        tracker.swing_low = 2700
        tracker.rally_day = 2
        # 스윙 로우 하회
        tracker.update('2026-01-07', 2690, 2720)
        self.assertEqual(tracker.state, RallyState.RALLY_FAILED)

    def test_ftd_window_timeout(self):
        """Day 11+ → RALLY_FAILED."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.FTD_WINDOW
        tracker.swing_low = 2700
        tracker.rally_day = 10  # 이미 Day 10
        # Day 11 → 타임아웃 (+0.5% but too late)
        tracker.update('2026-01-20', 2780, 2766, 1200000, 1000000)
        self.assertEqual(tracker.state, RallyState.RALLY_FAILED)

    def test_ftd_invalidated(self):
        """FTD 종가 하회 → FTD_INVALIDATED."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.FTD_CONFIRMED
        tracker.ftd_close = 2800
        # FTD 종가 하회
        tracker.update('2026-01-15', 2780, 2810)
        self.assertEqual(tracker.state, RallyState.FTD_INVALIDATED)

    def test_get_state(self):
        """get_state() 필수 키 포함."""
        tracker = RallyTracker('KOSPI')
        state = tracker.get_state()
        required_keys = ['index_name', 'state', 'swing_low', 'rally_day',
                         'ftd_close', 'history']
        for key in required_keys:
            self.assertIn(key, state)

    def test_reset(self):
        """reset() 후 초기 상태."""
        tracker = RallyTracker('KOSPI')
        tracker.state = RallyState.FTD_CONFIRMED
        tracker.swing_low = 2700
        tracker.rally_day = 5
        tracker.reset()
        self.assertEqual(tracker.state, RallyState.NO_SIGNAL)
        self.assertIsNone(tracker.swing_low)
        self.assertEqual(tracker.rally_day, 0)


# ── FTD Qualifier 컴포넌트 테스트 ───────────────────

class TestVolumeScoring(unittest.TestCase):

    def test_below_threshold(self):
        self.assertEqual(score_volume_surge(0.8), 0.0)

    def test_moderate(self):
        self.assertEqual(score_volume_surge(1.3), 50.0)

    def test_high(self):
        self.assertEqual(score_volume_surge(1.8), 70.0)

    def test_extreme(self):
        self.assertGreaterEqual(score_volume_surge(2.5), 90.0)


class TestDayNumberScoring(unittest.TestCase):

    def test_day_4_best(self):
        self.assertEqual(score_day_number(4), 100.0)

    def test_day_7_moderate(self):
        self.assertEqual(score_day_number(7), 65.0)

    def test_day_10_worst(self):
        self.assertEqual(score_day_number(10), 20.0)

    def test_out_of_range(self):
        self.assertEqual(score_day_number(15), 0.0)


class TestGainScoring(unittest.TestCase):

    def test_below_minimum(self):
        self.assertEqual(score_gain_size(0.01), 0.0)

    def test_minimum(self):
        self.assertEqual(score_gain_size(0.015), 40.0)

    def test_large_gain(self):
        self.assertEqual(score_gain_size(0.04), 100.0)


class TestBreadthConfirmation(unittest.TestCase):

    def test_strong_improvement(self):
        self.assertGreaterEqual(score_breadth_confirmation(0.06), 80.0)

    def test_no_change(self):
        result = score_breadth_confirmation(0.0)
        self.assertGreater(result, 0)

    def test_deterioration(self):
        self.assertLessEqual(score_breadth_confirmation(-0.05), 20.0)


class TestForeignFlow(unittest.TestCase):

    def test_strong_reversal(self):
        """순매도에서 2일 연속 순매수 전환."""
        score = score_foreign_flow(100.0, 50.0, True)
        self.assertGreaterEqual(score, 90.0)

    def test_single_day_reversal(self):
        """당일만 순매수 전환."""
        score = score_foreign_flow(100.0, -50.0, True)
        self.assertGreaterEqual(score, 60.0)

    def test_continued_selling(self):
        """순매도 지속."""
        score = score_foreign_flow(-100.0, -50.0, True)
        self.assertLessEqual(score, 20.0)


# ── FTDQualifier 통합 테스트 ────────────────────────

class TestFTDQualifier(unittest.TestCase):

    def setUp(self):
        self.qualifier = FTDQualifier()

    def test_valid_ftd(self):
        """유효한 FTD → is_ftd=True."""
        result = self.qualifier.qualify(
            rally_day=5, daily_return=0.02, volume_ratio=1.5,
            breadth_change=0.03, foreign_net_today=100,
            foreign_net_yesterday=-50, was_selling=True)
        self.assertTrue(result['is_ftd'])
        self.assertGreater(result['quality_score'], 0)

    def test_invalid_day(self):
        """Day 3 → is_ftd=False."""
        result = self.qualifier.qualify(
            rally_day=3, daily_return=0.02, volume_ratio=1.5)
        self.assertFalse(result['is_ftd'])

    def test_invalid_gain(self):
        """상승률 미달 → is_ftd=False."""
        result = self.qualifier.qualify(
            rally_day=5, daily_return=0.01, volume_ratio=1.5)
        self.assertFalse(result['is_ftd'])

    def test_invalid_volume(self):
        """거래량 감소 → is_ftd=False."""
        result = self.qualifier.qualify(
            rally_day=5, daily_return=0.02, volume_ratio=0.8)
        self.assertFalse(result['is_ftd'])

    def test_quality_range(self):
        """품질 점수 0-100 범위."""
        result = self.qualifier.qualify(
            rally_day=4, daily_return=0.04, volume_ratio=2.5,
            breadth_change=0.06, foreign_net_today=200,
            foreign_net_yesterday=100, was_selling=True)
        self.assertTrue(result['is_ftd'])
        self.assertGreaterEqual(result['quality_score'], 0)
        self.assertLessEqual(result['quality_score'], 100)

    def test_exposure_mapping(self):
        """노출 수준 매핑."""
        result = self.qualifier.qualify(
            rally_day=4, daily_return=0.04, volume_ratio=2.5,
            breadth_change=0.06, foreign_net_today=200,
            foreign_net_yesterday=100, was_selling=True)
        self.assertIn('name', result['exposure'])
        self.assertIn('exposure', result['exposure'])


# ── PostFTDMonitor 테스트 ───────────────────────────

class TestPostFTDMonitor(unittest.TestCase):

    def test_healthy_state(self):
        """정상 상태."""
        monitor = PostFTDMonitor(ftd_close=2800, swing_low=2700)
        result = monitor.check(2820, 2800, 100, 90)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['health'], 'healthy')

    def test_ftd_close_break(self):
        """FTD 종가 하회 → 무효화."""
        monitor = PostFTDMonitor(ftd_close=2800, swing_low=2700)
        result = monitor.check(2780, 2810, 100, 90)
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['invalidation_reason'], 'ftd_close_broken')

    def test_swing_low_break(self):
        """스윙 로우 이탈 → 무효화 (ftd_close는 유지하면서 swing_low만 이탈)."""
        monitor = PostFTDMonitor(ftd_close=2650, swing_low=2700)
        result = monitor.check(2690, 2750, 100, 90)
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['invalidation_reason'], 'swing_low_broken')

    def test_excessive_distribution(self):
        """분배일 3일 → 무효화."""
        monitor = PostFTDMonitor(ftd_close=2800, swing_low=2700)
        # 3번의 분배일 (하락 + 거래량 증가)
        monitor.check(2802, 2810, 120, 100)  # dist day 1: -0.9%
        monitor.check(2805, 2815, 130, 110)  # dist day 2: -0.35%
        result = monitor.check(2808, 2820, 140, 120)  # dist day 3: -0.42%
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['invalidation_reason'], 'excessive_distribution')

    def test_warning_state(self):
        """분배일 2일 → warning."""
        monitor = PostFTDMonitor(ftd_close=2800, swing_low=2700)
        monitor.check(2802, 2810, 120, 100)  # dist day 1
        result = monitor.check(2805, 2815, 130, 110)  # dist day 2
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['health'], 'warning')


# ── Exposure Level 테스트 ────────────────────────────

class TestExposureLevel(unittest.TestCase):

    def test_strong(self):
        level = get_exposure_level(85)
        self.assertEqual(level['name'], 'Strong FTD')

    def test_moderate(self):
        level = get_exposure_level(70)
        self.assertEqual(level['name'], 'Moderate FTD')

    def test_weak(self):
        level = get_exposure_level(45)
        self.assertEqual(level['name'], 'Weak FTD')

    def test_no_ftd(self):
        level = get_exposure_level(20)
        self.assertEqual(level['name'], 'No FTD')


# ── 가중치/상수 검증 ──────────────────────────────

class TestConstants(unittest.TestCase):

    def test_weights_sum_to_1(self):
        """가중치 합계 = 1.0."""
        total = sum(QUALITY_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_five_components(self):
        """5개 컴포넌트."""
        self.assertEqual(len(QUALITY_WEIGHTS), 5)

    def test_ftd_window(self):
        """FTD 윈도우 Day 4-10."""
        self.assertEqual(FTD_WINDOW_START, 4)
        self.assertEqual(FTD_WINDOW_END, 10)

    def test_min_gain(self):
        """최소 상승률 1.5%."""
        self.assertEqual(FTD_MIN_GAIN, 0.015)

    def test_exposure_levels_count(self):
        """4개 노출 수준."""
        self.assertEqual(len(EXPOSURE_LEVELS), 4)


# ── 이중 추적 테스트 ────────────────────────────────

class TestDualIndexTracking(unittest.TestCase):

    def test_independent_trackers(self):
        """KOSPI/KOSDAQ 독립 추적."""
        kospi = RallyTracker('KOSPI')
        kosdaq = RallyTracker('KOSDAQ')
        self.assertNotEqual(id(kospi), id(kosdaq))
        self.assertEqual(kospi.index_name, 'KOSPI')
        self.assertEqual(kosdaq.index_name, 'KOSDAQ')

    def test_separate_state(self):
        """상태가 독립적."""
        kospi = RallyTracker('KOSPI')
        kosdaq = RallyTracker('KOSDAQ')
        kospi.state = RallyState.CORRECTION
        self.assertEqual(kospi.state, RallyState.CORRECTION)
        self.assertEqual(kosdaq.state, RallyState.NO_SIGNAL)


# ── 리포트 생성 테스트 ──────────────────────────────

class TestReportGenerator(unittest.TestCase):

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'kospi': {'state': 'ftd_confirmed', 'rally_day': 5, 'swing_low': 2700},
                'kosdaq': {'state': 'rally_attempt', 'rally_day': 3, 'swing_low': 850},
                'ftd_result': {
                    'is_ftd': True,
                    'quality_score': 72.5,
                    'components': {
                        'volume_surge': 70, 'day_number': 90,
                        'gain_size': 60, 'breadth_confirmation': 60,
                        'foreign_flow': 70,
                    },
                    'exposure': {'name': 'Moderate FTD', 'exposure': '50-75%'},
                },
                'dual_ftd': False,
            }
            output = reporter.generate(result)
            self.assertTrue(os.path.exists(output['json_path']))
            self.assertTrue(os.path.exists(output['md_path']))

            with open(output['json_path'], 'r') as f:
                data = json.load(f)
            self.assertTrue(data['is_ftd'])
            self.assertAlmostEqual(data['quality_score'], 72.5)

    def test_md_contains_sections(self):
        """Markdown에 핵심 섹션."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'kospi': {'state': 'no_signal', 'rally_day': 0, 'swing_low': None},
                'kosdaq': {'state': 'no_signal', 'rally_day': 0, 'swing_low': None},
                'ftd_result': None,
                'dual_ftd': False,
            }
            output = reporter.generate(result)
            md = output['md_content']
            self.assertIn('종합 결과', md)
            self.assertIn('지수별 상태', md)
            self.assertIn('노출 가이드', md)


if __name__ == '__main__':
    unittest.main()
