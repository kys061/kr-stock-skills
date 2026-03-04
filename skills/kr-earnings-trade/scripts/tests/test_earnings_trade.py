"""kr-earnings-trade: 5팩터 실적 트레이드 분석 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gap_analyzer import calc_gap, score_gap, GAP_SCORE_TABLE, KR_PRICE_LIMIT
from trend_analyzer import (calc_pre_earnings_trend, score_trend,
                            TREND_SCORE_TABLE, TREND_LOOKBACK)
from volume_analyzer import (calc_volume_ratio, score_volume,
                             VOLUME_SCORE_TABLE, VOLUME_SHORT_WINDOW,
                             VOLUME_LONG_WINDOW)
from ma_position_analyzer import (calc_sma, calc_ma_distance,
                                  score_ma200, score_ma50,
                                  MA200_SCORE_TABLE, MA50_SCORE_TABLE,
                                  MA200_PERIOD, MA50_PERIOD)
from scorer import (calc_composite_score, apply_foreign_bonus,
                    WEIGHTS, GRADE_THRESHOLDS,
                    FOREIGN_BUY_BONUS_DAYS, FOREIGN_BUY_BONUS_SCORE,
                    FOREIGN_BUY_MIN_AMOUNT, MARKET_CAP_MIN, LOOKBACK_DAYS)
from report_generator import EarningsTradeReportGenerator


# ─── 헬퍼 ───

def make_ohlcv(closes, opens=None, volumes=None):
    """테스트용 OHLCV 리스트 생성."""
    n = len(closes)
    if opens is None:
        opens = closes
    if volumes is None:
        volumes = [1000] * n
    return [{'open': opens[i], 'close': closes[i], 'volume': volumes[i],
             'date': f'2026-01-{i+1:02d}'} for i in range(n)]


# ═══════════════════════════════════════════
# Factor 1: Gap Analyzer
# ═══════════════════════════════════════════

class TestGapAnalyzer:

    def test_after_close_gap(self):
        """장후 발표: open[D+1]/close[D] - 1."""
        prices = make_ohlcv(
            closes=[100, 100, 100],
            opens=[100, 100, 110],
        )
        gap = calc_gap(prices, 1, 'after_close')
        assert abs(gap - 0.10) < 1e-9

    def test_before_open_gap(self):
        """장전 발표: open[D]/close[D-1] - 1."""
        prices = make_ohlcv(
            closes=[100, 105, 105],
            opens=[100, 108, 105],
        )
        gap = calc_gap(prices, 1, 'before_open')
        assert abs(gap - 0.08) < 1e-9

    def test_during_market_gap(self):
        """장중 발표: close[D]/open[D] - 1."""
        prices = make_ohlcv(
            closes=[100, 110, 110],
            opens=[100, 100, 110],
        )
        gap = calc_gap(prices, 1, 'during_market')
        assert abs(gap - 0.10) < 1e-9

    def test_empty_prices(self):
        assert calc_gap([], 0) == 0.0

    def test_negative_idx(self):
        prices = make_ohlcv([100, 105])
        assert calc_gap(prices, -1) == 0.0

    def test_last_idx_after_close(self):
        """마지막 인덱스에서 after_close → D+1 없음 → 0.0."""
        prices = make_ohlcv([100, 105])
        assert calc_gap(prices, 1, 'after_close') == 0.0

    def test_score_gap_boundaries(self):
        """GAP 점수 경계값 테스트."""
        assert score_gap(10.0)['score'] == 100
        assert score_gap(7.0)['score'] == 85
        assert score_gap(5.0)['score'] == 70
        assert score_gap(3.0)['score'] == 55
        assert score_gap(1.0)['score'] == 35
        assert score_gap(0.5)['score'] == 15

    def test_score_gap_negative(self):
        """음수 갭도 절대값으로 점수화."""
        result = score_gap(-8.0)
        assert result['score'] == 85
        assert result['abs_gap'] == 8.0


# ═══════════════════════════════════════════
# Factor 2: Trend Analyzer
# ═══════════════════════════════════════════

class TestTrendAnalyzer:

    def test_uptrend(self):
        """20일 상승 추세."""
        closes = [100] * 10 + [120] + [120] * 10
        prices = make_ohlcv(closes)
        # earnings_idx=20, lookback=20 → start=0(100), end=19(120)
        trend = calc_pre_earnings_trend(prices, 20, 20)
        assert trend == pytest.approx(20.0, abs=0.1)

    def test_downtrend(self):
        """20일 하락 추세."""
        closes = [100] * 10 + [80] + [80] * 10
        prices = make_ohlcv(closes)
        trend = calc_pre_earnings_trend(prices, 20, 20)
        assert trend == pytest.approx(-20.0, abs=0.1)

    def test_insufficient_data(self):
        """데이터 부족 시 0.0."""
        prices = make_ohlcv([100] * 5)
        assert calc_pre_earnings_trend(prices, 3, 20) == 0.0

    def test_empty_prices(self):
        assert calc_pre_earnings_trend([], 0) == 0.0

    def test_score_trend_boundaries(self):
        assert score_trend(15.0)['score'] == 100
        assert score_trend(10.0)['score'] == 85
        assert score_trend(5.0)['score'] == 70
        assert score_trend(0.0)['score'] == 50
        assert score_trend(-5.0)['score'] == 30
        assert score_trend(-10.0)['score'] == 15

    def test_score_trend_returns_pct(self):
        result = score_trend(12.345)
        assert result['trend_pct'] == 12.35


# ═══════════════════════════════════════════
# Factor 3: Volume Analyzer
# ═══════════════════════════════════════════

class TestVolumeAnalyzer:

    def test_high_volume_ratio(self):
        """단기>장기 → 비율 > 1."""
        volumes = [1000] * 60 + [3000] * 20 + [1000]
        ratio = calc_volume_ratio(volumes, 80)
        # short_avg=3000, long_avg=(40*1000+20*3000)/60=1666.7 → 1.8
        assert ratio == pytest.approx(1.8, abs=0.01)

    def test_equal_volume(self):
        """균등 거래량 → 비율 ≈ 1."""
        volumes = [1000] * 100
        ratio = calc_volume_ratio(volumes, 80)
        assert abs(ratio - 1.0) < 0.01

    def test_insufficient_data(self):
        """데이터 부족 시 1.0."""
        volumes = [1000] * 30
        assert calc_volume_ratio(volumes, 10) == 1.0

    def test_empty_volumes(self):
        assert calc_volume_ratio([], 0) == 1.0

    def test_score_volume_boundaries(self):
        assert score_volume(2.0)['score'] == 100
        assert score_volume(1.5)['score'] == 80
        assert score_volume(1.2)['score'] == 60
        assert score_volume(1.0)['score'] == 40
        assert score_volume(0.5)['score'] == 20


# ═══════════════════════════════════════════
# Factor 4,5: MA Position Analyzer
# ═══════════════════════════════════════════

class TestMAPositionAnalyzer:

    def test_calc_sma(self):
        """SMA 계산 정확성."""
        prices = list(range(1, 11))  # 1~10
        sma = calc_sma(prices, 5)
        assert sma == pytest.approx(8.0)  # (6+7+8+9+10)/5

    def test_calc_sma_insufficient(self):
        """데이터 부족 시 0.0."""
        assert calc_sma([1, 2, 3], 5) == 0.0

    def test_calc_ma_distance_above(self):
        """MA 위: 양수 거리."""
        dist = calc_ma_distance(110, 100)
        assert dist == pytest.approx(10.0)

    def test_calc_ma_distance_below(self):
        """MA 아래: 음수 거리."""
        dist = calc_ma_distance(90, 100)
        assert dist == pytest.approx(-10.0)

    def test_calc_ma_distance_zero_ma(self):
        assert calc_ma_distance(100, 0) == 0.0

    def test_score_ma200_boundaries(self):
        assert score_ma200(20.0)['score'] == 100
        assert score_ma200(10.0)['score'] == 85
        assert score_ma200(5.0)['score'] == 70
        assert score_ma200(0.0)['score'] == 55
        assert score_ma200(-5.0)['score'] == 35
        assert score_ma200(-10.0)['score'] == 15

    def test_score_ma50_boundaries(self):
        assert score_ma50(10.0)['score'] == 100
        assert score_ma50(5.0)['score'] == 80
        assert score_ma50(0.0)['score'] == 60
        assert score_ma50(-5.0)['score'] == 35
        assert score_ma50(-10.0)['score'] == 15


# ═══════════════════════════════════════════
# Composite Scorer
# ═══════════════════════════════════════════

class TestCompositeScorer:

    def test_all_perfect(self):
        """모든 팩터 100점."""
        components = {k: 100 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['composite_score'] == 100
        assert result['grade'] == 'A'

    def test_all_zero(self):
        """모든 팩터 0점."""
        components = {k: 0 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['composite_score'] == 0
        assert result['grade'] == 'D'

    def test_grade_a_boundary(self):
        components = {k: 85 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['grade'] == 'A'

    def test_grade_b_boundary(self):
        components = {k: 70 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['grade'] == 'B'

    def test_grade_c_boundary(self):
        components = {k: 55 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['grade'] == 'C'

    def test_weakest_strongest(self):
        components = {
            'gap_size': 30,
            'pre_earnings_trend': 90,
            'volume_trend': 60,
            'ma200_position': 50,
            'ma50_position': 70,
        }
        result = calc_composite_score(components)
        assert result['weakest_component'] == 'gap_size'
        assert result['strongest_component'] == 'pre_earnings_trend'

    def test_component_breakdown(self):
        components = {k: 80 for k in WEIGHTS}
        result = calc_composite_score(components)
        breakdown = result['component_breakdown']
        for k, w in WEIGHTS.items():
            assert breakdown[k]['score'] == 80
            assert breakdown[k]['weight'] == w
            assert breakdown[k]['weighted'] == pytest.approx(80 * w, abs=0.1)


# ═══════════════════════════════════════════
# Foreign Buy Bonus
# ═══════════════════════════════════════════

class TestForeignBuyBonus:

    def test_bonus_applied(self):
        """5일 연속 10억+ 순매수 → 보너스 적용."""
        buys = [2_000_000_000] * 5
        result = apply_foreign_bonus(80, buys)
        assert result['final_score'] == 85
        assert result['bonus_applied'] is True
        assert result['consecutive_days'] == 5

    def test_bonus_not_applied_insufficient_days(self):
        """3일만 충족 → 보너스 미적용."""
        buys = [2_000_000_000] * 3 + [500_000_000] * 2
        result = apply_foreign_bonus(80, buys)
        assert result['final_score'] == 80
        assert result['bonus_applied'] is False
        assert result['consecutive_days'] == 3

    def test_bonus_cap_at_100(self):
        """보너스 적용 후 100점 상한."""
        buys = [2_000_000_000] * 5
        result = apply_foreign_bonus(98, buys)
        assert result['final_score'] == 100

    def test_empty_buys(self):
        result = apply_foreign_bonus(70, [])
        assert result['final_score'] == 70
        assert result['bonus_applied'] is False


# ═══════════════════════════════════════════
# Report Generator
# ═══════════════════════════════════════════

class TestReportGenerator:

    def test_generate_json(self, tmp_path):
        gen = EarningsTradeReportGenerator(str(tmp_path))
        results = [
            {'ticker': '005930', 'name': '삼성전자', 'grade': 'A',
             'final_score': 90, 'gap_pct': 5.0, 'trend_pct': 10.0,
             'volume_ratio': 2.0, 'ma200_distance': 15.0,
             'ma50_distance': 5.0, 'bonus_applied': True},
        ]
        filepath = gen.generate_json(results)
        assert os.path.exists(filepath)
        import json
        with open(filepath) as f:
            data = json.load(f)
        assert data['summary']['grade_a'] == 1

    def test_generate_markdown(self, tmp_path):
        gen = EarningsTradeReportGenerator(str(tmp_path))
        results = [
            {'ticker': '005930', 'name': '삼성전자', 'grade': 'B',
             'final_score': 75, 'gap_pct': 3.0, 'trend_pct': 5.0,
             'volume_ratio': 1.5, 'ma200_distance': 8.0,
             'ma50_distance': 3.0, 'bonus_applied': False},
        ]
        filepath = gen.generate_markdown(results)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
        assert '005930' in content
        assert '삼성전자' in content

    def test_empty_results(self, tmp_path):
        gen = EarningsTradeReportGenerator(str(tmp_path))
        filepath = gen.generate_json([])
        import json
        with open(filepath) as f:
            data = json.load(f)
        assert data['summary']['total'] == 0


# ═══════════════════════════════════════════
# Constants Validation
# ═══════════════════════════════════════════

class TestConstants:

    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_grade_thresholds_complete(self):
        """등급 0~100 전범위 커버."""
        covered = set()
        for band in GRADE_THRESHOLDS:
            for i in range(band['min'], band['max'] + 1):
                covered.add(i)
        for i in range(101):
            assert i in covered, f"Score {i} not covered by grades"

    def test_kr_specific_constants(self):
        assert KR_PRICE_LIMIT == 0.30
        assert FOREIGN_BUY_BONUS_DAYS == 5
        assert FOREIGN_BUY_BONUS_SCORE == 5
        assert FOREIGN_BUY_MIN_AMOUNT == 1_000_000_000
        assert MARKET_CAP_MIN == 500_000_000_000
        assert LOOKBACK_DAYS == 14

    def test_period_constants(self):
        assert TREND_LOOKBACK == 20
        assert VOLUME_SHORT_WINDOW == 20
        assert VOLUME_LONG_WINDOW == 60
        assert MA200_PERIOD == 200
        assert MA50_PERIOD == 50
