"""
kr-macro-regime: 메인 오케스트레이터.
6-컴포넌트 크로스에셋 비율 분석으로 레짐 판정.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'calculators'))

from calculators.concentration_calculator import ConcentrationCalculator
from calculators.yield_curve_calculator import YieldCurveCalculator
from calculators.credit_calculator import CreditCalculator
from calculators.size_factor_calculator import SizeFactorCalculator
from calculators.equity_bond_calculator import EquityBondCalculator
from calculators.sector_rotation_calculator import SectorRotationCalculator
from scorer import MacroRegimeScorer
from report_generator import ReportGenerator


def analyze(data: dict, output_dir: str = './output') -> dict:
    """매크로 레짐 종합 분석.

    Args:
        data: {
            'top10_ratios': list[float],
            'yields_10y': list[float],
            'yields_3y': list[float],
            'bbb_yields': list[float],
            'aa_yields': list[float],
            'kospi_values': list[float],
            'kosdaq_values': list[float],
            'bond_prices': list[float],
            'sector_returns': dict,
        }
        output_dir: 리포트 출력 디렉토리
    Returns:
        {'classified': dict, 'report': dict}
    """
    # 1. 시장 집중도
    conc_calc = ConcentrationCalculator()
    conc = conc_calc.calculate(data.get('top10_ratios', []))

    # 2. 금리 곡선
    yc_calc = YieldCurveCalculator()
    yc = yc_calc.calculate(
        data.get('yields_10y', []),
        data.get('yields_3y', []),
    )

    # 3. 신용 환경
    credit_calc = CreditCalculator()
    credit = credit_calc.calculate(
        data.get('bbb_yields', []),
        data.get('aa_yields', []),
    )

    # 4. 사이즈 팩터
    sf_calc = SizeFactorCalculator()
    sf = sf_calc.calculate(
        data.get('kospi_values', []),
        data.get('kosdaq_values', []),
    )

    # 5. 주식-채권 관계
    eb_calc = EquityBondCalculator()
    eb = eb_calc.calculate(
        data.get('kospi_values', []),
        data.get('bond_prices', []),
    )

    # 6. 섹터 로테이션
    sr_calc = SectorRotationCalculator()
    sr = sr_calc.calculate(data.get('sector_returns', {}))

    # 레짐 분류
    components = {
        'concentration': conc,
        'yield_curve': yc,
        'credit': credit,
        'size_factor': sf,
        'equity_bond': eb,
        'sector_rotation': sr,
    }

    scorer = MacroRegimeScorer()
    classified = scorer.classify(components)

    # 리포트
    reporter = ReportGenerator(output_dir)
    report_input = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'classified': classified,
    }
    report = reporter.generate(report_input)

    return {
        'classified': classified,
        'report': report,
    }
