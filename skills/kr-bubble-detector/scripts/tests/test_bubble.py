"""
kr-bubble-detector 테스트.
6 정량 지표 + 3 정성 조정 + 리스크 존 + 리포트 생성.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bubble_scorer import (
    BubbleScorer,
    INDICATOR_NAMES,
    ADJUSTMENT_NAMES,
    RISK_ZONES,
    score_vkospi_market,
    score_credit_balance,
    score_ipo_heat,
    score_breadth_anomaly,
    score_price_acceleration,
    score_per_band,
    classify_risk_zone,
)
from report_generator import ReportGenerator


# ── 지표 1: VKOSPI + 시장 위치 ──────────────────────

class TestScoreVkospiMarket(unittest.TestCase):

    def test_extreme_complacency(self):
        """VKOSPI < 13 + 고점 근접 → 2점."""
        self.assertEqual(score_vkospi_market(12.0, -0.02), 2)

    def test_moderate_optimism(self):
        """VKOSPI 13-18 + 고점 근처 → 1점."""
        self.assertEqual(score_vkospi_market(16.0, -0.05), 1)

    def test_healthy_caution(self):
        """VKOSPI > 18 → 0점."""
        self.assertEqual(score_vkospi_market(22.0, -0.03), 0)

    def test_high_vkospi_near_high(self):
        """VKOSPI > 18 이면 고점 근접해도 0점."""
        self.assertEqual(score_vkospi_market(25.0, -0.01), 0)

    def test_low_vkospi_far_from_high(self):
        """VKOSPI < 13 이지만 고점 대비 5%+ 하락 → 1점 (pct_from_high > -0.10)."""
        self.assertEqual(score_vkospi_market(12.0, -0.08), 1)


# ── 지표 2: 신용잔고 변화 ────────────────────────────

class TestScoreCreditBalance(unittest.TestCase):

    def test_extreme_leverage(self):
        """YoY +20% AND ATH → 2점."""
        self.assertEqual(score_credit_balance(0.25, True), 2)

    def test_moderate_leverage(self):
        """YoY +10-20% → 1점."""
        self.assertEqual(score_credit_balance(0.15, False), 1)

    def test_normal_leverage(self):
        """YoY < 10% → 0점."""
        self.assertEqual(score_credit_balance(0.05, False), 0)

    def test_high_yoy_but_not_ath(self):
        """YoY +20% 이지만 ATH 아님 → 1점 (is_ath=False이므로 2점 조건 미충족)."""
        self.assertEqual(score_credit_balance(0.22, False), 1)


# ── 지표 3: IPO 과열도 ──────────────────────────────

class TestScoreIPOHeat(unittest.TestCase):

    def test_extreme_heat(self):
        """IPO 2배+ AND 경쟁률 500:1+ → 2점."""
        self.assertEqual(score_ipo_heat(40, 18.0, 600.0), 2)

    def test_moderate_heat(self):
        """IPO 1.5배+ → 1점."""
        self.assertEqual(score_ipo_heat(30, 18.0, 200.0), 1)

    def test_normal(self):
        """IPO 정상 → 0점."""
        self.assertEqual(score_ipo_heat(15, 18.0, 100.0), 0)

    def test_zero_avg(self):
        """5년 평균이 0이면 → 0점 (division by zero 방지)."""
        self.assertEqual(score_ipo_heat(40, 0.0, 600.0), 0)


# ── 지표 4: 시장폭 이상 ─────────────────────────────

class TestScoreBreadthAnomaly(unittest.TestCase):

    def test_severe_anomaly(self):
        """신고가 + breadth < 45% → 2점."""
        self.assertEqual(score_breadth_anomaly(True, 0.42), 2)

    def test_mild_anomaly(self):
        """breadth 45-60% → 1점."""
        self.assertEqual(score_breadth_anomaly(False, 0.55), 1)

    def test_healthy(self):
        """breadth > 60% → 0점."""
        self.assertEqual(score_breadth_anomaly(True, 0.65), 0)


# ── 지표 5: 가격 가속화 ─────────────────────────────

class TestScorePriceAcceleration(unittest.TestCase):

    def test_extreme_acceleration(self):
        """95th percentile 이상 → 2점."""
        self.assertEqual(score_price_acceleration(0.22, 0.96), 2)

    def test_elevated_acceleration(self):
        """85-95th percentile → 1점."""
        self.assertEqual(score_price_acceleration(0.14, 0.90), 1)

    def test_normal(self):
        """85th 미만 → 0점."""
        self.assertEqual(score_price_acceleration(0.08, 0.70), 0)


# ── 지표 6: KOSPI PER 밴드 ──────────────────────────

class TestScorePerBand(unittest.TestCase):

    def test_overheated(self):
        """PER >= 14 → 2점."""
        self.assertEqual(score_per_band(14.5), 2)

    def test_elevated(self):
        """PER 12-14 → 1점."""
        self.assertEqual(score_per_band(13.0), 1)

    def test_normal(self):
        """PER < 12 → 0점."""
        self.assertEqual(score_per_band(10.5), 0)

    def test_boundary_14(self):
        """PER 정확히 14 → 2점."""
        self.assertEqual(score_per_band(14.0), 2)

    def test_boundary_12(self):
        """PER 정확히 12 → 1점."""
        self.assertEqual(score_per_band(12.0), 1)


# ── BubbleScorer 통합 테스트 ────────────────────────

class TestBubbleScorerQuantitative(unittest.TestCase):

    def setUp(self):
        self.scorer = BubbleScorer()

    def test_max_score(self):
        """모든 지표 2점 → 정량 12점."""
        indicators = {
            'vkospi_market': {'vkospi': 10.0, 'pct_from_high': -0.01},
            'credit_balance': {'credit_yoy': 0.30, 'is_ath': True},
            'ipo_heat': {'quarterly_ipo_count': 50, 'avg_5y': 18.0,
                         'avg_competition': 700.0},
            'breadth_anomaly': {'is_new_high': True, 'breadth_200ma': 0.40},
            'price_acceleration': {'return_3m': 0.25, 'percentile': 0.97},
            'per_band': {'kospi_per': 16.0},
        }
        result = self.scorer.score_quantitative(indicators)
        self.assertEqual(result['total'], 12)
        for score in result['scores'].values():
            self.assertEqual(score, 2)

    def test_min_score(self):
        """모든 지표 0점 → 정량 0점."""
        indicators = {
            'vkospi_market': {'vkospi': 25.0, 'pct_from_high': -0.15},
            'credit_balance': {'credit_yoy': 0.03, 'is_ath': False},
            'ipo_heat': {'quarterly_ipo_count': 10, 'avg_5y': 18.0,
                         'avg_competition': 100.0},
            'breadth_anomaly': {'is_new_high': False, 'breadth_200ma': 0.70},
            'price_acceleration': {'return_3m': 0.05, 'percentile': 0.50},
            'per_band': {'kospi_per': 9.0},
        }
        result = self.scorer.score_quantitative(indicators)
        self.assertEqual(result['total'], 0)

    def test_empty_indicators(self):
        """빈 지표 → 모두 0점."""
        result = self.scorer.score_quantitative({})
        self.assertEqual(result['total'], 0)


class TestBubbleScorerQualitative(unittest.TestCase):

    def setUp(self):
        self.scorer = BubbleScorer()

    def test_all_adjustments(self):
        """3개 모두 충족 → +3점."""
        adj = {
            'social_penetration': True,
            'media_trend': True,
            'valuation_disconnect': True,
        }
        result = self.scorer.score_qualitative(adj)
        self.assertEqual(result['total'], 3)

    def test_no_adjustments(self):
        """모두 미충족 → 0점."""
        result = self.scorer.score_qualitative({})
        self.assertEqual(result['total'], 0)

    def test_partial_adjustments(self):
        """일부만 충족 → 해당 점수."""
        adj = {'social_penetration': True, 'media_trend': False}
        result = self.scorer.score_qualitative(adj)
        self.assertEqual(result['total'], 1)


# ── 리스크 존 매핑 ──────────────────────────────────

class TestRiskZoneMapping(unittest.TestCase):

    def test_normal_zone(self):
        """0-4 → Normal."""
        for score in [0, 2, 4]:
            zone = classify_risk_zone(score)
            self.assertEqual(zone['name'], 'Normal')

    def test_caution_zone(self):
        """5-7 → Caution."""
        for score in [5, 6, 7]:
            zone = classify_risk_zone(score)
            self.assertEqual(zone['name'], 'Caution')

    def test_elevated_risk_zone(self):
        """8-9 → Elevated Risk."""
        for score in [8, 9]:
            zone = classify_risk_zone(score)
            self.assertEqual(zone['name'], 'Elevated_Risk')

    def test_euphoria_zone(self):
        """10-12 → Euphoria."""
        for score in [10, 11, 12]:
            zone = classify_risk_zone(score)
            self.assertEqual(zone['name'], 'Euphoria')

    def test_critical_zone(self):
        """13-15 → Critical."""
        for score in [13, 14, 15]:
            zone = classify_risk_zone(score)
            self.assertEqual(zone['name'], 'Critical')

    def test_out_of_range(self):
        """범위 초과 → clamped."""
        zone = classify_risk_zone(20)
        self.assertEqual(zone['name'], 'Critical')  # clamped to 15
        zone = classify_risk_zone(-5)
        self.assertEqual(zone['name'], 'Normal')  # clamped to 0


# ── Final Score 계산 ────────────────────────────────

class TestCalculateFinal(unittest.TestCase):

    def setUp(self):
        self.scorer = BubbleScorer()

    def test_combined_score(self):
        """정량 + 정성 → 최종 점수."""
        quant = {'scores': {}, 'total': 9}
        qual = {'adjustments': {}, 'total': 3}
        final = self.scorer.calculate_final(quant, qual)
        self.assertEqual(final['final_score'], 12)
        self.assertEqual(final['risk_zone']['name'], 'Euphoria')

    def test_max_clamped(self):
        """최대 15점 클램핑."""
        quant = {'scores': {}, 'total': 12}
        qual = {'adjustments': {}, 'total': 3}
        final = self.scorer.calculate_final(quant, qual)
        self.assertEqual(final['final_score'], 15)
        self.assertEqual(final['max_possible'], 15)


# ── 리포트 생성 ────────────────────────────────────

class TestReportGenerator(unittest.TestCase):

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'quantitative': {
                    'scores': {
                        'vkospi_market': 2,
                        'credit_balance': 1,
                        'ipo_heat': 0,
                        'breadth_anomaly': 1,
                        'price_acceleration': 1,
                        'per_band': 2,
                    },
                    'total': 7,
                },
                'qualitative': {
                    'adjustments': {
                        'social_penetration': 1,
                        'media_trend': 0,
                        'valuation_disconnect': 0,
                    },
                    'total': 1,
                },
                'final': {
                    'final_score': 8,
                    'risk_zone': {
                        'name': 'Elevated_Risk',
                        'label': '위험 상승',
                        'budget': '50-70%',
                    },
                    'max_possible': 15,
                    'quantitative_total': 7,
                    'qualitative_total': 1,
                },
            }
            output = reporter.generate(result)
            self.assertTrue(os.path.exists(output['json_path']))
            self.assertTrue(os.path.exists(output['md_path']))

            with open(output['json_path'], 'r') as f:
                data = json.load(f)
            self.assertEqual(data['final_score'], 8)
            self.assertEqual(data['risk_zone'], 'Elevated_Risk')

    def test_md_contains_key_sections(self):
        """Markdown에 핵심 섹션 포함."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'quantitative': {'scores': {}, 'total': 0},
                'qualitative': {'adjustments': {}, 'total': 0},
                'final': {
                    'final_score': 0,
                    'risk_zone': {'name': 'Normal', 'label': '정상', 'budget': '100%'},
                    'max_possible': 15,
                },
            }
            output = reporter.generate(result)
            md = output['md_content']
            self.assertIn('종합 결과', md)
            self.assertIn('Phase 2: 정량 지표', md)
            self.assertIn('Phase 3: 정성 조정', md)
            self.assertIn('리스크 존 가이드', md)


# ── 상수 검증 ──────────────────────────────────────

class TestConstants(unittest.TestCase):

    def test_indicator_count(self):
        """정량 지표 6개."""
        self.assertEqual(len(INDICATOR_NAMES), 6)

    def test_adjustment_count(self):
        """정성 조정 3개."""
        self.assertEqual(len(ADJUSTMENT_NAMES), 3)

    def test_risk_zones_continuous(self):
        """리스크 존이 0-15를 빈틈 없이 커버."""
        covered = set()
        for zone in RISK_ZONES:
            for i in range(zone['min'], zone['max'] + 1):
                covered.add(i)
        expected = set(range(0, 16))
        self.assertEqual(covered, expected)


if __name__ == '__main__':
    unittest.main()
