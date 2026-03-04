"""kr-weekly-strategy: 주간 전략 통합."""


# ─── 주간 전략 섹션 ───

WEEKLY_SECTIONS = [
    'market_summary',
    'this_week_action',
    'scenario_plans',
    'sector_strategy',
    'risk_management',
    'operation_guide',
]


def generate_scenarios(market_phase, macro_data=None):
    """시나리오별 계획 생성.

    Args:
        market_phase: str, 'RISK_ON'/'BASE'/'CAUTION'/'STRESS'.
        macro_data: dict with optional context (e.g., bok_decision, events).

    Returns:
        dict: {base, bull, bear} with probability and actions.
    """
    if macro_data is None:
        macro_data = {}

    scenarios = {
        'RISK_ON': {
            'base': {
                'probability': 50,
                'description': '상승 추세 지속',
                'actions': ['비중 유지', '이익 실현 일부', '신규 진입 탐색'],
            },
            'bull': {
                'probability': 30,
                'description': '강한 상승 가속',
                'actions': ['비중 확대', '모멘텀 종목 추가', '현금 최소화'],
            },
            'bear': {
                'probability': 20,
                'description': '단기 조정',
                'actions': ['부분 이익 실현', '지지선 확인', '추가 매수 대기'],
            },
        },
        'BASE': {
            'base': {
                'probability': 50,
                'description': '횡보 지속',
                'actions': ['현재 비중 유지', '종목 교체 검토', '배당주 관심'],
            },
            'bull': {
                'probability': 25,
                'description': '상승 전환',
                'actions': ['비중 소폭 확대', '성장주 편입', '현금 일부 투입'],
            },
            'bear': {
                'probability': 25,
                'description': '하락 전환',
                'actions': ['비중 축소', '방어주 전환', '현금 확보'],
            },
        },
        'CAUTION': {
            'base': {
                'probability': 40,
                'description': '약세 횡보',
                'actions': ['방어적 유지', '손절 기준 점검', '현금 비중 확대'],
            },
            'bull': {
                'probability': 20,
                'description': '반등 시도',
                'actions': ['소량 매수 테스트', 'FTD 확인 후 대응', '핵심 종목만 유지'],
            },
            'bear': {
                'probability': 40,
                'description': '추가 하락',
                'actions': ['비중 대폭 축소', '손절 실행', '현금 비중 50%+'],
            },
        },
        'STRESS': {
            'base': {
                'probability': 40,
                'description': '약세 지속',
                'actions': ['최소 비중 유지', '반등 모니터링', '현금 극대화'],
            },
            'bull': {
                'probability': 15,
                'description': '바닥 확인',
                'actions': ['FTD 확인 시 소량 진입', '핵심 종목 저가 매수', '단계적 비중 확대'],
            },
            'bear': {
                'probability': 45,
                'description': '급락 계속',
                'actions': ['전량 현금화 고려', '헤지 포지션', '관망'],
            },
        },
    }

    return scenarios.get(market_phase, scenarios['BASE'])


def generate_weekly_plan(environment, sectors, scenarios):
    """주간 전략 통합.

    Args:
        environment: dict from classify_market_phase().
        sectors: dict from recommend_sector_allocation().
        scenarios: dict from generate_scenarios().

    Returns:
        dict: {summary, action, scenarios, sectors, risks, guide}
    """
    phase = environment.get('phase', 'BASE')
    eq_target = environment.get('equity_target', (60, 80))

    # 시장 요약 (3줄)
    summary = [
        f'시장 상태: {phase} ({environment.get("description", "")})',
        f'환경 점수: {environment.get("score", 50):.1f}/100',
        f'주식 목표 비중: {eq_target[0]}-{eq_target[1]}%',
    ]

    # 이번 주 액션
    base_scenario = scenarios.get('base', {})
    action = base_scenario.get('actions', ['현재 비중 유지'])

    # 상위 섹터 추출
    allocations = sectors.get('allocations', {})
    top_sectors = sorted(
        [(s, a) for s, a in allocations.items() if a > 0],
        key=lambda x: x[1], reverse=True,
    )[:5]

    # 리스크 관리
    risks = _generate_risk_items(phase, environment)

    # 운용 가이드
    guide = _generate_operation_guide(phase)

    return {
        'summary': summary,
        'action': action,
        'scenarios': scenarios,
        'sectors': {
            'top': top_sectors,
            'allocations': allocations,
            'changes': sectors.get('changes', {}),
        },
        'risks': risks,
        'guide': guide,
    }


def _generate_risk_items(phase, environment):
    """리스크 관리 항목 생성."""
    items = []

    if phase in ('CAUTION', 'STRESS'):
        items.append({
            'type': 'stop_loss',
            'description': '손절 기준 확인 (개별 종목 -7%, 포트폴리오 -5%)',
            'priority': 'high',
        })
        items.append({
            'type': 'cash_management',
            'description': f'현금 비중 {environment.get("cash_target", (20, 35))[0]}% 이상 유지',
            'priority': 'high',
        })

    items.append({
        'type': 'position_size',
        'description': '단일 종목 비중 15% 초과 금지',
        'priority': 'medium',
    })
    items.append({
        'type': 'diversification',
        'description': '섹터 집중도 40% 초과 금지',
        'priority': 'medium',
    })

    return items


def _generate_operation_guide(phase):
    """겸업 투자자 운용 가이드."""
    guides = {
        'RISK_ON': {
            'frequency': '주 2-3회 체크',
            'actions': ['이익 실현 주문 설정', '추가 매수 지정가 입력'],
            'warnings': ['과도한 레버리지 주의', '수익에 취해 집중투자 금지'],
        },
        'BASE': {
            'frequency': '주 2회 체크',
            'actions': ['관망 위주', '배당주 적립식 매수'],
            'warnings': ['소음에 흔들리지 말 것', '무리한 매매 금지'],
        },
        'CAUTION': {
            'frequency': '매일 1회 체크',
            'actions': ['손절 주문 확인', '현금 비중 관리'],
            'warnings': ['물타기 금지', '감정적 매수 금지'],
        },
        'STRESS': {
            'frequency': '매일 1-2회 체크',
            'actions': ['포트폴리오 방어', 'FTD 모니터링'],
            'warnings': ['바닥 잡기 금지', '공포 매도 주의'],
        },
    }
    return guides.get(phase, guides['BASE'])
