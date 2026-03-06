"""kr-supply-demand-analyzer 종합 테스트."""

import pytest

from ..market_flow_analyzer import (
    MARKET_FLOW_CONFIG,
    MARKET_FLOW_SIGNALS,
    SENTIMENT_WEIGHTS,
    _classify_amount,
    _amount_to_score,
    calc_consecutive_days,
    calc_investor_sentiment,
    analyze_market_flow,
)
from ..sector_flow_mapper import (
    KR_SECTORS,
    SECTOR_FLOW_CONFIG,
    calc_sector_hhi,
    calc_sector_divergence,
    map_sector_flows,
)
from ..liquidity_tracker import (
    LIQUIDITY_CONFIG,
    LIQUIDITY_GRADES,
    calc_volume_ratio,
    calc_turnover_rate,
    analyze_liquidity,
)
from ..report_generator import (
    SUPPLY_DEMAND_COMPOSITE_WEIGHTS,
    SUPPLY_DEMAND_GRADES,
    calc_composite_score,
    generate_supply_demand_report,
)


# ═══════════════════════════════════════════════
# 상수 검증
# ═══════════════════════════════════════════════

class TestConstants:
    """설계 상수 검증."""

    def test_market_flow_config_markets(self):
        assert MARKET_FLOW_CONFIG['markets'] == ['KOSPI', 'KOSDAQ']

    def test_market_flow_config_investor_groups(self):
        assert MARKET_FLOW_CONFIG['investor_groups'] == ['foreign', 'institution', 'individual']

    def test_consecutive_thresholds(self):
        t = MARKET_FLOW_CONFIG['consecutive_thresholds']
        assert t['strong'] == 10
        assert t['moderate'] == 5
        assert t['mild'] == 3

    def test_amount_thresholds_foreign(self):
        f = MARKET_FLOW_CONFIG['amount_thresholds']['foreign']
        assert f['strong'] == 500_000_000_000
        assert f['moderate'] == 100_000_000_000
        assert f['mild'] == 50_000_000_000

    def test_amount_thresholds_institution(self):
        i = MARKET_FLOW_CONFIG['amount_thresholds']['institution']
        assert i['strong'] == 300_000_000_000
        assert i['moderate'] == 100_000_000_000
        assert i['mild'] == 30_000_000_000

    def test_market_flow_signals_count(self):
        assert len(MARKET_FLOW_SIGNALS) == 7

    def test_market_flow_signals_order(self):
        scores = [v['min_score'] for v in MARKET_FLOW_SIGNALS.values()]
        assert scores == sorted(scores, reverse=True)

    def test_sentiment_weights_sum(self):
        total = sum(SENTIMENT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_kr_sectors_count(self):
        assert len(KR_SECTORS) == 15

    def test_kr_sectors_contents(self):
        assert '반도체' in KR_SECTORS
        assert '2차전지' in KR_SECTORS
        assert '방산' in KR_SECTORS

    def test_sector_flow_config(self):
        assert SECTOR_FLOW_CONFIG['rotation_lookback'] == 5
        assert SECTOR_FLOW_CONFIG['hhi_warning'] == 0.25
        assert SECTOR_FLOW_CONFIG['hhi_critical'] == 0.40
        assert SECTOR_FLOW_CONFIG['divergence_threshold'] == 0.30

    def test_liquidity_config(self):
        assert LIQUIDITY_CONFIG['volume_ma_periods'] == [5, 20, 60]
        assert LIQUIDITY_CONFIG['turnover_warning'] == 0.5
        assert LIQUIDITY_CONFIG['turnover_high'] == 2.0
        assert LIQUIDITY_CONFIG['concentration_warning'] == 0.30
        assert LIQUIDITY_CONFIG['concentration_critical'] == 0.50

    def test_liquidity_grades_count(self):
        assert len(LIQUIDITY_GRADES) == 4

    def test_liquidity_grades_order(self):
        scores = [v['min_score'] for v in LIQUIDITY_GRADES.values()]
        assert scores == sorted(scores, reverse=True)

    def test_composite_weights_sum(self):
        total = sum(v['weight'] for v in SUPPLY_DEMAND_COMPOSITE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_composite_weights_values(self):
        w = SUPPLY_DEMAND_COMPOSITE_WEIGHTS
        assert w['market_flow']['weight'] == 0.30
        assert w['sector_rotation']['weight'] == 0.25
        assert w['liquidity']['weight'] == 0.25
        assert w['investor_sentiment']['weight'] == 0.20

    def test_supply_demand_grades_count(self):
        assert len(SUPPLY_DEMAND_GRADES) == 5

    def test_supply_demand_grades_order(self):
        scores = [v['min_score'] for v in SUPPLY_DEMAND_GRADES.values()]
        assert scores == sorted(scores, reverse=True)


# ═══════════════════════════════════════════════
# market_flow_analyzer 테스트
# ═══════════════════════════════════════════════

class TestClassifyAmount:
    """_classify_amount 테스트."""

    def test_foreign_strong_buy(self):
        assert _classify_amount(600_000_000_000, 'foreign') == 'strong_buy'

    def test_foreign_buy(self):
        assert _classify_amount(200_000_000_000, 'foreign') == 'buy'

    def test_foreign_mild_buy(self):
        assert _classify_amount(60_000_000_000, 'foreign') == 'mild_buy'

    def test_foreign_neutral(self):
        assert _classify_amount(10_000_000_000, 'foreign') == 'neutral'

    def test_foreign_mild_sell(self):
        assert _classify_amount(-60_000_000_000, 'foreign') == 'mild_sell'

    def test_foreign_sell(self):
        assert _classify_amount(-200_000_000_000, 'foreign') == 'sell'

    def test_foreign_strong_sell(self):
        assert _classify_amount(-600_000_000_000, 'foreign') == 'strong_sell'

    def test_institution_strong_buy(self):
        assert _classify_amount(400_000_000_000, 'institution') == 'strong_buy'

    def test_institution_moderate(self):
        assert _classify_amount(50_000_000_000, 'institution') == 'mild_buy'

    def test_unknown_investor(self):
        assert _classify_amount(999_000_000_000, 'individual') == 'neutral'

    def test_zero_amount(self):
        assert _classify_amount(0, 'foreign') == 'neutral'

    def test_none_amount(self):
        assert _classify_amount(None, 'foreign') == 'neutral'


class TestAmountToScore:
    """_amount_to_score 테스트."""

    def test_strong_buy_score(self):
        assert _amount_to_score(600_000_000_000, 'foreign') == 95

    def test_neutral_score(self):
        assert _amount_to_score(0, 'foreign') == 50

    def test_strong_sell_score(self):
        assert _amount_to_score(-600_000_000_000, 'foreign') == 5


class TestConsecutiveDays:
    """calc_consecutive_days 테스트."""

    def test_consecutive_buy(self):
        data = {
            '2026-03-04': {'foreign': 100e9},
            '2026-03-03': {'foreign': 50e9},
            '2026-03-02': {'foreign': 30e9},
        }
        result = calc_consecutive_days(data, 'foreign')
        assert result['buy_days'] == 3
        assert result['direction'] == 'buy'
        assert result['strength'] == 'mild'

    def test_consecutive_sell(self):
        data = {f'2026-03-{i:02d}': {'foreign': -100e9} for i in range(1, 12)}
        result = calc_consecutive_days(data, 'foreign')
        assert result['sell_days'] == 11
        assert result['direction'] == 'sell'
        assert result['strength'] == 'strong'

    def test_no_data(self):
        result = calc_consecutive_days({}, 'foreign')
        assert result['direction'] == 'neutral'
        assert result['strength'] == 'none'

    def test_mixed_direction(self):
        data = {
            '2026-03-04': {'foreign': 100e9},
            '2026-03-03': {'foreign': -50e9},
        }
        result = calc_consecutive_days(data, 'foreign')
        assert result['buy_days'] == 1
        assert result['direction'] == 'buy'

    def test_moderate_consecutive(self):
        data = {f'2026-03-{i:02d}': {'institution': 50e9} for i in range(1, 8)}
        result = calc_consecutive_days(data, 'institution')
        assert result['buy_days'] == 7
        assert result['strength'] == 'moderate'


class TestInvestorSentiment:
    """calc_investor_sentiment 테스트."""

    def test_all_bullish(self):
        # 외국인 90, 기관 80, 개인 20 (역지표 → 80) = 높은 심리
        result = calc_investor_sentiment(90, 80, 20)
        expected = 90 * 0.45 + 80 * 0.35 + 80 * 0.20
        assert result == round(expected, 1)

    def test_all_bearish(self):
        result = calc_investor_sentiment(10, 20, 90)
        # 개인 90 → 역전 10
        expected = 10 * 0.45 + 20 * 0.35 + 10 * 0.20
        assert result == round(expected, 1)

    def test_neutral(self):
        result = calc_investor_sentiment(50, 50, 50)
        assert result == 50.0

    def test_clamped_high(self):
        result = calc_investor_sentiment(100, 100, 0)
        assert result <= 100

    def test_clamped_low(self):
        result = calc_investor_sentiment(0, 0, 100)
        assert result >= 0


class TestAnalyzeMarketFlow:
    """analyze_market_flow 종합 테스트."""

    def test_empty_data(self):
        result = analyze_market_flow({})
        assert result['signal'] == 'NEUTRAL'
        assert result['sentiment_score'] == 50.0

    def test_bullish_market(self):
        data = {
            f'2026-03-{i:02d}': {
                'foreign': 200_000_000_000,
                'institution': 150_000_000_000,
                'individual': -300_000_000_000,
            }
            for i in range(1, 6)
        }
        result = analyze_market_flow(data, market='KOSPI')
        assert result['market'] == 'KOSPI'
        assert result['foreign_score'] > 60
        assert result['signal'] in ('STRONG_BUY', 'BUY', 'MILD_BUY')

    def test_bearish_market(self):
        data = {
            f'2026-03-{i:02d}': {
                'foreign': -300_000_000_000,
                'institution': -200_000_000_000,
                'individual': 500_000_000_000,
            }
            for i in range(1, 6)
        }
        result = analyze_market_flow(data)
        assert result['foreign_score'] < 40
        assert result['signal'] in ('STRONG_SELL', 'SELL', 'MILD_SELL')

    def test_kosdaq_market(self):
        data = {
            '2026-03-04': {
                'foreign': 50_000_000_000,
                'institution': 30_000_000_000,
                'individual': -80_000_000_000,
            }
        }
        result = analyze_market_flow(data, market='KOSDAQ')
        assert result['market'] == 'KOSDAQ'

    def test_consecutive_days_in_result(self):
        data = {
            f'2026-03-{i:02d}': {'foreign': 100e9, 'institution': 50e9}
            for i in range(1, 4)
        }
        result = analyze_market_flow(data)
        assert 'consecutive_days' in result
        assert result['consecutive_days']['foreign']['buy_days'] == 3


# ═══════════════════════════════════════════════
# sector_flow_mapper 테스트
# ═══════════════════════════════════════════════

class TestSectorHHI:
    """calc_sector_hhi 테스트."""

    def test_empty_data(self):
        assert calc_sector_hhi({}) == 0.0

    def test_single_sector_concentration(self):
        data = {'반도체': {'net': 1000}, '자동차': {'net': 0}}
        hhi = calc_sector_hhi(data)
        assert hhi == 1.0  # 완전 집중

    def test_equal_distribution(self):
        data = {sector: {'net': 100} for sector in KR_SECTORS}
        hhi = calc_sector_hhi(data)
        n = len(KR_SECTORS)
        expected = n * (1/n) ** 2  # 1/n
        assert abs(hhi - round(expected, 4)) < 0.001

    def test_two_sector_split(self):
        data = {'반도체': {'net': 500}, '자동차': {'net': 500}}
        hhi = calc_sector_hhi(data)
        assert abs(hhi - 0.5) < 0.001

    def test_dict_with_foreign_key(self):
        data = {'반도체': {'foreign': 1000}, '자동차': {'foreign': 1000}}
        hhi = calc_sector_hhi(data)
        assert abs(hhi - 0.5) < 0.001

    def test_scalar_values(self):
        data = {'반도체': 500, '자동차': 500}
        hhi = calc_sector_hhi(data)
        assert abs(hhi - 0.5) < 0.001


class TestSectorDivergence:
    """calc_sector_divergence 테스트."""

    def test_no_divergence(self):
        data = {'반도체': {'foreign': 100, 'institution': 100}}
        result = calc_sector_divergence(data)
        assert result['반도체'] == 0.0

    def test_full_divergence(self):
        data = {'반도체': {'foreign': 100, 'institution': -100}}
        result = calc_sector_divergence(data)
        assert result['반도체'] == 1.0  # foreign buy, institution sell

    def test_zero_flow(self):
        data = {'반도체': {'foreign': 0, 'institution': 0}}
        result = calc_sector_divergence(data)
        assert result['반도체'] == 0.0

    def test_multiple_sectors(self):
        data = {
            '반도체': {'foreign': 100, 'institution': -100},
            '자동차': {'foreign': 50, 'institution': 50},
        }
        result = calc_sector_divergence(data)
        assert abs(result['반도체']) > 0
        assert result['자동차'] == 0.0


class TestMapSectorFlows:
    """map_sector_flows 종합 테스트."""

    def test_empty_data(self):
        result = map_sector_flows({})
        assert result['hhi'] == 0.0
        assert result['sector_score'] > 0

    def test_basic_flows(self):
        data = {
            '반도체': {'foreign': 500, 'institution': 300, 'individual': -700},
            '자동차': {'foreign': -200, 'institution': 100, 'individual': 100},
        }
        result = map_sector_flows(data)
        assert '반도체' in result['flows']
        assert result['flows']['반도체']['net'] == 100
        assert result['heatmap']['반도체'] == 'inflow'

    def test_heatmap_outflow(self):
        data = {
            '반도체': {'foreign': -500, 'institution': -300, 'individual': 100},
        }
        result = map_sector_flows(data)
        assert result['heatmap']['반도체'] == 'outflow'

    def test_with_previous_data(self):
        current = {
            '반도체': {'foreign': 500, 'institution': 300},
            '자동차': {'foreign': -200, 'institution': -100},
        }
        previous = {
            '반도체': {'foreign': -300, 'institution': -200},
            '자동차': {'foreign': 200, 'institution': 100},
        }
        result = map_sector_flows(current, previous)
        assert 'rotation_score' in result

    def test_concentrated_flow(self):
        data = {
            '반도체': {'foreign': 10000, 'institution': 5000, 'individual': -1000},
        }
        result = map_sector_flows(data)
        assert result['hhi'] == 1.0  # 단일 섹터

    def test_sector_score_range(self):
        data = {sector: {'foreign': 100, 'institution': 100, 'individual': -100}
                for sector in KR_SECTORS}
        result = map_sector_flows(data)
        assert 0 <= result['sector_score'] <= 100


# ═══════════════════════════════════════════════
# liquidity_tracker 테스트
# ═══════════════════════════════════════════════

class TestVolumeRatio:
    """calc_volume_ratio 테스트."""

    def test_empty_data(self):
        result = calc_volume_ratio([])
        assert result['5d_ratio'] == 1.0

    def test_equal_volume(self):
        data = [100] * 60
        result = calc_volume_ratio(data)
        assert result['5d_ratio'] == 1.0
        assert result['20d_ratio'] == 1.0
        assert result['60d_ratio'] == 1.0

    def test_high_volume(self):
        data = [200] + [100] * 59
        result = calc_volume_ratio(data)
        assert result['60d_ratio'] > 1.0

    def test_low_volume(self):
        data = [50] + [100] * 59
        result = calc_volume_ratio(data)
        assert result['60d_ratio'] < 1.0

    def test_short_data(self):
        data = [100, 80, 120]
        result = calc_volume_ratio(data)
        assert '5d_ratio' in result  # 3일 데이터로도 계산 가능


class TestTurnoverRate:
    """calc_turnover_rate 테스트."""

    def test_normal_turnover(self):
        volume = 10_000_000_000  # 100억
        market_cap = 1_000_000_000_000  # 1조
        rate = calc_turnover_rate(volume, market_cap)
        assert rate == 1.0  # 1%

    def test_zero_market_cap(self):
        assert calc_turnover_rate(100, 0) == 0.0

    def test_none_market_cap(self):
        assert calc_turnover_rate(100, None) == 0.0

    def test_high_turnover(self):
        rate = calc_turnover_rate(30_000_000_000, 1_000_000_000_000)
        assert rate == 3.0  # 3%

    def test_low_turnover(self):
        rate = calc_turnover_rate(3_000_000_000, 1_000_000_000_000)
        assert rate == 0.3  # 0.3%


class TestAnalyzeLiquidity:
    """analyze_liquidity 종합 테스트."""

    def test_empty_data(self):
        result = analyze_liquidity([])
        assert result['grade'] in LIQUIDITY_GRADES

    def test_abundant_liquidity(self):
        # 높은 거래대금 + 정상 회전율
        data = [200] + [100] * 59
        result = analyze_liquidity(data, market_cap_data=10000)
        assert result['score'] > 50

    def test_with_market_cap(self):
        data = [10_000_000_000]  # 100억
        result = analyze_liquidity(data, market_cap_data=1_000_000_000_000)
        assert result['turnover'] == 1.0

    def test_with_concentration(self):
        data = [100]
        result = analyze_liquidity(
            data, top10_volume=60, total_volume=100,
        )
        assert result['concentration'] == 0.6
        # 60% 집중 → 위험 → 낮은 점수
        assert result['concentration_score'] < 20

    def test_score_range(self):
        data = [100] * 60
        result = analyze_liquidity(
            data, market_cap_data=10000,
            top10_volume=20, total_volume=100,
        )
        assert 0 <= result['score'] <= 100

    def test_grade_assignment(self):
        data = [100] * 60
        result = analyze_liquidity(data)
        assert result['grade'] in ('ABUNDANT', 'NORMAL', 'TIGHT', 'DRIED')


# ═══════════════════════════════════════════════
# report_generator 테스트
# ═══════════════════════════════════════════════

class TestCompositeScore:
    """calc_composite_score 테스트."""

    def test_all_high(self):
        result = calc_composite_score(90, 85, 80, 75)
        assert result['grade'] == 'STRONG_INFLOW'
        assert result['score'] > 80

    def test_all_low(self):
        result = calc_composite_score(10, 15, 20, 10)
        assert result['grade'] == 'STRONG_OUTFLOW'
        assert result['score'] < 20

    def test_balanced(self):
        result = calc_composite_score(50, 50, 50, 50)
        assert result['grade'] == 'BALANCED'
        assert result['score'] == 50.0

    def test_weight_verification(self):
        result = calc_composite_score(100, 100, 100, 100)
        assert result['score'] == 100.0

    def test_zero_scores(self):
        result = calc_composite_score(0, 0, 0, 0)
        assert result['score'] == 0.0
        assert result['grade'] == 'STRONG_OUTFLOW'

    def test_components_present(self):
        result = calc_composite_score(70, 60, 55, 65)
        assert 'components' in result
        assert len(result['components']) == 4
        for key in SUPPLY_DEMAND_COMPOSITE_WEIGHTS:
            assert key in result['components']

    def test_weighted_sum(self):
        result = calc_composite_score(80, 60, 70, 50)
        expected = 80*0.30 + 60*0.25 + 70*0.25 + 50*0.20
        assert result['score'] == round(expected, 1)

    def test_grade_boundaries(self):
        # STRONG_INFLOW: 80+
        r = calc_composite_score(80, 80, 80, 80)
        assert r['grade'] == 'STRONG_INFLOW'
        # INFLOW: 65+
        r = calc_composite_score(65, 65, 65, 65)
        assert r['grade'] == 'INFLOW'
        # BALANCED: 45+
        r = calc_composite_score(45, 45, 45, 45)
        assert r['grade'] == 'BALANCED'
        # OUTFLOW: 30+
        r = calc_composite_score(30, 30, 30, 30)
        assert r['grade'] == 'OUTFLOW'
        # STRONG_OUTFLOW: 0+
        r = calc_composite_score(10, 10, 10, 10)
        assert r['grade'] == 'STRONG_OUTFLOW'


class TestGenerateReport:
    """generate_supply_demand_report 테스트."""

    def test_basic_report(self):
        market_flow = {
            'market': 'KOSPI',
            'foreign_score': 75,
            'institution_score': 65,
            'individual_score': 30,
            'consecutive_days': {
                'foreign': {'buy_days': 5, 'sell_days': 0, 'direction': 'buy', 'strength': 'moderate'},
                'institution': {'buy_days': 3, 'sell_days': 0, 'direction': 'buy', 'strength': 'mild'},
            },
            'signal': 'BUY',
            'sentiment_score': 72.5,
        }
        sector_flow = {
            'flows': {'반도체': {'foreign': 500, 'institution': 300, 'individual': -200, 'net': 600}},
            'heatmap': {'반도체': 'inflow'},
            'rotation_score': 65.0,
            'hhi': 0.15,
            'hhi_score': 50.0,
            'divergence': {},
            'divergence_score': 70.0,
            'sector_score': 60.0,
        }
        liquidity = {
            'volume_ratio': {'5d_ratio': 1.2, '20d_ratio': 1.1, '60d_ratio': 1.0},
            'volume_score': 65.0,
            'turnover': 1.2,
            'turnover_score': 79.0,
            'concentration': 0.25,
            'concentration_score': 55.0,
            'grade': 'NORMAL',
            'score': 65.0,
        }

        report = generate_supply_demand_report(market_flow, sector_flow, liquidity)
        assert '# 수급 종합 리포트' in report
        assert 'KOSPI' in report
        assert 'BUY' in report
        assert '반도체' in report
        assert 'NORMAL' in report

    def test_empty_data_report(self):
        market_flow = {
            'market': 'KOSPI',
            'foreign_score': 50,
            'institution_score': 50,
            'individual_score': 50,
            'consecutive_days': {},
            'signal': 'NEUTRAL',
            'sentiment_score': 50.0,
        }
        sector_flow = {
            'flows': {},
            'heatmap': {},
            'rotation_score': 60.0,
            'hhi': 0.0,
            'hhi_score': 90.0,
            'divergence': {},
            'divergence_score': 70.0,
            'sector_score': 70.0,
        }
        liquidity = {
            'volume_ratio': {},
            'volume_score': 50.0,
            'turnover': 0,
            'turnover_score': 50.0,
            'concentration': 0,
            'concentration_score': 70.0,
            'grade': 'NORMAL',
            'score': 55.0,
        }

        report = generate_supply_demand_report(market_flow, sector_flow, liquidity)
        assert 'NEUTRAL' in report
        assert '종합 등급' in report
