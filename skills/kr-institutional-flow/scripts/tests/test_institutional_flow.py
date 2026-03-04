"""kr-institutional-flow: 수급 동향 분석 테스트."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from investor_flow_analyzer import (
    aggregate_by_group, calc_consecutive_days,
    score_foreign_flow, score_institutional_flow,
    INVESTOR_GROUPS, ANALYSIS_WINDOW, TREND_WINDOW,
    FOREIGN_CONSECUTIVE_STRONG, FOREIGN_CONSECUTIVE_MODERATE,
    FOREIGN_CONSECUTIVE_MILD, FOREIGN_STRONG_AMOUNT,
    FOREIGN_MODERATE_AMOUNT,
    INST_CONSECUTIVE_STRONG, INST_CONSECUTIVE_MODERATE,
    INST_CONSECUTIVE_MILD, INST_STRONG_AMOUNT, INST_MODERATE_AMOUNT,
)
from foreign_flow_tracker import calc_ownership_trend, detect_turning_point
from accumulation_detector import (
    detect_accumulation, detect_retail_counter,
    apply_retail_counter_bonus,
    RETAIL_COUNTER_BONUS, RETAIL_COUNTER_MIN_DAYS,
)
from scorer import (
    calc_flow_consistency, calc_volume_confirmation,
    calc_composite_score, get_rating,
    WEIGHTS, RATING_BANDS, CONSISTENCY_SCORE_TABLE,
    VOLUME_CONFIRM_TABLE, MARKET_CAP_MIN,
)
from report_generator import InstitutionalFlowReportGenerator


# ─── 헬퍼 ───

def make_investor_data(foreign_net, inst_net=None, retail_net=None, days=20):
    """테스트용 투자자 매매동향 데이터 생성."""
    if inst_net is None:
        inst_net = [0] * days
    if retail_net is None:
        retail_net = [0] * days
    data = []
    for i in range(days):
        fn = foreign_net[i] if i < len(foreign_net) else 0
        iin = inst_net[i] if i < len(inst_net) else 0
        rn = retail_net[i] if i < len(retail_net) else 0
        data.append({
            'date': f'2026-01-{i+1:02d}',
            'investors': {
                '외국인': fn,
                '금융투자': iin // 3 if iin else 0,
                '투신': iin // 3 if iin else 0,
                '연기금': iin - 2 * (iin // 3) if iin else 0,
                '보험': 0, '사모': 0, '은행': 0,
                '개인': rn,
                '기타법인': 0, '기타외국인': 0, '기타금융': 0, '국가': 0,
            },
        })
    return data


# ═══════════════════════════════════════════
# 투자자 매매동향 분석
# ═══════════════════════════════════════════

class TestInvestorFlowAnalyzer:

    def test_aggregate_foreign(self):
        """외국인 그룹 집계."""
        data = make_investor_data([100, 200, -50])
        result = aggregate_by_group(data, 'foreign')
        assert result[0] == 100
        assert result[1] == 200
        assert result[2] == -50

    def test_aggregate_institutional(self):
        """기관 그룹 집계 (금융투자+투신+연기금...)."""
        data = [{'investors': {'금융투자': 10, '보험': 20, '투신': 30,
                               '사모': 5, '은행': 5, '연기금': 30}}]
        result = aggregate_by_group(data, 'institutional')
        assert result[0] == 100

    def test_aggregate_retail(self):
        """개인 그룹 집계."""
        data = [{'investors': {'개인': -500}}]
        result = aggregate_by_group(data, 'retail')
        assert result[0] == -500

    def test_aggregate_invalid_group(self):
        assert aggregate_by_group([], 'unknown') == []

    def test_consecutive_buy(self):
        """연속 순매수 계산."""
        net = [-100, -200, 100, 200, 300]
        result = calc_consecutive_days(net)
        assert result['direction'] == 'buy'
        assert result['days'] == 3
        assert result['avg_amount'] == 200.0

    def test_consecutive_sell(self):
        """연속 순매도 계산."""
        net = [100, 200, -100, -200, -300]
        result = calc_consecutive_days(net)
        assert result['direction'] == 'sell'
        assert result['days'] == 3

    def test_consecutive_empty(self):
        result = calc_consecutive_days([])
        assert result['direction'] == 'neutral'
        assert result['days'] == 0


# ═══════════════════════════════════════════
# 외국인 수급 시그널
# ═══════════════════════════════════════════

class TestForeignFlowSignal:

    def test_strong_buy(self):
        """10일+ 연속 순매수 & ≥50억/일."""
        data = {'direction': 'buy', 'days': 12,
                'avg_amount': 6_000_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 100
        assert result['signal'] == 'Strong Buy'

    def test_buy(self):
        """5-9일 연속 순매수 & ≥10억/일."""
        data = {'direction': 'buy', 'days': 7,
                'avg_amount': 2_000_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 80
        assert result['signal'] == 'Buy'

    def test_mild_buy(self):
        """3-4일 연속 순매수."""
        data = {'direction': 'buy', 'days': 3,
                'avg_amount': 500_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 60
        assert result['signal'] == 'Mild Buy'

    def test_neutral(self):
        """방향 없음."""
        data = {'direction': 'neutral', 'days': 0, 'avg_amount': 0}
        result = score_foreign_flow(data)
        assert result['score'] == 40
        assert result['signal'] == 'Neutral'

    def test_mild_sell(self):
        data = {'direction': 'sell', 'days': 4,
                'avg_amount': 500_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 30
        assert result['signal'] == 'Mild Sell'

    def test_sell(self):
        data = {'direction': 'sell', 'days': 6,
                'avg_amount': 2_000_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 15
        assert result['signal'] == 'Sell'

    def test_strong_sell(self):
        data = {'direction': 'sell', 'days': 15,
                'avg_amount': 8_000_000_000}
        result = score_foreign_flow(data)
        assert result['score'] == 0
        assert result['signal'] == 'Strong Sell'


# ═══════════════════════════════════════════
# 기관 수급 시그널
# ═══════════════════════════════════════════

class TestInstitutionalFlowSignal:

    def test_strong_buy(self):
        data = {'direction': 'buy', 'days': 11,
                'avg_amount': 15_000_000_000}
        result = score_institutional_flow(data)
        assert result['score'] == 100

    def test_buy(self):
        data = {'direction': 'buy', 'days': 7,
                'avg_amount': 5_000_000_000}
        result = score_institutional_flow(data)
        assert result['score'] == 80

    def test_mild_buy(self):
        data = {'direction': 'buy', 'days': 3, 'avg_amount': 500_000_000}
        result = score_institutional_flow(data)
        assert result['score'] == 60

    def test_sell(self):
        data = {'direction': 'sell', 'days': 6,
                'avg_amount': 5_000_000_000}
        result = score_institutional_flow(data)
        assert result['score'] == 15

    def test_strong_sell(self):
        data = {'direction': 'sell', 'days': 12,
                'avg_amount': 12_000_000_000}
        result = score_institutional_flow(data)
        assert result['score'] == 0


# ═══════════════════════════════════════════
# 외국인 수급 추적
# ═══════════════════════════════════════════

class TestForeignFlowTracker:

    def test_ownership_trend_up(self):
        history = [{'ratio': 10.0}, {'ratio': 11.0}, {'ratio': 12.0}]
        result = calc_ownership_trend(history)
        assert result['trend_direction'] == 'up'
        assert result['change_rate'] == 2.0

    def test_ownership_trend_down(self):
        history = [{'ratio': 15.0}, {'ratio': 13.0}, {'ratio': 12.0}]
        result = calc_ownership_trend(history)
        assert result['trend_direction'] == 'down'

    def test_ownership_trend_sideways(self):
        history = [{'ratio': 10.0}, {'ratio': 10.1}, {'ratio': 10.2}]
        result = calc_ownership_trend(history)
        assert result['trend_direction'] == 'sideways'

    def test_turning_point_buy_to_sell(self):
        net = [100, 200, 300, 400, 500, -100, -200, -300, -400, -500]
        result = detect_turning_point(net, window=5)
        assert result['turning_point'] is True
        assert result['direction'] == 'buy_to_sell'

    def test_turning_point_sell_to_buy(self):
        net = [-100, -200, -300, -400, -500, 100, 200, 300, 400, 500]
        result = detect_turning_point(net, window=5)
        assert result['turning_point'] is True
        assert result['direction'] == 'sell_to_buy'

    def test_no_turning_point(self):
        net = [100] * 10
        result = detect_turning_point(net, window=5)
        assert result['turning_point'] is False


# ═══════════════════════════════════════════
# 축적/이탈 패턴 감지
# ═══════════════════════════════════════════

class TestAccumulationDetector:

    def test_accumulation_pattern(self):
        """외국인+ 기관+ 개인- → accumulation."""
        foreign = [100] * 5
        inst = [200] * 5
        retail = [-300] * 5
        result = detect_accumulation(foreign, inst, retail)
        assert result['pattern'] == 'accumulation'
        assert result['days'] == 5

    def test_distribution_pattern(self):
        """외국인- 기관- 개인+ → distribution."""
        foreign = [-100] * 5
        inst = [-200] * 5
        retail = [300] * 5
        result = detect_accumulation(foreign, inst, retail)
        assert result['pattern'] == 'distribution'
        assert result['days'] == 5

    def test_neutral_pattern(self):
        """혼조 → neutral."""
        foreign = [100, -100, 100, -100, 100]
        inst = [-100, 100, -100, 100, -100]
        retail = [0] * 5
        result = detect_accumulation(foreign, inst, retail)
        assert result['pattern'] == 'neutral'

    def test_retail_counter_detected(self):
        """개인 매도 & 스마트머니 매수 5일 연속."""
        retail = [-100] * 7
        smart = [200] * 7
        result = detect_retail_counter(retail, smart)
        assert result['counter_pattern'] is True
        assert result['consecutive_days'] == 7
        assert result['bonus_applicable'] is True

    def test_retail_counter_insufficient(self):
        """3일 역방향 → 패턴 감지, 보너스 미적용."""
        retail = [100, 100, -100, -100, -100]
        smart = [-50, -50, 200, 200, 200]
        result = detect_retail_counter(retail, smart)
        assert result['counter_pattern'] is True
        assert result['consecutive_days'] == 3
        assert result['bonus_applicable'] is False

    def test_bonus_applied(self):
        counter = {'bonus_applicable': True}
        result = apply_retail_counter_bonus(80, counter)
        assert result['final_score'] == 90
        assert result['bonus_applied'] is True

    def test_bonus_cap_100(self):
        counter = {'bonus_applicable': True}
        result = apply_retail_counter_bonus(95, counter)
        assert result['final_score'] == 100

    def test_bonus_not_applied(self):
        counter = {'bonus_applicable': False}
        result = apply_retail_counter_bonus(80, counter)
        assert result['final_score'] == 80
        assert result['bonus_applied'] is False


# ═══════════════════════════════════════════
# 수급 일관성
# ═══════════════════════════════════════════

class TestFlowConsistency:

    def test_high_consistency(self):
        """80%+ 순매수일 → 100점."""
        net = [100] * 17 + [-50] * 3  # 85%
        result = calc_flow_consistency(net)
        assert result['score'] == 100
        assert result['buy_days'] == 17

    def test_moderate_consistency(self):
        """60-79% → 80점."""
        net = [100] * 13 + [-50] * 7  # 65%
        result = calc_flow_consistency(net)
        assert result['score'] == 80

    def test_balanced(self):
        """50-59% → 60점."""
        net = [100] * 11 + [-50] * 9  # 55%
        result = calc_flow_consistency(net)
        assert result['score'] == 60

    def test_low_consistency(self):
        """40-49% → 40점."""
        net = [100] * 9 + [-50] * 11  # 45%
        result = calc_flow_consistency(net)
        assert result['score'] == 40

    def test_sell_dominant(self):
        """< 40% → 20점."""
        net = [100] * 5 + [-50] * 15  # 25%
        result = calc_flow_consistency(net)
        assert result['score'] == 20

    def test_empty(self):
        result = calc_flow_consistency([])
        assert result['score'] == 20


# ═══════════════════════════════════════════
# 거래량 확인
# ═══════════════════════════════════════════

class TestVolumeConfirmation:

    def test_strong_confirmation(self):
        """매수일 거래량 >> 매도일 → 100점."""
        net = [100, -50, 100, -50]
        vols = [3000, 1000, 3000, 1000]
        result = calc_volume_confirmation(net, vols)
        assert result['score'] == 100
        assert result['ratio'] == pytest.approx(3.0, abs=0.1)

    def test_moderate_confirmation(self):
        """매수일 거래량 ≥ 1.2x → 75점."""
        net = [100, -50, 100, -50]
        vols = [1300, 1000, 1300, 1000]
        result = calc_volume_confirmation(net, vols)
        assert result['score'] == 75

    def test_equal_volumes(self):
        """매수일 = 매도일 → 50점."""
        net = [100, -50, 100, -50]
        vols = [1000, 1000, 1000, 1000]
        result = calc_volume_confirmation(net, vols)
        assert result['score'] == 50

    def test_weak_confirmation(self):
        """매수일 < 매도일 → 25점."""
        net = [100, -50, 100, -50]
        vols = [500, 1000, 500, 1000]
        result = calc_volume_confirmation(net, vols)
        assert result['score'] == 25

    def test_empty(self):
        result = calc_volume_confirmation([], [])
        assert result['score'] == 25


# ═══════════════════════════════════════════
# 종합 스코어
# ═══════════════════════════════════════════

class TestFlowScorer:

    def test_all_perfect(self):
        components = {k: 100 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['composite_score'] == 100
        assert result['rating'] == 'Strong Accumulation'

    def test_all_zero(self):
        components = {k: 0 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['composite_score'] == 0
        assert result['rating'] == 'Distribution'

    def test_accumulation_boundary(self):
        components = {k: 70 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['rating'] == 'Accumulation'

    def test_neutral_boundary(self):
        components = {k: 40 for k in WEIGHTS}
        result = calc_composite_score(components)
        assert result['rating'] == 'Neutral'

    def test_get_rating(self):
        assert get_rating(90)['rating'] == 'Strong Accumulation'
        assert get_rating(75)['rating'] == 'Accumulation'
        assert get_rating(60)['rating'] == 'Mild Positive'
        assert get_rating(45)['rating'] == 'Neutral'
        assert get_rating(30)['rating'] == 'Distribution'


# ═══════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════

class TestReportGenerator:

    def test_generate_json(self, tmp_path):
        gen = InstitutionalFlowReportGenerator(str(tmp_path))
        results = [
            {'ticker': '005930', 'name': '삼성전자',
             'rating': 'Strong Accumulation', 'final_score': 92,
             'bonus_applied': True},
        ]
        filepath = gen.generate_json(results)
        assert os.path.exists(filepath)
        import json
        with open(filepath) as f:
            data = json.load(f)
        assert data['summary']['strong_accumulation'] == 1

    def test_generate_markdown(self, tmp_path):
        gen = InstitutionalFlowReportGenerator(str(tmp_path))
        results = [
            {'ticker': '005930', 'name': '삼성전자',
             'rating': 'Accumulation', 'final_score': 78,
             'foreign_signal': 'Buy', 'inst_signal': 'Mild Buy',
             'consistency_ratio': 70.0, 'volume_ratio': 1.3,
             'bonus_applied': False},
        ]
        filepath = gen.generate_markdown(results)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
        assert '005930' in content
        assert '삼성전자' in content


# ═══════════════════════════════════════════
# 상수 검증
# ═══════════════════════════════════════════

class TestConstants:

    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_rating_bands_complete(self):
        """등급 0~100 전범위 커버."""
        covered = set()
        for band in RATING_BANDS:
            for i in range(band['min'], band['max'] + 1):
                covered.add(i)
        for i in range(101):
            assert i in covered, f"Score {i} not covered by ratings"

    def test_investor_groups_coverage(self):
        """3+1 그룹 모두 정의."""
        assert 'foreign' in INVESTOR_GROUPS
        assert 'institutional' in INVESTOR_GROUPS
        assert 'retail' in INVESTOR_GROUPS
        assert 'other' in INVESTOR_GROUPS

    def test_kr_specific_constants(self):
        assert RETAIL_COUNTER_BONUS == 10
        assert RETAIL_COUNTER_MIN_DAYS == 5
        assert ANALYSIS_WINDOW == 20
        assert TREND_WINDOW == 60
        assert MARKET_CAP_MIN == 500_000_000_000

    def test_foreign_signal_constants(self):
        assert FOREIGN_CONSECUTIVE_STRONG == 10
        assert FOREIGN_CONSECUTIVE_MODERATE == 5
        assert FOREIGN_CONSECUTIVE_MILD == 3
        assert FOREIGN_STRONG_AMOUNT == 5_000_000_000
        assert FOREIGN_MODERATE_AMOUNT == 1_000_000_000

    def test_inst_signal_constants(self):
        assert INST_CONSECUTIVE_STRONG == 10
        assert INST_CONSECUTIVE_MODERATE == 5
        assert INST_CONSECUTIVE_MILD == 3
        assert INST_STRONG_AMOUNT == 10_000_000_000
        assert INST_MODERATE_AMOUNT == 3_000_000_000
