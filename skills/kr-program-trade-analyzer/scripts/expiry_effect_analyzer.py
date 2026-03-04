"""kr-program-trade-analyzer: 만기일 효과 분석."""

from datetime import date, timedelta
import calendar


# ─── 만기일 효과 ───

EXPIRY_CONFIG = {
    'monthly_expiry_weekday': 3,   # 목요일 (0=월, 3=목)
    'monthly_expiry_week': 2,      # 둘째 주
    'quarterly_months': [3, 6, 9, 12],  # 분기 만기월
}

# 만기 유형
EXPIRY_TYPES = {
    'MONTHLY': {
        'label': '월간 만기 (옵션)',
        'impact': 'moderate',
        'volatility_premium': 1.05,  # 변동성 5% 프리미엄
    },
    'QUARTERLY': {
        'label': '분기 만기 (선물+옵션)',
        'impact': 'high',
        'volatility_premium': 1.15,  # 변동성 15% 프리미엄
    },
}

# 만기일 근접도
EXPIRY_PROXIMITY = {
    'expiry_day': 0,    # D-day
    'near': 1,          # D-1
    'approaching': 3,   # D-3
    'week': 5,          # D-5 (만기 주간)
    'far': 999,         # 만기 주간 아님
}

# 만기 효과 패턴
EXPIRY_PATTERNS = {
    'pin_risk': '최대고통가격 근접 시 가격 고정 경향',
    'gamma_squeeze': '옵션 감마 급증으로 변동성 확대',
    'rollover_pressure': '선물 롤오버 매매 압력',
    'expiry_volatility': '만기일 거래량 급증 + 변동성',
}


def _find_nth_weekday(year, month, weekday, n):
    """N번째 특정 요일 날짜 찾기.

    Args:
        year: 연도.
        month: 월.
        weekday: 요일 (0=월, 6=일).
        n: N번째 (1=첫째, 2=둘째, ...).

    Returns:
        date: N번째 해당 요일 날짜.
    """
    first_day = date(year, month, 1)
    # 해당 월의 첫 번째 해당 요일
    first_weekday = first_day + timedelta(days=(weekday - first_day.weekday()) % 7)
    # N번째
    target = first_weekday + timedelta(weeks=n - 1)
    return target


def get_next_expiry(from_date=None):
    """다음 만기일 정보.

    Args:
        from_date: 기준 날짜 (default: 오늘).

    Returns:
        dict: {date, type, days_until, proximity, label, volatility_premium}
    """
    if from_date is None:
        from_date = date.today()
    elif isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)

    # 이번 달부터 3개월간 탐색
    for month_offset in range(4):
        year = from_date.year + (from_date.month + month_offset - 1) // 12
        month = (from_date.month + month_offset - 1) % 12 + 1

        expiry_date = _find_nth_weekday(
            year, month,
            EXPIRY_CONFIG['monthly_expiry_weekday'],
            EXPIRY_CONFIG['monthly_expiry_week'],
        )

        if expiry_date >= from_date:
            # 만기 유형
            is_quarterly = month in EXPIRY_CONFIG['quarterly_months']
            expiry_type = 'QUARTERLY' if is_quarterly else 'MONTHLY'
            type_info = EXPIRY_TYPES[expiry_type]

            days_until = (expiry_date - from_date).days

            # 근접도
            prox = EXPIRY_PROXIMITY
            if days_until == prox['expiry_day']:
                proximity = 'expiry_day'
            elif days_until <= prox['near']:
                proximity = 'near'
            elif days_until <= prox['approaching']:
                proximity = 'approaching'
            elif days_until <= prox['week']:
                proximity = 'week'
            else:
                proximity = 'far'

            return {
                'date': expiry_date.isoformat(),
                'type': expiry_type,
                'days_until': days_until,
                'proximity': proximity,
                'label': type_info['label'],
                'volatility_premium': type_info['volatility_premium'],
            }

    # 폴백
    return {
        'date': None,
        'type': 'MONTHLY',
        'days_until': 30,
        'proximity': 'far',
        'label': EXPIRY_TYPES['MONTHLY']['label'],
        'volatility_premium': 1.05,
    }


def _proximity_to_score(proximity, expiry_type):
    """근접도 → 0-100 영향 점수 (높을수록 만기 영향 큼)."""
    base_scores = {
        'expiry_day': 95,
        'near': 80,
        'approaching': 60,
        'week': 40,
        'far': 15,
    }
    base = base_scores.get(proximity, 15)

    # 분기 만기는 점수 보정
    if expiry_type == 'QUARTERLY':
        base = min(100, round(base * 1.15))

    return base


def analyze_expiry_effect(expiry_info, historical_data=None):
    """만기일 효과 분석.

    Args:
        expiry_info: get_next_expiry() 결과.
        historical_data: 과거 만기일 변동성 데이터 (optional).

    Returns:
        dict: {type, proximity, volatility_premium, patterns, impact_score}
    """
    expiry_type = expiry_info.get('type', 'MONTHLY')
    proximity = expiry_info.get('proximity', 'far')
    vol_premium = expiry_info.get('volatility_premium', 1.05)

    impact_score = _proximity_to_score(proximity, expiry_type)

    # 근접도별 활성 패턴
    active_patterns = []
    if proximity in ('expiry_day', 'near'):
        active_patterns = list(EXPIRY_PATTERNS.keys())
    elif proximity == 'approaching':
        active_patterns = ['rollover_pressure', 'gamma_squeeze']
    elif proximity == 'week':
        active_patterns = ['rollover_pressure']

    return {
        'type': expiry_type,
        'proximity': proximity,
        'days_until': expiry_info.get('days_until', 30),
        'volatility_premium': vol_premium,
        'patterns': active_patterns,
        'impact_score': impact_score,
    }


def calc_max_pain(option_data):
    """최대고통가격 계산 (간이 버전).

    Args:
        option_data: dict {strike_price: {call_oi, put_oi}} 또는 None.

    Returns:
        dict: {max_pain_price, current_distance_pct} 또는 빈 결과.
    """
    if not option_data:
        return {'max_pain_price': None, 'current_distance_pct': None}

    # 각 행사가에서 총 내재 손실 계산
    min_pain = float('inf')
    max_pain_strike = None

    strikes = sorted(option_data.keys())
    for test_strike in strikes:
        total_pain = 0
        for strike, oi in option_data.items():
            call_oi = oi.get('call_oi', 0) or 0
            put_oi = oi.get('put_oi', 0) or 0

            # 콜 옵션 손실: max(0, test_strike - strike) × call_oi
            if test_strike > strike:
                total_pain += (test_strike - strike) * call_oi

            # 풋 옵션 손실: max(0, strike - test_strike) × put_oi
            if strike > test_strike:
                total_pain += (strike - test_strike) * put_oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return {
        'max_pain_price': max_pain_strike,
        'current_distance_pct': None,  # 현재가 필요
    }


# ─── 프로그램 영향 스코어 ───

PROGRAM_IMPACT_WEIGHTS = {
    'arbitrage_flow': {'weight': 0.25, 'label': '차익거래 방향/규모'},
    'non_arb_flow': {'weight': 0.30, 'label': '비차익 방향/규모'},
    'basis_signal': {'weight': 0.25, 'label': '베이시스 이상 신호'},
    'expiry_effect': {'weight': 0.20, 'label': '만기일 근접도'},
}
# 가중치 합계: 0.25 + 0.30 + 0.25 + 0.20 = 1.00

PROGRAM_IMPACT_GRADES = {
    'POSITIVE': {'min_score': 65, 'label': '긍정적 (프로그램 매수 우위)'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'NEGATIVE': {'min_score': 20, 'label': '부정적 (프로그램 매도 우위)'},
    'WARNING': {'min_score': 0, 'label': '경고 (만기일/베이시스 이상)'},
}


def _classify_impact_grade(score):
    """점수 → 영향 등급."""
    for grade, cfg in PROGRAM_IMPACT_GRADES.items():
        if score >= cfg['min_score']:
            return grade
    return 'WARNING'


def calc_program_impact_score(program_analysis, basis_analysis, expiry_analysis):
    """프로그램 영향 종합 스코어.

    Args:
        program_analysis: analyze_program_trades() 결과.
        basis_analysis: analyze_basis() 결과.
        expiry_analysis: analyze_expiry_effect() 결과.

    Returns:
        dict: {score, grade, label, components}
    """
    arb_score = program_analysis.get('arbitrage', {}).get('score', 50)
    non_arb_score = program_analysis.get('non_arbitrage', {}).get('score', 50)
    basis_score = basis_analysis.get('score', 70)

    # 만기일 효과 → 점수 반전 (만기 근접 = 불안정 = 낮은 점수)
    expiry_impact = expiry_analysis.get('impact_score', 15)
    expiry_score = max(0, 100 - expiry_impact)

    weights = PROGRAM_IMPACT_WEIGHTS
    total = (
        arb_score * weights['arbitrage_flow']['weight']
        + non_arb_score * weights['non_arb_flow']['weight']
        + basis_score * weights['basis_signal']['weight']
        + expiry_score * weights['expiry_effect']['weight']
    )
    total = round(max(0, min(100, total)), 1)

    grade = _classify_impact_grade(total)
    label = PROGRAM_IMPACT_GRADES[grade]['label']

    return {
        'score': total,
        'grade': grade,
        'label': label,
        'components': {
            'arbitrage_flow': {'score': arb_score, 'weight': weights['arbitrage_flow']['weight']},
            'non_arb_flow': {'score': non_arb_score, 'weight': weights['non_arb_flow']['weight']},
            'basis_signal': {'score': basis_score, 'weight': weights['basis_signal']['weight']},
            'expiry_effect': {'score': expiry_score, 'weight': weights['expiry_effect']['weight']},
        },
    }
