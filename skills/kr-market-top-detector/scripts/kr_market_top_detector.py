"""
kr-market-top-detector: 메인 오케스트레이터.
7-컴포넌트 천장 리스크 분석.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from distribution_calculator import DistributionDayCalculator
from leading_stock_calculator import LeadingStockCalculator
from defensive_rotation_calculator import DefensiveRotationCalculator
from foreign_flow_calculator import ForeignFlowCalculator
from scorer import MarketTopScorer, score_index_technical, score_sentiment, score_breadth_divergence
from report_generator import ReportGenerator


def analyze(data: dict, output_dir: str = './output') -> dict:
    """천장 리스크 종합 분석.

    Args:
        data: {
            'kospi_closes': list, 'kospi_volumes': list,
            'kosdaq_closes': list, 'kosdaq_volumes': list,
            'leading_stocks': list[dict],
            'sector_returns': dict,
            'is_near_high': bool, 'breadth_ratio': float,
            'technical_signals': dict,
            'vkospi': float, 'credit_yoy': float,
            'foreign_daily_net': list[float],
        }
        output_dir: 리포트 출력 디렉토리
    Returns:
        {'scored': dict, 'report': dict}
    """
    # 1. 분배일
    dist_calc = DistributionDayCalculator()
    kospi_dist = dist_calc.count(
        data.get('kospi_closes', []), data.get('kospi_volumes', []))
    kosdaq_dist = dist_calc.count(
        data.get('kosdaq_closes', []), data.get('kosdaq_volumes', []))
    dist_score = dist_calc.score(kospi_dist, kosdaq_dist)

    # 2. 선도주 건전성
    ls_calc = LeadingStockCalculator()
    ls_health = ls_calc.calculate(data.get('leading_stocks', []))
    ls_score = ls_calc.score(ls_health)

    # 3. 방어 섹터 로테이션
    dr_calc = DefensiveRotationCalculator()
    dr_rotation = dr_calc.calculate(data.get('sector_returns', {}))
    dr_score = dr_calc.score(dr_rotation)

    # 4. 시장폭 다이버전스
    breadth_score = score_breadth_divergence(
        data.get('is_near_high', False),
        data.get('breadth_ratio', 0.5),
    )

    # 5. 기술적 조건
    tech_score = score_index_technical(data.get('technical_signals', {}))

    # 6. 센티먼트
    sent_score = score_sentiment(
        data.get('vkospi', 20.0),
        data.get('credit_yoy', 0.0),
    )

    # 7. 외국인 수급
    ff_calc = ForeignFlowCalculator()
    ff_flow = ff_calc.calculate(data.get('foreign_daily_net', []))
    ff_score = ff_calc.score(ff_flow)

    # 스코어링
    components = {
        'distribution': dist_score,
        'leading_stock': ls_score,
        'defensive_rotation': dr_score,
        'breadth_divergence': breadth_score,
        'index_technical': tech_score,
        'sentiment': sent_score,
        'foreign_flow': ff_score,
    }

    scorer = MarketTopScorer()
    scored = scorer.score(components)

    # 리포트
    reporter = ReportGenerator(output_dir)
    result = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'scored': scored,
    }
    report = reporter.generate(result)

    return {
        'scored': scored,
        'report': report,
    }
