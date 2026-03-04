"""kr-credit-monitor: 반대매매 리스크 분석."""

from .credit_balance_analyzer import (
    CREDIT_MARKET_RATIO_LEVELS,
    LEVERAGE_CYCLE_PHASES,
)


# ─── 반대매매 리스크 ───

MARGIN_CALL_CONFIG = {
    'maintenance_ratio': 1.40,      # 담보유지비율: 140%
    'initial_ratio': 2.00,          # 최초 담보비율: 200%
    'liquidation_delay_days': 2,    # D+2 반대매매
}

# 시장 하락 시나리오
FORCED_LIQUIDATION_SCENARIOS = [
    {'drop_pct': 0.10, 'label': '10% 하락', 'severity': 'mild'},
    {'drop_pct': 0.20, 'label': '20% 하락', 'severity': 'moderate'},
    {'drop_pct': 0.30, 'label': '30% 하락 (가격제한폭)', 'severity': 'severe'},
]

# 반대매매 영향도 기준
LIQUIDATION_IMPACT_LEVELS = {
    'negligible': 0.01,  # 시장 거래대금 대비 1% 미만
    'minor': 0.03,       # 3% 미만
    'significant': 0.05, # 5% 미만
    'major': 0.10,       # 10% 미만
    'critical': 0.10,    # 10% 이상 (연쇄 하락 가능)
}

# ─── 신용 리스크 스코어 ───

CREDIT_RISK_WEIGHTS = {
    'credit_level': {'weight': 0.30, 'label': '시총 대비 신용잔고 수준'},
    'growth_rate': {'weight': 0.25, 'label': '신용잔고 증가 속도'},
    'forced_liquidation': {'weight': 0.25, 'label': '반대매매 근접도'},
    'leverage_cycle': {'weight': 0.20, 'label': '사이클 위치'},
}
# 가중치 합계: 0.30 + 0.25 + 0.25 + 0.20 = 1.00

CREDIT_RISK_GRADES = {
    'SAFE': {'min_score': 0, 'max_score': 20, 'label': '안전'},
    'NORMAL': {'min_score': 20, 'max_score': 40, 'label': '보통'},
    'ELEVATED': {'min_score': 40, 'max_score': 60, 'label': '상승'},
    'HIGH': {'min_score': 60, 'max_score': 80, 'label': '높음'},
    'CRITICAL': {'min_score': 80, 'max_score': 100, 'label': '위험'},
}


def calc_margin_call_threshold(credit_amount, initial_ratio=None, maintenance_ratio=None):
    """담보부족 발생 가격 하락률 계산.

    Args:
        credit_amount: 신용융자 금액.
        initial_ratio: 최초 담보비율 (default: 2.00 = 200%).
        maintenance_ratio: 담보유지비율 (default: 1.40 = 140%).

    Returns:
        dict: {trigger_price_drop, buffer_pct}
    """
    if initial_ratio is None:
        initial_ratio = MARGIN_CALL_CONFIG['initial_ratio']
    if maintenance_ratio is None:
        maintenance_ratio = MARGIN_CALL_CONFIG['maintenance_ratio']

    if initial_ratio <= 0 or maintenance_ratio <= 0:
        return {'trigger_price_drop': 0.0, 'buffer_pct': 0.0}

    # 담보비율 = 평가금액 / 대출금
    # 200%일 때 평가금액 = 대출금 × 2 (자기자금 50% + 대출 50%)
    # 가격이 x% 하락하면: 평가금액 = 대출금 × 초기비율 × (1-x)
    # 담보유지비율 이하: 대출금 × 초기비율 × (1-x) / 대출금 ≤ 유지비율
    # 초기비율 × (1-x) ≤ 유지비율
    # (1-x) ≤ 유지비율 / 초기비율
    # x ≥ 1 - (유지비율 / 초기비율)

    trigger_drop = 1 - (maintenance_ratio / initial_ratio)
    buffer_pct = trigger_drop  # 현재 가격 기준 여유분

    return {
        'trigger_price_drop': round(trigger_drop, 4),
        'buffer_pct': round(buffer_pct, 4),
    }


def _classify_impact_level(impact_ratio):
    """반대매매 영향도 분류."""
    if impact_ratio >= LIQUIDATION_IMPACT_LEVELS['critical']:
        return 'critical'
    elif impact_ratio >= LIQUIDATION_IMPACT_LEVELS['major']:
        return 'major'
    elif impact_ratio >= LIQUIDATION_IMPACT_LEVELS['significant']:
        return 'significant'
    elif impact_ratio >= LIQUIDATION_IMPACT_LEVELS['minor']:
        return 'minor'
    return 'negligible'


def estimate_forced_liquidation(credit_data, daily_volume=None, scenarios=None):
    """시장 하락 시나리오별 반대매매 영향 추정.

    Args:
        credit_data: dict with {total, market_ratio} (analyze_credit_balance 결과).
        daily_volume: 일 평균 시장 거래대금 (원, optional).
        scenarios: list of dict (default: FORCED_LIQUIDATION_SCENARIOS).

    Returns:
        dict: {scenarios: [{drop_pct, affected_amount, market_impact, impact_level, severity}],
               worst_case}
    """
    if scenarios is None:
        scenarios = FORCED_LIQUIDATION_SCENARIOS

    total_credit = credit_data.get('total', 0)
    margin_info = calc_margin_call_threshold(total_credit)
    trigger_drop = margin_info['trigger_price_drop']

    results = []
    for scenario in scenarios:
        drop_pct = scenario['drop_pct']

        # 하락률이 담보부족 기준 초과 시 반대매매 발생
        if drop_pct >= trigger_drop:
            # 담보부족 비율 추정: 초과분에 비례
            excess = drop_pct - trigger_drop
            # 담보부족 비율 = excess / (1 - trigger_drop) (단순화)
            deficit_ratio = min(1.0, excess / (1 - trigger_drop)) if trigger_drop < 1 else 1.0
            affected_amount = round(total_credit * deficit_ratio)
        else:
            affected_amount = 0

        # 시장 영향도
        market_impact = 0.0
        impact_level = 'negligible'
        if daily_volume and daily_volume > 0 and affected_amount > 0:
            market_impact = round(affected_amount / daily_volume, 4)
            impact_level = _classify_impact_level(market_impact)

        results.append({
            'drop_pct': drop_pct,
            'label': scenario['label'],
            'severity': scenario['severity'],
            'affected_amount': affected_amount,
            'market_impact': market_impact,
            'impact_level': impact_level,
            'triggers_margin_call': drop_pct >= trigger_drop,
        })

    # 최악 시나리오
    worst = max(results, key=lambda r: r['affected_amount']) if results else None

    return {
        'trigger_price_drop': trigger_drop,
        'scenarios': results,
        'worst_case': worst,
    }


def _credit_level_to_risk(level):
    """시총 대비 비율 수준 → 리스크 점수."""
    scores = {
        'critical': 90,
        'high': 70,
        'elevated': 50,
        'normal': 30,
        'safe': 10,
    }
    return scores.get(level, 30)


def _growth_to_risk(growth):
    """성장률 → 리스크 점수."""
    yoy_level = growth.get('yoy_level', 'normal')
    mom_level = growth.get('mom_level', 'normal')

    level_scores = {'critical': 90, 'warning': 65, 'normal': 30}
    yoy_score = level_scores.get(yoy_level, 30)
    mom_score = level_scores.get(mom_level, 30)

    return round(yoy_score * 0.6 + mom_score * 0.4, 1)


def _liquidation_to_risk(liquidation_result):
    """반대매매 → 리스크 점수."""
    if not liquidation_result or not liquidation_result.get('scenarios'):
        return 20

    # 가장 현실적인 시나리오(-10%)의 margin call 여부
    scenarios = liquidation_result['scenarios']
    mild_scenario = scenarios[0] if scenarios else {}

    if mild_scenario.get('triggers_margin_call'):
        # -10%로도 반대매매 발동 → 높은 리스크
        impact = mild_scenario.get('impact_level', 'negligible')
        impact_scores = {'critical': 95, 'major': 80, 'significant': 65, 'minor': 50, 'negligible': 40}
        return impact_scores.get(impact, 40)

    # 발동 안 함 → trigger까지 거리 기반
    trigger = liquidation_result.get('trigger_price_drop', 0.3)
    if trigger <= 0.15:
        return 60  # 15% 하락이면 발동 → 높은 리스크
    elif trigger <= 0.25:
        return 35  # 25% 하락이면 발동 → 보통
    return 15  # 30%+ → 낮은 리스크


def _cycle_to_risk(cycle_phase):
    """사이클 → 리스크 점수."""
    phase_scores = {
        'PEAK': 85,
        'EXPANSION': 55,
        'CONTRACTION': 35,
        'TROUGH': 15,
    }
    return phase_scores.get(cycle_phase, 40)


def _classify_risk_grade(score):
    """리스크 점수 → 등급."""
    for grade, cfg in CREDIT_RISK_GRADES.items():
        if cfg['min_score'] <= score < cfg['max_score']:
            return grade
    if score >= 80:
        return 'CRITICAL'
    return 'SAFE'


def calc_credit_risk_score(balance_analysis, liquidation_risk=None):
    """신용 리스크 스코어 계산.

    Args:
        balance_analysis: analyze_credit_balance() 결과.
        liquidation_risk: estimate_forced_liquidation() 결과 (optional).

    Returns:
        dict: {score, grade, label, components}
    """
    # 신용잔고 수준
    credit_risk = _credit_level_to_risk(balance_analysis.get('market_ratio_level', 'safe'))

    # 성장률
    growth_risk = _growth_to_risk(balance_analysis.get('growth', {}))

    # 반대매매
    liquidation_score = _liquidation_to_risk(liquidation_risk)

    # 사이클
    cycle_risk = _cycle_to_risk(balance_analysis.get('cycle_phase', 'TROUGH'))

    # 가중 합산
    weights = CREDIT_RISK_WEIGHTS
    total = (
        credit_risk * weights['credit_level']['weight']
        + growth_risk * weights['growth_rate']['weight']
        + liquidation_score * weights['forced_liquidation']['weight']
        + cycle_risk * weights['leverage_cycle']['weight']
    )
    total = round(max(0, min(100, total)), 1)

    grade = _classify_risk_grade(total)
    label = CREDIT_RISK_GRADES[grade]['label']

    return {
        'score': total,
        'grade': grade,
        'label': label,
        'components': {
            'credit_level': {'score': credit_risk, 'weight': weights['credit_level']['weight']},
            'growth_rate': {'score': growth_risk, 'weight': weights['growth_rate']['weight']},
            'forced_liquidation': {'score': liquidation_score, 'weight': weights['forced_liquidation']['weight']},
            'leverage_cycle': {'score': cycle_risk, 'weight': weights['leverage_cycle']['weight']},
        },
    }
