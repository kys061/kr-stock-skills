"""kr-weekly-strategy: 시장 환경 분석."""


# ─── 시장 상태 ───

MARKET_PHASES = {
    'RISK_ON': {
        'description': '위험 선호 (강세장)',
        'equity_target': (80, 100),
        'cash_target': (0, 10),
    },
    'BASE': {
        'description': '보통 (횡보장)',
        'equity_target': (60, 80),
        'cash_target': (10, 20),
    },
    'CAUTION': {
        'description': '주의 (약세 전환 가능)',
        'equity_target': (40, 60),
        'cash_target': (20, 35),
    },
    'STRESS': {
        'description': '스트레스 (약세장)',
        'equity_target': (10, 40),
        'cash_target': (35, 60),
    },
}

# ─── 주간 체크리스트 ───

KR_WEEKLY_CHECKLIST = [
    'kospi_kosdaq_trend',
    'foreign_net_flow',
    'institutional_net_flow',
    'bok_rate_decision',
    'major_earnings',
    'dart_disclosures',
    'geopolitical_events',
    'usd_krw_trend',
]

# ─── 환경 판단 가중치 ───

ENVIRONMENT_WEIGHTS = {
    'kospi_trend': 0.25,
    'foreign_flow': 0.20,
    'macro_regime': 0.20,
    'usd_krw': 0.15,
    'breadth': 0.10,
    'volatility': 0.10,
}


def classify_market_phase(indicators):
    """시장 환경 분류.

    Args:
        indicators: dict with keys:
            kospi_trend: 'up'/'sideways'/'down'
            foreign_flow: 'buy'/'neutral'/'sell'
            macro_regime: 'expansion'/'transitional'/'contraction'
            usd_krw: 'stable'/'volatile'/'crisis'
            breadth_score: float (0-100)
            vix_kr: float (optional, KR VIX)

    Returns:
        dict: {phase, description, equity_target, cash_target, score}
    """
    score = 0

    # KOSPI 추세 (25%)
    trend = indicators.get('kospi_trend', 'sideways')
    trend_scores = {'up': 85, 'sideways': 50, 'down': 15}
    score += trend_scores.get(trend, 50) * ENVIRONMENT_WEIGHTS['kospi_trend']

    # 외국인 수급 (20%)
    foreign = indicators.get('foreign_flow', 'neutral')
    foreign_scores = {'buy': 80, 'neutral': 50, 'sell': 20}
    score += foreign_scores.get(foreign, 50) * ENVIRONMENT_WEIGHTS['foreign_flow']

    # 거시 레짐 (20%)
    regime = indicators.get('macro_regime', 'transitional')
    regime_scores = {
        'expansion': 85, 'late_expansion': 65, 'recovery': 70,
        'transitional': 50, 'contraction': 20, 'inflationary': 30,
    }
    score += regime_scores.get(regime, 50) * ENVIRONMENT_WEIGHTS['macro_regime']

    # 환율 (15%)
    usd_krw = indicators.get('usd_krw', 'stable')
    fx_scores = {'stable': 70, 'volatile': 40, 'crisis': 10}
    score += fx_scores.get(usd_krw, 50) * ENVIRONMENT_WEIGHTS['usd_krw']

    # 시장 폭 (10%)
    breadth = indicators.get('breadth_score', 50)
    score += min(100, max(0, breadth)) * ENVIRONMENT_WEIGHTS['breadth']

    # 변동성 (10%) - 낮을수록 좋음
    vix = indicators.get('vix_kr', 20)
    vix_score = max(0, min(100, 100 - vix * 3))
    score += vix_score * ENVIRONMENT_WEIGHTS['volatility']

    score = round(score, 1)

    # 상태 분류
    if score >= 70:
        phase = 'RISK_ON'
    elif score >= 50:
        phase = 'BASE'
    elif score >= 35:
        phase = 'CAUTION'
    else:
        phase = 'STRESS'

    config = MARKET_PHASES[phase]
    return {
        'phase': phase,
        'description': config['description'],
        'equity_target': config['equity_target'],
        'cash_target': config['cash_target'],
        'score': score,
    }


def generate_weekly_checklist(market_data):
    """주간 체크리스트 생성.

    Args:
        market_data: dict with keys matching KR_WEEKLY_CHECKLIST.

    Returns:
        list: [{item, status, value, note}, ...]
    """
    checklist = []
    for item in KR_WEEKLY_CHECKLIST:
        data = market_data.get(item)
        if data is None:
            checklist.append({
                'item': item,
                'status': 'missing',
                'value': None,
                'note': '데이터 없음',
            })
        else:
            note = ''
            if item == 'kospi_kosdaq_trend':
                if isinstance(data, dict):
                    note = f'KOSPI: {data.get("kospi", "N/A")}, KOSDAQ: {data.get("kosdaq", "N/A")}'
                else:
                    note = str(data)
            elif item == 'foreign_net_flow':
                note = f'순매수: {data:+,}원' if isinstance(data, (int, float)) else str(data)
            elif item == 'institutional_net_flow':
                note = f'순매수: {data:+,}원' if isinstance(data, (int, float)) else str(data)
            elif item == 'bok_rate_decision':
                note = str(data) if data else '해당 없음'
            elif item == 'usd_krw_trend':
                note = f'{data}원' if isinstance(data, (int, float)) else str(data)
            else:
                note = str(data)

            checklist.append({
                'item': item,
                'status': 'checked',
                'value': data,
                'note': note,
            })

    return checklist
