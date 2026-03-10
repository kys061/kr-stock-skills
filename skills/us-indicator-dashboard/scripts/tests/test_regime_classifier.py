"""regime_classifier.py 테스트."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from regime_classifier import (
    Regime, COMPONENT_WEIGHTS,
    calc_inflation_score, calc_growth_score,
    calc_employment_score, calc_sentiment_score,
    calc_external_score, classify_regime, analyze_regime,
)


class TestComponentWeights:
    """컴포넌트 가중치 테스트."""

    def test_weights_sum_to_1(self):
        """가중치 합 = 1.0."""
        assert abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) < 0.001

    def test_inflation_highest(self):
        """물가 가중치 최대 (0.30)."""
        assert COMPONENT_WEIGHTS['inflation'] == 0.30


class TestInflationScore:
    """물가 스코어 테스트."""

    def test_low_inflation(self):
        """물가 안정 시 높은 점수."""
        result = calc_inflation_score(cpi=2.0, pce=2.0)
        assert result['score'] >= 70
        assert result['level'] == 'low'

    def test_high_inflation(self):
        """물가 높을 시 낮은 점수."""
        result = calc_inflation_score(cpi=5.0, pce=4.5)
        assert result['score'] <= 30
        assert result['level'] in ('high', 'very_high')

    def test_moderate_inflation(self):
        """보통 수준."""
        result = calc_inflation_score(cpi=2.9, pce=2.5)
        assert 30 < result['score'] < 80

    def test_no_data(self):
        """데이터 없음."""
        result = calc_inflation_score()
        assert result['score'] == 50.0
        assert result['level'] == 'unknown'

    def test_partial_data(self):
        """일부 데이터만."""
        result = calc_inflation_score(cpi=2.5)
        assert result['score'] > 0
        assert 'cpi' in result['detail']


class TestGrowthScore:
    """경기 스코어 테스트."""

    def test_strong_growth(self):
        """강한 성장."""
        result = calc_growth_score(gdp=3.5, ism_pmi=55.0, retail_sales=0.5)
        assert result['score'] >= 60
        assert result['level'] in ('moderate', 'strong')

    def test_weak_growth(self):
        """약한 성장."""
        result = calc_growth_score(gdp=0.5, ism_pmi=45.0, retail_sales=-1.0)
        assert result['score'] <= 40

    def test_recession(self):
        """경기 침체."""
        result = calc_growth_score(gdp=-1.0, ism_pmi=40.0)
        assert result['level'] in ('weak', 'recession')


class TestEmploymentScore:
    """고용 스코어 테스트."""

    def test_tight_labor(self):
        """고용 과열."""
        result = calc_employment_score(unemployment=3.4, jobless_claims=180)
        assert result['score'] >= 60

    def test_weak_labor(self):
        """고용 약화."""
        result = calc_employment_score(unemployment=6.0, jobless_claims=350)
        assert result['score'] <= 30

    def test_balanced(self):
        """균형 고용."""
        result = calc_employment_score(unemployment=4.5, jobless_claims=250)
        assert 30 <= result['score'] <= 70


class TestSentimentScore:
    """심리 스코어 테스트."""

    def test_optimistic(self):
        """낙관적."""
        result = calc_sentiment_score(consumer_sentiment=110, consumer_confidence=120)
        assert result['score'] >= 60

    def test_pessimistic(self):
        """비관적."""
        result = calc_sentiment_score(consumer_sentiment=55, consumer_confidence=65)
        assert result['score'] <= 30


class TestExternalScore:
    """대외 스코어 테스트."""

    def test_healthy(self):
        """양호."""
        result = calc_external_score(current_account=-100)
        assert result['score'] >= 60

    def test_deficit_widening(self):
        """적자 확대."""
        result = calc_external_score(current_account=-350)
        assert result['score'] <= 30

    def test_no_data(self):
        """데이터 없음."""
        result = calc_external_score()
        assert result['score'] == 50.0


class TestClassifyRegime:
    """레짐 분류 테스트."""

    def test_goldilocks(self):
        """골디락스: 물가 안정 + 경기 강세."""
        result = classify_regime(70, 60, 50, 60, 50)
        assert result['regime'] == Regime.GOLDILOCKS

    def test_overheating(self):
        """과열: 물가 높음 + 경기 강세."""
        result = classify_regime(30, 65, 70, 60, 50)
        assert result['regime'] == Regime.OVERHEATING

    def test_stagflation(self):
        """스태그플레이션: 물가 높음 + 경기 약세."""
        result = classify_regime(30, 35, 40, 30, 40)
        assert result['regime'] == Regime.STAGFLATION

    def test_recession(self):
        """침체: 물가 안정 + 경기 약세."""
        result = classify_regime(70, 35, 30, 30, 50)
        assert result['regime'] == Regime.RECESSION

    def test_boundary_tiebreak_optimistic(self):
        """경계값 tie-break — 심리 낙관."""
        result = classify_regime(50, 50, 50, 60, 50)
        assert result['regime'] == Regime.GOLDILOCKS

    def test_boundary_tiebreak_pessimistic(self):
        """경계값 tie-break — 심리 비관."""
        result = classify_regime(50, 50, 50, 30, 50)
        assert result['regime'] == Regime.STAGFLATION

    def test_composite_score(self):
        """종합 점수 계산."""
        result = classify_regime(60, 50, 50, 60, 50)
        expected = 60*0.3 + 50*0.25 + 50*0.25 + 60*0.1 + 50*0.1
        assert abs(result['composite_score'] - expected) < 0.1


class TestAnalyzeRegime:
    """레짐 전체 분석 테스트."""

    def test_analyze_with_data(self):
        """지표 데이터로 레짐 분석."""
        indicators = [
            {'id': 'cpi', 'value': 2.5},
            {'id': 'pce', 'value': 2.3},
            {'id': 'gdp', 'value': 2.8},
            {'id': 'ism_pmi', 'value': 52.0},
            {'id': 'unemployment', 'value': 4.0},
            {'id': 'consumer_sentiment', 'value': 95},
            {'id': 'current_account', 'value': -200},
        ]
        result = analyze_regime(indicators)
        assert 'regime' in result
        assert 'composite_score' in result
        assert 'component_details' in result

    def test_analyze_empty(self):
        """빈 지표 리스트."""
        result = analyze_regime([])
        assert 'regime' in result
