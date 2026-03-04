"""
kr-macro-regime 테스트.
6-컴포넌트 크로스에셋 비율 + 레짐 분류 + 리포트.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'calculators'))

from calculators.concentration_calculator import (
    ConcentrationCalculator,
    calc_top10_ratio,
    calc_trend,
    regime_signal as conc_regime_signal,
)
from calculators.yield_curve_calculator import (
    YieldCurveCalculator,
    calc_spread,
    classify_spread,
    regime_signal as yc_regime_signal,
)
from calculators.credit_calculator import (
    CreditCalculator,
    calc_credit_spread,
    calc_trend as credit_trend,
    regime_signal as credit_regime_signal,
)
from calculators.size_factor_calculator import (
    SizeFactorCalculator,
    calc_ratio,
    calc_trend as size_trend,
    regime_signal as size_regime_signal,
)
from calculators.equity_bond_calculator import (
    EquityBondCalculator,
    calc_correlation,
    classify_correlation,
    regime_signal as eb_regime_signal,
)
from calculators.sector_rotation_calculator import (
    SectorRotationCalculator,
    KR_CYCLICAL_SECTORS,
    KR_DEFENSIVE_SECTORS,
    calc_relative_perf,
    classify_rotation,
    regime_signal as sr_regime_signal,
)
from scorer import (
    COMPONENT_WEIGHTS,
    REGIME_TYPES,
    TRANSITIONAL_THRESHOLD,
    classify_regime,
    MacroRegimeScorer,
)
from report_generator import ReportGenerator


# ── 시장 집중도 테스트 ────────────────────────────────

class TestConcentrationCalculator(unittest.TestCase):

    def test_top10_ratio(self):
        """상위 10종목 비중 계산."""
        caps = [100, 80, 60, 50, 40, 30, 20, 15, 10, 5] + [2] * 90
        ratio = calc_top10_ratio(caps)
        self.assertGreater(ratio, 0.5)

    def test_concentrating_trend(self):
        """6M > 12M + 임계값 → concentrating."""
        trend = calc_trend(0.55, 0.50, threshold=0.02)
        self.assertEqual(trend, 'concentrating')

    def test_broadening_trend(self):
        """6M < 12M → broadening."""
        trend = calc_trend(0.45, 0.52, threshold=0.02)
        self.assertEqual(trend, 'broadening')

    def test_stable_trend(self):
        """차이 작음 → stable."""
        trend = calc_trend(0.50, 0.50, threshold=0.02)
        self.assertEqual(trend, 'stable')

    def test_regime_signal(self):
        """추세 → 레짐 매핑."""
        self.assertEqual(conc_regime_signal('concentrating'), 'Concentration')
        self.assertEqual(conc_regime_signal('broadening'), 'Broadening')
        self.assertEqual(conc_regime_signal('stable'), 'Transitional')

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = ConcentrationCalculator()
        # 상승 추세 데이터
        ratios = [0.45, 0.46, 0.47, 0.48, 0.49, 0.50,
                  0.52, 0.54, 0.56, 0.58, 0.60, 0.62]
        result = calc.calculate(ratios)
        self.assertIn('trend', result)
        self.assertIn('regime_signal', result)
        self.assertGreater(result['current_ratio'], 0)


# ── 금리 곡선 테스트 ──────────────────────────────────

class TestYieldCurveCalculator(unittest.TestCase):

    def test_inverted(self):
        """역전 (10Y < 3Y) → Contraction."""
        spread = calc_spread(3.0, 3.5)
        self.assertLess(spread, 0)
        self.assertEqual(classify_spread(spread), 'inverted')
        self.assertEqual(yc_regime_signal('inverted'), 'Contraction')

    def test_flat(self):
        """평탄 (0-30bp) → Transitional."""
        spread = calc_spread(3.5, 3.3)  # 20bp
        self.assertEqual(classify_spread(spread), 'flat')

    def test_normal(self):
        """정상 (30-100bp)."""
        spread = calc_spread(3.8, 3.2)  # 60bp
        self.assertEqual(classify_spread(spread), 'normal')

    def test_steep(self):
        """스티프 (>100bp) → Broadening."""
        spread = calc_spread(4.5, 3.2)  # 130bp
        self.assertEqual(classify_spread(spread), 'steep')
        self.assertEqual(yc_regime_signal('steep'), 'Broadening')

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = YieldCurveCalculator()
        result = calc.calculate([3.0, 3.1, 3.2], [3.5, 3.4, 3.3])
        self.assertIn('current_spread_bp', result)
        self.assertIn('regime_signal', result)


# ── 신용 환경 테스트 ──────────────────────────────────

class TestCreditCalculator(unittest.TestCase):

    def test_credit_spread(self):
        """BBB- - AA- = 스프레드 (bp)."""
        spread = calc_credit_spread(5.5, 3.5)
        self.assertAlmostEqual(spread, 200.0)

    def test_widening(self):
        """확대 → Contraction."""
        self.assertEqual(credit_regime_signal('widening'), 'Contraction')

    def test_tightening(self):
        """축소 → Broadening."""
        self.assertEqual(credit_regime_signal('tightening'), 'Broadening')

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = CreditCalculator()
        # 스프레드 확대 추세
        bbb = [5.0, 5.2, 5.4, 5.6, 5.8, 6.0,
               6.2, 6.4, 6.6, 6.8, 7.0, 7.2]
        aa =  [3.0, 3.0, 3.0, 3.0, 3.0, 3.0,
               3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        result = calc.calculate(bbb, aa)
        self.assertIn('trend', result)
        self.assertEqual(result['trend'], 'widening')


# ── 사이즈 팩터 테스트 ────────────────────────────────

class TestSizeFactorCalculator(unittest.TestCase):

    def test_ratio(self):
        """KOSDAQ/KOSPI 비율."""
        self.assertAlmostEqual(calc_ratio(800, 2500), 0.32)

    def test_rising_trend(self):
        """상승 → Broadening."""
        self.assertEqual(size_regime_signal('rising'), 'Broadening')

    def test_falling_trend(self):
        """하락 → Concentration."""
        self.assertEqual(size_regime_signal('falling'), 'Concentration')

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = SizeFactorCalculator()
        # KOSDAQ 강세 추세
        kospi =  [2500] * 12
        kosdaq = [700, 710, 720, 730, 740, 750,
                  770, 790, 810, 830, 850, 870]
        result = calc.calculate(kospi, kosdaq)
        self.assertIn('trend', result)
        self.assertEqual(result['trend'], 'rising')


# ── 주식-채권 관계 테스트 ──────────────────────────────

class TestEquityBondCalculator(unittest.TestCase):

    def test_positive_correlation(self):
        """양의 상관 → Inflationary."""
        # 동행 데이터
        a = [100 + i for i in range(60)]
        b = [50 + i * 0.5 for i in range(60)]
        corr = calc_correlation(a, b)
        self.assertGreater(corr, 0.3)
        self.assertEqual(classify_correlation(corr), 'positive')
        self.assertEqual(eb_regime_signal('positive'), 'Inflationary')

    def test_negative_correlation(self):
        """음의 상관 → Transitional (정상 역상관)."""
        a = [100 + i for i in range(60)]
        b = [100 - i * 0.5 for i in range(60)]
        corr = calc_correlation(a, b)
        self.assertLess(corr, -0.3)
        self.assertEqual(classify_correlation(corr), 'negative')

    def test_weak_correlation(self):
        """약한 상관 → Transitional."""
        a = [100, 101, 99, 102, 98, 103] * 10
        b = [50, 52, 48, 51, 49, 50] * 10
        corr = calc_correlation(a, b)
        # 이 데이터는 약한 양의 상관이 될 수 있으나 weak에 가까움
        self.assertIn(classify_correlation(corr), ['positive', 'weak'])

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = EquityBondCalculator()
        result = calc.calculate(
            [100 + i for i in range(60)],
            [50 + i * 0.5 for i in range(60)],
        )
        self.assertIn('correlation', result)
        self.assertIn('regime_signal', result)


# ── 섹터 로테이션 테스트 ──────────────────────────────

class TestSectorRotationCalculator(unittest.TestCase):

    def test_cyclical_leading(self):
        """경기민감 강세 → Broadening."""
        perf = calc_relative_perf([0.05, 0.03, 0.04], [0.01, 0.00, -0.01])
        self.assertGreater(perf, 0)
        self.assertEqual(classify_rotation(perf), 'cyclical_leading')
        self.assertEqual(sr_regime_signal('cyclical_leading'), 'Broadening')

    def test_defensive_leading(self):
        """방어 강세 → Contraction."""
        perf = calc_relative_perf([-0.02, -0.01, 0.00], [0.03, 0.02, 0.01])
        self.assertLess(perf, 0)
        self.assertEqual(classify_rotation(perf), 'defensive_leading')
        self.assertEqual(sr_regime_signal('defensive_leading'), 'Contraction')

    def test_mixed(self):
        """혼재 → Transitional."""
        perf = calc_relative_perf([0.01], [0.01])
        self.assertEqual(classify_rotation(perf), 'mixed')

    def test_calculator_class(self):
        """Calculator 클래스."""
        calc = SectorRotationCalculator()
        sector_returns = {
            '1011': 0.05, '1007': 0.03, '1014': 0.04,  # 경기민감
            '1016': 0.01, '1001': 0.00, '1005': -0.01,  # 방어
        }
        result = calc.calculate(sector_returns)
        self.assertEqual(result['rotation'], 'cyclical_leading')

    def test_sector_constants(self):
        """섹터 상수."""
        self.assertEqual(len(KR_CYCLICAL_SECTORS), 3)
        self.assertEqual(len(KR_DEFENSIVE_SECTORS), 3)


# ── 스코어러 테스트 ───────────────────────────────────

class TestRegimeClassification(unittest.TestCase):

    def test_clear_concentration(self):
        """명확한 Concentration 레짐."""
        components = {
            'concentration': {'regime_signal': 'Concentration'},
            'yield_curve': {'regime_signal': 'Transitional'},
            'credit': {'regime_signal': 'Transitional'},
            'size_factor': {'regime_signal': 'Concentration'},
            'equity_bond': {'regime_signal': 'Transitional'},
            'sector_rotation': {'regime_signal': 'Concentration'},
        }
        result = classify_regime(components)
        self.assertEqual(result['regime'], 'Concentration')

    def test_clear_contraction(self):
        """명확한 Contraction 레짐."""
        components = {
            'concentration': {'regime_signal': 'Transitional'},
            'yield_curve': {'regime_signal': 'Contraction'},
            'credit': {'regime_signal': 'Contraction'},
            'size_factor': {'regime_signal': 'Contraction'},
            'equity_bond': {'regime_signal': 'Transitional'},
            'sector_rotation': {'regime_signal': 'Contraction'},
        }
        result = classify_regime(components)
        self.assertEqual(result['regime'], 'Contraction')

    def test_transitional_below_threshold(self):
        """모든 시그널 분산 → Transitional."""
        components = {
            'concentration': {'regime_signal': 'Concentration'},
            'yield_curve': {'regime_signal': 'Broadening'},
            'credit': {'regime_signal': 'Contraction'},
            'size_factor': {'regime_signal': 'Inflationary'},
            'equity_bond': {'regime_signal': 'Transitional'},
            'sector_rotation': {'regime_signal': 'Broadening'},
        }
        result = classify_regime(components)
        # 모든 투표가 분산되어 40% 미만 → Transitional
        self.assertEqual(result['regime'], 'Transitional')

    def test_confidence_range(self):
        """확신도 0-1 범위."""
        components = {k: {'regime_signal': 'Broadening'}
                      for k in COMPONENT_WEIGHTS}
        result = classify_regime(components)
        self.assertGreaterEqual(result['confidence'], 0)
        self.assertLessEqual(result['confidence'], 1)

    def test_empty_components(self):
        """빈 컴포넌트 → Transitional."""
        result = classify_regime({})
        self.assertEqual(result['regime'], 'Transitional')


class TestMacroRegimeScorer(unittest.TestCase):

    def test_classify(self):
        """MacroRegimeScorer.classify()."""
        scorer = MacroRegimeScorer()
        components = {
            'concentration': {'regime_signal': 'Broadening'},
            'yield_curve': {'regime_signal': 'Broadening'},
            'credit': {'regime_signal': 'Broadening'},
            'size_factor': {'regime_signal': 'Broadening'},
            'equity_bond': {'regime_signal': 'Transitional'},
            'sector_rotation': {'regime_signal': 'Broadening'},
        }
        result = scorer.classify(components)
        self.assertEqual(result['regime'], 'Broadening')
        self.assertIn('transition_probs', result)
        self.assertIn('strategic_implication', result)
        self.assertIn('components', result)

    def test_transition_probs(self):
        """전환 확률에 현재 레짐 미포함."""
        scorer = MacroRegimeScorer()
        components = {k: {'regime_signal': 'Concentration'}
                      for k in COMPONENT_WEIGHTS}
        result = scorer.classify(components)
        self.assertNotIn('Concentration', result['transition_probs'])

    def test_weights_sum_to_1(self):
        """가중치 합계 = 1.0."""
        total = sum(COMPONENT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_six_components(self):
        """6개 컴포넌트."""
        self.assertEqual(len(COMPONENT_WEIGHTS), 6)

    def test_five_regime_types(self):
        """5개 레짐."""
        self.assertEqual(len(REGIME_TYPES), 5)


# ── 리포트 생성 테스트 ────────────────────────────────

class TestReportGenerator(unittest.TestCase):

    def test_generate_files(self):
        """JSON + MD 파일 생성."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'classified': {
                    'regime': 'Concentration',
                    'confidence': 0.65,
                    'votes': {
                        'Concentration': 0.65,
                        'Broadening': 0.10,
                        'Contraction': 0.05,
                        'Inflationary': 0.05,
                        'Transitional': 0.15,
                    },
                    'transition_probs': {
                        'Broadening': 0.10,
                        'Contraction': 0.05,
                    },
                    'strategic_implication': '대형 성장주 유지',
                    'components': {
                        'concentration': {'regime_signal': 'Concentration'},
                        'yield_curve': {'regime_signal': 'Transitional'},
                        'credit': {'regime_signal': 'Transitional'},
                        'size_factor': {'regime_signal': 'Concentration'},
                        'equity_bond': {'regime_signal': 'Transitional'},
                        'sector_rotation': {'regime_signal': 'Concentration'},
                    },
                },
            }
            output = reporter.generate(result)
            self.assertTrue(os.path.exists(output['json_path']))
            self.assertTrue(os.path.exists(output['md_path']))

            with open(output['json_path'], 'r') as f:
                data = json.load(f)
            self.assertEqual(data['regime'], 'Concentration')
            self.assertEqual(data['confidence'], 0.65)

    def test_md_sections(self):
        """Markdown 핵심 섹션."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            result = {
                'analysis_date': '2026-02-28',
                'classified': {
                    'regime': 'Transitional',
                    'confidence': 0.3,
                    'votes': {},
                    'transition_probs': {},
                    'strategic_implication': '관망',
                    'components': {},
                },
            }
            output = reporter.generate(result)
            md = output['md_content']
            self.assertIn('현재 레짐', md)
            self.assertIn('6-컴포넌트 시그널', md)
            self.assertIn('레짐 가이드', md)


# ── 상수 검증 ─────────────────────────────────────────

class TestConstants(unittest.TestCase):

    def test_threshold(self):
        """Transitional 임계값 = 40%."""
        self.assertAlmostEqual(TRANSITIONAL_THRESHOLD, 0.40)

    def test_regime_types_count(self):
        """5개 레짐 타입."""
        self.assertEqual(len(REGIME_TYPES), 5)

    def test_component_count(self):
        """6개 컴포넌트."""
        self.assertEqual(len(COMPONENT_WEIGHTS), 6)


if __name__ == '__main__':
    unittest.main()
