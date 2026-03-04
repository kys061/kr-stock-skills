"""
kr-market-top-detector 테스트.
7-컴포넌트 스코어링 + 분배일 + 선도주 + 방어 로테이션 + 외국인 + 리포트.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from distribution_calculator import (
    is_distribution_day,
    count_distribution_days,
    score_single_index,
    score_dual_index,
    DistributionDayCalculator,
    DISTRIBUTION_THRESHOLD,
    WINDOW,
)
from leading_stock_calculator import (
    KR_LEADING_STOCKS,
    calc_pct_below_50ma,
    calc_avg_drawdown,
    calc_declining_count,
    score_leading_stocks,
    LeadingStockCalculator,
)
from defensive_rotation_calculator import (
    KR_DEFENSIVE_SECTORS,
    KR_GROWTH_SECTORS,
    calc_relative_performance,
    score_rotation,
    DefensiveRotationCalculator,
)
from foreign_flow_calculator import (
    calc_consecutive_sell_days,
    calc_sell_intensity,
    score_foreign_flow,
    ForeignFlowCalculator,
)
from scorer import (
    COMPONENT_WEIGHTS,
    RISK_ZONES,
    classify_risk_zone,
    score_index_technical,
    score_sentiment,
    score_breadth_divergence,
    MarketTopScorer,
)
from report_generator import ReportGenerator


# ── 분배일 테스트 ────────────────────────────────────

class TestDistributionDay(unittest.TestCase):

    def test_is_distribution_day_true(self):
        """종가 -0.3%, 거래량 증가 → 분배일."""
        self.assertTrue(is_distribution_day(997, 1000, 150, 100))

    def test_is_distribution_day_false_volume(self):
        """종가 하락이지만 거래량 감소 → 비분배일."""
        self.assertFalse(is_distribution_day(997, 1000, 80, 100))

    def test_is_distribution_day_false_price(self):
        """종가 상승 → 비분배일."""
        self.assertFalse(is_distribution_day(1005, 1000, 150, 100))

    def test_boundary_threshold(self):
        """정확히 -0.2% → 분배일."""
        # 1000 * (1 - 0.002) = 998
        self.assertTrue(is_distribution_day(998, 1000, 100, 100))

    def test_count_distribution_days(self):
        """분배일 카운팅."""
        closes = [1000, 997, 1000, 995, 1000, 993]
        volumes = [100, 110, 100, 120, 100, 130]
        count = count_distribution_days(closes, volumes, window=5)
        self.assertGreaterEqual(count, 2)

    def test_count_empty(self):
        """빈 데이터 → 0."""
        self.assertEqual(count_distribution_days([], []), 0)


class TestDistributionScoring(unittest.TestCase):

    def test_score_zero(self):
        """0 분배일 → 0점."""
        self.assertEqual(score_single_index(0), 0.0)

    def test_score_five(self):
        """5 분배일 → 70점."""
        self.assertEqual(score_single_index(5), 70.0)

    def test_score_seven_plus(self):
        """7+ 분배일 → 100점."""
        self.assertEqual(score_single_index(8), 100.0)

    def test_dual_index(self):
        """이중 지수 복합 점수: max*0.7 + min*0.3."""
        result = score_dual_index(5, 3)  # 70*0.7 + 30*0.3 = 49+9 = 58
        self.assertAlmostEqual(result, 58.0)

    def test_dual_index_same(self):
        """두 지수 동일 → score*1.0."""
        result = score_dual_index(4, 4)
        self.assertAlmostEqual(result, 50.0)


class TestDistributionCalculator(unittest.TestCase):

    def test_class_usage(self):
        """Calculator 클래스 사용."""
        calc = DistributionDayCalculator()
        self.assertEqual(calc.score(3, 2), 30 * 0.7 + 20 * 0.3)


# ── 선도주 건전성 테스트 ──────────────────────────────

class TestLeadingStockMetrics(unittest.TestCase):

    def test_pct_below_50ma_all_below(self):
        """모두 50MA 아래 → 1.0."""
        data = [{'close': 90, 'ma50': 100}] * 8
        self.assertAlmostEqual(calc_pct_below_50ma(data), 1.0)

    def test_pct_below_50ma_none_below(self):
        """모두 50MA 위 → 0.0."""
        data = [{'close': 110, 'ma50': 100}] * 8
        self.assertAlmostEqual(calc_pct_below_50ma(data), 0.0)

    def test_avg_drawdown(self):
        """평균 하락률 계산."""
        data = [
            {'close': 90, 'high_52w': 100},
            {'close': 80, 'high_52w': 100},
        ]
        self.assertAlmostEqual(calc_avg_drawdown(data), -0.15)

    def test_declining_count(self):
        """하락 종목 수."""
        data = [
            {'weekly_return': -0.02},
            {'weekly_return': 0.03},
            {'weekly_return': -0.01},
        ]
        self.assertEqual(calc_declining_count(data), 2)


class TestLeadingStockScoring(unittest.TestCase):

    def test_healthy(self):
        """건전 → 낮은 점수."""
        score = score_leading_stocks(0.0, 0.0, 0, 8)
        self.assertLessEqual(score, 10)

    def test_deteriorating(self):
        """악화 → 높은 점수."""
        score = score_leading_stocks(0.88, -0.25, 7, 8)
        self.assertGreaterEqual(score, 80)

    def test_moderate(self):
        """중간 수준."""
        score = score_leading_stocks(0.50, -0.10, 4, 8)
        self.assertGreater(score, 30)
        self.assertLess(score, 80)


class TestLeadingStockCalculator(unittest.TestCase):

    def test_calculate(self):
        """종합 계산."""
        calc = LeadingStockCalculator()
        data = [
            {'close': 90, 'ma50': 100, 'high_52w': 100, 'weekly_return': -0.02},
            {'close': 110, 'ma50': 100, 'high_52w': 120, 'weekly_return': 0.01},
        ]
        health = calc.calculate(data)
        self.assertIn('pct_below_50ma', health)
        self.assertIn('avg_drawdown', health)
        self.assertEqual(health['total'], 2)


# ── 방어 섹터 로테이션 테스트 ──────────────────────────

class TestDefensiveRotation(unittest.TestCase):

    def test_growth_outperform(self):
        """성장 outperform → 낮은 점수."""
        score = score_rotation(-0.05)  # -5%
        self.assertLess(score, 10)

    def test_defensive_outperform(self):
        """방어 outperform +5% → 높은 점수."""
        score = score_rotation(0.05)
        self.assertGreaterEqual(score, 75)

    def test_neutral(self):
        """중립 → 중간 점수."""
        score = score_rotation(0.0)
        self.assertAlmostEqual(score, 30.0)


class TestDefensiveRotationCalculator(unittest.TestCase):

    def test_calculate(self):
        """업종별 수익률 → 상대 성과."""
        calc = DefensiveRotationCalculator()
        sector_returns = {
            '1013': 0.03, '1001': 0.02, '1005': 0.01,  # 방어 평균: 2%
            '1009': -0.01, '1021': 0.00, '1012': -0.02,  # 성장 평균: -1%
        }
        result = calc.calculate(sector_returns)
        self.assertGreater(result['relative_performance'], 0)
        self.assertAlmostEqual(result['defensive_avg'], 0.02)


# ── 외국인 수급 테스트 ────────────────────────────────

class TestForeignFlow(unittest.TestCase):

    def test_consecutive_sell_zero(self):
        """순매수 상태 → 0일."""
        self.assertEqual(calc_consecutive_sell_days([100, 200, 50]), 0)

    def test_consecutive_sell_three(self):
        """3일 연속 순매도."""
        self.assertEqual(
            calc_consecutive_sell_days([100, -50, -30, -20]), 3)

    def test_consecutive_sell_mixed(self):
        """중간에 순매수 끊김."""
        self.assertEqual(
            calc_consecutive_sell_days([-50, 10, -30, -20]), 2)

    def test_sell_intensity(self):
        """매도 강도 계산."""
        data = [10, 10, 10, 10, 10, -100, -100, -100, -100, -100]
        intensity = calc_sell_intensity(data, recent=5, avg_window=10)
        self.assertGreater(intensity, 1.0)

    def test_sell_intensity_empty(self):
        """빈 데이터 → 0."""
        self.assertEqual(calc_sell_intensity([], 5, 20), 0.0)


class TestForeignFlowScoring(unittest.TestCase):

    def test_no_sell(self):
        """순매도 없음 → 낮은 점수."""
        score = score_foreign_flow(0, 0.0)
        self.assertLessEqual(score, 10)

    def test_moderate_sell(self):
        """5일 순매도 → 50점 범위."""
        score = score_foreign_flow(5, 1.0)
        self.assertGreaterEqual(score, 45)
        self.assertLessEqual(score, 60)

    def test_strong_sell(self):
        """10일+ 순매도 + 높은 강도 → 75+ 점수."""
        score = score_foreign_flow(12, 2.5)
        self.assertGreaterEqual(score, 75)


class TestForeignFlowCalculator(unittest.TestCase):

    def test_calculate_inflow(self):
        """순매수 → inflow 시그널."""
        calc = ForeignFlowCalculator()
        result = calc.calculate([100, 200, 150, 80, 50])
        self.assertEqual(result['signal'], 'inflow')
        self.assertEqual(result['consecutive_sell_days'], 0)

    def test_calculate_strong_outflow(self):
        """10일+ 강한 순매도 → strong_outflow."""
        calc = ForeignFlowCalculator()
        # 초기 소량 매수 → 소량 매도 → 최근 대량 매도 (강도 급등)
        data = [1] * 20 + [-10] * 7 + [-500] * 5
        result = calc.calculate(data)
        self.assertEqual(result['signal'], 'strong_outflow')


# ── 스코어러 테스트 ───────────────────────────────────

class TestIndexTechnical(unittest.TestCase):

    def test_no_signals(self):
        """신호 없음 → 0점."""
        self.assertEqual(score_index_technical({}), 0)

    def test_all_signals(self):
        """모든 신호 → 100점 (capped)."""
        signals = {
            'ma10_below_ma21': True,
            'ma21_below_ma50': True,
            'ma50_below_ma200': True,
            'failed_rally': True,
            'lower_low': True,
            'declining_volume_rise': True,
        }
        self.assertEqual(score_index_technical(signals), 100)

    def test_partial_signals(self):
        """일부 신호."""
        signals = {'ma10_below_ma21': True, 'failed_rally': True}
        self.assertEqual(score_index_technical(signals), 35)


class TestSentiment(unittest.TestCase):

    def test_complacency(self):
        """VKOSPI < 13 + 고레버리지 → 높은 점수."""
        score = score_sentiment(11.0, 0.20)
        self.assertEqual(score, 70.0)  # 40 + 30

    def test_fear(self):
        """VKOSPI > 25 + 디레버리징 → 0 (clamped)."""
        score = score_sentiment(30.0, -0.10)
        self.assertEqual(score, 0.0)  # -10 + -10 = -20 → clamped 0

    def test_normal(self):
        """정상 VKOSPI + 정상 신용 → 20점."""
        score = score_sentiment(15.0, 0.0)
        self.assertEqual(score, 20.0)


class TestBreadthDivergence(unittest.TestCase):

    def test_near_high_healthy(self):
        """고점 근처 + 시장폭 건전 → 낮은 점수."""
        self.assertEqual(score_breadth_divergence(True, 0.75), 10.0)

    def test_near_high_divergence(self):
        """고점 근처 + 시장폭 < 45% → 높은 점수."""
        self.assertEqual(score_breadth_divergence(True, 0.42), 70.0)

    def test_not_near_high(self):
        """고점 아님 → 10점 (조정 중)."""
        self.assertEqual(score_breadth_divergence(False, 0.30), 10.0)


class TestRiskZoneMapping(unittest.TestCase):

    def test_green(self):
        zone = classify_risk_zone(10)
        self.assertEqual(zone['name'], 'Green')

    def test_yellow(self):
        zone = classify_risk_zone(35)
        self.assertEqual(zone['name'], 'Yellow')

    def test_orange(self):
        zone = classify_risk_zone(50)
        self.assertEqual(zone['name'], 'Orange')

    def test_red(self):
        zone = classify_risk_zone(70)
        self.assertEqual(zone['name'], 'Red')

    def test_critical(self):
        zone = classify_risk_zone(90)
        self.assertEqual(zone['name'], 'Critical')

    def test_clamp_low(self):
        zone = classify_risk_zone(-10)
        self.assertEqual(zone['name'], 'Green')

    def test_clamp_high(self):
        zone = classify_risk_zone(150)
        self.assertEqual(zone['name'], 'Critical')


class TestMarketTopScorer(unittest.TestCase):

    def test_all_components(self):
        """7 컴포넌트 종합 스코어링."""
        components = {
            'distribution': 70,
            'leading_stock': 60,
            'defensive_rotation': 50,
            'breadth_divergence': 40,
            'index_technical': 35,
            'sentiment': 30,
            'foreign_flow': 80,
        }
        scorer = MarketTopScorer()
        result = scorer.score(components)
        self.assertIn('composite_score', result)
        self.assertIn('risk_zone', result)
        self.assertGreater(result['composite_score'], 0)
        self.assertLessEqual(result['composite_score'], 100)

    def test_all_zero(self):
        """모든 컴포넌트 0 → Green."""
        components = {k: 0 for k in COMPONENT_WEIGHTS}
        scorer = MarketTopScorer()
        result = scorer.score(components)
        self.assertEqual(result['composite_score'], 0.0)
        self.assertEqual(result['risk_zone']['name'], 'Green')

    def test_all_hundred(self):
        """모든 컴포넌트 100 → Critical."""
        components = {k: 100 for k in COMPONENT_WEIGHTS}
        scorer = MarketTopScorer()
        result = scorer.score(components)
        self.assertEqual(result['composite_score'], 100.0)
        self.assertEqual(result['risk_zone']['name'], 'Critical')

    def test_partial_components(self):
        """일부 컴포넌트만 → 정규화."""
        components = {'distribution': 80, 'foreign_flow': 60}
        scorer = MarketTopScorer()
        result = scorer.score(components)
        self.assertGreater(result['composite_score'], 0)

    def test_weights_sum_to_1(self):
        """가중치 합계 = 1.0."""
        total = sum(COMPONENT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)


# ── 리포트 생성 테스트 ────────────────────────────────

class TestReportGenerator(unittest.TestCase):

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'scored': {
                    'composite_score': 55.0,
                    'risk_zone': {
                        'name': 'Orange',
                        'label': '위험 상승',
                        'budget': '60-75%',
                        'action': '약한 포지션 이익실현',
                    },
                    'components': {
                        'distribution': 70,
                        'leading_stock': 50,
                        'defensive_rotation': 40,
                        'breadth_divergence': 60,
                        'index_technical': 35,
                        'sentiment': 45,
                        'foreign_flow': 75,
                    },
                    'weights': dict(COMPONENT_WEIGHTS),
                },
            }
            output = reporter.generate(result)
            self.assertTrue(os.path.exists(output['json_path']))
            self.assertTrue(os.path.exists(output['md_path']))

            with open(output['json_path'], 'r') as f:
                data = json.load(f)
            self.assertEqual(data['composite_score'], 55.0)
            self.assertEqual(data['risk_zone'], 'Orange')

    def test_md_sections(self):
        """Markdown 핵심 섹션 확인."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'scored': {
                    'composite_score': 30.0,
                    'risk_zone': {'name': 'Yellow', 'label': '초기 경고',
                                  'budget': '80-90%', 'action': '손절 강화'},
                    'components': {},
                    'weights': dict(COMPONENT_WEIGHTS),
                },
            }
            output = reporter.generate(result)
            md = output['md_content']
            self.assertIn('종합 결과', md)
            self.assertIn('7-컴포넌트 상세', md)
            self.assertIn('리스크 존 가이드', md)


# ── 상수 검증 ─────────────────────────────────────────

class TestConstants(unittest.TestCase):

    def test_seven_components(self):
        """7개 컴포넌트."""
        self.assertEqual(len(COMPONENT_WEIGHTS), 7)

    def test_eight_leading_stocks(self):
        """선도주 8종목."""
        self.assertEqual(len(KR_LEADING_STOCKS), 8)

    def test_defensive_sectors(self):
        """방어 섹터 3개."""
        self.assertEqual(len(KR_DEFENSIVE_SECTORS), 3)

    def test_growth_sectors(self):
        """성장 섹터 3개."""
        self.assertEqual(len(KR_GROWTH_SECTORS), 3)

    def test_risk_zones_coverage(self):
        """리스크 존이 0-100을 커버."""
        for score in [0, 10, 20, 21, 40, 41, 60, 61, 80, 81, 100]:
            zone = classify_risk_zone(score)
            self.assertIn(zone['name'],
                          ['Green', 'Yellow', 'Orange', 'Red', 'Critical'])

    def test_distribution_threshold(self):
        """분배일 임계값 = -0.2%."""
        self.assertAlmostEqual(DISTRIBUTION_THRESHOLD, -0.002)


if __name__ == '__main__':
    unittest.main()
