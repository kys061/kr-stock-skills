"""kr-vcp-screener 테스트 (~34 tests).

TestTrendTemplate:     7점 템플릿 + 경계값
TestVCPPattern:        수축 탐지 + 깊이 진행
TestVolumePattern:     Dry-Up Ratio 구간
TestPivotProximity:    근접도 + 브레이크아웃
TestRelativeStrength:  RS Rank (leadership_calculator 재사용)
TestVCPScorer:         종합 스코어 + 등급
TestReportGenerator:   JSON/Markdown 출력
TestConstants:         가중치/파라미터 검증
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trend_template_calculator import (
    check_trend_template, TEMPLATE_PASS_THRESHOLD, TEMPLATE_PERFECT,
    SMA200_RISING_DAYS,
)
from vcp_pattern_calculator import (
    detect_contractions, check_contraction_progression, calc_pivot_point,
    score_contraction_quality,
    T1_MIN_DEPTH, T1_MAX_DEPTH_LARGE, T1_MAX_DEPTH_SMALL,
    CONTRACTION_RATIO, MIN_CONTRACTIONS, IDEAL_CONTRACTIONS,
    TIGHT_BONUS, DEEP_PENALTY,
)
from volume_pattern_calculator import (
    calc_dryup_ratio, calc_pivot_proximity,
    DRYUP_SCORES, DRYUP_DEFAULT,
)
from scorer import (
    calc_vcp_total, WEIGHTS, RATING_BANDS, STAGE2_MIN_POINTS,
)
from report_generator import VCPReportGenerator


# ═══════════════════════════════════════════════════════════════
# 1. TestTrendTemplate (6 tests)
# ═══════════════════════════════════════════════════════════════
class TestTrendTemplate(unittest.TestCase):
    """Stage 2 7-Point 트렌드 템플릿 테스트."""

    def test_perfect_7_points(self):
        """모든 7점 통과 = 100점."""
        r = check_trend_template(
            price=50000, sma50=48000, sma150=45000, sma200=43000,
            sma200_22d_ago=42000, high_52w=55000, low_52w=35000,
            rs_rank=85)
        self.assertEqual(r['points'], 7)
        self.assertTrue(r['passed'])
        self.assertEqual(r['score'], 100)

    def test_6_points_pass(self):
        """6점 통과 경계 = passed."""
        # RS Rank = 65 → 조건 7 실패
        r = check_trend_template(
            price=50000, sma50=48000, sma150=45000, sma200=43000,
            sma200_22d_ago=42000, high_52w=55000, low_52w=35000,
            rs_rank=65)
        self.assertEqual(r['points'], 6)
        self.assertTrue(r['passed'])

    def test_5_points_fail(self):
        """5점 = 미통과."""
        # RS Rank 실패 + SMA200 미상승
        r = check_trend_template(
            price=50000, sma50=48000, sma150=45000, sma200=43000,
            sma200_22d_ago=44000, high_52w=55000, low_52w=35000,
            rs_rank=65)
        self.assertEqual(r['points'], 5)
        self.assertFalse(r['passed'])

    def test_condition1_price_below_sma(self):
        """조건1: 현재가 < SMA150 또는 SMA200 → 실패."""
        r = check_trend_template(
            price=42000, sma50=48000, sma150=45000, sma200=43000,
            sma200_22d_ago=42000, high_52w=55000, low_52w=35000,
            rs_rank=85)
        # price < sma150 and price < sma50 → 조건1,4 실패
        self.assertFalse(r['details'][0]['passed'])

    def test_condition5_52w_low(self):
        """조건5: 현재가 >= 52W Low * 1.25."""
        r = check_trend_template(
            price=43000, sma50=42000, sma150=41000, sma200=40000,
            sma200_22d_ago=39000, high_52w=55000, low_52w=40000,
            rs_rank=85)
        # 43000 < 40000 * 1.25 = 50000 → 조건5 실패
        self.assertFalse(r['details'][4]['passed'])

    def test_condition6_52w_high(self):
        """조건6: 현재가 >= 52W High * 0.75."""
        r = check_trend_template(
            price=40000, sma50=39000, sma150=38000, sma200=37000,
            sma200_22d_ago=36000, high_52w=60000, low_52w=30000,
            rs_rank=85)
        # 40000 < 60000 * 0.75 = 45000 → 조건6 실패
        self.assertFalse(r['details'][5]['passed'])


# ═══════════════════════════════════════════════════════════════
# 2. TestVCPPattern (6 tests)
# ═══════════════════════════════════════════════════════════════
class TestVCPPattern(unittest.TestCase):
    """VCP 패턴 수축 탐지 테스트."""

    def test_detect_3_contractions(self):
        """3회 수축 탐지."""
        highs = [(10, 1000), (40, 950), (70, 920)]
        lows = [(20, 800), (50, 780), (80, 800)]  # 3rd: (920-800)/920=13%
        contractions = detect_contractions(highs, lows)
        self.assertEqual(len(contractions), 3)
        # 첫 수축: (1000-800)/1000 = 20%
        self.assertAlmostEqual(contractions[0]['depth_pct'], 20.0, places=1)

    def test_detect_skips_shallow(self):
        """T1_MIN_DEPTH(10%) 미만 수축 무시."""
        highs = [(10, 1000), (30, 990)]
        lows = [(20, 950), (40, 960)]  # 5%, 3% → 모두 10% 미만
        contractions = detect_contractions(highs, lows)
        self.assertEqual(len(contractions), 0)

    def test_contraction_progression_ok(self):
        """수축 진행: 각 수축이 이전보다 얕음 (ratio <= 0.75)."""
        contractions = [
            {'depth_pct': 25},
            {'depth_pct': 15},  # 15/25 = 0.60 <= 0.75 OK
            {'depth_pct': 10},  # 10/15 = 0.67 <= 0.75 OK
        ]
        self.assertTrue(check_contraction_progression(contractions))

    def test_contraction_progression_fail(self):
        """수축 진행 실패: ratio > 0.75."""
        contractions = [
            {'depth_pct': 20},
            {'depth_pct': 18},  # 18/20 = 0.90 > 0.75 FAIL
        ]
        self.assertFalse(check_contraction_progression(contractions))

    def test_pivot_point(self):
        """피봇 포인트 = 마지막 수축 고가."""
        contractions = [
            {'high': 1000, 'low': 800, 'depth_pct': 20, 'high_idx': 10, 'low_idx': 20},
            {'high': 950, 'low': 850, 'depth_pct': 10.53, 'high_idx': 40, 'low_idx': 50},
        ]
        pivot = calc_pivot_point(contractions)
        self.assertEqual(pivot['pivot'], 950)
        self.assertAlmostEqual(pivot['stop_loss'], 833.0, places=0)

    def test_empty_contractions(self):
        """수축 없으면 피봇 0."""
        pivot = calc_pivot_point([])
        self.assertEqual(pivot['pivot'], 0)


# ═══════════════════════════════════════════════════════════════
# 3. TestContractionQuality (4 tests)
# ═══════════════════════════════════════════════════════════════
class TestContractionQuality(unittest.TestCase):
    """Contraction Quality 점수 테스트."""

    def test_4_contractions_ratio_ok(self):
        """4회 수축 + ratio OK = 90."""
        contractions = [
            {'depth_pct': 25}, {'depth_pct': 18},
            {'depth_pct': 12}, {'depth_pct': 8},
        ]
        r = score_contraction_quality(contractions)
        # 4회 + ratio OK + last < 10% tight bonus
        self.assertEqual(r['score'], min(100, 90 + TIGHT_BONUS))
        self.assertEqual(r['count'], 4)
        self.assertTrue(r['ratio_ok'])

    def test_3_contractions_ratio_ok(self):
        """3회 수축 + ratio OK = 80."""
        contractions = [
            {'depth_pct': 25}, {'depth_pct': 15}, {'depth_pct': 9},
        ]
        r = score_contraction_quality(contractions)
        # 80 + tight(9% < 10) = 90
        self.assertEqual(r['score'], 90)

    def test_2_contractions_ratio_fail(self):
        """2회 수축 + ratio 미달 = 40."""
        contractions = [
            {'depth_pct': 20}, {'depth_pct': 22},  # 22/20 > 0.75
        ]
        r = score_contraction_quality(contractions)
        # 40 + deep penalty(22>20) = 30
        self.assertEqual(r['score'], 30)
        self.assertFalse(r['ratio_ok'])

    def test_1_contraction_default(self):
        """1회 수축 = default(20)."""
        contractions = [{'depth_pct': 25}]
        r = score_contraction_quality(contractions)
        self.assertEqual(r['count'], 1)
        # deep penalty: 25 > 20 → -10 → max(0, 20-10)=10
        self.assertEqual(r['score'], 10)


# ═══════════════════════════════════════════════════════════════
# 4. TestVolumePattern (4 tests)
# ═══════════════════════════════════════════════════════════════
class TestVolumePattern(unittest.TestCase):
    """Dry-Up Ratio 스코어 테스트."""

    def test_strong_dryup(self):
        """Dry-Up < 0.30 = 90."""
        r = calc_dryup_ratio(
            contraction_volumes=[100, 120, 80],     # avg=100
            advance_volumes=[500, 400, 600])         # avg=500
        # 100/500 = 0.20 < 0.30
        self.assertEqual(r['score'], 90)
        self.assertAlmostEqual(r['ratio'], 0.2, places=1)

    def test_moderate_dryup(self):
        """Dry-Up 0.30-0.50 = 75."""
        r = calc_dryup_ratio(
            contraction_volumes=[200, 180, 220],     # avg=200
            advance_volumes=[500, 500, 500])          # avg=500
        # 200/500 = 0.40
        self.assertEqual(r['score'], 75)

    def test_weak_dryup(self):
        """Dry-Up 0.70-1.00 = 40."""
        r = calc_dryup_ratio(
            contraction_volumes=[400, 350, 450],     # avg=400
            advance_volumes=[500, 500, 500])          # avg=500
        # 400/500 = 0.80
        self.assertEqual(r['score'], 40)

    def test_no_dryup(self):
        """Dry-Up > 1.00 = 20."""
        r = calc_dryup_ratio(
            contraction_volumes=[600, 550, 650],     # avg=600
            advance_volumes=[500, 500, 500])          # avg=500
        # 600/500 = 1.20 > 1.00
        self.assertEqual(r['score'], DRYUP_DEFAULT)


# ═══════════════════════════════════════════════════════════════
# 5. TestPivotProximity (5 tests)
# ═══════════════════════════════════════════════════════════════
class TestPivotProximity(unittest.TestCase):
    """피봇 근접도 테스트."""

    def test_breakout(self):
        """피봇 0-3% 위 = 100 (breakout)."""
        r = calc_pivot_proximity(10200, 10000)  # +2%
        self.assertEqual(r['score'], 100)
        self.assertEqual(r['position'], 'breakout')

    def test_near_pivot(self):
        """피봇 0-3% 아래 = 85."""
        r = calc_pivot_proximity(9800, 10000)  # -2%
        self.assertEqual(r['score'], 85)
        self.assertEqual(r['position'], 'near_pivot')

    def test_watch(self):
        """피봇 3-5% 아래 = 75."""
        r = calc_pivot_proximity(9600, 10000)  # -4%
        self.assertEqual(r['score'], 75)
        self.assertEqual(r['position'], 'watch')

    def test_forming(self):
        """피봇 5-10% 아래 = 50."""
        r = calc_pivot_proximity(9200, 10000)  # -8%
        self.assertEqual(r['score'], 50)
        self.assertEqual(r['position'], 'forming')

    def test_no_chase(self):
        """피봇 20%+ 아래 = 20."""
        r = calc_pivot_proximity(7500, 10000)  # -25%
        self.assertEqual(r['score'], 20)
        self.assertEqual(r['position'], 'no_chase')


# ═══════════════════════════════════════════════════════════════
# 6. TestVCPScorer (5 tests)
# ═══════════════════════════════════════════════════════════════
class TestVCPScorer(unittest.TestCase):
    """종합 VCP 스코어 테스트."""

    def test_textbook_vcp(self):
        """Textbook VCP = 90+."""
        components = {
            'trend_template': 100,
            'contraction_quality': 90,
            'volume_pattern': 90,
            'pivot_proximity': 100,
            'relative_strength': 90,
        }
        r = calc_vcp_total(components, stage2_points=7)
        # 100*0.25 + 90*0.25 + 90*0.20 + 100*0.15 + 90*0.15
        # = 25 + 22.5 + 18 + 15 + 13.5 = 94
        self.assertEqual(r['total_score'], 94)
        self.assertEqual(r['rating'], 'Textbook VCP')
        self.assertTrue(r['stage2_passed'])

    def test_strong_vcp(self):
        """Strong VCP = 80-89."""
        components = {
            'trend_template': 85,
            'contraction_quality': 80,
            'volume_pattern': 75,
            'pivot_proximity': 85,
            'relative_strength': 80,
        }
        r = calc_vcp_total(components, stage2_points=7)
        # 85*0.25 + 80*0.25 + 75*0.20 + 85*0.15 + 80*0.15
        # = 21.25 + 20 + 15 + 12.75 + 12 = 81
        self.assertEqual(r['total_score'], 81)
        self.assertEqual(r['rating'], 'Strong VCP')

    def test_developing(self):
        """Developing = 60-69."""
        components = {
            'trend_template': 71,
            'contraction_quality': 60,
            'volume_pattern': 60,
            'pivot_proximity': 50,
            'relative_strength': 60,
        }
        r = calc_vcp_total(components, stage2_points=6)
        # 71*0.25 + 60*0.25 + 60*0.20 + 50*0.15 + 60*0.15
        # = 17.75 + 15 + 12 + 7.5 + 9 = 61.25 → 61
        self.assertEqual(r['total_score'], 61)
        self.assertEqual(r['rating'], 'Developing')

    def test_stage2_fail_no_vcp(self):
        """Stage 2 미통과 → 자동 No VCP (0점)."""
        components = {
            'trend_template': 100,
            'contraction_quality': 90,
            'volume_pattern': 90,
            'pivot_proximity': 100,
            'relative_strength': 90,
        }
        r = calc_vcp_total(components, stage2_points=4)
        self.assertEqual(r['total_score'], 0)
        self.assertEqual(r['rating'], 'No VCP')
        self.assertFalse(r['stage2_passed'])

    def test_no_vcp_low_score(self):
        """No VCP = < 60."""
        components = {
            'trend_template': 57,
            'contraction_quality': 40,
            'volume_pattern': 40,
            'pivot_proximity': 30,
            'relative_strength': 40,
        }
        r = calc_vcp_total(components, stage2_points=6)
        # 57*0.25 + 40*0.25 + 40*0.20 + 30*0.15 + 40*0.15
        # = 14.25 + 10 + 8 + 4.5 + 6 = 42.75 → 43
        self.assertEqual(r['total_score'], 43)
        self.assertEqual(r['rating'], 'No VCP')


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
            'ticker': '005930', 'name': '삼성전자',
            'score_data': {
                'total_score': 85, 'rating': 'Strong VCP',
                'stage2_passed': True,
                'components': {
                    'trend_template': 85, 'contraction_quality': 80,
                    'volume_pattern': 75, 'pivot_proximity': 85,
                    'relative_strength': 80,
                },
            },
        }]
        gen = VCPReportGenerator(self.tmpdir)
        path = gen.generate_json(results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data['skill'], 'kr-vcp-screener')
        self.assertEqual(data['summary']['total'], 1)
        self.assertEqual(data['summary']['strong'], 1)

    def test_markdown_report(self):
        results = [{
            'ticker': '005930', 'name': '삼성전자',
            'score_data': {
                'total_score': 85, 'rating': 'Strong VCP',
                'stage2_passed': True,
                'components': {
                    'trend_template': 85, 'contraction_quality': 80,
                    'volume_pattern': 75, 'pivot_proximity': 85,
                    'relative_strength': 80,
                },
            },
        }]
        gen = VCPReportGenerator(self.tmpdir)
        path = gen.generate_markdown(results)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn('한국 VCP 패턴 스크리닝 리포트', content)
        self.assertIn('삼성전자', content)


# ═══════════════════════════════════════════════════════════════
# 8. TestConstants (3 tests)
# ═══════════════════════════════════════════════════════════════
class TestConstants(unittest.TestCase):
    """가중치/파라미터 디자인 검증."""

    def test_weights_sum_100(self):
        """5-컴포넌트 가중치 합 = 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=2)

    def test_vcp_parameters(self):
        """한국 VCP 파라미터 설계값 검증."""
        self.assertEqual(T1_MIN_DEPTH, 10)
        self.assertEqual(T1_MAX_DEPTH_LARGE, 30)
        self.assertEqual(T1_MAX_DEPTH_SMALL, 40)
        self.assertEqual(CONTRACTION_RATIO, 0.75)
        self.assertEqual(MIN_CONTRACTIONS, 2)
        self.assertEqual(IDEAL_CONTRACTIONS, (3, 4))
        self.assertEqual(STAGE2_MIN_POINTS, 6)

    def test_rating_bands(self):
        """등급 범위 연속성 + 5단계."""
        self.assertEqual(len(RATING_BANDS), 5)
        self.assertEqual(RATING_BANDS[0]['name'], 'Textbook VCP')
        self.assertEqual(RATING_BANDS[-1]['name'], 'No VCP')
        # 범위 연속성 검증
        for i in range(len(RATING_BANDS) - 1):
            self.assertEqual(RATING_BANDS[i]['min'] - 1, RATING_BANDS[i + 1]['max'])


if __name__ == '__main__':
    unittest.main()
