"""kr-short-sale-tracker 종합 테스트."""

import pytest

from ..short_ratio_analyzer import (
    SHORT_RATIO_CONFIG,
    SHORT_BALANCE_LEVELS,
    SHORT_TRADE_LEVELS,
    _classify_balance_level,
    _classify_trade_level,
    calc_short_percentile,
    analyze_short_ratio,
    analyze_sector_concentration,
)
from ..short_cover_detector import (
    SHORT_COVER_CONFIG,
    SQUEEZE_CONDITIONS,
    SHORT_COVER_SIGNALS,
    SHORT_RISK_WEIGHTS,
    SHORT_RISK_GRADES,
    calc_days_to_cover,
    calc_squeeze_probability,
    detect_short_cover,
    calc_short_risk_score,
)
from ..report_generator import generate_short_sale_report


# ═══════════════════════════════════════════════
# 상수 검증
# ═══════════════════════════════════════════════

class TestConstants:
    """설계 상수 검증."""

    def test_short_ratio_config(self):
        assert SHORT_RATIO_CONFIG['ma_periods'] == [5, 20, 60]
        assert SHORT_RATIO_CONFIG['percentile_lookback'] == 252

    def test_balance_levels(self):
        assert SHORT_BALANCE_LEVELS['extreme'] == 0.10
        assert SHORT_BALANCE_LEVELS['high'] == 0.05
        assert SHORT_BALANCE_LEVELS['moderate'] == 0.02
        assert SHORT_BALANCE_LEVELS['low'] == 0.01
        assert SHORT_BALANCE_LEVELS['minimal'] == 0.0

    def test_trade_levels(self):
        assert SHORT_TRADE_LEVELS['extreme'] == 0.20
        assert SHORT_TRADE_LEVELS['high'] == 0.10
        assert SHORT_TRADE_LEVELS['moderate'] == 0.05
        assert SHORT_TRADE_LEVELS['low'] == 0.0

    def test_cover_config(self):
        c = SHORT_COVER_CONFIG['consecutive_decrease']
        assert c['strong'] == 7
        assert c['moderate'] == 5
        assert c['mild'] == 3
        assert SHORT_COVER_CONFIG['sharp_decrease_pct'] == 0.10

    def test_dtc_thresholds(self):
        d = SHORT_COVER_CONFIG['days_to_cover']
        assert d['critical'] == 10
        assert d['high'] == 5
        assert d['moderate'] == 3
        assert d['low'] == 0

    def test_squeeze_conditions(self):
        assert SQUEEZE_CONDITIONS['high_balance'] == 0.05
        assert SQUEEZE_CONDITIONS['high_days_to_cover'] == 5

    def test_cover_signals_count(self):
        assert len(SHORT_COVER_SIGNALS) == 5

    def test_risk_weights_sum(self):
        total = sum(v['weight'] for v in SHORT_RISK_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_risk_grades_count(self):
        assert len(SHORT_RISK_GRADES) == 4

    def test_risk_grades_coverage(self):
        # 0-100 범위 커버 확인
        assert SHORT_RISK_GRADES['LOW']['min_score'] == 0
        assert SHORT_RISK_GRADES['EXTREME']['max_score'] == 100


# ═══════════════════════════════════════════════
# short_ratio_analyzer 테스트
# ═══════════════════════════════════════════════

class TestClassifyBalanceLevel:
    """잔고비율 수준 분류 테스트."""

    def test_extreme(self):
        assert _classify_balance_level(0.12) == 'extreme'

    def test_high(self):
        assert _classify_balance_level(0.07) == 'high'

    def test_moderate(self):
        assert _classify_balance_level(0.03) == 'moderate'

    def test_low(self):
        assert _classify_balance_level(0.015) == 'low'

    def test_minimal(self):
        assert _classify_balance_level(0.005) == 'minimal'

    def test_boundary_extreme(self):
        assert _classify_balance_level(0.10) == 'extreme'

    def test_boundary_high(self):
        assert _classify_balance_level(0.05) == 'high'


class TestClassifyTradeLevel:
    """거래비율 수준 분류 테스트."""

    def test_extreme(self):
        assert _classify_trade_level(0.25) == 'extreme'

    def test_high(self):
        assert _classify_trade_level(0.12) == 'high'

    def test_moderate(self):
        assert _classify_trade_level(0.07) == 'moderate'

    def test_low(self):
        assert _classify_trade_level(0.03) == 'low'


class TestShortPercentile:
    """calc_short_percentile 테스트."""

    def test_empty_history(self):
        assert calc_short_percentile(0.05, []) == 50.0

    def test_high_percentile(self):
        history = [0.01 * i for i in range(1, 11)]  # 0.01 ~ 0.10
        result = calc_short_percentile(0.09, history)
        assert result >= 80

    def test_low_percentile(self):
        history = [0.01 * i for i in range(1, 11)]
        result = calc_short_percentile(0.02, history)
        assert result <= 20

    def test_median_percentile(self):
        history = [0.01 * i for i in range(1, 11)]
        result = calc_short_percentile(0.05, history)
        assert 30 <= result <= 60


class TestAnalyzeShortRatio:
    """analyze_short_ratio 종합 테스트."""

    def test_empty_data(self):
        result = analyze_short_ratio([], 1_000_000)
        assert result['balance_ratio'] == 0.0
        assert result['balance_level'] == 'minimal'

    def test_high_short(self):
        data = [
            {'date': '2026-03-04', 'short_balance': 60_000, 'short_volume': 5_000, 'total_volume': 50_000},
        ]
        result = analyze_short_ratio(data, 1_000_000)
        assert result['balance_ratio'] == 0.06  # 6%
        assert result['balance_level'] == 'high'
        assert result['trade_level'] == 'high'  # 10%

    def test_low_short(self):
        data = [
            {'date': '2026-03-04', 'short_balance': 5_000, 'short_volume': 1_000, 'total_volume': 100_000},
        ]
        result = analyze_short_ratio(data, 1_000_000)
        assert result['balance_ratio'] == 0.005
        assert result['balance_level'] == 'minimal'

    def test_zero_outstanding(self):
        data = [{'date': '2026-03-04', 'short_balance': 100, 'short_volume': 10, 'total_volume': 100}]
        result = analyze_short_ratio(data, 0)
        assert result['balance_ratio'] == 0.0


class TestSectorConcentration:
    """analyze_sector_concentration 테스트."""

    def test_empty_data(self):
        result = analyze_sector_concentration({})
        assert result['hhi'] == 0.0
        assert result['anomalies'] == []

    def test_concentrated(self):
        data = {
            '반도체': {'short_balance': 900},
            '자동차': {'short_balance': 100},
        }
        result = analyze_sector_concentration(data)
        assert result['hhi'] > 0.5
        assert '반도체' in result['anomalies']

    def test_distributed(self):
        data = {f'sector_{i}': {'short_balance': 100} for i in range(10)}
        result = analyze_sector_concentration(data)
        assert result['hhi'] == 0.1
        assert result['anomalies'] == []


# ═══════════════════════════════════════════════
# short_cover_detector 테스트
# ═══════════════════════════════════════════════

class TestDaysToCover:
    """calc_days_to_cover 테스트."""

    def test_normal(self):
        dtc = calc_days_to_cover(1_000_000, 200_000)
        assert dtc == 5.0

    def test_zero_volume(self):
        assert calc_days_to_cover(1_000_000, 0) == 0.0

    def test_none_volume(self):
        assert calc_days_to_cover(1_000_000, None) == 0.0

    def test_high_dtc(self):
        dtc = calc_days_to_cover(2_000_000, 100_000)
        assert dtc == 20.0


class TestSqueezeProbability:
    """calc_squeeze_probability 테스트."""

    def test_all_conditions_met(self):
        prob = calc_squeeze_probability(0.08, 7, True, True)
        assert prob >= 0.85

    def test_three_conditions(self):
        prob = calc_squeeze_probability(0.08, 7, True, False)
        assert 0.5 <= prob <= 0.75

    def test_no_conditions(self):
        prob = calc_squeeze_probability(0.01, 1, False, False)
        assert prob == 0.0

    def test_one_condition(self):
        prob = calc_squeeze_probability(0.08, 1, False, False)
        assert prob == 0.25


class TestDetectShortCover:
    """detect_short_cover 종합 테스트."""

    def test_empty_data(self):
        result = detect_short_cover([])
        assert result['signal'] == 'NEUTRAL'

    def test_strong_cover(self):
        # 8일 연속 감소: 최근(index 0)이 가장 작아야 함
        # 잔고: 200, 300, 400, ... 1000 (최근순 → 감소 추세)
        data = [
            {'short_balance': 200 + i * 100, 'total_volume': 500}
            for i in range(10)
        ]
        result = detect_short_cover(data)
        assert result['consecutive_decrease'] >= 7
        assert result['decrease_strength'] == 'strong'
        assert result['signal'] in ('STRONG_COVER', 'COVER')

    def test_building_short(self):
        # 잔고 증가: 최근(index 0)이 가장 큼
        data = [
            {'short_balance': 1500 - i * 100, 'total_volume': 500}
            for i in range(5)
        ]
        result = detect_short_cover(data)
        assert result['consecutive_decrease'] == 0

    def test_sharp_decrease(self):
        data = [
            {'short_balance': 800, 'total_volume': 500},
            {'short_balance': 1000, 'total_volume': 500},
        ]
        result = detect_short_cover(data)
        assert result['sharp_decrease'] is True
        assert result['sharp_decrease_pct'] == -0.2

    def test_dtc_calculation(self):
        data = [
            {'short_balance': 10_000, 'total_volume': 1_000}
            for _ in range(20)
        ]
        result = detect_short_cover(data)
        assert result['days_to_cover'] == 10.0
        assert result['dtc_level'] == 'critical'

    def test_with_price_data(self):
        data = [
            {'short_balance': 1000 - i * 50, 'total_volume': 500, 'balance_ratio': 0.06}
            for i in range(10)
        ]
        prices = [110, 108, 106, 104, 100]  # 상승 추세
        result = detect_short_cover(data, price_data=prices)
        assert result['squeeze_probability'] > 0


class TestShortRiskScore:
    """calc_short_risk_score 테스트."""

    def test_low_risk(self):
        ratio_data = {'balance_level': 'minimal', 'trade_level': 'low'}
        cover_data = {'consecutive_decrease': 8, 'sharp_decrease': True, 'days_to_cover': 1}
        result = calc_short_risk_score(ratio_data, cover_data)
        assert result['grade'] == 'LOW'

    def test_high_risk(self):
        ratio_data = {'balance_level': 'extreme', 'trade_level': 'extreme'}
        cover_data = {'consecutive_decrease': 0, 'sharp_decrease': False, 'days_to_cover': 12}
        result = calc_short_risk_score(ratio_data, cover_data)
        assert result['grade'] in ('HIGH', 'EXTREME')

    def test_moderate_risk(self):
        ratio_data = {'balance_level': 'moderate', 'trade_level': 'moderate'}
        cover_data = {'consecutive_decrease': 3, 'sharp_decrease': False, 'days_to_cover': 4}
        result = calc_short_risk_score(ratio_data, cover_data)
        assert result['grade'] in ('LOW', 'MODERATE', 'HIGH')

    def test_components_present(self):
        ratio_data = {'balance_level': 'high', 'trade_level': 'high'}
        cover_data = {'consecutive_decrease': 5, 'sharp_decrease': False, 'days_to_cover': 6}
        result = calc_short_risk_score(ratio_data, cover_data)
        assert len(result['components']) == 4
        for key in SHORT_RISK_WEIGHTS:
            assert key in result['components']

    def test_with_concentration(self):
        ratio_data = {'balance_level': 'high', 'trade_level': 'high'}
        cover_data = {'consecutive_decrease': 0, 'sharp_decrease': False, 'days_to_cover': 3}
        conc_data = {'hhi': 0.5, 'anomalies': ['반도체']}
        result = calc_short_risk_score(ratio_data, cover_data, conc_data)
        assert result['components']['concentration']['score'] > 30


# ═══════════════════════════════════════════════
# report_generator 테스트
# ═══════════════════════════════════════════════

class TestGenerateReport:
    """generate_short_sale_report 테스트."""

    def test_basic_report(self):
        ratio = {
            'balance_ratio': 0.05,
            'trade_ratio': 0.10,
            'balance_level': 'high',
            'trade_level': 'high',
            'percentile': 85.0,
            'ma_ratios': {'5d_ma': 0.048, '20d_ma': 0.045},
        }
        cover = {
            'signal': 'COVER',
            'consecutive_decrease': 5,
            'decrease_strength': 'moderate',
            'sharp_decrease': False,
            'sharp_decrease_pct': 0.0,
            'days_to_cover': 6.5,
            'dtc_level': 'high',
            'squeeze_probability': 0.5,
        }
        report = generate_short_sale_report(ratio, cover)
        assert '# 공매도 분석 리포트' in report
        assert 'COVER' in report
        assert '5.00%' in report
        assert '6.5일' in report

    def test_with_risk_score(self):
        ratio = {
            'balance_ratio': 0.03,
            'trade_ratio': 0.06,
            'balance_level': 'moderate',
            'trade_level': 'moderate',
            'percentile': 60.0,
            'ma_ratios': {},
        }
        cover = {
            'signal': 'NEUTRAL',
            'consecutive_decrease': 2,
            'decrease_strength': 'none',
            'sharp_decrease': False,
            'sharp_decrease_pct': 0.0,
            'days_to_cover': 3.5,
            'dtc_level': 'moderate',
            'squeeze_probability': 0.1,
        }
        risk = {
            'score': 45.0,
            'grade': 'MODERATE',
            'label': '보통',
            'components': {
                'short_ratio': {'score': 50, 'weight': 0.30},
                'trend': {'score': 40, 'weight': 0.30},
                'concentration': {'score': 30, 'weight': 0.20},
                'days_to_cover': {'score': 50, 'weight': 0.20},
            },
        }
        report = generate_short_sale_report(ratio, cover, risk)
        assert '리스크 등급' in report
        assert 'MODERATE' in report
