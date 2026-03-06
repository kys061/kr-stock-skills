"""kr-supply-demand-analyzer: 섹터별 자금 흐름 분석."""


# Phase 6/8과 동일한 15 섹터 (kr-weekly-strategy)
KR_SECTORS = [
    '반도체', '자동차', '조선/해운', '철강/화학',
    '바이오/제약', '금융/은행', '유통/소비', '건설/부동산',
    'IT/소프트웨어', '통신', '에너지/유틸리티', '엔터테인먼트',
    '방산', '2차전지', '원전',
]

SECTOR_FLOW_CONFIG = {
    'rotation_lookback': 5,   # 로테이션 비교: 전주 대비
    'hhi_warning': 0.25,      # HHI 집중도 경고: 0.25 이상
    'hhi_critical': 0.40,     # HHI 집중도 위험: 0.40 이상
    'divergence_threshold': 0.30,  # 외국인-기관 괴리 경고: 30% 이상
}


def _safe_abs_total(sector_flows):
    """섹터별 절대값 합계 (0 제외)."""
    total = 0
    for sector, data in sector_flows.items():
        if isinstance(data, dict):
            net = data.get('net', data.get('foreign', 0))
        else:
            net = data
        total += abs(net) if net else 0
    return total


def calc_sector_hhi(sector_flows):
    """섹터별 자금 흐름 HHI (허핀달-허시만 지수) 계산.

    HHI = Σ(Si²), Si = 각 섹터 비중 (0-1)
    HHI 0 = 완전 분산, HHI 1 = 완전 집중

    Args:
        sector_flows: dict {sector_name: net_amount} 또는
                      dict {sector_name: {net: amount}} 또는
                      dict {sector_name: {foreign: net, institution: net}}

    Returns:
        float: HHI (0-1)
    """
    if not sector_flows:
        return 0.0

    abs_total = _safe_abs_total(sector_flows)
    if abs_total == 0:
        return 0.0

    hhi = 0.0
    for sector, data in sector_flows.items():
        if isinstance(data, dict):
            net = data.get('net', data.get('foreign', 0))
        else:
            net = data
        share = abs(net) / abs_total if net else 0
        hhi += share ** 2

    return round(hhi, 4)


def _hhi_to_score(hhi):
    """HHI → 0-100 점수 (분산이 건전할수록 높은 점수)."""
    if hhi >= SECTOR_FLOW_CONFIG['hhi_critical']:
        return 15  # 과도한 집중 → 낮은 점수
    elif hhi >= SECTOR_FLOW_CONFIG['hhi_warning']:
        # 0.25 ~ 0.40 → 15~50 선형
        ratio = (hhi - SECTOR_FLOW_CONFIG['hhi_warning']) / (
            SECTOR_FLOW_CONFIG['hhi_critical'] - SECTOR_FLOW_CONFIG['hhi_warning']
        )
        return round(50 - ratio * 35, 1)
    else:
        # 0 ~ 0.25 → 50~90 선형
        if SECTOR_FLOW_CONFIG['hhi_warning'] == 0:
            return 90
        ratio = hhi / SECTOR_FLOW_CONFIG['hhi_warning']
        return round(90 - ratio * 40, 1)


def calc_sector_divergence(sector_flows):
    """섹터별 외국인-기관 괴리도 계산.

    Args:
        sector_flows: dict {sector_name: {foreign: net, institution: net}}

    Returns:
        dict: {sector: divergence_score} (-1 ~ +1, 양수 = 외국인 매수/기관 매도)
    """
    divergences = {}
    for sector, data in sector_flows.items():
        if not isinstance(data, dict):
            continue
        f_net = data.get('foreign', 0) or 0
        i_net = data.get('institution', 0) or 0

        total = abs(f_net) + abs(i_net)
        if total == 0:
            divergences[sector] = 0.0
            continue

        # 괴리도: 같은 방향이면 0에 가깝고, 반대 방향이면 ±1에 가까움
        if (f_net > 0 and i_net < 0) or (f_net < 0 and i_net > 0):
            divergences[sector] = round(
                (f_net - i_net) / total, 4
            )
        else:
            divergences[sector] = 0.0

    return divergences


def _divergence_to_score(divergences):
    """괴리도 → 0-100 점수 (괴리가 작을수록 높은 점수)."""
    if not divergences:
        return 70.0

    threshold = SECTOR_FLOW_CONFIG['divergence_threshold']
    warning_count = sum(
        1 for d in divergences.values() if abs(d) >= threshold
    )
    total = len(divergences)
    if total == 0:
        return 70.0

    warning_ratio = warning_count / total
    # 경고 비율 0% → 90, 50% → 40, 100% → 10
    return round(max(10, 90 - warning_ratio * 80), 1)


def _calc_rotation_score(current_flows, previous_flows):
    """로테이션 속도 점수 (과도한 로테이션은 불안정 → 낮은 점수).

    Args:
        current_flows: dict {sector: net_amount}
        previous_flows: dict {sector: net_amount}

    Returns:
        float: 0-100
    """
    if not current_flows or not previous_flows:
        return 60.0

    # 방향 전환 섹터 수
    direction_changes = 0
    total_sectors = 0

    for sector in KR_SECTORS:
        curr = current_flows.get(sector)
        prev = previous_flows.get(sector)
        if curr is None or prev is None:
            continue

        curr_net = curr.get('net', curr.get('foreign', 0)) if isinstance(curr, dict) else curr
        prev_net = prev.get('net', prev.get('foreign', 0)) if isinstance(prev, dict) else prev

        total_sectors += 1
        if (curr_net > 0 and prev_net < 0) or (curr_net < 0 and prev_net > 0):
            direction_changes += 1

    if total_sectors == 0:
        return 60.0

    change_ratio = direction_changes / total_sectors
    # 로테이션 과도(60%+) → 25점, 적정(20-40%) → 75점, 없음(0%) → 60점
    if change_ratio > 0.6:
        return 25.0
    elif change_ratio > 0.4:
        return round(75 - (change_ratio - 0.4) * 250, 1)
    elif change_ratio > 0.2:
        return 75.0
    elif change_ratio > 0:
        return round(60 + change_ratio * 75, 1)
    return 60.0


def map_sector_flows(sector_data, previous_data=None):
    """섹터별 자금 흐름 종합 분석.

    Args:
        sector_data: dict {sector: {foreign: net, institution: net, individual: net}}
        previous_data: dict (optional) 전주 데이터 (로테이션 비교용)

    Returns:
        dict: {flows, heatmap, rotation_score, hhi, hhi_score, divergence,
               divergence_score, sector_score}
    """
    if not sector_data:
        return {
            'flows': {},
            'heatmap': {},
            'rotation_score': 60.0,
            'hhi': 0.0,
            'hhi_score': 90.0,
            'divergence': {},
            'divergence_score': 70.0,
            'sector_score': 70.0,
        }

    # 섹터별 순합계 계산
    flows = {}
    heatmap = {}
    for sector, data in sector_data.items():
        if not isinstance(data, dict):
            continue
        f_net = data.get('foreign', 0) or 0
        i_net = data.get('institution', 0) or 0
        ind_net = data.get('individual', 0) or 0
        total_net = f_net + i_net + ind_net

        flows[sector] = {
            'foreign': f_net,
            'institution': i_net,
            'individual': ind_net,
            'net': total_net,
        }

        # 히트맵: 양수 = 유입, 음수 = 유출
        if total_net > 0:
            heatmap[sector] = 'inflow'
        elif total_net < 0:
            heatmap[sector] = 'outflow'
        else:
            heatmap[sector] = 'neutral'

    # HHI 집중도
    hhi = calc_sector_hhi(flows)
    hhi_score = _hhi_to_score(hhi)

    # 외국인-기관 괴리도
    divergence = calc_sector_divergence(sector_data)
    divergence_score = _divergence_to_score(divergence)

    # 로테이션 속도
    rotation_score = _calc_rotation_score(sector_data, previous_data)

    # 섹터 종합 점수 (HHI 40% + 괴리도 30% + 로테이션 30%)
    sector_score = round(
        hhi_score * 0.40 + divergence_score * 0.30 + rotation_score * 0.30,
        1,
    )

    return {
        'flows': flows,
        'heatmap': heatmap,
        'rotation_score': rotation_score,
        'hhi': hhi,
        'hhi_score': hhi_score,
        'divergence': divergence,
        'divergence_score': divergence_score,
        'sector_score': sector_score,
    }
