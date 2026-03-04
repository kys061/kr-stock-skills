"""kr-theme-detector 단위 테스트.

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

from theme_classifier import ThemeClassifier
from scorer import (
    ThemeScorer, calculate_theme_heat, classify_lifecycle,
    assess_confidence, detect_direction, HEAT_WEIGHTS,
)
from report_generator import ReportGenerator


# ─────────────────────────────────────────────
# Mock 데이터 생성 헬퍼
# ─────────────────────────────────────────────

def make_theme_data(name, stocks_data):
    """IndustryDataCollector.collect() 형태의 mock 데이터."""
    return {
        'name': name,
        'description': f'{name} 테마',
        'stocks': stocks_data,
    }


def make_stock(ticker='005930', name='삼성전자', role='core',
               close=70000, change_1w=2.0, change_1m=5.0,
               volume_ratio=1.3, above_200ma=True, above_50ma=True,
               positive_5d=3, market_cap=400_000_000_000_000):
    return {
        'ticker': ticker, 'name': name, 'role': role,
        'close': close, 'change_1w': change_1w, 'change_1m': change_1m,
        'volume_ratio': volume_ratio, 'above_200ma': above_200ma,
        'above_50ma': above_50ma, 'positive_5d': positive_5d,
        'market_cap': market_cap,
    }


def make_bullish_stats():
    """강세 테마 통계."""
    return {
        'name': 'AI/반도체',
        'avg_change_1w': 3.5, 'avg_change_1m': 8.0,
        'weighted_change_1w': 3.0, 'weighted_change_1m': 7.5,
        'avg_volume_ratio': 1.5, 'uptrend_ratio': 75.0,
        'breadth_5d': 60.0, 'stock_count': 4, 'core_count': 2,
    }


def make_bearish_stats():
    """약세 테마 통계."""
    return {
        'name': '2차전지',
        'avg_change_1w': -3.0, 'avg_change_1m': -8.0,
        'weighted_change_1w': -2.5, 'weighted_change_1m': -7.0,
        'avg_volume_ratio': 0.7, 'uptrend_ratio': 25.0,
        'breadth_5d': 20.0, 'stock_count': 4, 'core_count': 2,
    }


def make_neutral_stats():
    """중립 테마 통계."""
    return {
        'name': '통신/유틸리티',
        'avg_change_1w': 0.5, 'avg_change_1m': 1.0,
        'weighted_change_1w': 0.3, 'weighted_change_1m': 0.8,
        'avg_volume_ratio': 1.0, 'uptrend_ratio': 45.0,
        'breadth_5d': 40.0, 'stock_count': 2, 'core_count': 2,
    }


# ─────────────────────────────────────────────
# 테스트 클래스
# ─────────────────────────────────────────────

class TestThemeClassifier(unittest.TestCase):
    """ThemeClassifier 테스트."""

    def setUp(self):
        self.classifier = ThemeClassifier()

    def test_basic_stats(self):
        """기본 통계 계산."""
        theme_data = {
            'ai_semiconductor': make_theme_data('AI/반도체', [
                make_stock('005930', '삼성전자', 'core', change_1w=3.0, change_1m=5.0,
                           above_200ma=True, volume_ratio=1.5, positive_5d=4),
                make_stock('000660', 'SK하이닉스', 'core', change_1w=4.0, change_1m=7.0,
                           above_200ma=True, volume_ratio=1.2, positive_5d=3),
            ]),
        }

        result = self.classifier.classify(theme_data)
        stats = result['ai_semiconductor']

        self.assertEqual(stats['name'], 'AI/반도체')
        self.assertEqual(stats['stock_count'], 2)
        self.assertEqual(stats['core_count'], 2)
        self.assertAlmostEqual(stats['avg_change_1w'], 3.5, places=1)
        self.assertEqual(stats['uptrend_ratio'], 100.0)

    def test_empty_theme(self):
        """빈 테마 → 기본값."""
        theme_data = {
            'empty': make_theme_data('빈 테마', []),
        }
        result = self.classifier.classify(theme_data)
        self.assertEqual(result['empty']['stock_count'], 0)
        self.assertEqual(result['empty']['uptrend_ratio'], 0)

    def test_mixed_uptrend(self):
        """업트렌드 혼합."""
        theme_data = {
            'mixed': make_theme_data('혼합', [
                make_stock(above_200ma=True),
                make_stock(above_200ma=False),
                make_stock(above_200ma=True),
                make_stock(above_200ma=False),
            ]),
        }
        result = self.classifier.classify(theme_data)
        self.assertAlmostEqual(result['mixed']['uptrend_ratio'], 50.0, places=1)


class TestCalculateThemeHeat(unittest.TestCase):
    """calculate_theme_heat() 테스트."""

    def test_heat_weights_sum(self):
        """Heat 가중치 합계 = 1.0."""
        total = sum(HEAT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_high_heat(self):
        """강세 테마 → 높은 Heat."""
        stats = make_bullish_stats()
        heat = calculate_theme_heat(stats)
        self.assertGreater(heat, 60)

    def test_low_heat(self):
        """약세 테마 → 낮은 Heat."""
        stats = make_bearish_stats()
        heat = calculate_theme_heat(stats)
        self.assertLess(heat, 40)

    def test_heat_range(self):
        """Heat 0~100 범위."""
        for stats in [make_bullish_stats(), make_bearish_stats(), make_neutral_stats()]:
            heat = calculate_theme_heat(stats)
            self.assertGreaterEqual(heat, 0)
            self.assertLessEqual(heat, 100)


class TestClassifyLifecycle(unittest.TestCase):
    """classify_lifecycle() 테스트."""

    def test_early(self):
        """Early 라이프사이클."""
        stats = {
            'weighted_change_1w': 2.0, 'weighted_change_1m': 3.0,
            'avg_volume_ratio': 1.2, 'uptrend_ratio': 40,
        }
        self.assertEqual(classify_lifecycle(stats), 'Early')

    def test_mid(self):
        """Mid 라이프사이클."""
        stats = {
            'weighted_change_1w': 3.0, 'weighted_change_1m': 8.0,
            'avg_volume_ratio': 1.5, 'uptrend_ratio': 65,
        }
        self.assertEqual(classify_lifecycle(stats), 'Mid')

    def test_late(self):
        """Late 라이프사이클."""
        stats = {
            'weighted_change_1w': 5.0, 'weighted_change_1m': 20.0,
            'avg_volume_ratio': 2.5, 'uptrend_ratio': 85,
        }
        self.assertEqual(classify_lifecycle(stats), 'Late')

    def test_exhaustion(self):
        """Exhaustion 라이프사이클."""
        stats = {
            'weighted_change_1w': -2.0, 'weighted_change_1m': 15.0,
            'avg_volume_ratio': 0.8, 'uptrend_ratio': 60,
        }
        self.assertEqual(classify_lifecycle(stats), 'Exhaustion')


class TestAssessConfidence(unittest.TestCase):
    """assess_confidence() 테스트."""

    def test_high(self):
        stats = {'uptrend_ratio': 75, 'avg_volume_ratio': 1.5}
        self.assertEqual(assess_confidence(stats), 'High')

    def test_low(self):
        stats = {'uptrend_ratio': 30, 'avg_volume_ratio': 0.7}
        self.assertEqual(assess_confidence(stats), 'Low')

    def test_medium(self):
        stats = {'uptrend_ratio': 50, 'avg_volume_ratio': 1.0}
        self.assertEqual(assess_confidence(stats), 'Medium')


class TestDetectDirection(unittest.TestCase):
    """detect_direction() 테스트."""

    def test_bullish(self):
        stats = {'weighted_change_1w': 3.0, 'uptrend_ratio': 65, 'avg_volume_ratio': 1.5}
        self.assertEqual(detect_direction(stats), 'Bullish')

    def test_bearish(self):
        stats = {'weighted_change_1w': -3.0, 'uptrend_ratio': 30, 'avg_volume_ratio': 0.7}
        self.assertEqual(detect_direction(stats), 'Bearish')

    def test_neutral(self):
        stats = {'weighted_change_1w': 0.5, 'uptrend_ratio': 45, 'avg_volume_ratio': 1.0}
        self.assertEqual(detect_direction(stats), 'Neutral')


class TestThemeScorer(unittest.TestCase):
    """ThemeScorer 통합 테스트."""

    def setUp(self):
        self.scorer = ThemeScorer()

    def test_score_all(self):
        """전체 테마 스코어링."""
        classified = {
            'ai_semi': make_bullish_stats(),
            'battery': make_bearish_stats(),
            'telecom': make_neutral_stats(),
        }
        results = self.scorer.score_all(classified)

        self.assertEqual(len(results), 3)
        self.assertIn('ai_semi', results)
        self.assertIn('heat', results['ai_semi'])
        self.assertIn('lifecycle', results['ai_semi'])
        self.assertIn('confidence', results['ai_semi'])
        self.assertIn('direction', results['ai_semi'])

    def test_bullish_theme_high_heat(self):
        """강세 테마 = 높은 Heat."""
        classified = {'ai_semi': make_bullish_stats()}
        results = self.scorer.score_all(classified)
        self.assertGreater(results['ai_semi']['heat'], 50)
        self.assertEqual(results['ai_semi']['direction'], 'Bullish')

    def test_bearish_theme_low_heat(self):
        """약세 테마 = 낮은 Heat."""
        classified = {'battery': make_bearish_stats()}
        results = self.scorer.score_all(classified)
        self.assertLess(results['battery']['heat'], 40)
        self.assertEqual(results['battery']['direction'], 'Bearish')


class TestThemeReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = ReportGenerator(self.tmpdir)

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        scored_themes = {
            'ai_semi': {
                'name': 'AI/반도체',
                'heat': 78.5,
                'lifecycle': 'Mid',
                'confidence': 'High',
                'direction': 'Bullish',
                'stats': make_bullish_stats(),
            },
            'battery': {
                'name': '2차전지',
                'heat': 32.0,
                'lifecycle': 'Late',
                'confidence': 'Medium',
                'direction': 'Bearish',
                'stats': make_bearish_stats(),
            },
        }

        paths = self.reporter.generate(scored_themes)

        self.assertTrue(os.path.exists(paths['json_path']))
        self.assertTrue(os.path.exists(paths['md_path']))

        # JSON 검증
        with open(paths['json_path'], 'r') as f:
            data = json.load(f)
        self.assertIn('themes', data)
        self.assertIn('summary', data)
        self.assertEqual(data['summary']['bullish_count'], 1)
        self.assertEqual(data['summary']['bearish_count'], 1)

        # MD 검증
        with open(paths['md_path'], 'r') as f:
            md = f.read()
        self.assertIn('AI/반도체', md)
        self.assertIn('2차전지', md)
        self.assertIn('Bullish', md)
        self.assertIn('Bearish', md)
        self.assertIn('78.5', md)

    def test_summary_stats(self):
        """요약 통계 정확성."""
        scored = {
            'a': {'name': 'A', 'heat': 80, 'direction': 'Bullish',
                   'lifecycle': 'Mid', 'confidence': 'High', 'stats': {}},
            'b': {'name': 'B', 'heat': 20, 'direction': 'Bearish',
                   'lifecycle': 'Late', 'confidence': 'Low', 'stats': {}},
            'c': {'name': 'C', 'heat': 50, 'direction': 'Neutral',
                   'lifecycle': 'Early', 'confidence': 'Medium', 'stats': {}},
        }
        summary = self.reporter._build_summary(scored)
        self.assertEqual(summary['total_themes'], 3)
        self.assertEqual(summary['bullish_count'], 1)
        self.assertEqual(summary['bearish_count'], 1)
        self.assertEqual(summary['neutral_count'], 1)
        self.assertEqual(summary['hottest'], 'A')
        self.assertEqual(summary['coldest'], 'B')


class TestYamlLoad(unittest.TestCase):
    """kr_themes.yaml 로드 테스트."""

    def test_yaml_exists(self):
        """YAML 파일 존재 확인."""
        yaml_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'kr_themes.yaml'
        )
        self.assertTrue(os.path.exists(yaml_path), f"kr_themes.yaml not found at {yaml_path}")

    def test_yaml_structure(self):
        """YAML 구조 검증."""
        import yaml

        yaml_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'kr_themes.yaml'
        )
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.assertIn('themes', data)
        themes = data['themes']
        self.assertGreaterEqual(len(themes), 14)

        # 필수 필드 확인
        for theme_id, theme in themes.items():
            self.assertIn('name', theme, f"{theme_id} missing 'name'")
            self.assertIn('representative_stocks', theme, f"{theme_id} missing 'representative_stocks'")
            self.assertIn('industries', theme, f"{theme_id} missing 'industries'")

            # 최소 1개 대표종목
            self.assertGreater(len(theme['representative_stocks']), 0,
                               f"{theme_id} has no representative stocks")

            # 종목에 ticker, name 필드
            for stock in theme['representative_stocks']:
                self.assertIn('ticker', stock, f"{theme_id} stock missing 'ticker'")
                self.assertIn('name', stock, f"{theme_id} stock missing 'name'")

    def test_14_themes(self):
        """14개 테마 정의."""
        import yaml

        yaml_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'kr_themes.yaml'
        )
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.assertEqual(len(data['themes']), 14)


if __name__ == '__main__':
    unittest.main()
