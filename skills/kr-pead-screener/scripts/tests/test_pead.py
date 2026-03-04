"""
kr-pead-screener 테스트.
주봉 캔들 분석 + 브레이크아웃 판정 + 스테이지 분류 + 스코어링.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from weekly_candle_calculator import (
    detect_gap, classify_candle, analyze_weekly_candles,
    score_gap_size, score_pattern_quality,
    MIN_GAP_PCT, GAP_SCORE_TABLE,
)
from breakout_calculator import check_breakout, calc_risk_reward
from scorer import (
    classify_stage, score_earnings_surprise, calc_total_score,
    STAGES, MAX_WEEKS, WEIGHTS, RATING_BANDS, SURPRISE_THRESHOLDS,
)
from report_generator import PEADReportGenerator


# ═══════════════════════════════════════════════════════════
# 갭 감지
# ═══════════════════════════════════════════════════════════

class TestDetectGap(unittest.TestCase):

    def test_gap_up(self):
        """5% 갭업 감지."""
        result = detect_gap(10000, 10500)
        self.assertTrue(result['is_gap_up'])
        self.assertAlmostEqual(result['gap_pct'], 5.0, places=1)

    def test_small_gap(self):
        """2% 갭 → 미달 (최소 3%)."""
        result = detect_gap(10000, 10200)
        self.assertFalse(result['is_gap_up'])

    def test_large_gap(self):
        """15% 갭업."""
        result = detect_gap(10000, 11500)
        self.assertTrue(result['is_gap_up'])
        self.assertAlmostEqual(result['gap_pct'], 15.0, places=1)

    def test_gap_down(self):
        """갭다운 → 무시."""
        result = detect_gap(10000, 9500)
        self.assertFalse(result['is_gap_up'])

    def test_zero_prev_close(self):
        """전주 종가 0 → False."""
        result = detect_gap(0, 10000)
        self.assertFalse(result['is_gap_up'])


# ═══════════════════════════════════════════════════════════
# 캔들 분류
# ═══════════════════════════════════════════════════════════

class TestClassifyCandle(unittest.TestCase):

    def test_green(self):
        self.assertEqual(classify_candle(100, 110), 'green')

    def test_red(self):
        self.assertEqual(classify_candle(110, 100), 'red')

    def test_doji(self):
        self.assertEqual(classify_candle(100, 100), 'doji')


# ═══════════════════════════════════════════════════════════
# 주봉 캔들 분석
# ═══════════════════════════════════════════════════════════

class TestAnalyzeWeeklyCandles(unittest.TestCase):

    def test_red_candle_found(self):
        """첫 주봉이 적색 캔들."""
        candles = [
            {'open': 110, 'high': 112, 'low': 105, 'close': 107, 'volume': 1000},
            {'open': 108, 'high': 115, 'low': 107, 'close': 114, 'volume': 1500},
        ]
        result = analyze_weekly_candles(candles)
        self.assertTrue(result['red_candle_found'])
        self.assertEqual(result['red_candle_high'], 112)
        self.assertEqual(result['red_candle_low'], 105)

    def test_breakout_detected(self):
        """적색 → 녹색 브레이크아웃."""
        candles = [
            {'open': 110, 'high': 112, 'low': 105, 'close': 107, 'volume': 1000},
            {'open': 108, 'high': 115, 'low': 107, 'close': 114, 'volume': 1500},
        ]
        result = analyze_weekly_candles(candles)
        self.assertTrue(result['breakout_found'])

    def test_no_red_candle(self):
        """녹색 캔들만 → MONITORING."""
        candles = [
            {'open': 100, 'high': 115, 'low': 98, 'close': 112, 'volume': 2000},
        ]
        result = analyze_weekly_candles(candles)
        self.assertFalse(result['red_candle_found'])

    def test_volume_declining(self):
        """적색 캔들 거래량 < 이전 거래량."""
        candles = [
            {'open': 100, 'high': 110, 'low': 98, 'close': 108, 'volume': 2000},
            {'open': 110, 'high': 112, 'low': 105, 'close': 107, 'volume': 1000},
        ]
        result = analyze_weekly_candles(candles)
        self.assertTrue(result['volume_declining'])

    def test_empty_candles(self):
        """빈 리스트."""
        result = analyze_weekly_candles([])
        self.assertFalse(result['red_candle_found'])


# ═══════════════════════════════════════════════════════════
# 갭 크기 점수
# ═══════════════════════════════════════════════════════════

class TestGapSizeScore(unittest.TestCase):

    def test_large_gap(self):
        """15% 갭 → 100."""
        self.assertEqual(score_gap_size(15.0), 100)

    def test_medium_gap(self):
        """10% 갭 → 85."""
        self.assertEqual(score_gap_size(10.0), 85)

    def test_small_gap(self):
        """3% 갭 → 40."""
        self.assertEqual(score_gap_size(3.0), 40)

    def test_below_minimum(self):
        """2% 갭 → 0."""
        self.assertEqual(score_gap_size(2.0), 0)

    def test_7pct_gap(self):
        """7% 갭 → 70."""
        self.assertEqual(score_gap_size(7.0), 70)


# ═══════════════════════════════════════════════════════════
# 패턴 품질 점수
# ═══════════════════════════════════════════════════════════

class TestPatternQualityScore(unittest.TestCase):

    def test_perfect_pattern(self):
        """적색 + 거래량 감소 + 갭 유지 → 100."""
        self.assertEqual(score_pattern_quality(True, True, True), 100)

    def test_good_pattern(self):
        """적색 + 거래량 감소 → 80."""
        self.assertEqual(score_pattern_quality(True, True, False), 80)

    def test_red_only(self):
        """적색만 → 60."""
        self.assertEqual(score_pattern_quality(True, False, False), 60)

    def test_monitoring(self):
        """적색 없음 → 40."""
        self.assertEqual(score_pattern_quality(False, False, False), 40)


# ═══════════════════════════════════════════════════════════
# 브레이크아웃 판정
# ═══════════════════════════════════════════════════════════

class TestBreakoutCalculator(unittest.TestCase):

    def test_breakout_confirmed(self):
        """녹색 캔들 + 적색 고가 돌파."""
        result = check_breakout(115, 108, 112)
        self.assertTrue(result['is_breakout'])

    def test_no_breakout_red(self):
        """적색 캔들 (종가 < 시가)."""
        result = check_breakout(105, 110, 112)
        self.assertFalse(result['is_breakout'])

    def test_no_breakout_below(self):
        """녹색이지만 적색 고가 미돌파."""
        result = check_breakout(111, 108, 112)
        self.assertFalse(result['is_breakout'])

    def test_volume_confirmed(self):
        """거래량 확인."""
        result = check_breakout(115, 108, 112, current_volume=1500, avg_volume=1000)
        self.assertTrue(result['volume_confirmed'])


# ═══════════════════════════════════════════════════════════
# Risk/Reward
# ═══════════════════════════════════════════════════════════

class TestRiskReward(unittest.TestCase):

    def test_excellent_rr(self):
        """리스크 2%, 보상 10% → R/R 5.0 → 100점."""
        result = calc_risk_reward(100, 98, target_pct=10.0)
        self.assertEqual(result['score'], 100)
        self.assertGreaterEqual(result['rr_ratio'], 4.0)

    def test_good_rr(self):
        """리스크 3%, 보상 10% → R/R 3.33 → 85점."""
        result = calc_risk_reward(100, 97, target_pct=10.0)
        self.assertEqual(result['score'], 85)

    def test_moderate_rr(self):
        """리스크 5%, 보상 10% → R/R 2.0 → 70점."""
        result = calc_risk_reward(100, 95, target_pct=10.0)
        self.assertEqual(result['score'], 70)

    def test_zero_entry(self):
        """진입가 0 → 0점."""
        result = calc_risk_reward(0, 0)
        self.assertEqual(result['score'], 0)


# ═══════════════════════════════════════════════════════════
# 스테이지 분류
# ═══════════════════════════════════════════════════════════

class TestStageClassification(unittest.TestCase):

    def test_monitoring(self):
        """적색 없음 → MONITORING."""
        self.assertEqual(classify_stage(2, False, False), 'MONITORING')

    def test_signal_ready(self):
        """적색 있음, 브레이크아웃 없음 → SIGNAL_READY."""
        self.assertEqual(classify_stage(3, True, False), 'SIGNAL_READY')

    def test_breakout(self):
        """브레이크아웃 확인 → BREAKOUT."""
        self.assertEqual(classify_stage(3, True, True), 'BREAKOUT')

    def test_expired(self):
        """6주 경과 → EXPIRED."""
        self.assertEqual(classify_stage(6, True, False), 'EXPIRED')

    def test_boundary_week(self):
        """정확히 5주 → EXPIRED 아님."""
        self.assertEqual(classify_stage(5, True, False), 'SIGNAL_READY')


# ═══════════════════════════════════════════════════════════
# Earnings Surprise 점수
# ═══════════════════════════════════════════════════════════

class TestEarningsSurprise(unittest.TestCase):

    def test_large_surprise(self):
        """50% 서프라이즈 → 100."""
        self.assertEqual(score_earnings_surprise(50.0), 100)

    def test_moderate_surprise(self):
        """20% → 70."""
        self.assertEqual(score_earnings_surprise(20.0), 70)

    def test_negative_surprise(self):
        """음수 → 0."""
        self.assertEqual(score_earnings_surprise(-5.0), 0)

    def test_small_surprise(self):
        """5% → 40."""
        self.assertEqual(score_earnings_surprise(5.0), 40)


# ═══════════════════════════════════════════════════════════
# 종합 스코어
# ═══════════════════════════════════════════════════════════

class TestPEADTotalScore(unittest.TestCase):

    def test_strong_signal(self):
        """높은 점수 → Strong Signal."""
        result = calc_total_score(100, 100, 85, 85)
        self.assertGreaterEqual(result['total_score'], 80)
        self.assertEqual(result['rating'], 'Strong Signal')

    def test_good_signal(self):
        """70점대 → Good Signal."""
        result = calc_total_score(70, 80, 70, 55)
        self.assertGreaterEqual(result['total_score'], 65)

    def test_no_signal(self):
        """낮은 점수 → No Signal."""
        result = calc_total_score(40, 40, 40, 20)
        self.assertLess(result['total_score'], 50)
        self.assertEqual(result['rating'], 'No Signal')


# ═══════════════════════════════════════════════════════════
# Constants 검증
# ═══════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_weights_sum(self):
        """가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=5)

    def test_stages(self):
        """4개 스테이지."""
        self.assertEqual(len(STAGES), 4)
        self.assertIn('MONITORING', STAGES)
        self.assertIn('BREAKOUT', STAGES)

    def test_max_weeks(self):
        """만료 주기 5주."""
        self.assertEqual(MAX_WEEKS, 5)

    def test_min_gap(self):
        """최소 갭 3%."""
        self.assertEqual(MIN_GAP_PCT, 3.0)


# ═══════════════════════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════════════════════

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.reporter = PEADReportGenerator(self.tmpdir)
        self.sample_results = [
            {
                'ticker': '005930', 'name': '삼성전자',
                'stage': 'SIGNAL_READY', 'gap_pct': 8.5,
                'score_data': {'total_score': 75, 'rating': 'Good Signal',
                               'action': '브레이크아웃 대기',
                               'components': {'gap_size': 70, 'pattern_quality': 80,
                                              'earnings_surprise': 70, 'risk_reward': 85}},
            },
        ]

    def test_json_report(self):
        path = self.reporter.generate_json(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-pead-screener')

    def test_markdown_report(self):
        path = self.reporter.generate_markdown(self.sample_results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('PEAD', content)


if __name__ == '__main__':
    unittest.main()
