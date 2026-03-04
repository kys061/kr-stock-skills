"""kr-strategy-synthesizer: 자산 배분 엔진."""

from conviction_scorer import CONVICTION_ZONES, KR_ADAPTATION


def generate_allocation(conviction_score, pattern=None):
    """확신도 기반 자산 배분 생성.

    Args:
        conviction_score: dict with 'score' and 'zone' keys.
        pattern: dict from classify_pattern() (optional).

    Returns:
        dict: {equity, bonds, alternatives, cash, max_single}
    """
    score = conviction_score.get('score', 50)
    zone = conviction_score.get('zone', 'MODERATE')
    zone_config = CONVICTION_ZONES.get(zone, CONVICTION_ZONES['MODERATE'])

    eq_min, eq_max = zone_config['equity_range']
    max_single = zone_config['max_single_position']

    # 존 내에서 점수에 비례하여 비중 결정
    zone_min = zone_config['min_score']
    zone_range = 20  # 각 존 범위
    if zone == 'PRESERVATION':
        zone_range = 20
    elif zone == 'MAXIMUM':
        zone_range = 20

    ratio = min(1.0, max(0, (score - zone_min) / zone_range))
    equity = round(eq_min + (eq_max - eq_min) * ratio, 1)

    # 패턴 오버라이드
    if pattern and 'equity_range' in pattern:
        p_min, p_max = pattern['equity_range']
        pattern_equity = (p_min + p_max) / 2
        # 패턴과 존 중간값
        equity = round((equity + pattern_equity) / 2, 1)

    # 나머지 배분
    remaining = 100 - equity
    bonds = round(remaining * 0.4, 1)
    alternatives = round(remaining * 0.2, 1)
    cash = round(remaining - bonds - alternatives, 1)

    return {
        'equity': equity,
        'bonds': bonds,
        'alternatives': alternatives,
        'cash': cash,
        'max_single': max_single,
    }


def apply_kr_adjustment(allocation, kr_signals=None):
    """한국 시장 특수 요인 반영.

    Args:
        allocation: dict from generate_allocation().
        kr_signals: dict with optional keys:
            foreign_flow: 'buy'/'sell'/'neutral'
            bok_rate_direction: 'cut'/'hold'/'hike'
            usd_krw_trend: 'strengthening'/'stable'/'weakening'
            geopolitical_risk: bool

    Returns:
        dict: 조정된 자산 배분.
    """
    if kr_signals is None:
        return allocation

    adj = dict(allocation)
    equity = adj['equity']

    # 외국인 수급 반영
    foreign = kr_signals.get('foreign_flow')
    if foreign == 'buy':
        equity += KR_ADAPTATION['foreign_flow_weight'] * 100 * 0.3
    elif foreign == 'sell':
        equity -= KR_ADAPTATION['foreign_flow_weight'] * 100 * 0.3

    # BOK 금리 방향
    if KR_ADAPTATION['bok_rate_sensitivity']:
        bok = kr_signals.get('bok_rate_direction')
        if bok == 'cut':
            equity += 3.0
        elif bok == 'hike':
            equity -= 3.0

    # 환율 추세
    usd_krw = kr_signals.get('usd_krw_trend')
    if usd_krw == 'weakening':  # 원화 강세 = 외국인 유입
        equity += 2.0
    elif usd_krw == 'strengthening':  # 원화 약세 = 외국인 이탈
        equity -= 2.0

    # 지정학적 리스크
    if kr_signals.get('geopolitical_risk'):
        equity -= KR_ADAPTATION['geopolitical_premium'] * 100

    # 범위 제한 (0-100)
    equity = round(max(0, min(100, equity)), 1)

    # 나머지 재배분
    remaining = 100 - equity
    adj['equity'] = equity
    adj['bonds'] = round(remaining * 0.4, 1)
    adj['alternatives'] = round(remaining * 0.2, 1)
    adj['cash'] = round(remaining - adj['bonds'] - adj['alternatives'], 1)

    return adj
