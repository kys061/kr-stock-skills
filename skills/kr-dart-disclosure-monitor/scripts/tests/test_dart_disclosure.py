"""kr-dart-disclosure-monitor 테스트."""

import pytest

from ..disclosure_classifier import (
    DISCLOSURE_TYPES,
    classify_disclosure,
    classify_batch,
)
from ..event_impact_scorer import (
    EVENT_IMPACT_LEVELS,
    IMPACT_ADJUSTMENTS,
    FREQUENCY_ANOMALY,
    DISCLOSURE_RISK_WEIGHTS,
    DISCLOSURE_RISK_GRADES,
    score_event_impact,
    detect_frequency_anomaly,
    calc_disclosure_risk_score,
)
from ..stake_change_tracker import (
    STAKE_CHANGE_CONFIG,
    STAKE_SIGNALS,
    INSIDER_TYPES,
    track_stake_changes,
    track_insider_trades,
    track_treasury_stock,
)
from ..report_generator import generate_disclosure_report


# ════════════════════════════════════════
# Constants
# ════════════════════════════════════════

class TestDisclosureTypesConstants:
    """DISCLOSURE_TYPES 상수 검증."""

    def test_10_types(self):
        assert len(DISCLOSURE_TYPES) == 10

    def test_type_keys(self):
        expected = {
            'EARNINGS', 'DIVIDEND', 'CAPITAL', 'MA', 'GOVERNANCE',
            'STAKE', 'LEGAL', 'IPO', 'REGULATION', 'OTHER',
        }
        assert set(DISCLOSURE_TYPES.keys()) == expected

    def test_all_types_have_label(self):
        for dtype, info in DISCLOSURE_TYPES.items():
            assert 'label' in info, f"{dtype} missing label"

    def test_all_types_have_keywords(self):
        for dtype, info in DISCLOSURE_TYPES.items():
            assert 'keywords' in info, f"{dtype} missing keywords"
            assert len(info['keywords']) > 0, f"{dtype} has empty keywords"

    def test_all_types_have_subtypes(self):
        for dtype, info in DISCLOSURE_TYPES.items():
            assert 'subtypes' in info, f"{dtype} missing subtypes"
            assert len(info['subtypes']) > 0, f"{dtype} has empty subtypes"

    def test_earnings_has_dart_kinds(self):
        assert 'dart_kinds' in DISCLOSURE_TYPES['EARNINGS']
        kinds = DISCLOSURE_TYPES['EARNINGS']['dart_kinds']
        assert 'A001' in kinds  # 사업보고서
        assert 'D001' in kinds  # 잠정실적


class TestEventImpactConstants:
    """EVENT_IMPACT_LEVELS 상수 검증."""

    def test_5_levels(self):
        assert len(EVENT_IMPACT_LEVELS) == 5

    def test_level_keys(self):
        assert set(EVENT_IMPACT_LEVELS.keys()) == {1, 2, 3, 4, 5}

    def test_all_levels_have_fields(self):
        for level, info in EVENT_IMPACT_LEVELS.items():
            assert 'label' in info, f"Level {level} missing label"
            assert 'korean' in info, f"Level {level} missing korean"
            assert 'events' in info, f"Level {level} missing events"
            assert 'action' in info, f"Level {level} missing action"

    def test_critical_events(self):
        critical = EVENT_IMPACT_LEVELS[5]['events']
        assert 'delisting' in critical
        assert 'management_issue' in critical
        assert 'trading_halt' in critical

    def test_impact_adjustments(self):
        assert IMPACT_ADJUSTMENTS['market_cap_large'] == 1.0
        assert IMPACT_ADJUSTMENTS['market_cap_mid'] == 0.8
        assert IMPACT_ADJUSTMENTS['market_cap_small'] == 0.6
        assert IMPACT_ADJUSTMENTS['after_hours'] == 1.2
        assert IMPACT_ADJUSTMENTS['consecutive_disclosure'] == 1.5

    def test_frequency_anomaly(self):
        assert FREQUENCY_ANOMALY['normal_daily'] == 2
        assert FREQUENCY_ANOMALY['elevated_daily'] == 5
        assert FREQUENCY_ANOMALY['anomaly_daily'] == 10


class TestRiskWeightsConstants:
    """리스크 가중치 상수 검증."""

    def test_weight_sum_1(self):
        total = sum(v['weight'] for v in DISCLOSURE_RISK_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_4_components(self):
        assert len(DISCLOSURE_RISK_WEIGHTS) == 4

    def test_component_keys(self):
        expected = {'event_severity', 'frequency', 'stake_change', 'governance'}
        assert set(DISCLOSURE_RISK_WEIGHTS.keys()) == expected

    def test_4_grades(self):
        assert len(DISCLOSURE_RISK_GRADES) == 4

    def test_grade_keys(self):
        expected = {'NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL'}
        assert set(DISCLOSURE_RISK_GRADES.keys()) == expected


class TestStakeConstants:
    """지분 변동 상수 검증."""

    def test_stake_config(self):
        assert STAKE_CHANGE_CONFIG['major_threshold'] == 0.05
        assert STAKE_CHANGE_CONFIG['significant_change'] == 0.01
        assert STAKE_CHANGE_CONFIG['accumulation_days'] == 5
        assert STAKE_CHANGE_CONFIG['disposal_days'] == 5

    def test_5_signals(self):
        assert len(STAKE_SIGNALS) == 5

    def test_signal_keys(self):
        expected = {'ACCUMULATION', 'DISPOSAL', 'TREASURY_BUY', 'TREASURY_SELL', 'NEUTRAL'}
        assert set(STAKE_SIGNALS.keys()) == expected

    def test_4_insider_types(self):
        assert len(INSIDER_TYPES) == 4
        assert 'ceo' in INSIDER_TYPES
        assert 'executive' in INSIDER_TYPES


# ════════════════════════════════════════
# disclosure_classifier
# ════════════════════════════════════════

class TestClassifyDisclosure:
    """classify_disclosure 테스트."""

    def test_empty_title(self):
        result = classify_disclosure('')
        assert result['type'] == 'OTHER'

    def test_none_title(self):
        result = classify_disclosure(None)
        assert result['type'] == 'OTHER'

    def test_earnings_by_keyword(self):
        result = classify_disclosure('삼성전자 사업보고서 (2025.12)')
        assert result['type'] == 'EARNINGS'
        assert '사업보고서' in result['keywords_matched']

    def test_earnings_by_report_code(self):
        result = classify_disclosure('일반 공시 제목', report_code='A001')
        assert result['type'] == 'EARNINGS'
        assert 'A001' in result['keywords_matched']

    def test_dividend_keyword(self):
        result = classify_disclosure('현금배당 결정')
        assert result['type'] == 'DIVIDEND'

    def test_capital_keyword(self):
        result = classify_disclosure('유상증자 결정')
        assert result['type'] == 'CAPITAL'
        assert result['subtype'] == 'rights_offering'

    def test_ma_keyword(self):
        result = classify_disclosure('합병 결의')
        assert result['type'] == 'MA'
        assert result['subtype'] == 'merger'

    def test_governance_keyword(self):
        result = classify_disclosure('대표이사 변경')
        assert result['type'] == 'GOVERNANCE'
        assert result['subtype'] == 'ceo_change'

    def test_stake_keyword(self):
        result = classify_disclosure('대량보유 상황보고서')
        assert result['type'] == 'STAKE'
        assert result['subtype'] == 'major_holder'

    def test_legal_keyword(self):
        result = classify_disclosure('소송 제기')
        assert result['type'] == 'LEGAL'
        assert result['subtype'] == 'lawsuit'

    def test_ipo_keyword(self):
        result = classify_disclosure('상장폐지 결정')
        assert result['type'] == 'IPO'
        assert result['subtype'] == 'delisting'

    def test_regulation_keyword(self):
        result = classify_disclosure('관리종목 지정')
        assert result['type'] == 'REGULATION'
        assert result['subtype'] == 'management_issue'

    def test_other_keyword(self):
        result = classify_disclosure('대규모 수주 공시')
        assert result['type'] == 'OTHER'
        assert result['subtype'] == 'contract'

    def test_report_code_priority(self):
        """리포트 코드가 키워드보다 우선."""
        result = classify_disclosure('대량보유 사업보고서', report_code='A001')
        assert result['type'] == 'EARNINGS'

    def test_best_match_multiple_keywords(self):
        """키워드 매칭 수가 많은 유형 선택."""
        result = classify_disclosure('유상증자 및 전환사채 CB 발행')
        assert result['type'] == 'CAPITAL'

    def test_subtype_detection_preliminary(self):
        result = classify_disclosure('잠정실적 공시')
        assert result['type'] == 'EARNINGS'
        assert result['subtype'] == 'preliminary'


class TestClassifyBatch:
    """classify_batch 테스트."""

    def test_empty_list(self):
        assert classify_batch([]) == []

    def test_batch_classification(self):
        disclosures = [
            {'title': '사업보고서', 'report_code': 'A001', 'corp_name': '삼성전자'},
            {'title': '대표이사 변경', 'corp_name': 'LG화학'},
            {'title': '합병 결의', 'corp_name': 'SK하이닉스'},
        ]
        results = classify_batch(disclosures)
        assert len(results) == 3
        assert results[0]['type'] == 'EARNINGS'
        assert results[1]['type'] == 'GOVERNANCE'
        assert results[2]['type'] == 'MA'

    def test_batch_preserves_original(self):
        disclosures = [{'title': '배당 결정', 'corp_name': 'Test', 'date': '2025-01-01'}]
        results = classify_batch(disclosures)
        assert results[0]['corp_name'] == 'Test'
        assert results[0]['date'] == '2025-01-01'


# ════════════════════════════════════════
# event_impact_scorer
# ════════════════════════════════════════

class TestScoreEventImpact:
    """score_event_impact 테스트."""

    def test_critical_event(self):
        result = score_event_impact('IPO', 'delisting')
        assert result['level'] == 5
        assert result['label'] == 'Critical'

    def test_high_event(self):
        result = score_event_impact('MA', 'merger')
        assert result['level'] == 4
        assert result['label'] == 'High'

    def test_medium_event(self):
        result = score_event_impact('EARNINGS', 'preliminary')
        assert result['level'] == 3
        assert result['label'] == 'Medium'

    def test_low_event(self):
        result = score_event_impact('STAKE', 'treasury_stock')
        assert result['level'] == 2
        assert result['label'] == 'Low'

    def test_info_event(self):
        result = score_event_impact('EARNINGS', 'guidance')
        assert result['level'] == 1
        assert result['label'] == 'Info'

    def test_unknown_subtype(self):
        result = score_event_impact('OTHER', 'unknown_subtype')
        assert result['level'] == 1

    def test_none_subtype(self):
        result = score_event_impact('OTHER', None)
        assert result['level'] == 1

    def test_large_cap_adjustment(self):
        result = score_event_impact('MA', 'merger', market_cap=15_000_000_000_000)
        assert result['adjusted_level'] == 4.0  # 4 * 1.0

    def test_mid_cap_adjustment(self):
        result = score_event_impact('MA', 'merger', market_cap=5_000_000_000_000)
        assert result['adjusted_level'] == 3.2  # 4 * 0.8

    def test_small_cap_adjustment(self):
        result = score_event_impact('MA', 'merger', market_cap=500_000_000_000)
        assert result['adjusted_level'] == 2.4  # 4 * 0.6

    def test_after_hours_adjustment(self):
        result = score_event_impact('MA', 'merger', timing='after_hours')
        assert result['adjusted_level'] == 4.8  # 4 * 1.2

    def test_combined_adjustments(self):
        """시총 + 장후 공시 복합 보정."""
        result = score_event_impact(
            'MA', 'merger',
            market_cap=500_000_000_000,  # small → 0.6
            timing='after_hours',         # 1.2
        )
        # 4 * 0.6 * 1.2 = 2.88 → round → 2.9
        assert result['adjusted_level'] == 2.9

    def test_score_range(self):
        result = score_event_impact('IPO', 'delisting')
        assert 0 <= result['score'] <= 100


class TestDetectFrequencyAnomaly:
    """detect_frequency_anomaly 테스트."""

    def test_empty_disclosures(self):
        result = detect_frequency_anomaly([])
        assert result['total_count'] == 0
        assert result['is_anomaly'] is False

    def test_normal_frequency(self):
        disclosures = [{'title': f'공시 {i}'} for i in range(30)]
        result = detect_frequency_anomaly(disclosures, lookback_days=30)
        assert result['daily_avg'] == 1.0
        assert result['is_anomaly'] is False

    def test_elevated_frequency(self):
        disclosures = [{'title': f'공시 {i}'} for i in range(180)]
        result = detect_frequency_anomaly(disclosures, lookback_days=30)
        assert result['daily_avg'] == 6.0
        assert result['is_anomaly'] is False
        assert result['anomaly_score'] > 50

    def test_anomaly_frequency(self):
        disclosures = [{'title': f'공시 {i}'} for i in range(300)]
        result = detect_frequency_anomaly(disclosures, lookback_days=30)
        assert result['daily_avg'] == 10.0
        assert result['is_anomaly'] is True
        assert result['anomaly_score'] == 90

    def test_corp_code_filter(self):
        disclosures = [
            {'title': '공시1', 'corp_code': 'AAA'},
            {'title': '공시2', 'corp_code': 'BBB'},
            {'title': '공시3', 'corp_code': 'AAA'},
        ]
        result = detect_frequency_anomaly(disclosures, corp_code='AAA', lookback_days=30)
        assert result['total_count'] == 2

    def test_below_normal(self):
        disclosures = [{'title': '공시1'}]
        result = detect_frequency_anomaly(disclosures, lookback_days=30)
        assert result['anomaly_score'] == 5


class TestCalcDisclosureRiskScore:
    """calc_disclosure_risk_score 테스트."""

    def test_low_risk(self):
        events = [{'level': 1, 'score': 20}]
        result = calc_disclosure_risk_score(events)
        assert result['grade'] == 'NORMAL'
        assert result['score'] < 25

    def test_high_risk(self):
        events = [{'level': 5, 'score': 100}]
        governance = [{'subtype': 'ceo_change'}, {'subtype': 'ceo_change'}]
        freq_data = {'anomaly_score': 90}
        stake_data = {'signal': 'DISPOSAL'}
        result = calc_disclosure_risk_score(
            events,
            stake_data=stake_data,
            governance_data=governance,
            frequency_data=freq_data,
        )
        assert result['score'] > 50

    def test_components_present(self):
        events = [{'level': 3}]
        result = calc_disclosure_risk_score(events)
        assert 'components' in result
        comps = result['components']
        assert 'event_severity' in comps
        assert 'frequency' in comps
        assert 'stake_change' in comps
        assert 'governance' in comps

    def test_accumulation_lowers_risk(self):
        events = [{'level': 3}]
        result_neutral = calc_disclosure_risk_score(events)
        result_accum = calc_disclosure_risk_score(
            events, stake_data={'signal': 'ACCUMULATION'},
        )
        assert result_accum['score'] <= result_neutral['score']

    def test_disposal_raises_risk(self):
        events = [{'level': 3}]
        result_neutral = calc_disclosure_risk_score(events)
        result_disposal = calc_disclosure_risk_score(
            events, stake_data={'signal': 'DISPOSAL'},
        )
        assert result_disposal['score'] > result_neutral['score']

    def test_score_range(self):
        events = [{'level': 1}]
        result = calc_disclosure_risk_score(events)
        assert 0 <= result['score'] <= 100

    def test_empty_events(self):
        result = calc_disclosure_risk_score([])
        assert result['score'] >= 0

    def test_ceo_change_governance_risk(self):
        events = [{'level': 3}]
        gov_none = calc_disclosure_risk_score(events)
        gov_ceo = calc_disclosure_risk_score(
            events, governance_data=[{'subtype': 'ceo_change'}],
        )
        assert gov_ceo['score'] > gov_none['score']


# ════════════════════════════════════════
# stake_change_tracker
# ════════════════════════════════════════

class TestTrackStakeChanges:
    """track_stake_changes 테스트."""

    def test_empty_data(self):
        result = track_stake_changes([])
        assert result['signal'] == 'NEUTRAL'
        assert result['pattern'] is None

    def test_none_data(self):
        result = track_stake_changes(None)
        assert result['signal'] == 'NEUTRAL'

    def test_accumulation_pattern(self):
        """5건 이상 매수 → ACCUMULATION."""
        data = [
            {'holder': f'투자자{i}', 'change_pct': 0.02}
            for i in range(6)
        ]
        result = track_stake_changes(data)
        assert result['signal'] == 'ACCUMULATION'
        assert result['pattern'] == 'consecutive_buying'

    def test_disposal_pattern(self):
        """5건 이상 매도 → DISPOSAL."""
        data = [
            {'holder': f'투자자{i}', 'change_pct': -0.02}
            for i in range(6)
        ]
        result = track_stake_changes(data)
        assert result['signal'] == 'DISPOSAL'
        assert result['pattern'] == 'consecutive_selling'

    def test_net_buying_pattern(self):
        """매수 > 매도 (2건+) → ACCUMULATION net_buying."""
        data = [
            {'holder': 'A', 'change_pct': 0.02},
            {'holder': 'B', 'change_pct': 0.03},
            {'holder': 'C', 'change_pct': -0.015},
        ]
        result = track_stake_changes(data)
        assert result['signal'] == 'ACCUMULATION'
        assert result['pattern'] == 'net_buying'

    def test_net_selling_pattern(self):
        """매도 > 매수 (2건+) → DISPOSAL net_selling."""
        data = [
            {'holder': 'A', 'change_pct': -0.02},
            {'holder': 'B', 'change_pct': -0.03},
            {'holder': 'C', 'change_pct': 0.015},
        ]
        result = track_stake_changes(data)
        assert result['signal'] == 'DISPOSAL'
        assert result['pattern'] == 'net_selling'

    def test_insignificant_changes(self):
        """1%p 미만 변동 → NEUTRAL."""
        data = [
            {'holder': 'A', 'change_pct': 0.005},
            {'holder': 'B', 'change_pct': -0.003},
        ]
        result = track_stake_changes(data)
        assert result['signal'] == 'NEUTRAL'
        assert len(result['significant_changes']) == 0

    def test_before_after_calculation(self):
        """change_pct 없으면 before/after로 계산."""
        data = [
            {'holder': 'A', 'change_pct': None, 'before_pct': 0.05, 'after_pct': 0.08},
            {'holder': 'B', 'change_pct': None, 'before_pct': 0.05, 'after_pct': 0.07},
        ]
        result = track_stake_changes(data)
        assert len(result['significant_changes']) == 2

    def test_significant_changes_list(self):
        data = [
            {'holder': 'A', 'change_pct': 0.05},
            {'holder': 'B', 'change_pct': 0.001},  # insignificant
        ]
        result = track_stake_changes(data)
        assert len(result['significant_changes']) == 1


class TestTrackInsiderTrades:
    """track_insider_trades 테스트."""

    def test_empty_data(self):
        result = track_insider_trades([])
        assert result['signal'] == 'NEUTRAL'
        assert result['net_direction'] == 'none'

    def test_buy_signal(self):
        trades = [
            {'name': f'임원{i}', 'type': 'buy', 'amount': 100_000_000}
            for i in range(4)
        ]
        result = track_insider_trades(trades)
        assert result['signal'] == 'ACCUMULATION'
        assert result['net_direction'] == 'buy'
        assert result['summary']['buy_count'] == 4

    def test_sell_signal(self):
        trades = [
            {'name': f'임원{i}', 'type': 'sell', 'amount': 100_000_000}
            for i in range(4)
        ]
        result = track_insider_trades(trades)
        assert result['signal'] == 'DISPOSAL'
        assert result['net_direction'] == 'sell'

    def test_korean_type_매수(self):
        trades = [
            {'name': '대표이사', 'type': '매수', 'amount': 500_000_000},
            {'name': '부사장', 'type': '매수', 'amount': 300_000_000},
            {'name': '전무', 'type': '매수', 'amount': 200_000_000},
        ]
        result = track_insider_trades(trades)
        assert result['signal'] == 'ACCUMULATION'
        assert result['summary']['buy_count'] == 3

    def test_korean_type_매도(self):
        trades = [
            {'name': '임원A', 'type': '매도', 'amount': 500_000_000},
            {'name': '임원B', 'type': '매도', 'amount': 300_000_000},
            {'name': '임원C', 'type': '매도', 'amount': 200_000_000},
        ]
        result = track_insider_trades(trades)
        assert result['signal'] == 'DISPOSAL'

    def test_net_amount_calculation(self):
        trades = [
            {'name': 'A', 'type': 'buy', 'amount': 1_000_000},
            {'name': 'B', 'type': 'sell', 'amount': 300_000},
        ]
        result = track_insider_trades(trades)
        assert result['summary']['net_amount'] == 700_000

    def test_neutral_mixed(self):
        """매수/매도 혼재 (3건 미만) → NEUTRAL."""
        trades = [
            {'name': 'A', 'type': 'buy', 'amount': 100_000},
            {'name': 'B', 'type': 'sell', 'amount': 200_000},
        ]
        result = track_insider_trades(trades)
        assert result['signal'] == 'NEUTRAL'


class TestTrackTreasuryStock:
    """track_treasury_stock 테스트."""

    def test_empty_data(self):
        result = track_treasury_stock([])
        assert result['signal'] == 'NEUTRAL'
        assert result['total_buy'] == 0
        assert result['total_sell'] == 0

    def test_buy_signal(self):
        data = [{'type': 'buy', 'shares': 100_000}]
        result = track_treasury_stock(data)
        assert result['signal'] == 'TREASURY_BUY'
        assert result['total_buy'] == 100_000

    def test_sell_signal(self):
        data = [{'type': 'sell', 'shares': 50_000}]
        result = track_treasury_stock(data)
        assert result['signal'] == 'TREASURY_SELL'
        assert result['total_sell'] == 50_000

    def test_korean_type_취득(self):
        data = [{'type': '취득', 'shares': 200_000}]
        result = track_treasury_stock(data)
        assert result['signal'] == 'TREASURY_BUY'

    def test_korean_type_처분(self):
        data = [{'type': '처분', 'shares': 150_000}]
        result = track_treasury_stock(data)
        assert result['signal'] == 'TREASURY_SELL'

    def test_net_buy_signal(self):
        data = [
            {'type': 'buy', 'shares': 100_000},
            {'type': 'sell', 'shares': 30_000},
        ]
        result = track_treasury_stock(data)
        assert result['signal'] == 'TREASURY_BUY'

    def test_equal_amounts_neutral(self):
        data = [
            {'type': 'buy', 'shares': 50_000},
            {'type': 'sell', 'shares': 50_000},
        ]
        result = track_treasury_stock(data)
        assert result['signal'] == 'NEUTRAL'


# ════════════════════════════════════════
# report_generator
# ════════════════════════════════════════

class TestGenerateDisclosureReport:
    """generate_disclosure_report 테스트."""

    def test_basic_report(self):
        classifications = [
            {'type': 'EARNINGS', 'label': '실적 공시'},
            {'type': 'DIVIDEND', 'label': '배당 관련'},
        ]
        report = generate_disclosure_report(classifications)
        assert '# DART 공시 분석 리포트' in report
        assert '총 2건' in report

    def test_high_impact_section(self):
        classifications = [{'type': 'EARNINGS'}]
        impacts = [
            {'level': 5, 'label': 'Critical', 'korean': '매우 심각', 'action': '즉시 확인'},
        ]
        report = generate_disclosure_report(classifications, impacts=impacts)
        assert '주요 이벤트' in report
        assert 'Critical' in report

    def test_low_impact_not_shown(self):
        classifications = [{'type': 'OTHER'}]
        impacts = [
            {'level': 1, 'label': 'Info', 'korean': '정보', 'action': '기록'},
        ]
        report = generate_disclosure_report(classifications, impacts=impacts)
        assert '주요 이벤트' not in report

    def test_stake_changes_section(self):
        classifications = [{'type': 'STAKE'}]
        stake = {
            'signal': 'ACCUMULATION',
            'significant_changes': [
                {'holder': 'NPS', 'change_pct': 0.02},
            ],
        }
        report = generate_disclosure_report(classifications, stake_changes=stake)
        assert '지분 변동' in report
        assert 'ACCUMULATION' in report

    def test_risk_score_section(self):
        classifications = [{'type': 'EARNINGS'}]
        risk = {
            'grade': 'WARNING',
            'score': 65.0,
            'components': {
                'event_severity': {'score': 70, 'weight': 0.35},
                'frequency': {'score': 50, 'weight': 0.20},
                'stake_change': {'score': 60, 'weight': 0.25},
                'governance': {'score': 70, 'weight': 0.20},
            },
        }
        report = generate_disclosure_report(classifications, risk_score=risk)
        assert '리스크 등급' in report
        assert 'WARNING' in report

    def test_empty_classifications(self):
        report = generate_disclosure_report([])
        assert '총 0건' in report
