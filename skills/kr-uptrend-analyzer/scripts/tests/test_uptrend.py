"""kr-uptrend-analyzer 단위 테스트.

네트워크 불필요 - 모든 테스트는 mock 데이터로 수행.
"""

import sys
import os
import json
import tempfile
import unittest

import pandas as pd
import numpy as np

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from uptrend_calculator import (
    UptrendCalculator, is_uptrend, is_above_50ma,
    KR_SECTOR_GROUPS, SECTOR_TO_GROUP,
)
from scorer import UptrendScorer, WEIGHTS, UPTREND_ZONES, WARNINGS
from history_tracker import HistoryTracker
from report_generator import ReportGenerator


class TestIsUptrend(unittest.TestCase):
    """is_uptrend() 판정 테스트."""

    def _make_ohlcv(self, prices: list) -> pd.DataFrame:
        """테스트용 OHLCV DataFrame 생성."""
        return pd.DataFrame({
            '시가': prices,
            '고가': prices,
            '저가': prices,
            '종가': prices,
            '거래량': [1000] * len(prices),
        })

    def test_uptrend_rising(self):
        """상승 추세 → True."""
        # 200일 이상, 상승하는 가격
        prices = list(range(100, 350))  # 100~349 (250일)
        df = self._make_ohlcv(prices)
        self.assertTrue(is_uptrend(df))

    def test_downtrend(self):
        """하락 추세 → False."""
        prices = list(range(350, 100, -1))  # 350~101 (250일)
        df = self._make_ohlcv(prices)
        self.assertFalse(is_uptrend(df))

    def test_too_short(self):
        """데이터 부족 → False."""
        prices = list(range(100, 200))  # 100일
        df = self._make_ohlcv(prices)
        self.assertFalse(is_uptrend(df))

    def test_none_input(self):
        """None 입력 → False."""
        self.assertFalse(is_uptrend(None))

    def test_flat_below_sma(self):
        """횡보 후 SMA 아래 → False."""
        # SMA200 위에 있다가 급락
        prices = [100] * 200 + [50] * 50  # 250일
        df = self._make_ohlcv(prices)
        self.assertFalse(is_uptrend(df))


class TestIsAbove50MA(unittest.TestCase):
    """is_above_50ma() 테스트."""

    def _make_ohlcv(self, prices: list) -> pd.DataFrame:
        return pd.DataFrame({
            '시가': prices, '고가': prices, '저가': prices,
            '종가': prices, '거래량': [1000] * len(prices),
        })

    def test_above(self):
        """상승 → True."""
        prices = list(range(100, 200))  # 100일
        self.assertTrue(is_above_50ma(self._make_ohlcv(prices)))

    def test_below(self):
        """하락 → False."""
        prices = list(range(200, 100, -1))  # 100일
        self.assertFalse(is_above_50ma(self._make_ohlcv(prices)))

    def test_too_short(self):
        """데이터 부족 → False."""
        self.assertFalse(is_above_50ma(self._make_ohlcv([100] * 30)))


class TestUptrendCalculator(unittest.TestCase):
    """UptrendCalculator 테스트."""

    def test_overall_ratio(self):
        """전체 비율 계산."""
        sector_data = {
            '반도체': {'ratio': 75.0, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
            '자동차': {'ratio': 66.7, 'total': 3, 'uptrend': 2, 'group': 'Cyclical'},
            '통신': {'ratio': 33.3, 'total': 3, 'uptrend': 1, 'group': 'Defensive'},
        }
        overall = UptrendCalculator.calculate_overall_ratio(sector_data)
        # 6 uptrend / 10 total = 60%
        self.assertAlmostEqual(overall, 60.0, places=1)

    def test_group_averages(self):
        """그룹 평균 계산."""
        sector_data = {
            '반도체': {'ratio': 75.0, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
            '자동차': {'ratio': 65.0, 'total': 3, 'uptrend': 2, 'group': 'Cyclical'},
            '통신': {'ratio': 33.3, 'total': 3, 'uptrend': 1, 'group': 'Defensive'},
        }
        avgs = UptrendCalculator.calculate_group_averages(sector_data)
        self.assertAlmostEqual(avgs['Cyclical'], 70.0, places=1)
        self.assertAlmostEqual(avgs['Defensive'], 33.3, places=1)

    def test_sector_spread(self):
        """업종간 스프레드."""
        sector_data = {
            '반도체': {'ratio': 80.0, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
            '건설': {'ratio': 20.0, 'total': 5, 'uptrend': 1, 'group': 'Cyclical'},
        }
        spread = UptrendCalculator.calculate_sector_spread(sector_data)
        self.assertAlmostEqual(spread, 60.0, places=1)

    def test_group_std(self):
        """그룹 내 표준편차."""
        sector_data = {
            '반도체': {'ratio': 80.0, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
            '건설': {'ratio': 20.0, 'total': 5, 'uptrend': 1, 'group': 'Cyclical'},
        }
        stds = UptrendCalculator.calculate_group_std(sector_data)
        self.assertIn('Cyclical', stds)
        self.assertGreater(stds['Cyclical'], 20)  # 큰 편차

    def test_sector_to_group_mapping(self):
        """업종-그룹 매핑 완전성."""
        all_sectors = set()
        for sectors in KR_SECTOR_GROUPS.values():
            all_sectors.update(sectors)
        for sector in all_sectors:
            self.assertIn(sector, SECTOR_TO_GROUP)


class TestUptrendScorer(unittest.TestCase):
    """UptrendScorer 스코어링 테스트."""

    def setUp(self):
        self.scorer = UptrendScorer()

    def test_weights_sum_to_one(self):
        """가중치 합계 = 1.0."""
        total = sum(WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_strong_bull(self):
        """강세 시장 → 높은 점수."""
        data = {
            'overall_ratio': 75.0,
            'sector_data': {
                '반도체': {'ratio': 80, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
                '자동차': {'ratio': 70, 'total': 3, 'uptrend': 2, 'group': 'Cyclical'},
                '통신': {'ratio': 60, 'total': 3, 'uptrend': 2, 'group': 'Defensive'},
                '은행': {'ratio': 65, 'total': 3, 'uptrend': 2, 'group': 'Financial'},
            },
            'group_averages': {'Cyclical': 75, 'Defensive': 60, 'Financial': 65},
            'sector_spread': 20.0,
            'group_std': {'Cyclical': 5.0},
            'history': [50, 55, 60, 65, 70],
            'prev_ratio': 70.0,
        }
        result = self.scorer.score(data)
        self.assertGreaterEqual(result['composite_score'], 60)
        self.assertIn(result['uptrend_zone'], ['Strong Bull', 'Bull-Lower'])

    def test_strong_bear(self):
        """약세 시장 → 낮은 점수."""
        data = {
            'overall_ratio': 15.0,
            'sector_data': {
                '반도체': {'ratio': 20, 'total': 4, 'uptrend': 1, 'group': 'Cyclical'},
                '자동차': {'ratio': 10, 'total': 3, 'uptrend': 0, 'group': 'Cyclical'},
                '통신': {'ratio': 30, 'total': 3, 'uptrend': 1, 'group': 'Defensive'},
            },
            'group_averages': {'Cyclical': 15, 'Defensive': 30},
            'sector_spread': 20.0,
            'group_std': {'Cyclical': 5.0},
            'history': [50, 45, 40, 30, 20],
            'prev_ratio': 20.0,
        }
        result = self.scorer.score(data)
        self.assertLessEqual(result['composite_score'], 40)

    def test_neutral(self):
        """중립 시장 → 중간 점수."""
        data = {
            'overall_ratio': 50.0,
            'sector_data': {
                '반도체': {'ratio': 55, 'total': 4, 'uptrend': 2, 'group': 'Cyclical'},
                '통신': {'ratio': 45, 'total': 3, 'uptrend': 1, 'group': 'Defensive'},
            },
            'group_averages': {'Cyclical': 55, 'Defensive': 45},
            'sector_spread': 10.0,
            'group_std': {},
            'history': [50],
            'prev_ratio': 50.0,
        }
        result = self.scorer.score(data)
        self.assertGreaterEqual(result['composite_score'], 30)
        self.assertLessEqual(result['composite_score'], 70)

    def test_score_range(self):
        """종합 점수 0~100."""
        for ratio in [0, 25, 50, 75, 100]:
            data = {
                'overall_ratio': ratio,
                'sector_data': {
                    '반도체': {'ratio': ratio, 'total': 4, 'uptrend': int(ratio/25), 'group': 'Cyclical'},
                },
                'group_averages': {'Cyclical': ratio},
                'sector_spread': 0,
                'group_std': {},
                'history': [ratio],
                'prev_ratio': ratio,
            }
            result = self.scorer.score(data)
            self.assertGreaterEqual(result['composite_score'], 0)
            self.assertLessEqual(result['composite_score'], 100)

    def test_component_keys(self):
        """5개 컴포넌트 존재."""
        data = {
            'overall_ratio': 50, 'sector_data': {},
            'group_averages': {}, 'sector_spread': 0,
            'group_std': {}, 'history': [], 'prev_ratio': None,
        }
        result = self.scorer.score(data)
        expected = {'breadth', 'participation', 'rotation', 'momentum', 'historical'}
        self.assertEqual(set(result['components'].keys()), expected)

    def test_uptrend_zones_coverage(self):
        """Zone 정의 완전성."""
        self.assertEqual(len(UPTREND_ZONES), 5)
        self.assertEqual(UPTREND_ZONES[0][0], 80)   # Strong Bull starts at 80
        self.assertEqual(UPTREND_ZONES[-1][0], 0)    # Strong Bear starts at 0

    def test_high_spread_warning(self):
        """High Spread 경고."""
        data = {
            'overall_ratio': 50, 'sector_data': {},
            'group_averages': {}, 'sector_spread': 50,  # > 40
            'group_std': {}, 'history': [], 'prev_ratio': None,
        }
        result = self.scorer.score(data)
        warning_types = [w['type'] for w in result['warnings']]
        self.assertIn('high_spread', warning_types)

    def test_divergence_warning(self):
        """Divergence 경고."""
        data = {
            'overall_ratio': 50, 'sector_data': {},
            'group_averages': {}, 'sector_spread': 10,
            'group_std': {'Cyclical': 25},  # > 20
            'history': [], 'prev_ratio': None,
        }
        result = self.scorer.score(data)
        warning_types = [w['type'] for w in result['warnings']]
        self.assertIn('divergence', warning_types)

    def test_momentum_rising(self):
        """모멘텀 상승."""
        score = self.scorer._score_momentum(60.0, 50.0)
        self.assertGreater(score, 50)  # > 50 (상승)

    def test_momentum_falling(self):
        """모멘텀 하락."""
        score = self.scorer._score_momentum(40.0, 50.0)
        self.assertLess(score, 50)  # < 50 (하락)


class TestUptrendHistoryTracker(unittest.TestCase):
    """히스토리 관리 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.tmpdir, 'test_uptrend_history.json')
        self.tracker = HistoryTracker(self.filepath)

    def test_empty_history(self):
        self.assertEqual(self.tracker.load(), [])

    def test_save_and_load(self):
        self.tracker.save({
            'date': '2026-02-27', 'market': 'KRX',
            'composite_score': 65.0, 'overall_ratio': 55.0,
            'uptrend_zone': 'Bull-Lower',
        })
        loaded = self.tracker.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['composite_score'], 65.0)

    def test_max_entries(self):
        for i in range(35):
            self.tracker.save({
                'date': f'2026-01-{i+1:02d}', 'market': 'KRX',
                'composite_score': 50 + i, 'overall_ratio': 50,
                'uptrend_zone': 'Neutral',
            })
        loaded = self.tracker.load()
        self.assertLessEqual(len(loaded), 30)

    def test_trend_improving(self):
        for i, score in enumerate([40, 45, 50, 55, 60]):
            self.tracker.save({
                'date': f'2026-02-{20+i}', 'market': 'KRX',
                'composite_score': score, 'overall_ratio': score,
            })
        self.assertEqual(self.tracker.get_trend('KRX'), 'improving')

    def test_trend_deteriorating(self):
        for i, score in enumerate([60, 55, 50, 45, 40]):
            self.tracker.save({
                'date': f'2026-02-{20+i}', 'market': 'KRX',
                'composite_score': score, 'overall_ratio': score,
            })
        self.assertEqual(self.tracker.get_trend('KRX'), 'deteriorating')

    def test_trend_insufficient(self):
        self.assertEqual(self.tracker.get_trend(), 'insufficient')


class TestUptrendReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = ReportGenerator(self.tmpdir)

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        sector_data = {
            '반도체': {'ratio': 75.0, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
            '통신': {'ratio': 40.0, 'total': 3, 'uptrend': 1, 'group': 'Defensive'},
        }
        score_data = {
            'composite_score': 65,
            'uptrend_zone': 'Bull-Lower',
            'uptrend_zone_kr': '약강세',
            'equity_exposure': '80-100%',
            'components': {
                'breadth': {'score': 70, 'weight': 0.30, 'weighted': 21.0, 'detail': '전체 60%'},
                'participation': {'score': 60, 'weight': 0.25, 'weighted': 15.0, 'detail': '참여 3/4'},
                'rotation': {'score': 70, 'weight': 0.15, 'weighted': 10.5, 'detail': '경기민감 우위'},
                'momentum': {'score': 70, 'weight': 0.20, 'weighted': 14.0, 'detail': '상승'},
                'historical': {'score': 55, 'weight': 0.10, 'weighted': 5.5, 'detail': '백분위 55%'},
            },
            'warnings': [],
            'strongest_component': 'breadth',
            'weakest_component': 'historical',
        }

        paths = self.reporter.generate(
            sector_data, score_data, 'improving', 60.0,
            {'Cyclical': 75.0, 'Defensive': 40.0},
        )

        self.assertTrue(os.path.exists(paths['json_path']))
        self.assertTrue(os.path.exists(paths['md_path']))

        # JSON 내용 검증
        with open(paths['json_path'], 'r') as f:
            data = json.load(f)
        self.assertEqual(data['overall_ratio'], 60.0)
        self.assertEqual(data['score']['composite_score'], 65)

        # MD 내용 검증
        with open(paths['md_path'], 'r') as f:
            md = f.read()
        self.assertIn('Bull-Lower', md)
        self.assertIn('반도체', md)
        self.assertIn('80-100%', md)


if __name__ == '__main__':
    unittest.main()
