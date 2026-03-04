"""kr-pair-trade 테스트 (~32 tests).

TestCorrelationAnalyzer:    상관분석 + 안정성
TestCointegrationTester:    ADF + Half-Life
TestSpreadAnalyzer:         Z-Score + 시그널
TestZScore:                 Z-Score 구간별 분류
TestHalfLife:               Half-Life 계산
TestPairTradeScorer:        종합 스코어 + 등급
TestReportGenerator:        JSON/Markdown 출력
TestConstants:              가중치/파라미터 검증
"""

import os
import sys
import json
import math
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from correlation_analyzer import (
    calc_correlation, calc_rolling_correlation, check_stability,
    score_correlation,
    CORRELATION_MIN, ROLLING_WINDOW, STABILITY_THRESHOLD,
    STABILITY_BONUS, STABILITY_PENALTY,
)
from cointegration_tester import (
    calc_beta, calc_spread, run_adf_test, calc_half_life,
    score_cointegration, _simple_adf,
    ADF_PVALUE_THRESHOLD, HALFLIFE_BONUS_FAST,
)
from spread_analyzer import (
    calc_zscore, classify_signal, score_zscore, calc_risk_reward,
    ZSCORE_STOP, ZSCORE_ENTRY, ZSCORE_WATCH,
)
from scorer import (
    calc_pair_total, calc_risk_reward_score,
    WEIGHTS, RATING_BANDS, MIN_CORRELATION, COINTEGRATION_REQUIRED,
    KR_ROUND_TRIP_COST,
)
from report_generator import PairTradeReportGenerator


def _generate_correlated_prices(n=500, corr_target=0.85):
    """상관된 가격 데이터 생성 (테스트용)."""
    import random
    random.seed(42)
    base = [100]
    for _ in range(n - 1):
        base.append(base[-1] + random.gauss(0.05, 1))

    # 상관된 두 번째 시리즈
    prices_a = base[:]
    prices_b = [p * 0.5 + random.gauss(0, 0.5 * (1 - corr_target)) for p in base]
    return prices_a, prices_b


def _generate_cointegrated_prices(n=500):
    """공적분 관계 가격 생성 (평균 회귀 스프레드)."""
    import random
    random.seed(42)
    # 공통 트렌드
    trend = [100]
    for _ in range(n - 1):
        trend.append(trend[-1] + random.gauss(0.05, 0.5))

    # A = trend + noise
    prices_a = [t + random.gauss(0, 0.3) for t in trend]
    # B = 0.5 * trend + mean-reverting spread
    spread_val = 0
    prices_b = []
    for t in trend:
        spread_val = 0.8 * spread_val + random.gauss(0, 0.5)
        prices_b.append(0.5 * t + spread_val + 50)

    return prices_a, prices_b


# ═══════════════════════════════════════════════════════════════
# 1. TestCorrelationAnalyzer (5 tests)
# ═══════════════════════════════════════════════════════════════
class TestCorrelationAnalyzer(unittest.TestCase):
    """상관 분석 테스트."""

    def test_perfect_correlation(self):
        """완벽 양의 상관 = 1.0."""
        a = list(range(100, 200))
        b = [x * 2 for x in a]
        corr = calc_correlation(a, b)
        self.assertAlmostEqual(corr, 1.0, places=4)

    def test_perfect_negative(self):
        """완벽 음의 상관 = -1.0."""
        a = list(range(100, 200))
        b = [300 - x for x in a]
        corr = calc_correlation(a, b)
        self.assertAlmostEqual(corr, -1.0, places=4)

    def test_short_data(self):
        """데이터 부족 시 0.0."""
        corr = calc_correlation([1, 2, 3], [4, 5, 6])
        self.assertEqual(corr, 0.0)

    def test_score_strong_stable(self):
        """강한 + 안정적 상관 → 75 + 10 = 85."""
        stability = {'is_stable': True}
        r = score_correlation(0.80, stability)
        self.assertEqual(r['score'], 85)
        self.assertEqual(r['grade'], '강함')

    def test_score_strong_unstable(self):
        """강한 + 불안정 상관 → 75 - 15 = 60."""
        stability = {'is_stable': False}
        r = score_correlation(0.80, stability)
        self.assertEqual(r['score'], 60)


# ═══════════════════════════════════════════════════════════════
# 2. TestCointegrationTester (5 tests)
# ═══════════════════════════════════════════════════════════════
class TestCointegrationTester(unittest.TestCase):
    """공적분 테스트."""

    def test_beta_calculation(self):
        """OLS 베타 계산."""
        a = [100 + i * 2 for i in range(100)]
        b = [50 + i for i in range(100)]
        beta = calc_beta(a, b)
        self.assertAlmostEqual(beta, 2.0, places=1)

    def test_spread_calculation(self):
        """스프레드 = A - beta * B."""
        a = [100, 200, 300]
        b = [50, 100, 150]
        spread = calc_spread(a, b, beta=2.0)
        self.assertEqual(spread, [0, 0, 0])

    def test_simple_adf_stationary(self):
        """정상 시계열 → 공적분 확인."""
        # 평균 회귀 시계열 생성
        import random
        random.seed(42)
        spread = [0]
        for _ in range(499):
            spread.append(0.5 * spread[-1] + random.gauss(0, 1))
        result = _simple_adf(spread)
        self.assertTrue(result['is_cointegrated'])
        self.assertLess(result['p_value'], 0.05)

    def test_simple_adf_nonstationary(self):
        """비정상 시계열 → 공적분 없음."""
        # 랜덤워크 (단위근)
        import random
        random.seed(42)
        spread = [0]
        for _ in range(499):
            spread.append(spread[-1] + random.gauss(0, 1))
        result = _simple_adf(spread)
        self.assertFalse(result['is_cointegrated'])

    def test_score_strong_cointegration(self):
        """p < 0.01 → 100점."""
        r = score_cointegration(0.005, half_life=25)
        self.assertEqual(r['score'], 100)  # 100 (no HL bonus since already 100)
        self.assertEqual(r['grade'], '★★★ 매우 강함')


# ═══════════════════════════════════════════════════════════════
# 3. TestSpreadAnalyzer (6 tests)
# ═══════════════════════════════════════════════════════════════
class TestSpreadAnalyzer(unittest.TestCase):
    """Z-Score 분석 테스트."""

    def test_zscore_normal(self):
        """정상 범위 스프레드 → Z ≈ 0."""
        spread = [0.0] * 252
        r = calc_zscore(spread)
        self.assertEqual(r['zscore'], 0)

    def test_zscore_extreme(self):
        """극단 스프레드 → |Z| 높음."""
        spread = [0.0] * 251 + [10.0]
        r = calc_zscore(spread)
        self.assertGreater(abs(r['zscore']), 2.0)

    def test_signal_entry_negative(self):
        """Z < -2.0 → LONG_A_SHORT_B."""
        signal = classify_signal(-2.5)
        self.assertEqual(signal['signal'], 'ENTRY')
        self.assertEqual(signal['direction'], 'LONG_A_SHORT_B')

    def test_signal_entry_positive(self):
        """Z > +2.0 → SHORT_A_LONG_B."""
        signal = classify_signal(2.5)
        self.assertEqual(signal['signal'], 'ENTRY')
        self.assertEqual(signal['direction'], 'SHORT_A_LONG_B')

    def test_signal_stop(self):
        """Z > 3.0 → STOP."""
        signal = classify_signal(3.5)
        self.assertEqual(signal['signal'], 'STOP')

    def test_signal_exit(self):
        """Z ≈ 0 → EXIT."""
        signal = classify_signal(0.3)
        self.assertEqual(signal['signal'], 'EXIT')


# ═══════════════════════════════════════════════════════════════
# 4. TestZScore (4 tests)
# ═══════════════════════════════════════════════════════════════
class TestZScore(unittest.TestCase):
    """Z-Score 점수 구간별 테스트."""

    def test_entry_score(self):
        """|Z| 2.0-3.0 → 100."""
        r = score_zscore(2.5)
        self.assertEqual(r['score'], 100)
        self.assertEqual(r['signal'], 'ENTRY')

    def test_watch_score(self):
        """|Z| 1.5-2.0 → 70."""
        r = score_zscore(1.7)
        self.assertEqual(r['score'], 70)
        self.assertEqual(r['signal'], 'WATCH')

    def test_normal_score(self):
        """|Z| 0-1.5 → 40."""
        r = score_zscore(1.0)
        self.assertEqual(r['score'], 40)
        self.assertEqual(r['signal'], 'NORMAL')

    def test_stop_score(self):
        """|Z| > 3.0 → 20."""
        r = score_zscore(3.5)
        self.assertEqual(r['score'], 20)
        self.assertEqual(r['signal'], 'STOP')


# ═══════════════════════════════════════════════════════════════
# 5. TestHalfLife (3 tests)
# ═══════════════════════════════════════════════════════════════
class TestHalfLife(unittest.TestCase):
    """Half-Life 계산 테스트."""

    def test_fast_reversion(self):
        """빠른 회귀 → HL < 30."""
        import random
        random.seed(42)
        spread = [0]
        for _ in range(499):
            spread.append(0.3 * spread[-1] + random.gauss(0, 1))
        hl = calc_half_life(spread)
        self.assertLess(hl, 30)

    def test_slow_reversion(self):
        """느린 회귀 → HL > 5 (AR(1)=0.95, 이론값 ~13.5)."""
        import random
        random.seed(42)
        spread = [0]
        for _ in range(499):
            spread.append(0.95 * spread[-1] + random.gauss(0, 1))
        hl = calc_half_life(spread)
        self.assertGreater(hl, 5)

    def test_random_walk(self):
        """랜덤워크 → HL > 60 (단위근에 가까움, 매우 느린 회귀)."""
        import random
        random.seed(42)
        spread = [0]
        for _ in range(499):
            spread.append(spread[-1] + random.gauss(0, 1))
        hl = calc_half_life(spread)
        self.assertGreater(hl, 60)


# ═══════════════════════════════════════════════════════════════
# 6. TestPairTradeScorer (4 tests)
# ═══════════════════════════════════════════════════════════════
class TestPairTradeScorer(unittest.TestCase):
    """종합 페어 스코어 테스트."""

    def test_prime_pair(self):
        """Prime Pair = 85+."""
        components = {
            'correlation': 100,
            'cointegration': 100,
            'zscore_signal': 100,
            'risk_reward': 80,
        }
        r = calc_pair_total(components, correlation=0.92, is_cointegrated=True)
        # 100*0.30 + 100*0.30 + 100*0.25 + 80*0.15 = 30+30+25+12 = 97
        self.assertEqual(r['total_score'], 97)
        self.assertEqual(r['rating'], 'Prime Pair')

    def test_strong_pair(self):
        """Strong Pair = 70-84."""
        components = {
            'correlation': 85,
            'cointegration': 70,
            'zscore_signal': 70,
            'risk_reward': 60,
        }
        r = calc_pair_total(components, correlation=0.80, is_cointegrated=True)
        # 85*0.30 + 70*0.30 + 70*0.25 + 60*0.15 = 25.5+21+17.5+9 = 73
        self.assertEqual(r['total_score'], 73)
        self.assertEqual(r['rating'], 'Strong Pair')

    def test_correlation_gate_fail(self):
        """상관계수 부족 → No Pair (0점)."""
        components = {
            'correlation': 100,
            'cointegration': 100,
            'zscore_signal': 100,
            'risk_reward': 100,
        }
        r = calc_pair_total(components, correlation=0.55, is_cointegrated=True)
        self.assertEqual(r['total_score'], 0)
        self.assertEqual(r['rating'], 'No Pair')
        self.assertFalse(r['gates']['correlation_ok'])

    def test_cointegration_gate_fail(self):
        """공적분 미통과 → No Pair (0점)."""
        components = {
            'correlation': 100,
            'cointegration': 20,
            'zscore_signal': 100,
            'risk_reward': 80,
        }
        r = calc_pair_total(components, correlation=0.85, is_cointegrated=False)
        self.assertEqual(r['total_score'], 0)
        self.assertEqual(r['rating'], 'No Pair')


# ═══════════════════════════════════════════════════════════════
# 7. TestReportGenerator (2 tests)
# ═══════════════════════════════════════════════════════════════
class TestReportGenerator(unittest.TestCase):
    """리포트 생성 테스트."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_json_report(self):
        results = [{
            'ticker_a': '005930', 'ticker_b': '000660',
            'correlation': 0.85, 'is_cointegrated': True,
            'zscore': -2.1, 'half_life': 25,
            'signal': {'signal': 'ENTRY'},
            'score_data': {
                'total_score': 88, 'rating': 'Prime Pair',
            },
        }]
        gen = PairTradeReportGenerator(self.tmpdir)
        path = gen.generate_json(results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-pair-trade')
        self.assertEqual(data['summary']['prime'], 1)

    def test_markdown_report(self):
        results = [{
            'ticker_a': '005930', 'ticker_b': '000660',
            'correlation': 0.85, 'is_cointegrated': True,
            'zscore': -2.1, 'half_life': 25,
            'signal': {'signal': 'ENTRY'},
            'score_data': {
                'total_score': 88, 'rating': 'Prime Pair',
            },
        }]
        gen = PairTradeReportGenerator(self.tmpdir)
        path = gen.generate_markdown(results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('한국 페어 트레이딩 스크리닝 리포트', content)


# ═══════════════════════════════════════════════════════════════
# 8. TestConstants (3 tests)
# ═══════════════════════════════════════════════════════════════
class TestConstants(unittest.TestCase):
    """가중치/파라미터 디자인 검증."""

    def test_weights_sum_100(self):
        """4-컴포넌트 가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=2)

    def test_pair_parameters(self):
        """한국 페어 트레이딩 파라미터 설계값 검증."""
        self.assertEqual(MIN_CORRELATION, 0.70)
        self.assertTrue(COINTEGRATION_REQUIRED)
        self.assertAlmostEqual(KR_ROUND_TRIP_COST, 0.0025, places=4)
        self.assertEqual(ZSCORE_ENTRY, 2.0)
        self.assertEqual(ZSCORE_STOP, 3.0)
        self.assertEqual(ADF_PVALUE_THRESHOLD, 0.05)

    def test_rating_bands(self):
        """등급 범위 연속성 + 5단계."""
        self.assertEqual(len(RATING_BANDS), 5)
        self.assertEqual(RATING_BANDS[0]['name'], 'Prime Pair')
        self.assertEqual(RATING_BANDS[-1]['name'], 'No Pair')
        for i in range(len(RATING_BANDS) - 1):
            self.assertEqual(RATING_BANDS[i]['min'] - 1, RATING_BANDS[i + 1]['max'])


if __name__ == '__main__':
    unittest.main()
