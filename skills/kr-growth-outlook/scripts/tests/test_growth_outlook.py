"""Tests for kr-growth-outlook skill."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tam_analyzer import (
    score_tam_cagr, score_market_share_trend, score_sam_penetration,
    get_sector_tam_data, analyze_tam,
    TAM_CAGR_BENCHMARKS, SECTOR_GROWTH_RATINGS,
)
from moat_scorer import (
    score_moat_type, classify_moat_strength, analyze_competitive_moat,
    MOAT_TYPES,
)
from pipeline_evaluator import (
    score_new_products, score_rd_capability, analyze_pipeline,
    PIPELINE_WEIGHTS,
)
from earnings_projector import (
    score_consensus_growth, score_margin_trajectory, analyze_earnings_path,
    EARNINGS_WEIGHTS,
)
from policy_analyzer import (
    score_government_support, analyze_policy,
    POLICY_WEIGHTS, SECTOR_POLICY_DEFAULTS,
)
from management_scorer import (
    score_execution, analyze_management,
    MANAGEMENT_WEIGHTS,
)
from growth_synthesizer import (
    calc_growth_score, analyze_growth_outlook,
    GROWTH_COMPONENTS, TIME_HORIZON_MULTIPLIER,
    COMPOSITE_HORIZON_WEIGHTS, GROWTH_GRADES,
)


# ─── Weight sum verification ───

class TestWeightSums:
    """All weight sets must sum to 1.00."""

    def test_growth_components_sum(self):
        total = sum(c['weight'] for c in GROWTH_COMPONENTS.values())
        assert abs(total - 1.0) < 0.001

    def test_moat_types_sum(self):
        total = sum(m['weight'] for m in MOAT_TYPES.values())
        assert abs(total - 1.0) < 0.001

    def test_pipeline_weights_sum(self):
        total = sum(PIPELINE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_earnings_weights_sum(self):
        total = sum(EARNINGS_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_policy_weights_sum(self):
        total = sum(POLICY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_management_weights_sum(self):
        total = sum(MANAGEMENT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_composite_horizon_sum(self):
        total = sum(COMPOSITE_HORIZON_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


# ─── TAM Analyzer ───

class TestTamAnalyzer:

    def test_score_tam_cagr_hyper(self):
        assert score_tam_cagr(20) >= 90

    def test_score_tam_cagr_none(self):
        assert score_tam_cagr(None) == 50.0

    def test_score_tam_cagr_negative(self):
        assert score_tam_cagr(-5) <= 20

    def test_score_market_share_trend_gaining(self):
        assert score_market_share_trend(22, 20) > score_market_share_trend(18, 20)

    def test_score_market_share_trend_none(self):
        assert score_market_share_trend(None, None) == 50.0

    def test_score_sam_penetration_optimal(self):
        # 5-15% is optimal range (highest score)
        assert score_sam_penetration(10) >= 80

    def test_score_sam_penetration_dominant(self):
        # 30%+ has growth ceiling
        assert score_sam_penetration(40) < score_sam_penetration(10)

    def test_get_sector_tam_data(self):
        data = get_sector_tam_data('semiconductor')
        assert data is not None
        assert data['cagr_26_30'] == 0.12

    def test_get_sector_tam_data_unknown(self):
        assert get_sector_tam_data('unknown_sector') is None

    def test_analyze_tam(self):
        result = analyze_tam('semiconductor', market_share=20, prev_market_share=18)
        assert 'score' in result
        assert 0 <= result['score'] <= 100

    def test_analyze_tam_sector_only(self):
        result = analyze_tam('semiconductor')
        assert result['score'] > 40

    def test_analyze_tam_unknown_sector(self):
        result = analyze_tam('unknown')
        assert result['cagr_score'] == 50.0

    def test_14_sectors(self):
        assert len(SECTOR_GROWTH_RATINGS) == 14


# ─── Moat Scorer ───

class TestMoatScorer:

    def test_score_moat_type_high(self):
        data = {'cost_advantage': 90, 'switching_cost': 80}
        result = score_moat_type(data)
        assert result['weighted_score'] > 60

    def test_score_moat_type_empty(self):
        result = score_moat_type({})
        assert result['weighted_score'] == 50.0

    def test_classify_moat_strength_wide(self):
        assert classify_moat_strength(82) == 'wide'

    def test_classify_moat_strength_narrow(self):
        assert classify_moat_strength(55) == 'narrow'

    def test_classify_moat_strength_none(self):
        assert classify_moat_strength(30) == 'none'

    def test_analyze_competitive_moat(self):
        data = {
            'cost_advantage': 80,
            'switching_cost': 60,
            'network_effect': 40,
            'intangible_assets': 85,
            'efficient_scale': 70,
        }
        result = analyze_competitive_moat(data)
        assert 'score' in result
        assert 'strength' in result
        assert 0 <= result['score'] <= 100

    def test_analyze_competitive_moat_empty(self):
        result = analyze_competitive_moat({})
        assert result['score'] == 50.0

    def test_top_moats_identified(self):
        data = {'cost_advantage': 90, 'switching_cost': 30}
        result = analyze_competitive_moat(data)
        top_types = [m['type'] for m in result['top_moats']]
        assert 'cost_advantage' in top_types


# ─── Pipeline Evaluator ───

class TestPipelineEvaluator:

    def test_score_new_products_breakthrough(self):
        assert score_new_products('breakthrough') == 90

    def test_score_new_products_none(self):
        assert score_new_products(None) == 50.0

    def test_score_rd_capability(self):
        score = score_rd_capability(15, patent_growth=20)
        assert score >= 80

    def test_score_rd_capability_none(self):
        assert score_rd_capability(None) == 50.0

    def test_analyze_pipeline(self):
        data = {'new_products': 'major', 'rd_to_revenue': 10, 'tech_position': 'leader'}
        result = analyze_pipeline(data)
        assert 'score' in result
        assert result['score'] > 60


# ─── Earnings Projector ───

class TestEarningsProjector:

    def test_score_consensus_growth_hyper(self):
        assert score_consensus_growth(60) == 95

    def test_score_consensus_growth_none(self):
        assert score_consensus_growth(None) == 50.0

    def test_score_consensus_growth_decline(self):
        assert score_consensus_growth(-5) == 25

    def test_score_margin_trajectory_expanding(self):
        assert score_margin_trajectory(2) == 75

    def test_analyze_earnings_path(self):
        data = {'eps_growth_yoy': 30, 'opm_change': 2, 'roic': 15, 'geographic': 'global'}
        result = analyze_earnings_path(data)
        assert result['score'] > 60
        assert 'consensus_score' in result


# ─── Policy Analyzer ───

class TestPolicyAnalyzer:

    def test_score_government_support_strong(self):
        assert score_government_support('strong_tailwind') == 90

    def test_score_government_support_none(self):
        assert score_government_support(None) == 50.0

    def test_sector_policy_defaults(self):
        assert SECTOR_POLICY_DEFAULTS['semiconductor'] == 'strong_tailwind'
        assert SECTOR_POLICY_DEFAULTS['construction'] == 'moderate_headwind'

    def test_analyze_policy(self):
        data = {'support_level': 'strong_tailwind', 'regulatory': 'deregulating',
                'esg': 'aligned'}
        result = analyze_policy(data)
        assert result['score'] > 70

    def test_analyze_policy_sector_default(self):
        result = analyze_policy({'sector': 'semiconductor'})
        assert result['support_score'] == 90


# ─── Management Scorer ───

class TestManagementScorer:

    def test_score_execution(self):
        data = {'guidance_accuracy': 'high', 'strategy_delivery': 'strong'}
        score = score_execution(data)
        assert score > 70

    def test_analyze_management(self):
        data = {
            'guidance_accuracy': 'high',
            'strategy_delivery': 'strong',
            'dividend_consistency': 'strong',
            'chaebol_discount': 'independent',
        }
        result = analyze_management(data)
        assert 'score' in result
        assert result['score'] > 60


# ─── Growth Synthesizer ───

class TestGrowthSynthesizer:

    def test_calc_growth_score_all_high(self):
        scores = {k: 90 for k in GROWTH_COMPONENTS}
        result = calc_growth_score(scores, 'short_1_3y')
        assert result['score'] >= 85
        assert result['grade'] == 'S'

    def test_calc_growth_score_all_low(self):
        scores = {k: 20 for k in GROWTH_COMPONENTS}
        result = calc_growth_score(scores, 'short_1_3y')
        assert result['score'] <= 25
        assert result['grade'] == 'D'

    def test_calc_growth_score_default_50(self):
        result = calc_growth_score({}, 'short_1_3y')
        assert abs(result['score'] - 50.0) < 1

    def test_horizons_differ(self):
        # Pipeline/earnings weighted more in short, TAM/moat in long
        scores = {'tam_sam': 90, 'competitive_moat': 90,
                  'pipeline': 30, 'earnings_path': 30,
                  'policy_tailwind': 90, 'management': 90}
        short = calc_growth_score(scores, 'short_1_3y')
        long = calc_growth_score(scores, 'long_10y')
        assert long['score'] > short['score']

    def test_analyze_growth_outlook(self):
        data = {k: 70 for k in GROWTH_COMPONENTS}
        result = analyze_growth_outlook(data)
        assert 'short' in result
        assert 'mid' in result
        assert 'long' in result
        assert 'composite' in result
        assert 'grade' in result

    def test_analyze_growth_outlook_composite_calculation(self):
        data = {k: 80 for k in GROWTH_COMPONENTS}
        result = analyze_growth_outlook(data)
        assert abs(result['composite'] - 80.0) < 2

    def test_growth_grade_boundaries(self):
        assert GROWTH_GRADES['S']['min'] == 85
        assert GROWTH_GRADES['A']['min'] == 70
        assert GROWTH_GRADES['B']['min'] == 55
        assert GROWTH_GRADES['C']['min'] == 40
        assert GROWTH_GRADES['D']['min'] == 0

    def test_time_horizon_multiplier_keys(self):
        for horizon in TIME_HORIZON_MULTIPLIER:
            for comp in GROWTH_COMPONENTS:
                assert comp in TIME_HORIZON_MULTIPLIER[horizon]

    def test_score_clamping(self):
        scores = {'tam_sam': 150, 'competitive_moat': -10}
        result = calc_growth_score(scores, 'short_1_3y')
        for comp_data in result['components'].values():
            assert 0 <= comp_data['score'] <= 100


# ─── Growth Quick Scorer ───

class TestGrowthQuickScorer:

    @pytest.fixture(autouse=True)
    def setup(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'kr-stock-analysis', 'scripts'))
        from growth_quick_scorer import (
            score_quick_consensus, score_quick_rd, calc_growth_quick_score,
            GROWTH_QUICK_COMPONENTS,
        )
        self.score_quick_consensus = score_quick_consensus
        self.score_quick_rd = score_quick_rd
        self.calc_growth_quick_score = calc_growth_quick_score
        self.GROWTH_QUICK_COMPONENTS = GROWTH_QUICK_COMPONENTS

    def test_quick_components_sum(self):
        total = sum(c['weight'] for c in self.GROWTH_QUICK_COMPONENTS.values())
        assert abs(total - 1.0) < 0.001

    def test_score_quick_consensus_hyper(self):
        assert self.score_quick_consensus(60) == 95

    def test_score_quick_consensus_none(self):
        assert self.score_quick_consensus(None) == 50.0

    def test_score_quick_rd(self):
        assert self.score_quick_rd(15) == 90
        assert self.score_quick_rd(None) == 50.0

    def test_calc_growth_quick_score(self):
        result = self.calc_growth_quick_score(
            consensus_eps=30, rd_ratio=10,
            sector='semiconductor',
        )
        assert 'score' in result
        assert 'grade' in result
        assert result['score'] > 60

    def test_calc_growth_quick_score_defaults(self):
        result = self.calc_growth_quick_score()
        assert result['score'] == 50.0


# ─── Comprehensive Scorer Weight Update ───

class TestComprehensiveScorerPatch:

    @pytest.fixture(autouse=True)
    def setup(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'kr-stock-analysis', 'scripts'))
        from comprehensive_scorer import COMPREHENSIVE_SCORING, calc_comprehensive_score
        self.COMPREHENSIVE_SCORING = COMPREHENSIVE_SCORING
        self.calc_comprehensive_score = calc_comprehensive_score

    def test_new_weights_sum(self):
        total = sum(c['weight'] for c in self.COMPREHENSIVE_SCORING.values())
        assert abs(total - 1.0) < 0.001

    def test_growth_component_exists(self):
        assert 'growth' in self.COMPREHENSIVE_SCORING
        assert self.COMPREHENSIVE_SCORING['growth']['weight'] == 0.13

    def test_growth_quick_param(self):
        result = self.calc_comprehensive_score(
            fundamental={'score': 70},
            growth_quick={'score': 80},
        )
        assert 'growth' in result['components']
        assert result['components']['growth']['score'] == 80


# ─── Conviction Scorer Patch ───

class TestConvictionScorerPatch:

    @pytest.fixture(autouse=True)
    def setup(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'kr-strategy-synthesizer', 'scripts'))
        from conviction_scorer import CONVICTION_COMPONENTS, calc_component_scores
        self.CONVICTION_COMPONENTS = CONVICTION_COMPONENTS
        self.calc_component_scores = calc_component_scores

    def test_8_components(self):
        assert len(self.CONVICTION_COMPONENTS) == 8

    def test_new_weights_sum(self):
        total = sum(c['weight'] for c in self.CONVICTION_COMPONENTS.values())
        assert abs(total - 1.0) < 0.001

    def test_growth_outlook_component(self):
        assert 'growth_outlook' in self.CONVICTION_COMPONENTS
        assert self.CONVICTION_COMPONENTS['growth_outlook']['weight'] == 0.12

    def test_calc_includes_growth(self):
        reports = {'kr-growth-outlook': {'composite': 75}}
        components = self.calc_component_scores(reports)
        assert 'growth_outlook' in components
        assert components['growth_outlook']['score'] == 75.0


# ─── Sector Growth Scorer ───

class TestSectorGrowthScorer:

    @pytest.fixture(autouse=True)
    def setup(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'kr-sector-analyst', 'scripts'))
        from sector_growth_scorer import (
            get_sector_growth_outlook, generate_sector_growth_table,
            SECTOR_GROWTH_RATINGS,
        )
        self.get_sector_growth_outlook = get_sector_growth_outlook
        self.generate_sector_growth_table = generate_sector_growth_table
        self.SECTOR_GROWTH_RATINGS = SECTOR_GROWTH_RATINGS

    def test_14_sectors(self):
        assert len(self.SECTOR_GROWTH_RATINGS) == 14

    def test_get_sector_growth_outlook(self):
        result = self.get_sector_growth_outlook('semiconductor')
        assert result['grade'] == 'S'
        assert result['cagr'] == 0.12

    def test_get_sector_growth_outlook_unknown(self):
        assert self.get_sector_growth_outlook('unknown') is None

    def test_generate_sector_growth_table(self):
        table = self.generate_sector_growth_table()
        assert len(table) == 14
        assert table[0]['grade'] == 'S'

    def test_generate_sector_growth_table_subset(self):
        table = self.generate_sector_growth_table(['semiconductor', 'steel'])
        assert len(table) == 2
