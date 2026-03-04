"""kr-market-breadth 단위 테스트.

네트워크 불필요 - 모든 테스트는 mock 데이터로 수행.
"""

import sys
import os
import json
import tempfile
import unittest

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from scorer import BreadthScorer, HEALTH_ZONES
from history_tracker import HistoryTracker
from report_generator import ReportGenerator


class TestBreadthScorer(unittest.TestCase):
    """스코어 계산 테스트."""

    def setUp(self):
        self.scorer = BreadthScorer()

    def test_weights_sum_to_one(self):
        """가중치 합계 = 1.0."""
        total = sum(self.scorer.WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_strong_breadth(self):
        """강세 시장폭 → 높은 점수."""
        data = {
            'breadth_raw': 75.0,
            'breadth_8ma': 72.0,
            'breadth_200ma': 55.0,
            'trend': 'up',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': False,
            'breadth_history': [60, 62, 65, 68, 70, 72, 75],
            'index_history': [2600, 2620, 2650],
        }
        result = self.scorer.score(data)
        self.assertGreaterEqual(result['composite_score'], 60)
        self.assertIn(result['health_zone'], ['Strong', 'Healthy'])

    def test_weak_breadth(self):
        """약세 시장폭 → 낮은 점수."""
        data = {
            'breadth_raw': 25.0,
            'breadth_8ma': 28.0,
            'breadth_200ma': 45.0,
            'trend': 'down',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': True,
            'breadth_history': [45, 40, 35, 30, 28, 25],
            'index_history': [2600, 2580, 2550],
        }
        result = self.scorer.score(data)
        self.assertLessEqual(result['composite_score'], 40)
        self.assertIn(result['health_zone'], ['Weakening', 'Critical'])

    def test_neutral_breadth(self):
        """중립 시장폭 → 중간 점수."""
        data = {
            'breadth_raw': 50.0,
            'breadth_8ma': 50.0,
            'breadth_200ma': 50.0,
            'trend': 'flat',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': False,
            'breadth_history': [48, 49, 50, 51, 50],
            'index_history': [2600, 2600],
        }
        result = self.scorer.score(data)
        self.assertGreaterEqual(result['composite_score'], 30)
        self.assertLessEqual(result['composite_score'], 70)

    def test_bearish_signal_penalty(self):
        """약세 신호 활성 시 bearish 컴포넌트 = 0."""
        data = {
            'breadth_raw': 35.0,
            'breadth_8ma': 35.0,
            'breadth_200ma': 50.0,
            'trend': 'down',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': True,
            'breadth_history': [35],
            'index_history': [2600],
        }
        result = self.scorer.score(data)
        self.assertEqual(result['components']['bearish']['score'], 0)

    def test_no_bearish_signal_bonus(self):
        """약세 신호 없을 때 bearish 컴포넌트 = 100."""
        data = {
            'breadth_raw': 65.0,
            'breadth_8ma': 65.0,
            'breadth_200ma': 55.0,
            'trend': 'up',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': False,
            'breadth_history': [65],
            'index_history': [2600],
        }
        result = self.scorer.score(data)
        self.assertEqual(result['components']['bearish']['score'], 100)

    def test_score_range(self):
        """종합 점수 0~100 범위."""
        for raw in [0, 25, 50, 75, 100]:
            data = {
                'breadth_raw': raw,
                'breadth_8ma': raw,
                'breadth_200ma': 50.0,
                'trend': 'flat',
                'is_peak': False,
                'is_trough': False,
                'bearish_signal': raw < 30,
                'breadth_history': [raw],
                'index_history': [2600],
            }
            result = self.scorer.score(data)
            self.assertGreaterEqual(result['composite_score'], 0)
            self.assertLessEqual(result['composite_score'], 100)

    def test_component_keys(self):
        """모든 6개 컴포넌트가 결과에 포함."""
        data = {
            'breadth_raw': 50.0, 'breadth_8ma': 50.0, 'breadth_200ma': 50.0,
            'trend': 'flat', 'is_peak': False, 'is_trough': False,
            'bearish_signal': False, 'breadth_history': [50], 'index_history': [2600],
        }
        result = self.scorer.score(data)
        expected_keys = {'breadth_level', 'crossover', 'cycle', 'bearish', 'percentile', 'divergence'}
        self.assertEqual(set(result['components'].keys()), expected_keys)

    def test_health_zones_coverage(self):
        """모든 Health Zone이 정의되어 있음."""
        self.assertEqual(len(HEALTH_ZONES), 5)
        # 0-100 전체 범위 커버
        ranges = [(low, high) for low, high, *_ in HEALTH_ZONES]
        self.assertEqual(ranges[0][0], 80)   # Strong starts at 80
        self.assertEqual(ranges[-1][0], 0)   # Critical starts at 0


class TestHistoryTracker(unittest.TestCase):
    """히스토리 관리 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.tmpdir, 'test_history.json')
        self.tracker = HistoryTracker(self.filepath)

    def test_empty_history(self):
        """비어있는 히스토리."""
        self.assertEqual(self.tracker.load(), [])

    def test_save_and_load(self):
        """저장 후 로드."""
        entry = {
            'date': '2026-02-27',
            'market': 'KOSPI200',
            'composite_score': 72.5,
            'breadth_raw': 65.0,
            'health_zone': 'Healthy',
        }
        self.tracker.save(entry)
        loaded = self.tracker.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['composite_score'], 72.5)

    def test_max_entries(self):
        """최대 엔트리 제한 (30개)."""
        for i in range(35):
            self.tracker.save({
                'date': f'2026-01-{i+1:02d}',
                'market': 'KOSPI200',
                'composite_score': 50 + i,
                'breadth_raw': 50 + i,
                'health_zone': 'Neutral',
            })
        loaded = self.tracker.load()
        self.assertLessEqual(len(loaded), 30)

    def test_trend_insufficient(self):
        """데이터 부족 시 insufficient."""
        self.assertEqual(self.tracker.get_trend(), 'insufficient')

    def test_trend_improving(self):
        """점수 상승 → improving."""
        for i, score in enumerate([50, 55, 60, 65, 70]):
            self.tracker.save({
                'date': f'2026-02-{20+i}',
                'market': 'KOSPI200',
                'composite_score': score,
                'breadth_raw': score,
                'health_zone': 'Neutral',
            })
        self.assertEqual(self.tracker.get_trend('KOSPI200'), 'improving')

    def test_trend_deteriorating(self):
        """점수 하락 → deteriorating."""
        for i, score in enumerate([70, 65, 60, 55, 50]):
            self.tracker.save({
                'date': f'2026-02-{20+i}',
                'market': 'KOSPI200',
                'composite_score': score,
                'breadth_raw': score,
                'health_zone': 'Neutral',
            })
        self.assertEqual(self.tracker.get_trend('KOSPI200'), 'deteriorating')

    def test_breadth_raw_history(self):
        """Breadth Raw 히스토리 추출."""
        for i, raw in enumerate([60, 62, 64]):
            self.tracker.save({
                'date': f'2026-02-{25+i}',
                'market': 'KOSPI200',
                'composite_score': 65,
                'breadth_raw': raw,
                'health_zone': 'Healthy',
            })
        history = self.tracker.get_breadth_raw_history('KOSPI200')
        self.assertEqual(history, [60, 62, 64])


class TestReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = ReportGenerator(self.tmpdir)

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        breadth_data = {
            'date': '2026-02-27',
            'market': 'KOSPI200',
            'breadth_raw': 65.0,
            'breadth_8ma': 63.0,
            'breadth_200ma': 55.0,
            'trend': 'up',
            'is_peak': False,
            'is_trough': False,
            'bearish_signal': False,
            'total_stocks': 200,
            'above_200ma': 130,
            'index_price': 2650.0,
        }
        score_data = {
            'composite_score': 72.5,
            'health_zone': 'Healthy',
            'health_zone_kr': '건강',
            'equity_exposure': '75-90%',
            'components': {
                'breadth_level': {'score': 80, 'weight': 0.25, 'weighted': 20.0, 'detail': '8MA=63.0'},
                'crossover': {'score': 70, 'weight': 0.20, 'weighted': 14.0, 'detail': '갭 +8'},
                'cycle': {'score': 70, 'weight': 0.20, 'weighted': 14.0, 'detail': '상승 구간'},
                'bearish': {'score': 100, 'weight': 0.15, 'weighted': 15.0, 'detail': '없음'},
                'percentile': {'score': 60, 'weight': 0.10, 'weighted': 6.0, 'detail': '상위 40%'},
                'divergence': {'score': 80, 'weight': 0.10, 'weighted': 8.0, 'detail': '확인'},
            },
            'strongest_component': 'bearish',
            'weakest_component': 'percentile',
        }

        paths = self.reporter.generate(breadth_data, score_data, 'improving')

        self.assertTrue(os.path.exists(paths['json_path']))
        self.assertTrue(os.path.exists(paths['md_path']))

        # JSON 내용 검증
        with open(paths['json_path'], 'r') as f:
            data = json.load(f)
        self.assertEqual(data['market'], 'KOSPI200')
        self.assertEqual(data['score']['composite_score'], 72.5)

        # MD 내용 검증
        with open(paths['md_path'], 'r') as f:
            md = f.read()
        self.assertIn('KOSPI200', md)
        self.assertIn('72.5', md)
        self.assertIn('Healthy', md)
        self.assertIn('75-90%', md)


class TestBreadthCalculatorUnit(unittest.TestCase):
    """BreadthCalculator 유틸리티 메서드 테스트."""

    def test_detect_peak(self):
        """고점 탐지."""
        import pandas as pd
        from breadth_calculator import BreadthCalculator

        # 고점: ..., 60, 65, 63 → True (65가 고점)
        series = pd.Series([50, 55, 60, 65, 63])
        self.assertTrue(BreadthCalculator._detect_peak(series))

        # 상승 중: ..., 60, 63, 65 → False
        series = pd.Series([50, 55, 60, 63, 65])
        self.assertFalse(BreadthCalculator._detect_peak(series))

    def test_detect_trough(self):
        """저점 탐지."""
        import pandas as pd
        from breadth_calculator import BreadthCalculator

        # 저점: ..., 40, 35, 38 → True (35가 저점)
        series = pd.Series([50, 45, 40, 35, 38])
        self.assertTrue(BreadthCalculator._detect_trough(series))

        # 하락 중: ..., 40, 38, 35 → False
        series = pd.Series([50, 45, 40, 38, 35])
        self.assertFalse(BreadthCalculator._detect_trough(series))

    def test_detect_with_short_series(self):
        """짧은 시리즈에서는 False."""
        import pandas as pd
        from breadth_calculator import BreadthCalculator

        series = pd.Series([50, 55])
        self.assertFalse(BreadthCalculator._detect_peak(series))
        self.assertFalse(BreadthCalculator._detect_trough(series))


if __name__ == '__main__':
    unittest.main()
