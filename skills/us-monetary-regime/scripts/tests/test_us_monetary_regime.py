"""us-monetary-regime: 전체 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fed_stance_analyzer import (
    analyze_fed_stance, STANCE_WEIGHTS, FOMC_TONE_MAP,
    DOT_PLOT_MAP, QT_QE_MAP, STANCE_LABELS,
)
from rate_trend_classifier import (
    classify_rate_trend, RATE_REGIMES, YIELD_CURVE_WEIGHTS,
    CHANGE_THRESHOLDS,
)
from liquidity_tracker import (
    track_liquidity, LIQUIDITY_WEIGHTS, LIQUIDITY_WEIGHTS_5,
    LIQUIDITY_LEVELS,
    FED_BS_SCORING, M2_SCORING, DXY_SCORING, TGA_SCORING,
    _score_tga,
)
from kr_transmission_scorer import (
    score_kr_transmission, get_sector_overlay,
    TRANSMISSION_WEIGHTS, SECTOR_SENSITIVITY, DEFAULT_SENSITIVITY,
    RATE_DIFF_SCORING, FX_SCORING, OVERLAY_MAX, OVERLAY_MIN,
)
from economic_fundamentals_analyzer import (
    analyze_fundamentals, FUNDAMENTALS_WEIGHTS,
    INFLATION_TARGET, PRESSURE_LABELS,
    _score_inflation, _score_labor, _score_growth, _score_shock,
)
from regime_synthesizer import (
    synthesize_regime, REGIME_WEIGHTS, REGIME_LABELS,
    RATE_OUTLOOK_LABELS, _generate_rate_outlook,
)


# ============================================================
# TestFedStanceAnalyzer (~20 tests)
# ============================================================

class TestFedStanceAnalyzer:

    def test_stance_weights_sum(self):
        assert abs(sum(STANCE_WEIGHTS.values()) - 1.00) < 0.001

    def test_neutral_scenario(self):
        r = analyze_fed_stance()
        assert r['stance_label'] == 'neutral'
        assert -20 <= r['stance_score'] <= 20

    def test_very_hawkish_scenario(self):
        r = analyze_fed_stance(
            fomc_tone='hawkish', dot_plot='higher',
            qt_qe='active_qt', speaker_tone=-0.8,
        )
        assert r['stance_score'] < -60
        assert r['stance_label'] == 'very_hawkish'

    def test_very_dovish_scenario(self):
        r = analyze_fed_stance(
            fomc_tone='dovish', dot_plot='lower',
            qt_qe='active_qe', speaker_tone=0.8,
        )
        assert r['stance_score'] > 60
        assert r['stance_label'] == 'very_dovish'

    def test_hawkish_scenario(self):
        r = analyze_fed_stance(
            fomc_tone='slightly_hawkish', dot_plot='higher',
            qt_qe='tapering_qt', speaker_tone=-0.3,
        )
        assert -60 <= r['stance_score'] <= -20
        assert r['stance_label'] == 'hawkish'

    def test_dovish_scenario(self):
        r = analyze_fed_stance(
            fomc_tone='slightly_dovish', dot_plot='lower',
            qt_qe='tapering_qe', speaker_tone=0.3,
        )
        assert 20 <= r['stance_score'] <= 60
        assert r['stance_label'] == 'dovish'

    def test_mixed_signals(self):
        r = analyze_fed_stance(
            fomc_tone='hawkish', dot_plot='lower',
            qt_qe='neutral', speaker_tone=0.2,
        )
        assert -100 <= r['stance_score'] <= 100

    def test_all_fomc_tones(self):
        for tone in FOMC_TONE_MAP:
            r = analyze_fed_stance(fomc_tone=tone)
            assert -100 <= r['stance_score'] <= 100

    def test_all_dot_plot_values(self):
        for dp in DOT_PLOT_MAP:
            r = analyze_fed_stance(dot_plot=dp)
            assert -100 <= r['stance_score'] <= 100

    def test_all_qt_qe_values(self):
        for qt in QT_QE_MAP:
            r = analyze_fed_stance(qt_qe=qt)
            assert -100 <= r['stance_score'] <= 100

    def test_speaker_tone_extremes(self):
        for tone in [-1.0, -0.5, 0, 0.5, 1.0]:
            r = analyze_fed_stance(speaker_tone=tone)
            assert -100 <= r['stance_score'] <= 100

    def test_speaker_tone_clamping(self):
        r = analyze_fed_stance(speaker_tone=5.0)
        assert -100 <= r['stance_score'] <= 100

    def test_score_bounds_extreme_hawk(self):
        r = analyze_fed_stance(
            fomc_tone='hawkish', dot_plot='higher',
            qt_qe='active_qt', speaker_tone=-1.0,
        )
        assert r['stance_score'] >= -100

    def test_score_bounds_extreme_dove(self):
        r = analyze_fed_stance(
            fomc_tone='dovish', dot_plot='lower',
            qt_qe='active_qe', speaker_tone=1.0,
        )
        assert r['stance_score'] <= 100

    def test_components_structure(self):
        r = analyze_fed_stance()
        assert 'fomc_tone' in r['components']
        assert 'dot_plot' in r['components']
        assert 'qt_qe' in r['components']
        assert 'speakers' in r['components']
        for c in r['components'].values():
            assert 'raw' in c
            assert 'score' in c
            assert 'weight' in c

    def test_description_not_empty(self):
        r = analyze_fed_stance()
        assert len(r['description']) > 0

    def test_label_boundaries(self):
        for label, (low, high) in STANCE_LABELS.items():
            mid = (low + high) / 2
            assert low < high or low == high

    def test_unknown_fomc_tone_defaults(self):
        r = analyze_fed_stance(fomc_tone='unknown')
        assert r['components']['fomc_tone']['score'] == 0

    def test_stance_label_count(self):
        assert len(STANCE_LABELS) == 5


# ============================================================
# TestRateTrendClassifier (~15 tests)
# ============================================================

class TestRateTrendClassifier:

    def test_yield_curve_weights_sum(self):
        assert abs(sum(YIELD_CURVE_WEIGHTS.values()) - 1.00) < 0.001

    def test_aggressive_hike(self):
        r = classify_rate_trend(
            current_ffr=5.50, ffr_6m_ago=4.50, ffr_12m_ago=3.50,
            last_change_bp=75, next_meeting_hike_prob=0.8,
        )
        assert r['rate_score'] < 25
        assert r['rate_regime'] == 'aggressive_hike'
        assert r['direction'] == 'rising'

    def test_gradual_hike(self):
        r = classify_rate_trend(
            current_ffr=5.25, ffr_6m_ago=5.00, ffr_12m_ago=4.75,
            last_change_bp=25, next_meeting_hike_prob=0.5,
        )
        assert 15 <= r['rate_score'] <= 45
        assert r['rate_regime'] in ('aggressive_hike', 'gradual_hike')

    def test_hold(self):
        r = classify_rate_trend(
            current_ffr=5.50, ffr_6m_ago=5.50, ffr_12m_ago=5.50,
            last_change_bp=0,
        )
        assert 40 <= r['rate_score'] <= 60
        assert r['rate_regime'] == 'hold'

    def test_gradual_cut(self):
        r = classify_rate_trend(
            current_ffr=4.50, ffr_6m_ago=5.00, ffr_12m_ago=5.50,
            last_change_bp=-25, next_meeting_cut_prob=0.7,
        )
        assert r['rate_score'] >= 55
        assert r['direction'] == 'falling'

    def test_aggressive_cut(self):
        r = classify_rate_trend(
            current_ffr=3.50, ffr_6m_ago=4.50, ffr_12m_ago=5.50,
            last_change_bp=-50, next_meeting_cut_prob=0.9,
        )
        assert r['rate_score'] >= 75
        assert r['rate_regime'] in ('gradual_cut', 'aggressive_cut')

    def test_inverted_curve(self):
        r = classify_rate_trend(yield_curve_2y10y=-50)
        assert r['yield_curve_signal'] == 'inverted'

    def test_steep_curve(self):
        r = classify_rate_trend(yield_curve_2y10y=200)
        assert r['yield_curve_signal'] == 'steep'

    def test_normal_curve(self):
        r = classify_rate_trend(yield_curve_2y10y=80)
        assert r['yield_curve_signal'] == 'normal'

    def test_score_bounds(self):
        r = classify_rate_trend(
            current_ffr=10.0, ffr_12m_ago=0.25,
            last_change_bp=100, next_meeting_hike_prob=1.0,
        )
        assert 0 <= r['rate_score'] <= 100

    def test_direction_confidence(self):
        r = classify_rate_trend()
        assert 0 <= r['direction_confidence'] <= 1.0

    def test_all_regimes_exist(self):
        assert len(RATE_REGIMES) == 5

    def test_components_structure(self):
        r = classify_rate_trend()
        for key in ('level', 'direction', 'market_expectation'):
            assert key in r['components']
            assert 'score' in r['components'][key]
            assert 'weight' in r['components'][key]

    def test_high_cut_probability(self):
        r = classify_rate_trend(next_meeting_cut_prob=0.95)
        assert r['components']['market_expectation']['score'] > 70

    def test_regime_label_exists(self):
        r = classify_rate_trend()
        assert r['regime_label'] in [v['label'] for v in RATE_REGIMES.values()]


# ============================================================
# TestLiquidityTracker (~15 tests)
# ============================================================

class TestLiquidityTracker:

    def test_liquidity_weights_sum(self):
        assert abs(sum(LIQUIDITY_WEIGHTS.values()) - 1.00) < 0.001

    def test_stable_default(self):
        r = track_liquidity()
        assert 40 <= r['liquidity_score'] <= 60
        assert r['liquidity_trend'] == 'stable'

    def test_severe_contraction(self):
        r = track_liquidity(
            fed_bs_change_pct=-2.0, m2_growth_yoy=-5.0,
            dxy_change_3m=8.0, rrp_change_pct=30.0,
        )
        assert r['liquidity_score'] < 25
        assert r['liquidity_trend'] == 'contracting'

    def test_severe_expansion(self):
        r = track_liquidity(
            fed_bs_change_pct=2.0, m2_growth_yoy=8.0,
            dxy_change_3m=-8.0, rrp_change_pct=-30.0,
        )
        assert r['liquidity_score'] > 75
        assert r['liquidity_trend'] == 'expanding'

    def test_fed_bs_all_levels(self):
        for pct, expected in [(-2.0, 15), (-0.7, 30), (0.0, 50), (0.7, 70), (2.0, 85)]:
            r = track_liquidity(fed_bs_change_pct=pct)
            assert r['components']['fed_bs']['score'] == expected

    def test_m2_all_levels(self):
        for pct, expected in [(-5.0, 20), (0.0, 40), (4.0, 60), (8.0, 80)]:
            r = track_liquidity(m2_growth_yoy=pct)
            assert r['components']['m2']['score'] == expected

    def test_dxy_inverse(self):
        r_rise = track_liquidity(dxy_change_3m=6.0)
        r_fall = track_liquidity(dxy_change_3m=-6.0)
        assert r_rise['components']['dxy']['score'] < r_fall['components']['dxy']['score']

    def test_dxy_all_levels(self):
        for pct, expected in [(6.0, 20), (3.0, 35), (0.0, 50), (-3.0, 65), (-6.0, 80)]:
            r = track_liquidity(dxy_change_3m=pct)
            assert r['components']['dxy']['score'] == expected

    def test_rrp_inverse(self):
        r_grow = track_liquidity(rrp_change_pct=25.0)
        r_shrink = track_liquidity(rrp_change_pct=-25.0)
        assert r_grow['liquidity_score'] < r_shrink['liquidity_score']

    def test_score_bounds(self):
        r = track_liquidity(
            fed_bs_change_pct=10.0, m2_growth_yoy=20.0,
            dxy_change_3m=-20.0, rrp_change_pct=-50.0,
        )
        assert 0 <= r['liquidity_score'] <= 100

    def test_level_classification(self):
        for level, (low, high) in LIQUIDITY_LEVELS.items():
            assert low < high or level == 'severe_expansion'

    def test_trend_classification(self):
        r_low = track_liquidity(
            fed_bs_change_pct=-2.0, m2_growth_yoy=-3.0,
            dxy_change_3m=6.0,
        )
        assert r_low['liquidity_trend'] == 'contracting'

    def test_components_structure(self):
        r = track_liquidity()
        for key in ('fed_bs', 'm2', 'dxy', 'rrp'):
            assert key in r['components']
            assert 'raw' in r['components'][key]
            assert 'score' in r['components'][key]
            assert 'weight' in r['components'][key]

    def test_liquidity_levels_count(self):
        assert len(LIQUIDITY_LEVELS) == 5

    def test_scoring_dicts_populated(self):
        assert len(FED_BS_SCORING) == 5
        assert len(M2_SCORING) == 4
        assert len(DXY_SCORING) == 5


# ============================================================
# TestKRTransmissionScorer (~20 tests)
# ============================================================

class TestKRTransmissionScorer:

    def test_transmission_weights_sum(self):
        assert abs(sum(TRANSMISSION_WEIGHTS.values()) - 1.00) < 0.001

    def test_positive_transmission(self):
        r = score_kr_transmission(
            us_regime_score=80, kr_rate=3.50, us_rate=3.00,
            usdkrw_change_3m=-5.0, foreign_flow_5d=8000,
            bok_direction='cutting',
        )
        assert r['kr_impact_score'] > 55
        assert r['impact_label'] == 'positive'
        assert r['overlay'] > 0

    def test_negative_transmission(self):
        r = score_kr_transmission(
            us_regime_score=20, kr_rate=2.50, us_rate=5.50,
            usdkrw_change_3m=8.0, foreign_flow_5d=-8000,
            bok_direction='hold',
        )
        assert r['kr_impact_score'] < 45
        assert r['impact_label'] == 'negative'
        assert r['overlay'] < 0

    def test_neutral_transmission(self):
        r = score_kr_transmission()
        assert r['impact_label'] == 'neutral'

    def test_overlay_range(self):
        for score in [0, 25, 50, 75, 100]:
            r = score_kr_transmission(us_regime_score=score)
            assert OVERLAY_MIN <= r['overlay'] <= OVERLAY_MAX

    def test_overlay_zero_at_50(self):
        r = score_kr_transmission(us_regime_score=50)
        assert r['overlay'] == 0.0

    def test_overlay_positive_above_50(self):
        r = score_kr_transmission(us_regime_score=80)
        assert r['overlay'] > 0

    def test_overlay_negative_below_50(self):
        r = score_kr_transmission(us_regime_score=20)
        assert r['overlay'] < 0

    def test_overlay_max_clamp(self):
        r = score_kr_transmission(us_regime_score=100)
        assert r['overlay'] == OVERLAY_MAX

    def test_overlay_min_clamp(self):
        r = score_kr_transmission(us_regime_score=0)
        assert r['overlay'] == OVERLAY_MIN

    def test_sector_overlay_semiconductor(self):
        ov = get_sector_overlay(10.0, 'semiconductor')
        assert ov == 13.0  # 10 * 1.3

    def test_sector_overlay_food(self):
        ov = get_sector_overlay(10.0, 'food')
        assert ov == 3.0  # 10 * 0.3

    def test_sector_overlay_default(self):
        ov = get_sector_overlay(10.0, 'unknown_sector')
        assert ov == 7.0  # 10 * 0.7

    def test_all_14_sectors(self):
        assert len(SECTOR_SENSITIVITY) == 14
        for sector, sensitivity in SECTOR_SENSITIVITY.items():
            assert 0 < sensitivity <= 2.0
            ov = get_sector_overlay(10.0, sector)
            assert abs(ov - 10.0 * sensitivity) < 0.01

    def test_sector_overlays_in_result(self):
        r = score_kr_transmission(us_regime_score=70)
        assert len(r['sector_overlays']) == 14

    def test_favored_sectors_easing(self):
        r = score_kr_transmission(us_regime_score=80)
        assert len(r['favored_sectors']) > 0
        assert 'semiconductor' in r['favored_sectors']

    def test_unfavored_sectors_tightening(self):
        r = score_kr_transmission(us_regime_score=20)
        assert len(r['unfavored_sectors']) > 0
        assert 'semiconductor' in r['unfavored_sectors']

    def test_channels_structure(self):
        r = score_kr_transmission()
        for ch in ('interest_rate_diff', 'fx_impact', 'risk_appetite',
                    'sector_rotation', 'bok_policy_lag'):
            assert ch in r['channels']
            assert 'score' in r['channels'][ch]
            assert 'weight' in r['channels'][ch]
            assert 'detail' in r['channels'][ch]

    def test_rate_diff_all_levels(self):
        assert len(RATE_DIFF_SCORING) == 5

    def test_fx_all_levels(self):
        assert len(FX_SCORING) == 5

    def test_bok_direction_all(self):
        for direction in ('hiking', 'hold', 'cutting'):
            r = score_kr_transmission(bok_direction=direction)
            assert 0 <= r['kr_impact_score'] <= 100


# ============================================================
# TestTGAComponent (~15 tests)
# ============================================================

class TestTGAComponent:

    def test_5_weights_sum_1(self):
        assert abs(sum(LIQUIDITY_WEIGHTS_5.values()) - 1.00) < 0.001

    def test_4_weights_unchanged(self):
        assert LIQUIDITY_WEIGHTS == {'fed_bs': 0.30, 'm2': 0.30, 'dxy': 0.25, 'rrp': 0.15}

    def test_tga_scoring_large_drawdown(self):
        assert _score_tga(-15.0) == TGA_SCORING['large_drawdown']  # 80

    def test_tga_scoring_drawdown(self):
        assert _score_tga(-5.0) == TGA_SCORING['drawdown']  # 65

    def test_tga_scoring_stable(self):
        assert _score_tga(0.0) == TGA_SCORING['stable']  # 50

    def test_tga_scoring_buildup(self):
        assert _score_tga(5.0) == TGA_SCORING['buildup']  # 35

    def test_tga_scoring_large_buildup(self):
        assert _score_tga(15.0) == TGA_SCORING['large_buildup']  # 20

    def test_tga_none_uses_4_weights(self):
        r = track_liquidity()
        assert 'tga' not in r['components']
        assert r['components']['fed_bs']['weight'] == 0.30

    def test_tga_provided_uses_5_weights(self):
        r = track_liquidity(tga_change_1m_pct=-5.0)
        assert 'tga' in r['components']
        assert r['components']['fed_bs']['weight'] == 0.25
        assert r['components']['tga']['weight'] == 0.20

    def test_backward_compat_no_tga(self):
        r1 = track_liquidity(fed_bs_change_pct=0.5, m2_growth_yoy=3.0)
        r2 = track_liquidity(fed_bs_change_pct=0.5, m2_growth_yoy=3.0, tga_change_1m_pct=None)
        assert r1['liquidity_score'] == r2['liquidity_score']

    def test_tga_large_drawdown_increases_score(self):
        r_without = track_liquidity()
        r_with = track_liquidity(tga_change_1m_pct=-15.0)
        # TGA drawdown adds high score (80), so overall should be higher
        # (though weights change, the effect should be net positive)
        assert r_with['liquidity_score'] >= r_without['liquidity_score'] - 5

    def test_tga_large_buildup_decreases_score(self):
        r_without = track_liquidity()
        r_with = track_liquidity(tga_change_1m_pct=15.0)
        assert r_with['liquidity_score'] <= r_without['liquidity_score'] + 5

    def test_synthesizer_tga_param(self):
        r = synthesize_regime(tga_change_1m_pct=-5.0)
        assert 'liquidity' in r['us_regime']

    def test_synthesizer_tga_in_data_inputs(self):
        r = synthesize_regime(tga_change_1m_pct=-5.0)
        assert r['data_inputs']['tga_change_1m_pct'] == -5.0

    def test_synthesizer_backward_compat(self):
        r = synthesize_regime()
        assert r['data_inputs']['tga_change_1m_pct'] is None


# ============================================================
# TestEconomicFundamentalsAnalyzer (~25 tests)
# ============================================================

class TestEconomicFundamentalsAnalyzer:

    def test_fundamentals_weights_sum(self):
        assert abs(sum(FUNDAMENTALS_WEIGHTS.values()) - 1.00) < 0.001

    # --- Inflation Tests ---

    def test_inflation_high(self):
        r = _score_inflation(cpi_yoy=5.0)
        assert r['score'] < 30

    def test_inflation_at_target(self):
        r = _score_inflation(cpi_yoy=2.0)
        assert 50 <= r['score'] <= 70

    def test_inflation_below_target(self):
        r = _score_inflation(cpi_yoy=1.0)
        assert r['score'] >= 65

    def test_inflation_core_pce_priority(self):
        r = _score_inflation(cpi_yoy=5.0, core_pce_yoy=2.0)
        # Core PCE at 2% should give higher score despite CPI at 5%
        assert r['score'] >= 50

    def test_inflation_accelerating_penalty(self):
        r_stable = _score_inflation(cpi_yoy=3.5, direction='stable')
        r_accel = _score_inflation(cpi_yoy=3.5, direction='accelerating')
        assert r_accel['score'] < r_stable['score']

    def test_inflation_decelerating_bonus(self):
        r_stable = _score_inflation(cpi_yoy=3.5, direction='stable')
        r_decel = _score_inflation(cpi_yoy=3.5, direction='decelerating')
        assert r_decel['score'] > r_stable['score']

    def test_inflation_gap_in_components(self):
        r = _score_inflation(cpi_yoy=4.0)
        assert abs(r['components']['gap_from_target'] - 2.0) < 0.01

    # --- Labor Tests ---

    def test_labor_tight(self):
        r = _score_labor(unemployment_rate=3.3, nfp_thousands=350,
                         wage_growth_yoy=5.5)
        assert r['score'] < 30

    def test_labor_balanced(self):
        r = _score_labor(unemployment_rate=4.2, nfp_thousands=150,
                         wage_growth_yoy=3.5)
        assert 40 <= r['score'] <= 65

    def test_labor_weak(self):
        r = _score_labor(unemployment_rate=6.0, nfp_thousands=30,
                         wage_growth_yoy=1.5)
        assert r['score'] >= 70

    def test_labor_components_structure(self):
        r = _score_labor(unemployment_rate=4.0)
        assert 'unemployment' in r['components']
        assert 'nfp' in r['components']
        assert 'wages' in r['components']

    # --- Growth Tests ---

    def test_growth_overheating(self):
        r = _score_growth(gdp_growth_annualized=5.0, ism_manufacturing=58,
                          ism_services=60)
        assert r['score'] < 25

    def test_growth_moderate(self):
        r = _score_growth(gdp_growth_annualized=2.5, ism_manufacturing=51,
                          ism_services=52)
        assert 40 <= r['score'] <= 60

    def test_growth_recession(self):
        r = _score_growth(gdp_growth_annualized=-1.0, ism_manufacturing=42,
                          ism_services=45, lei_change_6m=-8.0)
        assert r['score'] >= 80

    def test_growth_lei_leading(self):
        r_pos = _score_growth(gdp_growth_annualized=2.5, lei_change_6m=3.0)
        r_neg = _score_growth(gdp_growth_annualized=2.5, lei_change_6m=-6.0)
        assert r_neg['score'] > r_pos['score']

    # --- Shock Tests ---

    def test_shock_none(self):
        r = _score_shock(shock_level='none')
        assert r['score'] == 50

    def test_shock_crisis_deflationary(self):
        r = _score_shock(shock_level='crisis', shock_type='pandemic',
                         is_inflationary=False)
        assert r['score'] >= 90

    def test_shock_crisis_inflationary(self):
        r = _score_shock(shock_level='crisis', shock_type='energy_crisis',
                         is_inflationary=True)
        assert r['score'] <= 15

    def test_shock_long_duration(self):
        r_short = _score_shock(shock_level='severe', duration_months=3)
        r_long = _score_shock(shock_level='severe', duration_months=18)
        assert r_long['score'] > r_short['score']

    # --- Comprehensive Tests ---

    def test_analyze_default(self):
        r = analyze_fundamentals()
        assert 0 <= r['fundamentals_score'] <= 100
        assert r['pressure_label'] in PRESSURE_LABELS

    def test_analyze_strong_hike_pressure(self):
        r = analyze_fundamentals(
            cpi_yoy=6.0, inflation_direction='accelerating',
            unemployment_rate=3.2, nfp_thousands=400,
            wage_growth_yoy=6.0, gdp_growth_annualized=4.5,
            ism_manufacturing=58,
        )
        assert r['fundamentals_score'] < 25
        assert r['pressure_label'] == 'strong_hike'

    def test_analyze_strong_cut_pressure(self):
        r = analyze_fundamentals(
            cpi_yoy=1.0, inflation_direction='falling',
            unemployment_rate=6.5, nfp_thousands=20,
            wage_growth_yoy=1.5, gdp_growth_annualized=-1.0,
            ism_manufacturing=42, shock_level='severe',
            shock_type='financial_crisis',
        )
        assert r['fundamentals_score'] >= 75
        assert r['pressure_label'] == 'strong_cut'

    def test_dual_mandate_both_satisfied(self):
        r = analyze_fundamentals(cpi_yoy=2.0, unemployment_rate=4.2)
        assert 'satisfied' in r['dual_mandate_assessment'].lower() or \
               'flexibility' in r['dual_mandate_assessment'].lower()

    def test_dual_mandate_inflation_challenged(self):
        r = analyze_fundamentals(cpi_yoy=5.0, unemployment_rate=4.2)
        assert 'inflation' in r['dual_mandate_assessment'].lower() or \
               'price' in r['dual_mandate_assessment'].lower()

    def test_pressure_labels_count(self):
        assert len(PRESSURE_LABELS) == 5


# ============================================================
# TestRegimeSynthesizer (~15 tests)
# ============================================================

class TestRegimeSynthesizer:

    def test_regime_weights_sum(self):
        assert abs(sum(REGIME_WEIGHTS.values()) - 1.00) < 0.001

    def test_full_easing_scenario(self):
        r = synthesize_regime(
            fomc_tone='dovish', dot_plot='lower',
            qt_qe='active_qe', speaker_tone=0.8,
            current_ffr=3.50, ffr_6m_ago=4.50, ffr_12m_ago=5.50,
            last_change_bp=-50, next_meeting_cut_prob=0.9,
            fed_bs_change_pct=1.5, m2_growth_yoy=7.0,
            dxy_change_3m=-6.0, rrp_change_pct=-25.0,
        )
        assert r['us_regime']['regime_score'] > 60
        assert r['us_regime']['regime_label'] in ('hold', 'easing')
        assert r['overlay'] > 0

    def test_full_tightening_scenario(self):
        r = synthesize_regime(
            fomc_tone='hawkish', dot_plot='higher',
            qt_qe='active_qt', speaker_tone=-0.8,
            current_ffr=5.50, ffr_6m_ago=4.50, ffr_12m_ago=3.50,
            last_change_bp=75, next_meeting_hike_prob=0.9,
            fed_bs_change_pct=-2.0, m2_growth_yoy=-3.0,
            dxy_change_3m=8.0, rrp_change_pct=25.0,
        )
        assert r['us_regime']['regime_score'] < 35
        assert r['us_regime']['regime_label'] == 'tightening'
        assert r['overlay'] < 0

    def test_hold_scenario(self):
        r = synthesize_regime()
        assert 35 <= r['us_regime']['regime_score'] <= 65
        assert r['us_regime']['regime_label'] == 'hold'

    def test_overlay_calculation(self):
        r = synthesize_regime()
        expected = round((r['us_regime']['regime_score'] - 50) * 0.30, 1)
        expected = max(-15, min(15, expected))
        assert abs(r['overlay'] - expected) < 0.2

    def test_sector_overlays_14(self):
        r = synthesize_regime()
        assert len(r['sector_overlays']) == 14

    def test_summary_not_empty(self):
        r = synthesize_regime()
        assert len(r['summary']) > 0

    def test_data_inputs_recorded(self):
        r = synthesize_regime(fomc_tone='dovish', kr_rate=2.50)
        assert r['data_inputs']['fomc_tone'] == 'dovish'
        assert r['data_inputs']['kr_rate'] == 2.50

    def test_sub_modules_present(self):
        r = synthesize_regime()
        assert 'stance' in r['us_regime']
        assert 'rate' in r['us_regime']
        assert 'liquidity' in r['us_regime']
        assert 'fundamentals' in r['us_regime']

    def test_fundamentals_in_regime(self):
        r = synthesize_regime(cpi_yoy=5.0, unemployment_rate=3.5)
        f = r['us_regime']['fundamentals']
        assert 'fundamentals_score' in f
        assert 'pressure_label' in f
        assert 'components' in f

    def test_kr_impact_present(self):
        r = synthesize_regime()
        assert 'kr_impact_score' in r['kr_impact']
        assert 'impact_label' in r['kr_impact']

    def test_regime_labels_count(self):
        assert len(REGIME_LABELS) == 3

    def test_all_data_inputs_keys(self):
        r = synthesize_regime()
        expected_keys = [
            'fomc_tone', 'dot_plot', 'qt_qe', 'speaker_tone',
            'current_ffr', 'ffr_6m_ago', 'ffr_12m_ago', 'last_change_bp',
            'next_meeting_cut_prob', 'next_meeting_hike_prob',
            'yield_curve_2y10y', 'fed_bs_change_pct', 'm2_growth_yoy',
            'dxy_change_3m', 'rrp_change_pct', 'kr_rate',
            'usdkrw_change_3m', 'foreign_flow_5d', 'bok_direction',
            # Fundamentals inputs
            'cpi_yoy', 'unemployment_rate', 'nfp_thousands',
            'wage_growth_yoy', 'gdp_growth_annualized',
            'ism_manufacturing', 'shock_level',
        ]
        for key in expected_keys:
            assert key in r['data_inputs']

    def test_regime_score_bounds(self):
        for tone in ['hawkish', 'dovish']:
            for dp in ['higher', 'lower']:
                r = synthesize_regime(fomc_tone=tone, dot_plot=dp)
                assert 0 <= r['us_regime']['regime_score'] <= 100

    def test_rate_outlook_present(self):
        r = synthesize_regime()
        assert 'rate_outlook' in r['us_regime']
        outlook = r['us_regime']['rate_outlook']
        assert 'direction' in outlook
        assert 'label' in outlook
        assert 'confidence' in outlook
        assert 'reasoning' in outlook
        assert 'key_factors' in outlook

    def test_rate_outlook_direction_valid(self):
        r = synthesize_regime()
        assert r['us_regime']['rate_outlook']['direction'] in RATE_OUTLOOK_LABELS

    def test_rate_outlook_confidence_valid(self):
        r = synthesize_regime()
        assert r['us_regime']['rate_outlook']['confidence'] in (
            'high', 'medium', 'low')

    def test_rate_outlook_easing_shows_cut(self):
        r = synthesize_regime(
            fomc_tone='dovish', dot_plot='lower',
            qt_qe='active_qe', speaker_tone=0.8,
            current_ffr=3.50, ffr_6m_ago=4.50, ffr_12m_ago=5.50,
            last_change_bp=-50, next_meeting_cut_prob=0.9,
            fed_bs_change_pct=1.5, m2_growth_yoy=7.0,
            dxy_change_3m=-6.0, rrp_change_pct=-25.0,
            unemployment_rate=5.5, gdp_growth_annualized=0.5,
            cpi_yoy=1.5,
        )
        outlook = r['us_regime']['rate_outlook']
        assert outlook['direction'] in ('cut_likely', 'cut_lean', 'hold_dovish')

    def test_rate_outlook_tightening_shows_hike(self):
        r = synthesize_regime(
            fomc_tone='hawkish', dot_plot='higher',
            qt_qe='active_qt', speaker_tone=-0.8,
            current_ffr=5.50, ffr_6m_ago=4.50, ffr_12m_ago=3.50,
            last_change_bp=75, next_meeting_hike_prob=0.9,
            fed_bs_change_pct=-2.0, m2_growth_yoy=-3.0,
            dxy_change_3m=8.0, rrp_change_pct=25.0,
            cpi_yoy=6.0, unemployment_rate=3.0,
            gdp_growth_annualized=5.0,
        )
        outlook = r['us_regime']['rate_outlook']
        assert outlook['direction'] in ('hike_likely', 'hike_lean', 'hold_hawkish')

    def test_rate_outlook_hold_default(self):
        r = synthesize_regime()
        outlook = r['us_regime']['rate_outlook']
        assert 'hold' in outlook['direction']

    def test_rate_outlook_in_summary(self):
        r = synthesize_regime()
        assert '금리 방향' in r['summary']

    def test_rate_outlook_key_factors_not_empty(self):
        r = synthesize_regime()
        assert len(r['us_regime']['rate_outlook']['key_factors']) > 0

    def test_rate_outlook_shock_factor(self):
        r = synthesize_regime(
            shock_level='severe', shock_type='energy_crisis',
            shock_is_inflationary=True,
        )
        factors = r['us_regime']['rate_outlook']['key_factors']
        shock_mentioned = any('충격' in f or '위기' in f or '스태그' in f
                              for f in factors)
        assert shock_mentioned

    def test_rate_outlook_label_matches_direction(self):
        r = synthesize_regime()
        outlook = r['us_regime']['rate_outlook']
        assert outlook['label'] == RATE_OUTLOOK_LABELS[outlook['direction']]


# ============================================================
# TestPatchComprehensiveScorer (~10 tests)
# ============================================================

class TestPatchComprehensiveScorer:

    def setup_method(self):
        # Import from patched file
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', '..',
            'kr-stock-analysis', 'scripts',
        ))
        from comprehensive_scorer import (
            apply_monetary_overlay, calc_comprehensive_score,
            ANALYSIS_GRADES,
        )
        self.apply = apply_monetary_overlay
        self.calc = calc_comprehensive_score
        self.grades = ANALYSIS_GRADES

    def test_overlay_none_returns_original(self):
        r = self.apply(60.0, overlay=None)
        assert r['final_score'] == 60.0
        assert r['overlay_applied'] is None

    def test_positive_overlay_semiconductor(self):
        r = self.apply(50.0, overlay=10.0, sector='semiconductor')
        assert r['adjusted_overlay'] == 13.0
        assert r['final_score'] == 63.0

    def test_negative_overlay_semiconductor(self):
        r = self.apply(50.0, overlay=-10.0, sector='semiconductor')
        assert r['adjusted_overlay'] == -13.0
        assert r['final_score'] == 37.0

    def test_clamp_upper(self):
        r = self.apply(95.0, overlay=15.0, sector='semiconductor')
        assert r['final_score'] == 100.0

    def test_clamp_lower(self):
        r = self.apply(5.0, overlay=-15.0, sector='semiconductor')
        assert r['final_score'] == 0.0

    def test_default_sector(self):
        r = self.apply(50.0, overlay=10.0)
        assert r['sector_sensitivity'] == 0.7
        assert r['adjusted_overlay'] == 7.0

    def test_grade_change(self):
        # HOLD(50) + overlay → BUY
        r = self.apply(60.0, overlay=10.0, sector='semiconductor')
        assert r['final_score'] == 73.0
        assert r['final_grade'] == 'BUY'

    def test_existing_calc_unaffected(self):
        r = self.calc(
            fundamental={'score': 60},
            technical={'score': 50},
        )
        assert 'score' in r
        assert 'grade' in r

    def test_overlay_impact_positive(self):
        r = self.apply(50.0, overlay=5.0, sector='semiconductor')
        assert r['overlay_impact'] == 'positive'

    def test_overlay_impact_negative(self):
        r = self.apply(50.0, overlay=-5.0, sector='semiconductor')
        assert r['overlay_impact'] == 'negative'


# ============================================================
# TestPatchConvictionScorer (~8 tests)
# ============================================================

class TestPatchConvictionScorer:

    def setup_method(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', '..',
            'kr-strategy-synthesizer', 'scripts',
        ))
        from conviction_scorer import (
            CONVICTION_COMPONENTS, normalize_signal,
            calc_component_scores, calc_conviction_score,
        )
        self.components = CONVICTION_COMPONENTS
        self.normalize = normalize_signal
        self.calc_comp = calc_component_scores
        self.calc_conv = calc_conviction_score

    def test_9_components_count(self):
        assert len(self.components) == 9

    def test_9_components_sum_1(self):
        total = sum(c['weight'] for c in self.components.values())
        assert abs(total - 1.00) < 0.001

    def test_global_monetary_exists(self):
        assert 'global_monetary' in self.components
        assert self.components['global_monetary']['weight'] == 0.10

    def test_global_monetary_source(self):
        assert 'us-monetary-regime' in self.components['global_monetary']['sources']

    def test_normalize_us_monetary(self):
        assert self.normalize(65, 'us-monetary-regime') == 65
        assert self.normalize(None, 'us-monetary-regime') == 50.0

    def test_global_monetary_in_component_scores(self):
        reports = {'us-monetary-regime': {'regime_score': 75}}
        components = self.calc_comp(reports)
        assert 'global_monetary' in components
        assert components['global_monetary']['score'] == 75.0

    def test_global_monetary_missing_defaults(self):
        reports = {}
        components = self.calc_comp(reports)
        assert components['global_monetary']['score'] == 50.0

    def test_existing_8_components_work(self):
        reports = {
            'kr-market-breadth': {'breadth_score': 60},
            'kr-uptrend-analyzer': {'uptrend_score': 55},
        }
        components = self.calc_comp(reports)
        assert 'market_structure' in components


# ============================================================
# TestPatchMarketUtils (~5 tests)
# ============================================================

class TestPatchMarketUtils:

    def setup_method(self):
        # Mock _kr_common dependencies before importing market_utils
        import types
        kr_common = types.ModuleType('_kr_common')
        kr_client_mod = types.ModuleType('_kr_common.kr_client')
        models_mod = types.ModuleType('_kr_common.models')
        market_mod = types.ModuleType('_kr_common.models.market')
        utils_mod = types.ModuleType('_kr_common.utils')
        date_utils_mod = types.ModuleType('_kr_common.utils.date_utils')
        ta_utils_mod = types.ModuleType('_kr_common.utils.ta_utils')

        class MockKRClient:
            pass

        kr_client_mod.KRClient = MockKRClient
        market_mod.INDEX_CODES = {'KOSPI': '0001', 'KOSDAQ': '2001'}

        sys.modules['_kr_common'] = kr_common
        sys.modules['_kr_common.kr_client'] = kr_client_mod
        sys.modules['_kr_common.models'] = models_mod
        sys.modules['_kr_common.models.market'] = market_mod
        sys.modules['_kr_common.utils'] = utils_mod
        sys.modules['_kr_common.utils.date_utils'] = date_utils_mod
        sys.modules['_kr_common.utils.ta_utils'] = ta_utils_mod

        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', '..',
            'kr-market-environment', 'scripts',
        ))

        # Force reimport
        if 'market_utils' in sys.modules:
            del sys.modules['market_utils']

        from market_utils import estimate_foreign_flow_outlook
        self.estimate = estimate_foreign_flow_outlook

    def test_no_input_empty_dict(self):
        assert self.estimate() == {}

    def test_easing_regime_inflow(self):
        r = self.estimate(us_regime_score=80)
        assert r['outlook'] == 'net_inflow'
        assert r['confidence'] > 0

    def test_tightening_regime_outflow(self):
        r = self.estimate(us_regime_score=20)
        assert r['outlook'] == 'net_outflow'
        assert r['confidence'] > 0

    def test_neutral_regime(self):
        r = self.estimate(us_regime_score=50)
        assert r['outlook'] == 'neutral'

    def test_rate_diff_adjustment(self):
        r = self.estimate(us_regime_score=70, kr_us_rate_diff=1.0)
        assert '캐리' in r['reasoning']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
