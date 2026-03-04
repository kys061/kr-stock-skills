"""
kr-dividend-pullback 테스트.
배당 성장 필터 + RSI 타이밍 + 4-컴포넌트 스코어링.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from growth_filter import (
    filter_growth, filter_rsi, score_rsi, calc_dividend_cagr,
    MIN_YIELD, MIN_DIVIDEND_CAGR, MIN_CONSECUTIVE_YEARS, MIN_MARKET_CAP,
    MAX_DE_RATIO, MIN_CURRENT_RATIO, MAX_PAYOUT_RATIO, RSI_THRESHOLD,
)
from scorer import (
    calc_dividend_growth_score, calc_financial_quality_score,
    calc_technical_setup_score, calc_valuation_score, calc_total_score,
    WEIGHTS, RATING_BANDS, CONSECUTIVE_BONUS,
)
from report_generator import PullbackReportGenerator


# ═══════════════════════════════════════════════════════════
# 배당 성장 필터
# ═══════════════════════════════════════════════════════════

class TestGrowthFilter(unittest.TestCase):

    def _make_stock(self, **overrides):
        base = {
            'div_yield': 3.0,
            'dividend_cagr': 12.0,
            'dividend_history': [800, 900, 1000, 1100],
            'market_cap': 500_000_000_000,
            'revenue_trend_positive': True,
            'eps_trend_positive': True,
            'de_ratio': 80.0,
            'current_ratio': 1.5,
            'payout_ratio': 50.0,
        }
        base.update(overrides)
        return base

    def test_pass_all(self):
        """모든 조건 충족."""
        self.assertTrue(filter_growth(self._make_stock()))

    def test_fail_low_yield(self):
        """배당수익률 미달."""
        self.assertFalse(filter_growth(self._make_stock(div_yield=1.5)))

    def test_fail_low_cagr(self):
        """CAGR 미달."""
        self.assertFalse(filter_growth(self._make_stock(dividend_cagr=5.0)))

    def test_fail_dividend_cut(self):
        """배당 삭감."""
        self.assertFalse(filter_growth(self._make_stock(dividend_history=[1100, 1000, 900, 800])))

    def test_fail_small_cap(self):
        """시가총액 미달."""
        self.assertFalse(filter_growth(self._make_stock(market_cap=100_000_000_000)))

    def test_fail_high_debt(self):
        """부채비율 초과."""
        self.assertFalse(filter_growth(self._make_stock(de_ratio=160.0)))

    def test_fail_no_revenue_growth(self):
        """매출 성장 없음."""
        self.assertFalse(filter_growth(self._make_stock(revenue_trend_positive=False)))

    def test_fail_high_payout(self):
        """배당성향 초과."""
        self.assertFalse(filter_growth(self._make_stock(payout_ratio=85.0)))


# ═══════════════════════════════════════════════════════════
# RSI 필터
# ═══════════════════════════════════════════════════════════

class TestRSIFilter(unittest.TestCase):

    def test_oversold_passes(self):
        """RSI 25 → 통과."""
        self.assertTrue(filter_rsi(25.0))

    def test_threshold_passes(self):
        """RSI 40 → 통과."""
        self.assertTrue(filter_rsi(40.0))

    def test_above_threshold_fails(self):
        """RSI 41 → 실패."""
        self.assertFalse(filter_rsi(41.0))

    def test_extreme_oversold(self):
        """RSI 15 → 통과."""
        self.assertTrue(filter_rsi(15.0))


# ═══════════════════════════════════════════════════════════
# RSI 점수
# ═══════════════════════════════════════════════════════════

class TestRSIScore(unittest.TestCase):

    def test_extreme_oversold(self):
        """RSI < 30 → 90점."""
        self.assertEqual(score_rsi(25.0), 90)

    def test_strong_oversold(self):
        """RSI 30-35 → 80점."""
        self.assertEqual(score_rsi(32.0), 80)

    def test_initial_pullback(self):
        """RSI 35-40 → 70점."""
        self.assertEqual(score_rsi(38.0), 70)

    def test_above_threshold(self):
        """RSI > 40 → 0점."""
        self.assertEqual(score_rsi(50.0), 0)


# ═══════════════════════════════════════════════════════════
# 배당 CAGR 계산
# ═══════════════════════════════════════════════════════════

class TestDividendCAGR(unittest.TestCase):

    def test_positive_growth(self):
        """100 → 200 over 3 years → ~26%."""
        cagr = calc_dividend_cagr([100, 120, 150, 200])
        self.assertAlmostEqual(cagr, 26.0, delta=1.0)

    def test_flat(self):
        """동일 배당 → 0%."""
        cagr = calc_dividend_cagr([100, 100, 100])
        self.assertAlmostEqual(cagr, 0.0, delta=0.01)

    def test_zero_start(self):
        """시작 배당 0 → 0%."""
        cagr = calc_dividend_cagr([0, 100, 200])
        self.assertEqual(cagr, 0.0)

    def test_single_value(self):
        """단일 값 → 0%."""
        cagr = calc_dividend_cagr([100])
        self.assertEqual(cagr, 0.0)


# ═══════════════════════════════════════════════════════════
# Dividend Growth Score
# ═══════════════════════════════════════════════════════════

class TestDividendGrowthScore(unittest.TestCase):

    def test_high_cagr(self):
        """CAGR 20% → 100."""
        result = calc_dividend_growth_score(20.0)
        self.assertEqual(result['score'], 100)

    def test_moderate_cagr(self):
        """CAGR 10% → 70."""
        result = calc_dividend_growth_score(10.0)
        self.assertEqual(result['score'], 70)

    def test_with_consecutive_bonus(self):
        """CAGR 10% (70) + 5년 연속 (+10) = 80."""
        result = calc_dividend_growth_score(10.0, consecutive_years=5)
        self.assertEqual(result['score'], 80)

    def test_capped_at_100(self):
        """CAGR 20% (100) + 보너스 → 캡 100."""
        result = calc_dividend_growth_score(20.0, consecutive_years=10)
        self.assertEqual(result['score'], 100)


# ═══════════════════════════════════════════════════════════
# Financial Quality Score
# ═══════════════════════════════════════════════════════════

class TestFinancialQualityScore(unittest.TestCase):

    def test_excellent(self):
        """ROE 25%, OPM 25%, D/E 30% → ~100."""
        result = calc_financial_quality_score(25.0, 25.0, 30.0)
        self.assertEqual(result['score'], 100)

    def test_moderate(self):
        """ROE 12%, OPM 12%, D/E 80% → 60*0.4 + 60*0.3 + 80*0.3 = 66."""
        result = calc_financial_quality_score(12.0, 12.0, 80.0)
        self.assertEqual(result['score'], 66)

    def test_weak(self):
        """ROE 3%, OPM 3%, D/E 160% → 20*0.4 + 20*0.3 + 20*0.3 = 20."""
        result = calc_financial_quality_score(3.0, 3.0, 160.0)
        self.assertEqual(result['score'], 20)


# ═══════════════════════════════════════════════════════════
# Technical Setup Score
# ═══════════════════════════════════════════════════════════

class TestTechnicalSetupScore(unittest.TestCase):

    def test_extreme_oversold(self):
        """RSI 25 → 90."""
        result = calc_technical_setup_score(25.0)
        self.assertEqual(result['score'], 90)

    def test_strong_oversold(self):
        """RSI 32 → 80."""
        result = calc_technical_setup_score(32.0)
        self.assertEqual(result['score'], 80)

    def test_above_threshold(self):
        """RSI 50 → 0."""
        result = calc_technical_setup_score(50.0)
        self.assertEqual(result['score'], 0)


# ═══════════════════════════════════════════════════════════
# Valuation Score
# ═══════════════════════════════════════════════════════════

class TestValuationScore(unittest.TestCase):

    def test_excellent_value(self):
        """PER 8, PBR 0.6 → PER 100, PBR 100 → 100."""
        result = calc_valuation_score(8.0, 0.6)
        self.assertEqual(result['score'], 100)

    def test_moderate_value(self):
        """PER 14, PBR 0.9 → PER 80, PBR 80 → 80."""
        result = calc_valuation_score(14.0, 0.9)
        self.assertEqual(result['score'], 80)


# ═══════════════════════════════════════════════════════════
# 종합 스코어
# ═══════════════════════════════════════════════════════════

class TestPullbackTotalScore(unittest.TestCase):

    def test_strong_buy(self):
        """모든 컴포넌트 90+ → Strong Buy."""
        result = calc_total_score(95, 90, 90, 90)
        self.assertGreaterEqual(result['total_score'], 85)
        self.assertEqual(result['rating'], 'Strong Buy')

    def test_buy(self):
        """80점대 → Buy."""
        result = calc_total_score(80, 80, 80, 80)
        self.assertEqual(result['total_score'], 80)
        self.assertEqual(result['rating'], 'Buy')

    def test_pass_rating(self):
        """40점대 → Pass."""
        result = calc_total_score(40, 40, 40, 40)
        self.assertEqual(result['total_score'], 40)
        self.assertEqual(result['rating'], 'Pass')


# ═══════════════════════════════════════════════════════════
# Constants 검증
# ═══════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_weights_sum(self):
        """가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=5)

    def test_filter_thresholds(self):
        """필터 임계값 설계값 일치."""
        self.assertEqual(MIN_YIELD, 2.0)
        self.assertEqual(MIN_DIVIDEND_CAGR, 8.0)
        self.assertEqual(MIN_CONSECUTIVE_YEARS, 4)
        self.assertEqual(RSI_THRESHOLD, 40)

    def test_rating_bands(self):
        """등급 4개."""
        self.assertEqual(len(RATING_BANDS), 4)


# ═══════════════════════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════════════════════

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = PullbackReportGenerator(self.tmpdir)
        self.sample_results = [
            {
                'ticker': '005930', 'name': '삼성전자', 'rsi': 28.5, 'cagr': 15.0,
                'score_data': {
                    'total_score': 88, 'rating': 'Strong Buy',
                    'action': '즉시 매수',
                    'components': {'dividend_growth': 90, 'financial_quality': 85,
                                   'technical_setup': 90, 'valuation': 80},
                },
            },
        ]

    def test_json_report(self):
        """JSON 리포트."""
        path = self.reporter.generate_json(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-dividend-pullback')

    def test_markdown_report(self):
        """Markdown 리포트."""
        path = self.reporter.generate_markdown(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('배당 성장 풀백', content)


if __name__ == '__main__':
    unittest.main()
