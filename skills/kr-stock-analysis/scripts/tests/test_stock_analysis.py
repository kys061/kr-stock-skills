"""kr-stock-analysis 테스트."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fundamental_analyzer import (
    FUNDAMENTAL_METRICS, VALUATION_BENCHMARKS, PROFITABILITY_BENCHMARKS,
    GROWTH_BENCHMARKS, HEALTH_BENCHMARKS,
    _score_valuation, _score_profitability, _score_growth,
    _score_financial_health, analyze_fundamentals,
)
from technical_analyzer import (
    TECHNICAL_INDICATORS, calc_moving_averages, calc_rsi,
    calc_macd, calc_bollinger_bands, analyze_technicals,
)
from supply_demand_analyzer import (
    SUPPLY_DEMAND_ANALYSIS, FLOW_THRESHOLDS,
    classify_supply_signal, analyze_supply_demand,
)
from comprehensive_scorer import (
    COMPREHENSIVE_SCORING, ANALYSIS_TYPES, ANALYSIS_GRADES,
    calc_comprehensive_score,
)
from report_generator import StockAnalysisReportGenerator


# ═══════════════════════════════════════════════════════
# 1. 상수 테스트
# ═══════════════════════════════════════════════════════

class TestConstants:
    """상수 정의 검증."""

    def test_fundamental_metrics_4_groups(self):
        assert len(FUNDAMENTAL_METRICS) == 4
        assert set(FUNDAMENTAL_METRICS.keys()) == {
            'valuation', 'profitability', 'growth', 'financial_health',
        }

    def test_fundamental_valuation_4_metrics(self):
        assert len(FUNDAMENTAL_METRICS['valuation']) == 4
        assert 'per' in FUNDAMENTAL_METRICS['valuation']
        assert 'pbr' in FUNDAMENTAL_METRICS['valuation']

    def test_fundamental_profitability_4_metrics(self):
        assert len(FUNDAMENTAL_METRICS['profitability']) == 4
        assert 'roe' in FUNDAMENTAL_METRICS['profitability']

    def test_fundamental_growth_3_metrics(self):
        assert len(FUNDAMENTAL_METRICS['growth']) == 3
        assert 'revenue_growth_3y' in FUNDAMENTAL_METRICS['growth']

    def test_fundamental_health_3_metrics(self):
        assert len(FUNDAMENTAL_METRICS['financial_health']) == 3
        assert 'debt_ratio' in FUNDAMENTAL_METRICS['financial_health']

    def test_fundamental_total_14_metrics(self):
        total = sum(len(v) for v in FUNDAMENTAL_METRICS.values())
        assert total == 14

    def test_technical_indicators_4_groups(self):
        assert len(TECHNICAL_INDICATORS) == 4
        assert set(TECHNICAL_INDICATORS.keys()) == {
            'trend', 'momentum', 'volatility', 'volume',
        }

    def test_technical_8_indicators(self):
        total = sum(len(v) for v in TECHNICAL_INDICATORS.values())
        assert total == 8

    def test_supply_demand_3_investor_types(self):
        assert len(SUPPLY_DEMAND_ANALYSIS['investor_types']) == 3

    def test_supply_demand_4_periods(self):
        assert SUPPLY_DEMAND_ANALYSIS['periods'] == [1, 5, 20, 60]

    def test_supply_demand_5_signals(self):
        assert len(SUPPLY_DEMAND_ANALYSIS['signals']) == 5

    def test_scoring_5_components(self):
        assert len(COMPREHENSIVE_SCORING) == 5
        weights = sum(v['weight'] for v in COMPREHENSIVE_SCORING.values())
        assert abs(weights - 1.0) < 0.001

    def test_scoring_weights_match_design(self):
        assert COMPREHENSIVE_SCORING['fundamental']['weight'] == 0.30
        assert COMPREHENSIVE_SCORING['technical']['weight'] == 0.22
        assert COMPREHENSIVE_SCORING['supply_demand']['weight'] == 0.22
        assert COMPREHENSIVE_SCORING['valuation']['weight'] == 0.13
        assert COMPREHENSIVE_SCORING['growth']['weight'] == 0.13

    def test_analysis_types_5(self):
        assert len(ANALYSIS_TYPES) == 5
        assert 'COMPREHENSIVE' in ANALYSIS_TYPES
        assert 'SUPPLY_DEMAND' in ANALYSIS_TYPES

    def test_analysis_grades_5(self):
        assert len(ANALYSIS_GRADES) == 5
        assert ANALYSIS_GRADES['STRONG_BUY'] == 80
        assert ANALYSIS_GRADES['BUY'] == 65
        assert ANALYSIS_GRADES['HOLD'] == 50
        assert ANALYSIS_GRADES['SELL'] == 35
        assert ANALYSIS_GRADES['STRONG_SELL'] == 0

    def test_flow_thresholds(self):
        assert FLOW_THRESHOLDS['strong_buy'] == 1_000_000_000
        assert FLOW_THRESHOLDS['buy'] == 100_000_000


# ═══════════════════════════════════════════════════════
# 2. 펀더멘털 분석 테스트
# ═══════════════════════════════════════════════════════

class TestValuationScoring:
    """밸류에이션 점수 테스트."""

    def test_cheap_valuation(self):
        data = {'per': 8, 'pbr': 0.5, 'psr': 0.3, 'ev_ebitda': 4}
        score = _score_valuation(data)
        assert score >= 80

    def test_expensive_valuation(self):
        data = {'per': 30, 'pbr': 3.0, 'psr': 8.0, 'ev_ebitda': 20}
        score = _score_valuation(data)
        assert score <= 40

    def test_fair_valuation(self):
        data = {'per': 15, 'pbr': 1.0, 'psr': 1.5, 'ev_ebitda': 10}
        score = _score_valuation(data)
        assert 50 <= score <= 75

    def test_empty_data_returns_50(self):
        assert _score_valuation({}) == 50.0

    def test_negative_per_ignored(self):
        data = {'per': -5, 'pbr': 1.0}
        score = _score_valuation(data)
        # per ignored, only pbr counts
        assert score > 0


class TestProfitabilityScoring:
    """수익성 점수 테스트."""

    def test_excellent_profitability(self):
        data = {'roe': 25, 'roa': 12, 'operating_margin': 25, 'net_margin': 18}
        score = _score_profitability(data)
        assert score >= 80

    def test_poor_profitability(self):
        data = {'roe': 2, 'roa': 1, 'operating_margin': 2, 'net_margin': 1}
        score = _score_profitability(data)
        assert score <= 35

    def test_average_profitability(self):
        data = {'roe': 10, 'roa': 5, 'operating_margin': 10, 'net_margin': 7}
        score = _score_profitability(data)
        assert 50 <= score <= 75


class TestGrowthScoring:
    """성장성 점수 테스트."""

    def test_high_growth(self):
        data = {'revenue_growth_3y': 25, 'earnings_growth_3y': 35, 'dividend_growth_3y': 20}
        score = _score_growth(data)
        assert score >= 75

    def test_low_growth(self):
        data = {'revenue_growth_3y': 3, 'earnings_growth_3y': 2, 'dividend_growth_3y': 1}
        score = _score_growth(data)
        assert score <= 45

    def test_negative_growth(self):
        data = {'revenue_growth_3y': -5, 'earnings_growth_3y': -10}
        score = _score_growth(data)
        assert score <= 30


class TestHealthScoring:
    """재무건전성 점수 테스트."""

    def test_healthy_company(self):
        data = {'debt_ratio': 50, 'current_ratio': 2.0, 'interest_coverage': 10}
        score = _score_financial_health(data)
        assert score >= 80

    def test_risky_company(self):
        data = {'debt_ratio': 500, 'current_ratio': 0.5, 'interest_coverage': 0.5}
        score = _score_financial_health(data)
        assert score <= 30

    def test_moderate_health(self):
        data = {'debt_ratio': 150, 'current_ratio': 1.2, 'interest_coverage': 4.0}
        score = _score_financial_health(data)
        assert 50 <= score <= 80


class TestAnalyzeFundamentals:
    """종합 펀더멘털 분석 테스트."""

    def test_returns_all_components(self):
        data = {
            'valuation': {'per': 12, 'pbr': 0.8},
            'profitability': {'roe': 15, 'operating_margin': 12},
            'growth': {'revenue_growth_3y': 10},
            'financial_health': {'debt_ratio': 100, 'current_ratio': 1.5},
        }
        result = analyze_fundamentals(data)
        assert 'valuation' in result
        assert 'profitability' in result
        assert 'growth' in result
        assert 'health' in result
        assert 'score' in result

    def test_score_range(self):
        data = {
            'valuation': {'per': 12},
            'profitability': {'roe': 15},
            'growth': {'revenue_growth_3y': 10},
            'financial_health': {'debt_ratio': 100},
        }
        result = analyze_fundamentals(data)
        assert 0 <= result['score'] <= 100

    def test_empty_data(self):
        result = analyze_fundamentals({})
        assert result['score'] == 50.0

    def test_strong_fundamentals_high_score(self):
        data = {
            'valuation': {'per': 8, 'pbr': 0.5},
            'profitability': {'roe': 25, 'roa': 12, 'operating_margin': 20, 'net_margin': 15},
            'growth': {'revenue_growth_3y': 20, 'earnings_growth_3y': 30},
            'financial_health': {'debt_ratio': 40, 'current_ratio': 2.5, 'interest_coverage': 10},
        }
        result = analyze_fundamentals(data)
        assert result['score'] >= 70


# ═══════════════════════════════════════════════════════
# 3. 기술적 분석 테스트
# ═══════════════════════════════════════════════════════

class TestMovingAverages:
    """이동평균 테스트."""

    def test_ma20_calculation(self):
        prices = list(range(1, 25))  # 24 prices
        result = calc_moving_averages(prices, (20,))
        expected = sum(range(5, 25)) / 20
        assert result['ma20'] == round(expected, 2)

    def test_insufficient_data(self):
        prices = list(range(1, 15))  # 14 prices
        result = calc_moving_averages(prices, (20,))
        assert result['ma20'] is None

    def test_multiple_periods(self):
        prices = list(range(1, 130))  # 129 prices
        result = calc_moving_averages(prices)
        assert result['ma20'] is not None
        assert result['ma60'] is not None
        assert result['ma120'] is not None


class TestRSI:
    """RSI 테스트."""

    def test_uptrend_high_rsi(self):
        # Consistently rising prices → high RSI
        prices = [100 + i * 2 for i in range(20)]
        rsi = calc_rsi(prices)
        assert rsi is not None
        assert rsi > 70

    def test_downtrend_low_rsi(self):
        # Consistently falling prices → low RSI
        prices = [200 - i * 2 for i in range(20)]
        rsi = calc_rsi(prices)
        assert rsi is not None
        assert rsi < 30

    def test_insufficient_data(self):
        prices = [100, 101, 102]
        assert calc_rsi(prices) is None

    def test_rsi_range(self):
        prices = [100 + (i % 5) * 3 - 6 for i in range(30)]
        rsi = calc_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_all_same_price(self):
        prices = [100] * 20
        rsi = calc_rsi(prices)
        # No gains, no losses → RSI = 100 (avg_loss=0)
        assert rsi == 100.0


class TestMACD:
    """MACD 테스트."""

    def test_basic_calculation(self):
        prices = [100 + i * 0.5 for i in range(50)]
        result = calc_macd(prices)
        assert result is not None
        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result

    def test_histogram_is_difference(self):
        prices = [100 + i * 0.5 for i in range(50)]
        result = calc_macd(prices)
        assert abs(result['histogram'] - (result['macd'] - result['signal'])) < 0.01

    def test_insufficient_data(self):
        prices = [100, 101, 102]
        assert calc_macd(prices) is None


class TestBollingerBands:
    """볼린저 밴드 테스트."""

    def test_basic_calculation(self):
        prices = [100 + i * 0.5 for i in range(25)]
        result = calc_bollinger_bands(prices)
        assert result is not None
        assert result['upper'] > result['middle'] > result['lower']

    def test_bandwidth_positive(self):
        prices = [100 + (i % 3) * 2 for i in range(25)]
        result = calc_bollinger_bands(prices)
        assert result['bandwidth'] > 0

    def test_percent_b_within_bands(self):
        prices = [100] * 20 + [100]  # Stable price → %B near 50
        result = calc_bollinger_bands(prices)
        # With constant prices, std=0, so %B should be 50 (special case)
        assert result is not None

    def test_insufficient_data(self):
        prices = [100, 101]
        assert calc_bollinger_bands(prices) is None


class TestAnalyzeTechnicals:
    """종합 기술적 분석 테스트."""

    def test_returns_all_components(self):
        prices = [100 + i * 0.5 for i in range(130)]
        volumes = [1000000 + i * 10000 for i in range(130)]
        result = analyze_technicals({'prices': prices, 'volumes': volumes})
        assert 'trend' in result
        assert 'momentum' in result
        assert 'volatility' in result
        assert 'volume' in result
        assert 'score' in result

    def test_score_range(self):
        prices = [100 + i * 0.5 for i in range(50)]
        result = analyze_technicals({'prices': prices})
        assert 0 <= result['score'] <= 100

    def test_uptrend_higher_score(self):
        up_prices = [100 + i * 2 for i in range(130)]
        down_prices = [300 - i * 2 for i in range(130)]
        up_result = analyze_technicals({'prices': up_prices})
        down_result = analyze_technicals({'prices': down_prices})
        assert up_result['score'] > down_result['score']


# ═══════════════════════════════════════════════════════
# 4. 수급 분석 테스트
# ═══════════════════════════════════════════════════════

class TestClassifySupplySignal:
    """수급 시그널 분류 테스트."""

    def test_strong_buy(self):
        signal = classify_supply_signal(2_000_000_000, 500_000_000)
        assert signal == 'STRONG_BUY'

    def test_buy(self):
        signal = classify_supply_signal(500_000_000, 50_000_000)
        assert signal == 'BUY'

    def test_neutral(self):
        signal = classify_supply_signal(50_000_000, 50_000_000)
        assert signal == 'NEUTRAL'

    def test_sell(self):
        signal = classify_supply_signal(-500_000_000, -500_000_000)
        assert signal == 'SELL'

    def test_strong_sell_individual_buying(self):
        signal = classify_supply_signal(-500_000_000, -500_000_000, 1_000_000_000)
        assert signal == 'STRONG_SELL'

    def test_foreign_sell_inst_neutral(self):
        signal = classify_supply_signal(-500_000_000, 0)
        assert signal == 'SELL'


class TestAnalyzeSupplyDemand:
    """종합 수급 분석 테스트."""

    def test_returns_all_components(self):
        data = {
            'foreign': {1: 500_000_000, 5: 2_000_000_000, 20: 5_000_000_000, 60: 10_000_000_000},
            'institution': {1: 200_000_000, 5: 800_000_000, 20: 1_500_000_000, 60: 3_000_000_000},
            'individual': {1: -700_000_000, 5: -2_800_000_000, 20: -6_500_000_000, 60: -13_000_000_000},
        }
        result = analyze_supply_demand(data)
        assert 'foreign' in result
        assert 'institution' in result
        assert 'individual' in result
        assert 'signal' in result
        assert 'score' in result

    def test_strong_buy_high_score(self):
        data = {
            'foreign': {1: 5_000_000_000, 5: 10_000_000_000, 20: 20_000_000_000, 60: 40_000_000_000},
            'institution': {1: 3_000_000_000, 5: 6_000_000_000, 20: 12_000_000_000, 60: 24_000_000_000},
            'individual': {1: -8_000_000_000, 5: -16_000_000_000, 20: -32_000_000_000, 60: -64_000_000_000},
        }
        result = analyze_supply_demand(data)
        assert result['signal'] == 'STRONG_BUY'
        assert result['score'] >= 70

    def test_sell_low_score(self):
        data = {
            'foreign': {1: -5_000_000_000, 5: -10_000_000_000, 20: -20_000_000_000, 60: -40_000_000_000},
            'institution': {1: -3_000_000_000, 5: -6_000_000_000, 20: -12_000_000_000, 60: -24_000_000_000},
            'individual': {1: 8_000_000_000, 5: 16_000_000_000, 20: 32_000_000_000, 60: 64_000_000_000},
        }
        result = analyze_supply_demand(data)
        assert result['signal'] == 'STRONG_SELL'
        assert result['score'] <= 40

    def test_score_range(self):
        data = {
            'foreign': {1: 0, 5: 0},
            'institution': {1: 0, 5: 0},
            'individual': {1: 0, 5: 0},
        }
        result = analyze_supply_demand(data)
        assert 0 <= result['score'] <= 100


# ═══════════════════════════════════════════════════════
# 5. 종합 스코어링 테스트
# ═══════════════════════════════════════════════════════

class TestComprehensiveScorer:
    """종합 스코어링 테스트."""

    def test_all_components(self):
        result = calc_comprehensive_score(
            fundamental={'score': 80, 'valuation': {'score': 75}},
            technical={'score': 70},
            supply_demand={'score': 65},
        )
        assert 'score' in result
        assert 'grade' in result
        assert 'components' in result
        assert 'recommendation' in result

    def test_strong_buy_grade(self):
        result = calc_comprehensive_score(
            fundamental={'score': 90, 'valuation': {'score': 85}},
            technical={'score': 85},
            supply_demand={'score': 88},
        )
        assert result['grade'] == 'STRONG_BUY'
        assert result['score'] >= 80

    def test_strong_sell_grade(self):
        result = calc_comprehensive_score(
            fundamental={'score': 20, 'valuation': {'score': 15}},
            technical={'score': 15},
            supply_demand={'score': 10},
        )
        assert result['grade'] == 'STRONG_SELL'
        assert result['score'] < 35

    def test_hold_grade(self):
        result = calc_comprehensive_score(
            fundamental={'score': 55, 'valuation': {'score': 50}},
            technical={'score': 50},
            supply_demand={'score': 55},
        )
        assert result['grade'] == 'HOLD'

    def test_partial_data(self):
        result = calc_comprehensive_score(
            fundamental={'score': 70, 'valuation': {'score': 65}},
        )
        assert result['score'] > 0
        assert result['grade'] in ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL')

    def test_no_data_returns_50(self):
        result = calc_comprehensive_score()
        assert result['score'] == 50.0

    def test_explicit_valuation_score(self):
        result = calc_comprehensive_score(
            fundamental={'score': 70},
            valuation_score=80,
        )
        assert 'valuation' in result['components']
        assert result['components']['valuation']['score'] == 80

    def test_recommendation_has_summary(self):
        result = calc_comprehensive_score(
            fundamental={'score': 75, 'valuation': {'score': 70}},
            technical={'score': 72},
            supply_demand={'score': 68},
        )
        assert result['recommendation']['summary'] != ''

    def test_recommendation_identifies_strengths(self):
        result = calc_comprehensive_score(
            fundamental={'score': 85, 'valuation': {'score': 30}},
            technical={'score': 80},
            supply_demand={'score': 25},
        )
        assert '펀더멘털' in result['recommendation']['strengths']
        assert '기술적' in result['recommendation']['strengths']


# ═══════════════════════════════════════════════════════
# 6. 리포트 생성기 테스트
# ═══════════════════════════════════════════════════════

class TestReportGenerator:
    """리포트 생성기 테스트."""

    def test_empty_report(self):
        gen = StockAnalysisReportGenerator('005930', '삼성전자')
        report = gen.generate()
        assert '삼성전자' in report
        assert '005930' in report

    def test_comprehensive_report(self):
        gen = StockAnalysisReportGenerator('005930', '삼성전자')
        gen.add_fundamental({
            'score': 75,
            'valuation': {'data': {'per': 12, 'pbr': 1.2}, 'score': 70},
            'profitability': {'data': {'roe': 15}, 'score': 72},
            'growth': {'data': {'revenue_growth_3y': 10}, 'score': 65},
            'health': {'data': {'debt_ratio': 80}, 'score': 80},
        })
        gen.add_technical({
            'score': 65,
            'trend': {'moving_averages': {'ma20': 70000}, 'current_price': 72000, 'score': 60},
            'momentum': {'rsi': 55, 'macd': {'macd': 500, 'signal': 300, 'histogram': 200}, 'score': 65},
            'volatility': {'bollinger': {'upper': 75000, 'middle': 70000, 'lower': 65000, 'percent_b': 60}, 'score': 60},
            'volume': {'volume_ratio': 1.2, 'score': 55},
        })
        gen.add_supply_demand({
            'score': 70,
            'signal': 'BUY',
            'foreign': {'flows': {1: 500_000_000, 5: 1_000_000_000}, 'score': 75},
            'institution': {'flows': {1: 200_000_000, 5: 300_000_000}, 'score': 65},
            'individual': {'flows': {1: -700_000_000, 5: -1_300_000_000}, 'score': 30},
        })
        gen.add_comprehensive({
            'score': 72.5,
            'grade': 'BUY',
            'components': {
                'fundamental': {'score': 75, 'weight': 0.35},
                'technical': {'score': 65, 'weight': 0.25},
                'supply_demand': {'score': 70, 'weight': 0.25},
                'valuation': {'score': 70, 'weight': 0.15},
            },
            'recommendation': {
                'summary': '매수 고려.',
                'strengths': ['펀더멘털', '수급'],
                'weaknesses': [],
            },
        })
        report = gen.generate()
        assert 'BUY' in report
        assert '72.5' in report
        assert '펀더멘털' in report
        assert '수급' in report
        assert 'RSI' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
