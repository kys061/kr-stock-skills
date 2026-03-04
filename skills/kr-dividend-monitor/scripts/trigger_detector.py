"""kr-dividend-monitor: T1-T5 트리거 감지 엔진.

DART 공시 기반 5대 강제 리뷰 트리거를 감지하고 상태 전이를 관리한다.
"""

# ─── 트리거 정의 ───

REVIEW_TRIGGERS = {
    'T1_DIVIDEND_CUT': {
        'name': '감배 감지',
        'source': 'DART',
        'severity': 'CRITICAL',
        'description': '전년 대비 주당배당금 감소',
        'action': 'REVIEW',
    },
    'T2_DIVIDEND_SUSPENSION': {
        'name': '무배당 전환',
        'source': 'DART',
        'severity': 'CRITICAL',
        'description': '배당 결의 없음 or 무배당 공시',
        'action': 'EXIT_REVIEW',
    },
    'T3_EARNINGS_DETERIORATION': {
        'name': '실적 악화',
        'source': 'DART',
        'severity': 'HIGH',
        'description': '영업이익 적자 전환 or 50% 이상 급감',
        'thresholds': {
            'earnings_decline_pct': -0.50,
            'operating_loss': True,
            'consecutive_decline': 2,
        },
    },
    'T4_PAYOUT_DANGER': {
        'name': '배당성향 위험',
        'source': 'calculated',
        'severity': 'HIGH',
        'threshold': 1.00,
        'action': 'WARN',
    },
    'T5_GOVERNANCE_ISSUE': {
        'name': '지배구조 이슈',
        'source': 'DART',
        'severity': 'MEDIUM',
        'subtypes': [
            'major_shareholder_sale',
            'management_dispute',
            'audit_qualified',
            'delisting_risk',
        ],
    },
}

# ─── 상태 정의 ───

MONITOR_STATES = ['OK', 'WARN', 'REVIEW', 'EXIT_REVIEW']

# ─── 상태 전이 규칙 ───

STATE_TRANSITIONS = {
    'OK': {
        'T3_minor': 'WARN',
        'T4': 'WARN',
        'T5': 'WARN',
        'T1': 'REVIEW',
        'T3_major': 'REVIEW',
        'T2': 'EXIT_REVIEW',
    },
    'WARN': {
        'resolved': 'OK',
        'T1': 'REVIEW',
        'T3_major': 'REVIEW',
        'T2': 'EXIT_REVIEW',
    },
    'REVIEW': {
        'resolved': 'OK',
        'maintained': 'WARN',
        'T2': 'EXIT_REVIEW',
    },
    'EXIT_REVIEW': {
        'recovered': 'REVIEW',
        'confirmed': 'EXIT',
    },
}

# ─── DART 공시 모니터링 대상 ───

DART_MONITORING = {
    'dividend_disclosure': {
        'kind': 'B',
        'keywords': ['배당', '주당배당금', '현금배당'],
        'check_frequency': 'quarterly',
    },
    'earnings_report': {
        'kind': 'A',
        'report_types': ['11013', '11012', '11014', '11011'],
        'check_frequency': 'quarterly',
    },
    'major_shareholder': {
        'kind': 'D',
        'keywords': ['대량보유', '임원', '주요주주'],
        'check_frequency': 'weekly',
    },
    'audit_report': {
        'kind': 'A',
        'keywords': ['감사의견', '적정', '한정', '부적정'],
        'check_frequency': 'annually',
    },
}


def detect_dividend_cut(current_dps: float, prev_dps: float) -> dict:
    """T1: 감배 감지.

    Returns:
        {'detected': bool, 'trigger': str, 'severity': str, 'detail': str}
    """
    if prev_dps > 0 and current_dps < prev_dps:
        cut_pct = (current_dps - prev_dps) / prev_dps
        return {
            'detected': True,
            'trigger': 'T1_DIVIDEND_CUT',
            'severity': REVIEW_TRIGGERS['T1_DIVIDEND_CUT']['severity'],
            'detail': f"DPS {prev_dps:,.0f} → {current_dps:,.0f} ({cut_pct:.1%})",
        }
    return {'detected': False, 'trigger': 'T1_DIVIDEND_CUT', 'severity': None, 'detail': ''}


def detect_dividend_suspension(current_dps: float, prev_dps: float) -> dict:
    """T2: 무배당 전환 감지."""
    if current_dps == 0 and prev_dps > 0:
        return {
            'detected': True,
            'trigger': 'T2_DIVIDEND_SUSPENSION',
            'severity': REVIEW_TRIGGERS['T2_DIVIDEND_SUSPENSION']['severity'],
            'detail': f"무배당 전환 (전년 DPS: {prev_dps:,.0f})",
        }
    return {'detected': False, 'trigger': 'T2_DIVIDEND_SUSPENSION', 'severity': None, 'detail': ''}


def detect_earnings_deterioration(current_op: float, prev_op: float,
                                   quarters: list = None) -> dict:
    """T3: 실적 악화 감지.

    Args:
        current_op: 현재 영업이익
        prev_op: 전년 동기 영업이익
        quarters: 최근 분기 영업이익 리스트

    Returns:
        {'detected': bool, 'trigger': str, 'severity': str,
         'detail': str, 'sub_type': str}
    """
    thresholds = REVIEW_TRIGGERS['T3_EARNINGS_DETERIORATION']['thresholds']

    # 영업적자 전환
    if current_op <= 0 and prev_op > 0:
        return {
            'detected': True,
            'trigger': 'T3_EARNINGS_DETERIORATION',
            'severity': 'HIGH',
            'detail': f"영업적자 전환 ({prev_op:,.0f} → {current_op:,.0f})",
            'sub_type': 'T3_major',
        }

    # 50% 이상 급감
    if prev_op > 0:
        decline = (current_op - prev_op) / prev_op
        if decline <= thresholds['earnings_decline_pct']:
            return {
                'detected': True,
                'trigger': 'T3_EARNINGS_DETERIORATION',
                'severity': 'HIGH',
                'detail': f"영업이익 {decline:.1%} 급감",
                'sub_type': 'T3_major',
            }

    # 연속 감소
    if quarters and len(quarters) >= thresholds['consecutive_decline']:
        recent = quarters[-thresholds['consecutive_decline']:]
        if all(q < 0 for q in recent):
            return {
                'detected': True,
                'trigger': 'T3_EARNINGS_DETERIORATION',
                'severity': 'HIGH',
                'detail': f"{len(recent)}분기 연속 적자",
                'sub_type': 'T3_major',
            }

    # 소폭 악화
    if prev_op > 0 and current_op < prev_op:
        decline = (current_op - prev_op) / prev_op
        if decline < 0:
            return {
                'detected': True,
                'trigger': 'T3_EARNINGS_DETERIORATION',
                'severity': 'MEDIUM',
                'detail': f"영업이익 {decline:.1%} 감소",
                'sub_type': 'T3_minor',
            }

    return {'detected': False, 'trigger': 'T3_EARNINGS_DETERIORATION',
            'severity': None, 'detail': '', 'sub_type': None}


def detect_payout_danger(payout_ratio: float) -> dict:
    """T4: 배당성향 위험 감지."""
    threshold = REVIEW_TRIGGERS['T4_PAYOUT_DANGER']['threshold']
    if payout_ratio > threshold:
        return {
            'detected': True,
            'trigger': 'T4_PAYOUT_DANGER',
            'severity': REVIEW_TRIGGERS['T4_PAYOUT_DANGER']['severity'],
            'detail': f"배당성향 {payout_ratio:.0%} > {threshold:.0%}",
        }
    return {'detected': False, 'trigger': 'T4_PAYOUT_DANGER', 'severity': None, 'detail': ''}


def detect_governance_issue(issue_type: str = None,
                             has_issue: bool = False) -> dict:
    """T5: 지배구조 이슈 감지.

    Args:
        issue_type: 이슈 유형 (major_shareholder_sale, management_dispute, etc.)
        has_issue: 이슈 존재 여부
    """
    valid_types = REVIEW_TRIGGERS['T5_GOVERNANCE_ISSUE']['subtypes']
    if has_issue and issue_type in valid_types:
        return {
            'detected': True,
            'trigger': 'T5_GOVERNANCE_ISSUE',
            'severity': REVIEW_TRIGGERS['T5_GOVERNANCE_ISSUE']['severity'],
            'detail': f"지배구조 이슈: {issue_type}",
        }
    return {'detected': False, 'trigger': 'T5_GOVERNANCE_ISSUE', 'severity': None, 'detail': ''}


def run_all_triggers(data: dict) -> list:
    """전체 트리거 실행.

    Args:
        data: {
            'current_dps': float, 'prev_dps': float,
            'current_op': float, 'prev_op': float,
            'op_quarters': list,
            'payout_ratio': float,
            'governance_issue_type': str, 'has_governance_issue': bool,
        }

    Returns:
        [{'detected': bool, 'trigger': str, ...}, ...] (감지된 것만)
    """
    results = []

    t1 = detect_dividend_cut(
        data.get('current_dps', 0), data.get('prev_dps', 0))
    if t1['detected']:
        results.append(t1)

    t2 = detect_dividend_suspension(
        data.get('current_dps', 0), data.get('prev_dps', 0))
    if t2['detected']:
        results.append(t2)

    t3 = detect_earnings_deterioration(
        data.get('current_op', 0), data.get('prev_op', 0),
        data.get('op_quarters'))
    if t3['detected']:
        results.append(t3)

    t4 = detect_payout_danger(data.get('payout_ratio', 0))
    if t4['detected']:
        results.append(t4)

    t5 = detect_governance_issue(
        data.get('governance_issue_type'),
        data.get('has_governance_issue', False))
    if t5['detected']:
        results.append(t5)

    return results


def determine_state(current_state: str, triggers: list) -> str:
    """트리거 기반 상태 전이.

    Args:
        current_state: 현재 상태 (OK, WARN, REVIEW, EXIT_REVIEW)
        triggers: run_all_triggers() 결과

    Returns:
        새 상태
    """
    if current_state not in STATE_TRANSITIONS:
        return current_state

    transitions = STATE_TRANSITIONS[current_state]

    if not triggers:
        if current_state in ('WARN', 'REVIEW'):
            return transitions.get('resolved', current_state)
        return current_state

    # 가장 심각한 트리거 우선
    for t in triggers:
        trigger_id = t.get('trigger', '')
        sub_type = t.get('sub_type')

        if 'T2' in trigger_id and 'T2' in transitions:
            return transitions['T2']

    for t in triggers:
        trigger_id = t.get('trigger', '')
        sub_type = t.get('sub_type')

        if 'T1' in trigger_id and 'T1' in transitions:
            return transitions['T1']
        if sub_type == 'T3_major' and 'T3_major' in transitions:
            return transitions['T3_major']

    for t in triggers:
        trigger_id = t.get('trigger', '')
        sub_type = t.get('sub_type')

        if sub_type == 'T3_minor' and 'T3_minor' in transitions:
            return transitions['T3_minor']
        if 'T4' in trigger_id and 'T4' in transitions:
            return transitions['T4']
        if 'T5' in trigger_id and 'T5' in transitions:
            return transitions['T5']

    return current_state
