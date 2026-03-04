"""
kr-canslim-screener 테스트.
7-컴포넌트 개별 + 가중합 + M=0 게이트 + 최소 기준선.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'calculators'))

from calculators.earnings_calculator import calc_quarterly_growth, C_THRESHOLDS
from calculators.growth_calculator import calc_annual_cagr, A_CAGR_THRESHOLDS, STABILITY_BONUS, DECLINE_PENALTY
from calculators.new_highs_calculator import calc_52w_proximity, BREAKOUT_VOLUME_MULTIPLIER
from calculators.supply_demand_calculator import calc_volume_ratio, VOLUME_WINDOW
from calculators.leadership_calculator import calc_rs_rank, calc_period_returns, RS_WEIGHTS
from calculators.market_calculator import calc_market_direction, M_BEAR, M_BULL, M_STRONG_BULL, VKOSPI_DANGER
from scorer import (
    calc_institutional_score, calc_canslim_total,
    WEIGHTS, MIN_THRESHOLDS, RATING_BANDS,
    I_NET_BUY_BONUS, I_PENSION_BONUS,
)
from report_generator import CANSLIMReportGenerator


# ═══════════════════════════════════════════════════════════
# C: Current Earnings
# ═══════════════════════════════════════════════════════════

class TestEarningsCalculator(unittest.TestCase):

    def test_exceptional_growth(self):
        """EPS +50% & 매출 +25% → 100."""
        r = calc_quarterly_growth(150, 100, 125, 100)
        self.assertEqual(r['score'], 100)

    def test_strong_growth(self):
        """EPS +35% → 80."""
        r = calc_quarterly_growth(135, 100)
        self.assertEqual(r['score'], 80)

    def test_moderate_growth(self):
        """EPS +20% → 60."""
        r = calc_quarterly_growth(120, 100)
        self.assertEqual(r['score'], 60)

    def test_weak_growth(self):
        """EPS +12% → 40."""
        r = calc_quarterly_growth(112, 100)
        self.assertEqual(r['score'], 40)

    def test_minimal_growth(self):
        """EPS +5% → 20."""
        r = calc_quarterly_growth(105, 100)
        self.assertEqual(r['score'], 20)

    def test_turnaround(self):
        """적자 → 흑자 → 80."""
        r = calc_quarterly_growth(50, -10)
        self.assertEqual(r['score'], 80)

    def test_eps50_without_rev25(self):
        """EPS +60% 이지만 매출 +10% → 100 조건 미충족 → 80 (다음 tier)."""
        r = calc_quarterly_growth(160, 100, 110, 100)
        self.assertEqual(r['score'], 80)


# ═══════════════════════════════════════════════════════════
# A: Annual Growth
# ═══════════════════════════════════════════════════════════

class TestGrowthCalculator(unittest.TestCase):

    def test_high_cagr(self):
        """CAGR ~41% (100→200 over 2yr) → 90."""
        r = calc_annual_cagr([100, 150, 200])
        self.assertEqual(r['score'], 90 + STABILITY_BONUS)

    def test_moderate_cagr(self):
        """CAGR ~26% → 50 + 안정성 보너스 = 60."""
        r = calc_annual_cagr([100, 126, 160])
        self.assertIn(r['score'], [50 + STABILITY_BONUS, 60])

    def test_stability_bonus(self):
        """3년 모두 증가 → +10."""
        r = calc_annual_cagr([100, 120, 150])
        self.assertEqual(r['stability_adj'], STABILITY_BONUS)

    def test_decline_penalty(self):
        """1년 감소 → -10."""
        r = calc_annual_cagr([100, 80, 130])
        self.assertEqual(r['stability_adj'], DECLINE_PENALTY)

    def test_insufficient_data(self):
        """데이터 부족 → 기본 점수."""
        r = calc_annual_cagr([100, 200])
        self.assertEqual(r['score'], 20)


# ═══════════════════════════════════════════════════════════
# N: New Highs
# ═══════════════════════════════════════════════════════════

class TestNewHighsCalculator(unittest.TestCase):

    def test_at_high_with_breakout(self):
        """52주 고가 2% 이내 + 브레이크아웃 → 100."""
        r = calc_52w_proximity(98, 100, current_volume=2000, avg_volume_50d=1000)
        self.assertEqual(r['score'], 100)

    def test_near_high_no_breakout(self):
        """52주 고가 3% 이내 but 브레이크아웃 없음 → 80."""
        r = calc_52w_proximity(97, 100, current_volume=500, avg_volume_50d=1000)
        self.assertEqual(r['score'], 80)

    def test_moderate_distance(self):
        """고가 12% 하락 → 60."""
        r = calc_52w_proximity(88, 100)
        self.assertEqual(r['score'], 60)

    def test_far_from_high(self):
        """고가 30% 하락 → 20."""
        r = calc_52w_proximity(70, 100)
        self.assertEqual(r['score'], 20)


# ═══════════════════════════════════════════════════════════
# S: Supply/Demand
# ═══════════════════════════════════════════════════════════

class TestSupplyDemandCalculator(unittest.TestCase):

    def test_strong_accumulation(self):
        """Up/Down 비율 2.5 → 100."""
        prices = [100 + i * 0.5 for i in range(10)]  # 상승 추세
        volumes = [1000] * 10
        r = calc_volume_ratio(prices, volumes)
        self.assertGreaterEqual(r['score'], 80)

    def test_neutral(self):
        """Up/Down 비율 ~1.0."""
        prices = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101]
        volumes = [1000] * 10
        r = calc_volume_ratio(prices, volumes)
        self.assertIn(r['score'], [60, 80])

    def test_selling_pressure(self):
        """하락 추세 → 낮은 점수."""
        prices = [100 - i for i in range(10)]  # 하락 추세
        volumes = [1000] * 10
        r = calc_volume_ratio(prices, volumes)
        self.assertLessEqual(r['score'], 40)

    def test_insufficient_data(self):
        """데이터 부족."""
        r = calc_volume_ratio([100], [1000])
        self.assertEqual(r['score'], 20)


# ═══════════════════════════════════════════════════════════
# L: Leadership / RS Rank
# ═══════════════════════════════════════════════════════════

class TestLeadershipCalculator(unittest.TestCase):

    def test_top_performer(self):
        """RS Rank ≥ 90 → 100."""
        # weighted=24, all below → 100% rank
        r = calc_rs_rank({'3m': 30, '6m': 25, '9m': 20, '12m': 15},
                         all_stock_returns=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        self.assertEqual(r['score'], 100)

    def test_moderate_performer(self):
        """RS Rank 75."""
        r = calc_rs_rank({'3m': 10, '6m': 8, '9m': 6, '12m': 4},
                         all_stock_returns=[2, 4, 6, 8])
        self.assertGreaterEqual(r['score'], 60)

    def test_laggard(self):
        """RS Rank < 50 → 40."""
        r = calc_rs_rank({'3m': -5, '6m': -3, '9m': -2, '12m': -1},
                         all_stock_returns=[5, 10, 15, 20])
        self.assertLessEqual(r['score'], 40)

    def test_rs_weights(self):
        """Minervini 가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(RS_WEIGHTS.values()), 1.0, places=5)

    def test_period_returns_structure(self):
        """기간별 수익률 구조."""
        prices = list(range(100, 360))  # 260 prices
        returns = calc_period_returns(prices)
        self.assertIn('3m', returns)
        self.assertIn('12m', returns)


# ═══════════════════════════════════════════════════════════
# I: Institutional
# ═══════════════════════════════════════════════════════════

class TestInstitutionalScore(unittest.TestCase):

    def test_ideal_foreign(self):
        """외국인 20-50% + 순매수 → 100 (캡)."""
        r = calc_institutional_score(30.0, net_buying_days=10)
        self.assertEqual(r['score'], 100)  # capped at 100

    def test_moderate_foreign(self):
        """외국인 15% + 순매수 → 80."""
        r = calc_institutional_score(15.0, net_buying_days=10)
        self.assertGreaterEqual(r['score'], 80)

    def test_pension_bonus(self):
        """연기금 보너스."""
        r = calc_institutional_score(30.0, net_buying_days=10, pension_buying=True)
        self.assertIn('pension', r['bonuses'])

    def test_selling_penalty(self):
        """외국인 순매도 10일+ → 20."""
        r = calc_institutional_score(30.0, selling_days=15)
        self.assertEqual(r['score'], 20)


# ═══════════════════════════════════════════════════════════
# M: Market Direction
# ═══════════════════════════════════════════════════════════

class TestMarketCalculator(unittest.TestCase):

    def test_strong_bull(self):
        """KOSPI > EMA50 + breadth 70 + regime Expansion → 100."""
        r = calc_market_direction(True, vkospi=15, breadth_score=70, regime='Expansion')
        self.assertEqual(r['score'], M_STRONG_BULL)

    def test_bull(self):
        """KOSPI > EMA50 + risk Yellow → 80."""
        r = calc_market_direction(True, vkospi=18, risk_zone='Yellow')
        self.assertEqual(r['score'], M_BULL)

    def test_critical_gate(self):
        """KOSPI < EMA50 + VKOSPI > 25 → 0 (GATE)."""
        r = calc_market_direction(False, vkospi=30)
        self.assertEqual(r['score'], M_BEAR)
        self.assertTrue(r['is_critical_gate'])

    def test_weak_market(self):
        """KOSPI < EMA50 + breadth 45 → 40."""
        r = calc_market_direction(False, breadth_score=45)
        self.assertEqual(r['score'], 40)


# ═══════════════════════════════════════════════════════════
# CANSLIM 종합 스코어
# ═══════════════════════════════════════════════════════════

class TestCANSLIMScorer(unittest.TestCase):

    def test_exceptional_plus(self):
        """모든 컴포넌트 90+ → Exceptional+."""
        comps = {'C': 95, 'A': 95, 'N': 90, 'S': 90, 'L': 95, 'I': 90, 'M': 100}
        r = calc_canslim_total(comps)
        self.assertGreaterEqual(r['total_score'], 90)
        self.assertEqual(r['rating'], 'Exceptional+')

    def test_m_gate_blocks(self):
        """M = 0 → 전체 0점."""
        comps = {'C': 100, 'A': 100, 'N': 100, 'S': 100, 'L': 100, 'I': 100, 'M': 0}
        r = calc_canslim_total(comps)
        self.assertEqual(r['total_score'], 0)
        self.assertTrue(r['is_m_gate'])

    def test_min_threshold_failure(self):
        """L < 70 → 기준선 미달, 등급 하락."""
        comps = {'C': 80, 'A': 80, 'N': 80, 'S': 80, 'L': 50, 'I': 80, 'M': 80}
        r = calc_canslim_total(comps)
        self.assertIn('L', r['min_threshold_failures'])

    def test_average_scores(self):
        """70점 내외 → Strong."""
        comps = {'C': 70, 'A': 75, 'N': 70, 'S': 70, 'L': 75, 'I': 70, 'M': 80}
        r = calc_canslim_total(comps)
        self.assertIn(r['rating'], ['Strong', 'Exceptional'])

    def test_below_average(self):
        """낮은 점수 → Below Average."""
        comps = {'C': 30, 'A': 30, 'N': 30, 'S': 30, 'L': 30, 'I': 30, 'M': 40}
        r = calc_canslim_total(comps)
        self.assertEqual(r['rating'], 'Below Average')

    def test_components_preserved(self):
        """컴포넌트 값 보존."""
        comps = {'C': 80, 'A': 90, 'N': 70, 'S': 60, 'L': 85, 'I': 75, 'M': 80}
        r = calc_canslim_total(comps)
        self.assertEqual(r['components']['C'], 80)
        self.assertEqual(r['components']['A'], 90)


# ═══════════════════════════════════════════════════════════
# Constants 검증
# ═══════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_weights_sum(self):
        """CANSLIM 가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=5)

    def test_seven_components(self):
        """7개 컴포넌트."""
        self.assertEqual(len(WEIGHTS), 7)
        for k in 'CANSLIM':
            self.assertIn(k, WEIGHTS)

    def test_min_thresholds(self):
        """최소 기준선 설계값."""
        self.assertEqual(MIN_THRESHOLDS['C'], 60)
        self.assertEqual(MIN_THRESHOLDS['L'], 70)
        self.assertEqual(MIN_THRESHOLDS['M'], 40)

    def test_vkospi_danger(self):
        """VKOSPI 위험 기준 25."""
        self.assertEqual(VKOSPI_DANGER, 25)

    def test_rating_bands(self):
        """5개 등급."""
        self.assertEqual(len(RATING_BANDS), 5)


# ═══════════════════════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════════════════════

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = CANSLIMReportGenerator(self.tmpdir)
        self.sample = [{'ticker': '005930', 'name': '삼성전자',
                         'score_data': {'total_score': 85, 'rating': 'Exceptional',
                                        'action': '강한 매수', 'is_m_gate': False,
                                        'min_threshold_failures': [],
                                        'components': {'C': 80, 'A': 90, 'N': 85, 'S': 80, 'L': 90, 'I': 75, 'M': 80}}}]

    def test_json_report(self):
        path = self.reporter.generate_json(self.sample)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-canslim-screener')

    def test_markdown_report(self):
        path = self.reporter.generate_markdown(self.sample)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('CANSLIM', content)


if __name__ == '__main__':
    unittest.main()
