"""
kr-value-dividend 테스트.
3-Phase 필터 + 4-컴포넌트 스코어링 + 리포트 생성.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fundamental_filter import (
    filter_phase1, filter_phase2, filter_phase3, filter_all_phases,
    PHASE1_MIN_YIELD, PHASE1_MAX_PER, PHASE1_MAX_PBR, PHASE1_MIN_MARKET_CAP,
    PHASE2_MIN_DIVIDEND_YEARS,
    PHASE3_MAX_PAYOUT, PHASE3_MAX_DE_RATIO, PHASE3_MIN_CURRENT_RATIO,
)
from scorer import (
    calc_value_score, calc_growth_score, calc_sustainability_score,
    calc_quality_score, calc_total_score,
    WEIGHTS, RATING_BANDS,
    PER_THRESHOLDS, PBR_THRESHOLDS,
    DIVIDEND_CAGR_THRESHOLDS, PAYOUT_THRESHOLDS, DE_RATIO_THRESHOLDS,
)
from report_generator import ValueDividendReportGenerator


# ═══════════════════════════════════════════════════════════
# Phase 1: 정량 필터
# ═══════════════════════════════════════════════════════════

class TestPhase1Filter(unittest.TestCase):

    def _make_stock(self, **overrides):
        base = {
            'div_yield': 3.0,
            'per': 10.0,
            'pbr': 1.0,
            'market_cap': 1_000_000_000_000,
        }
        base.update(overrides)
        return base

    def test_pass_all_criteria(self):
        """모든 Phase 1 조건 충족."""
        self.assertTrue(filter_phase1(self._make_stock()))

    def test_fail_low_yield(self):
        """배당수익률 미달."""
        self.assertFalse(filter_phase1(self._make_stock(div_yield=2.0)))

    def test_fail_high_per(self):
        """PER 초과."""
        self.assertFalse(filter_phase1(self._make_stock(per=16.0)))

    def test_fail_negative_per(self):
        """PER 음수 (적자)."""
        self.assertFalse(filter_phase1(self._make_stock(per=-5.0)))

    def test_fail_high_pbr(self):
        """PBR 초과."""
        self.assertFalse(filter_phase1(self._make_stock(pbr=2.0)))

    def test_fail_small_cap(self):
        """시가총액 미달."""
        self.assertFalse(filter_phase1(self._make_stock(market_cap=100_000_000_000)))

    def test_boundary_yield(self):
        """배당수익률 경계값 (정확히 2.5%)."""
        self.assertTrue(filter_phase1(self._make_stock(div_yield=2.5)))

    def test_boundary_per(self):
        """PER 경계값 (정확히 15)."""
        self.assertTrue(filter_phase1(self._make_stock(per=15.0)))


# ═══════════════════════════════════════════════════════════
# Phase 2: 성장 품질 필터
# ═══════════════════════════════════════════════════════════

class TestPhase2Filter(unittest.TestCase):

    def _make_stock(self, **overrides):
        base = {
            'dividend_history': [1000, 1100, 1200],
            'revenue_history': [100, 110, 120],
            'eps_history': [500, 600, 700],
        }
        base.update(overrides)
        return base

    def test_pass_all(self):
        """배당 무삭감 + 양의 추세."""
        self.assertTrue(filter_phase2(self._make_stock()))

    def test_fail_dividend_cut(self):
        """배당 삭감."""
        self.assertFalse(filter_phase2(self._make_stock(dividend_history=[1200, 1100, 1000])))

    def test_fail_dividend_zero(self):
        """배당 중단."""
        self.assertFalse(filter_phase2(self._make_stock(dividend_history=[1000, 0, 1200])))

    def test_fail_insufficient_data(self):
        """배당 데이터 2년만 (3년 필요)."""
        self.assertFalse(filter_phase2(self._make_stock(dividend_history=[1000, 1100])))

    def test_fail_revenue_decline(self):
        """매출 감소 추세."""
        self.assertFalse(filter_phase2(self._make_stock(revenue_history=[120, 110, 100])))

    def test_flat_dividend_passes(self):
        """배당 동결은 통과 (삭감 아님)."""
        self.assertTrue(filter_phase2(self._make_stock(dividend_history=[1000, 1000, 1000])))


# ═══════════════════════════════════════════════════════════
# Phase 3: 지속가능성 필터
# ═══════════════════════════════════════════════════════════

class TestPhase3Filter(unittest.TestCase):

    def _make_stock(self, **overrides):
        base = {
            'payout_ratio': 50.0,
            'de_ratio': 80.0,
            'current_ratio': 1.5,
        }
        base.update(overrides)
        return base

    def test_pass_all(self):
        """지속가능성 조건 충족."""
        self.assertTrue(filter_phase3(self._make_stock()))

    def test_fail_high_payout(self):
        """배당성향 초과."""
        self.assertFalse(filter_phase3(self._make_stock(payout_ratio=85.0)))

    def test_fail_high_debt(self):
        """부채비율 초과."""
        self.assertFalse(filter_phase3(self._make_stock(de_ratio=160.0)))

    def test_fail_low_current_ratio(self):
        """유동비율 미달."""
        self.assertFalse(filter_phase3(self._make_stock(current_ratio=0.8)))

    def test_boundary_payout(self):
        """배당성향 경계값 (79.9% → 통과)."""
        self.assertTrue(filter_phase3(self._make_stock(payout_ratio=79.9)))

    def test_boundary_payout_exact(self):
        """배당성향 정확히 80% → 실패."""
        self.assertFalse(filter_phase3(self._make_stock(payout_ratio=80.0)))


# ═══════════════════════════════════════════════════════════
# 3-Phase 통합 필터
# ═══════════════════════════════════════════════════════════

class TestAllPhasesFilter(unittest.TestCase):

    def test_pass_all_phases(self):
        """전 Phase 통과."""
        stock = {
            'div_yield': 3.0, 'per': 10.0, 'pbr': 1.0,
            'market_cap': 1_000_000_000_000,
            'dividend_history': [1000, 1100, 1200],
            'revenue_history': [100, 110, 120],
            'eps_history': [500, 600, 700],
            'payout_ratio': 50.0, 'de_ratio': 80.0, 'current_ratio': 1.5,
        }
        result = filter_all_phases(stock)
        self.assertTrue(result['passed'])
        self.assertIsNone(result['failed_at'])

    def test_fail_at_phase1(self):
        """Phase 1에서 실패."""
        stock = {'div_yield': 1.0, 'per': 10.0, 'pbr': 1.0, 'market_cap': 1e12}
        result = filter_all_phases(stock)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_at'], 'phase1')


# ═══════════════════════════════════════════════════════════
# Value Score
# ═══════════════════════════════════════════════════════════

class TestValueScore(unittest.TestCase):

    def test_excellent_value(self):
        """PER ≤ 8, PBR ≤ 0.5 → 100."""
        result = calc_value_score(7.0, 0.4)
        self.assertEqual(result['score'], 100)

    def test_moderate_value(self):
        """PER 10, PBR 0.8 → PER 80, PBR 80 → 80."""
        result = calc_value_score(10.0, 0.8)
        self.assertEqual(result['score'], 80)

    def test_low_value(self):
        """PER 14, PBR 1.4 → PER 40, PBR 40 → 40."""
        result = calc_value_score(14.0, 1.4)
        self.assertEqual(result['score'], 40)

    def test_mixed_value(self):
        """PER 8 (100), PBR 1.0 (60) → 100*0.6 + 60*0.4 = 84."""
        result = calc_value_score(8.0, 1.0)
        self.assertEqual(result['score'], 84)


# ═══════════════════════════════════════════════════════════
# Growth Score
# ═══════════════════════════════════════════════════════════

class TestGrowthScore(unittest.TestCase):

    def test_high_growth(self):
        """CAGR ≥ 15% → 100."""
        result = calc_growth_score(20.0)
        self.assertEqual(result['score'], 100)

    def test_moderate_growth(self):
        """CAGR 10% → 80."""
        result = calc_growth_score(10.0)
        self.assertEqual(result['score'], 80)

    def test_with_bonuses(self):
        """CAGR 5% (60) + 매출보너스(10) + EPS보너스(10) = 80."""
        result = calc_growth_score(5.0, True, True)
        self.assertEqual(result['score'], 80)

    def test_bonus_capped_at_100(self):
        """CAGR 15% (100) + 보너스 → 캡 100."""
        result = calc_growth_score(15.0, True, True)
        self.assertEqual(result['score'], 100)

    def test_flat_dividend(self):
        """CAGR 0% → 20."""
        result = calc_growth_score(0.0)
        self.assertEqual(result['score'], 20)


# ═══════════════════════════════════════════════════════════
# Sustainability Score
# ═══════════════════════════════════════════════════════════

class TestSustainabilityScore(unittest.TestCase):

    def test_excellent_sustainability(self):
        """Payout < 30%, D/E < 50% → 100."""
        result = calc_sustainability_score(25.0, 40.0)
        self.assertEqual(result['score'], 100)

    def test_moderate_sustainability(self):
        """Payout 50%, D/E 100% → 80 * 0.6 + 80 * 0.4 = 80."""
        result = calc_sustainability_score(50.0, 100.0)
        self.assertEqual(result['score'], 80)

    def test_weak_sustainability(self):
        """Payout 75%, D/E 140% → 40*0.6 + 60*0.4 = 48."""
        result = calc_sustainability_score(75.0, 140.0)
        self.assertEqual(result['score'], 48)

    def test_poor_sustainability(self):
        """Payout 79%, D/E 160% → 40*0.6 + 20*0.4 = 32."""
        result = calc_sustainability_score(79.0, 160.0)
        self.assertEqual(result['score'], 32)


# ═══════════════════════════════════════════════════════════
# Quality Score
# ═══════════════════════════════════════════════════════════

class TestQualityScore(unittest.TestCase):

    def test_excellent_quality(self):
        """ROE 25%, OPM 25% → 100."""
        result = calc_quality_score(25.0, 25.0)
        self.assertEqual(result['score'], 100)

    def test_moderate_quality(self):
        """ROE 12%, OPM 8% → 60*0.6 + 40*0.4 = 52."""
        result = calc_quality_score(12.0, 8.0)
        self.assertEqual(result['score'], 52)

    def test_low_quality(self):
        """ROE 3%, OPM 3% → 20*0.6 + 20*0.4 = 20."""
        result = calc_quality_score(3.0, 3.0)
        self.assertEqual(result['score'], 20)


# ═══════════════════════════════════════════════════════════
# 종합 스코어
# ═══════════════════════════════════════════════════════════

class TestTotalScore(unittest.TestCase):

    def test_excellent_total(self):
        """모든 컴포넌트 100점 → Excellent."""
        result = calc_total_score(100, 100, 100, 100)
        self.assertEqual(result['total_score'], 100)
        self.assertEqual(result['rating'], 'Excellent')

    def test_good_total(self):
        """80점대 → Good."""
        result = calc_total_score(80, 80, 80, 80)
        self.assertEqual(result['total_score'], 80)
        self.assertEqual(result['rating'], 'Good')

    def test_average_total(self):
        """60점대 → Average."""
        result = calc_total_score(60, 60, 60, 60)
        self.assertEqual(result['total_score'], 60)
        self.assertEqual(result['rating'], 'Average')

    def test_below_average_total(self):
        """40점대 → Below Average."""
        result = calc_total_score(40, 40, 40, 40)
        self.assertEqual(result['total_score'], 40)
        self.assertEqual(result['rating'], 'Below Average')

    def test_components_preserved(self):
        """컴포넌트 값 보존."""
        result = calc_total_score(90, 80, 70, 60)
        self.assertEqual(result['components']['value'], 90)
        self.assertEqual(result['components']['growth'], 80)


# ═══════════════════════════════════════════════════════════
# Constants 검증
# ═══════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_weights_sum_to_100(self):
        """가중치 합 = 1.0 (100%)."""
        total = sum(WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_rating_bands_complete(self):
        """등급 0-100 전체 커버."""
        self.assertEqual(len(RATING_BANDS), 4)
        self.assertEqual(RATING_BANDS[-1]['min'], 0)
        self.assertEqual(RATING_BANDS[0]['max'], 100)

    def test_phase1_thresholds(self):
        """Phase 1 임계값 설계값 일치."""
        self.assertEqual(PHASE1_MIN_YIELD, 2.5)
        self.assertEqual(PHASE1_MAX_PER, 15.0)
        self.assertEqual(PHASE1_MAX_PBR, 1.5)
        self.assertEqual(PHASE1_MIN_MARKET_CAP, 500_000_000_000)

    def test_phase3_thresholds(self):
        """Phase 3 임계값 설계값 일치."""
        self.assertEqual(PHASE3_MAX_PAYOUT, 80.0)
        self.assertEqual(PHASE3_MAX_DE_RATIO, 150.0)
        self.assertEqual(PHASE3_MIN_CURRENT_RATIO, 1.0)


# ═══════════════════════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════════════════════

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = ValueDividendReportGenerator(self.tmpdir)
        self.sample_results = [
            {
                'ticker': '005930',
                'name': '삼성전자',
                'score_data': {
                    'total_score': 85,
                    'rating': 'Excellent',
                    'action': '즉시 매수 고려',
                    'components': {'value': 90, 'growth': 80, 'sustainability': 85, 'quality': 70},
                },
            },
        ]

    def test_json_report(self):
        """JSON 리포트 생성."""
        path = self.reporter.generate_json(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-value-dividend')
        self.assertEqual(len(data['results']), 1)

    def test_markdown_report(self):
        """Markdown 리포트 생성."""
        path = self.reporter.generate_markdown(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('배당 가치주', content)
        self.assertIn('삼성전자', content)


if __name__ == '__main__':
    unittest.main()
