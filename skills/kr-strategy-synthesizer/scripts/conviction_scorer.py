"""kr-strategy-synthesizer: 9-컴포넌트 확신도 계산."""


# ─── 확신도 스코어링 ───

CONVICTION_COMPONENTS = {
    'market_structure': {
        'weight': 0.15,
        'sources': ['kr-market-breadth', 'kr-uptrend-analyzer'],
        'description': '시장 참여도 건강성',
    },
    'distribution_risk': {
        'weight': 0.14,
        'sources': ['kr-market-top-detector'],
        'description': '기관 매도 리스크 (역수)',
    },
    'bottom_confirmation': {
        'weight': 0.09,
        'sources': ['kr-ftd-detector'],
        'description': '바닥 확인 시그널',
    },
    'macro_alignment': {
        'weight': 0.14,
        'sources': ['kr-macro-regime'],
        'description': '거시 레짐 유리도',
    },
    'theme_quality': {
        'weight': 0.09,
        'sources': ['kr-theme-detector'],
        'description': '섹터 모멘텀 품질',
    },
    'setup_availability': {
        'weight': 0.08,
        'sources': ['kr-vcp-screener', 'kr-canslim-screener'],
        'description': '품질 셋업 가용성',
    },
    'signal_convergence': {
        'weight': 0.11,
        'sources': ['all_required'],
        'description': '스킬 간 시그널 수렴도',
    },
    'growth_outlook': {
        'weight': 0.10,
        'sources': ['kr-growth-outlook'],
        'description': '종목/섹터 성장성 전망',
    },
    'global_monetary': {
        'weight': 0.10,
        'sources': ['us-monetary-regime'],
        'description': '글로벌 통화정책 환경',
    },
}

# ─── 확신도 존 ───

CONVICTION_ZONES = {
    'MAXIMUM': {
        'min_score': 80,
        'equity_range': (90, 100),
        'daily_vol': 0.004,
        'max_single_position': 0.25,
    },
    'HIGH': {
        'min_score': 60,
        'equity_range': (70, 90),
        'daily_vol': 0.003,
        'max_single_position': 0.15,
    },
    'MODERATE': {
        'min_score': 40,
        'equity_range': (50, 70),
        'daily_vol': 0.0025,
        'max_single_position': 0.10,
    },
    'LOW': {
        'min_score': 20,
        'equity_range': (20, 50),
        'daily_vol': 0.0015,
        'max_single_position': 0.05,
    },
    'PRESERVATION': {
        'min_score': 0,
        'equity_range': (0, 20),
        'daily_vol': 0.001,
        'max_single_position': 0.03,
    },
}

# ─── 한국 시장 적응 ───

KR_ADAPTATION = {
    'foreign_flow_weight': 0.15,
    'bok_rate_sensitivity': True,
    'kospi_kosdaq_dual': True,
    'geopolitical_premium': 0.05,
    'report_max_age_hours': 72,
}


def normalize_signal(raw_value, source_skill):
    """스킬별 원시 값을 0-100 범위로 정규화.

    Args:
        raw_value: 원시 시그널 값.
        source_skill: str, 소스 스킬명.

    Returns:
        float: 정규화된 값 (0-100).
    """
    if raw_value is None:
        return 50.0

    # 스킬별 정규화 로직
    if source_skill == 'kr-market-breadth':
        # breadth_score: 이미 0-100
        return max(0, min(100, float(raw_value)))

    elif source_skill == 'kr-uptrend-analyzer':
        # uptrend_score: 이미 0-100
        return max(0, min(100, float(raw_value)))

    elif source_skill == 'kr-market-top-detector':
        # top_risk_score: 0-100이지만 역수 (높을수록 위험)
        return max(0, min(100, 100 - float(raw_value)))

    elif source_skill == 'kr-ftd-detector':
        # ftd_confirmed: bool → 70 (확인) / 30 (미확인)
        return 70.0 if raw_value else 30.0

    elif source_skill == 'kr-macro-regime':
        # regime: str → 점수 매핑
        regime_scores = {
            'expansion': 85,
            'late_expansion': 65,
            'transitional': 50,
            'contraction': 25,
            'recovery': 70,
            'inflationary': 35,
        }
        return float(regime_scores.get(str(raw_value).lower(), 50))

    elif source_skill == 'kr-theme-detector':
        # bullish 테마 수 기반
        if isinstance(raw_value, (list, tuple)):
            count = len(raw_value)
        else:
            count = int(raw_value) if raw_value else 0
        return min(100, count * 15 + 20)

    elif source_skill in ('kr-vcp-screener', 'kr-canslim-screener'):
        # 후보 종목 수 기반
        if isinstance(raw_value, (list, tuple)):
            count = len(raw_value)
        else:
            count = int(raw_value) if raw_value else 0
        return min(100, count * 10 + 10)

    elif source_skill == 'kr-growth-outlook':
        # growth composite score: 이미 0-100
        return max(0, min(100, float(raw_value)))

    elif source_skill == 'us-monetary-regime':
        # regime_score: 이미 0-100
        return max(0, min(100, float(raw_value)))

    return max(0, min(100, float(raw_value)))


def calc_component_scores(reports):
    """9-컴포넌트 개별 점수 계산.

    Args:
        reports: dict from load_skill_reports().

    Returns:
        dict: {component_name: {score, sources_used, description}, ...}
    """
    components = {}

    # 1. market_structure
    breadth = reports.get('kr-market-breadth', {})
    uptrend = reports.get('kr-uptrend-analyzer', {})
    breadth_score = normalize_signal(breadth.get('breadth_score'), 'kr-market-breadth')
    uptrend_score = normalize_signal(uptrend.get('uptrend_score'), 'kr-uptrend-analyzer')
    sources = []
    if breadth:
        sources.append('kr-market-breadth')
    if uptrend:
        sources.append('kr-uptrend-analyzer')
    ms_score = (breadth_score + uptrend_score) / 2
    components['market_structure'] = {
        'score': round(ms_score, 1),
        'sources_used': sources,
        'description': CONVICTION_COMPONENTS['market_structure']['description'],
    }

    # 2. distribution_risk (역수)
    top = reports.get('kr-market-top-detector', {})
    dr_score = normalize_signal(top.get('top_risk_score'), 'kr-market-top-detector')
    components['distribution_risk'] = {
        'score': round(dr_score, 1),
        'sources_used': ['kr-market-top-detector'] if top else [],
        'description': CONVICTION_COMPONENTS['distribution_risk']['description'],
    }

    # 3. bottom_confirmation
    ftd = reports.get('kr-ftd-detector', {})
    bc_score = normalize_signal(ftd.get('ftd_confirmed'), 'kr-ftd-detector')
    components['bottom_confirmation'] = {
        'score': round(bc_score, 1),
        'sources_used': ['kr-ftd-detector'] if ftd else [],
        'description': CONVICTION_COMPONENTS['bottom_confirmation']['description'],
    }

    # 4. macro_alignment
    macro = reports.get('kr-macro-regime', {})
    ma_score = normalize_signal(macro.get('regime'), 'kr-macro-regime')
    components['macro_alignment'] = {
        'score': round(ma_score, 1),
        'sources_used': ['kr-macro-regime'] if macro else [],
        'description': CONVICTION_COMPONENTS['macro_alignment']['description'],
    }

    # 5. theme_quality
    theme = reports.get('kr-theme-detector', {})
    tq_score = normalize_signal(theme.get('bullish_themes'), 'kr-theme-detector')
    components['theme_quality'] = {
        'score': round(tq_score, 1),
        'sources_used': ['kr-theme-detector'] if theme else [],
        'description': CONVICTION_COMPONENTS['theme_quality']['description'],
    }

    # 6. setup_availability
    vcp = reports.get('kr-vcp-screener', {})
    canslim = reports.get('kr-canslim-screener', {})
    vcp_score = normalize_signal(vcp.get('vcp_candidates'), 'kr-vcp-screener')
    canslim_score = normalize_signal(canslim.get('canslim_candidates'), 'kr-canslim-screener')
    sa_sources = []
    if vcp:
        sa_sources.append('kr-vcp-screener')
    if canslim:
        sa_sources.append('kr-canslim-screener')
    sa_score = (vcp_score + canslim_score) / 2
    components['setup_availability'] = {
        'score': round(sa_score, 1),
        'sources_used': sa_sources,
        'description': CONVICTION_COMPONENTS['setup_availability']['description'],
    }

    # 7. growth_outlook
    growth = reports.get('kr-growth-outlook', {})
    go_score = normalize_signal(growth.get('composite'), 'kr-growth-outlook')
    components['growth_outlook'] = {
        'score': round(go_score, 1),
        'sources_used': ['kr-growth-outlook'] if growth else [],
        'description': CONVICTION_COMPONENTS['growth_outlook']['description'],
    }

    # 8. global_monetary
    monetary = reports.get('us-monetary-regime', {})
    gm_score = normalize_signal(monetary.get('regime_score'), 'us-monetary-regime')
    components['global_monetary'] = {
        'score': round(gm_score, 1),
        'sources_used': ['us-monetary-regime'] if monetary else [],
        'description': CONVICTION_COMPONENTS['global_monetary']['description'],
    }

    # 9. signal_convergence
    other_scores = [c['score'] for name, c in components.items()
                    if name != 'signal_convergence']
    if other_scores:
        mean = sum(other_scores) / len(other_scores)
        variance = sum((s - mean) ** 2 for s in other_scores) / len(other_scores)
        std = variance ** 0.5
        # 낮은 표준편차 = 높은 수렴 = 높은 점수
        # std 0 → 100, std 30+ → 10
        convergence = max(10, min(100, 100 - std * 3))
    else:
        convergence = 50.0
    components['signal_convergence'] = {
        'score': round(convergence, 1),
        'sources_used': ['all'],
        'description': CONVICTION_COMPONENTS['signal_convergence']['description'],
    }

    return components


def _get_zone(score):
    """확신도 점수 → 존 분류."""
    for zone_name in ('MAXIMUM', 'HIGH', 'MODERATE', 'LOW', 'PRESERVATION'):
        if score >= CONVICTION_ZONES[zone_name]['min_score']:
            return zone_name
    return 'PRESERVATION'


def calc_conviction_score(components):
    """확신도 종합 점수 계산.

    Args:
        components: dict from calc_component_scores().

    Returns:
        dict: {score, zone, components, zone_details}
    """
    weighted_sum = 0
    total_weight = 0

    for name, config in CONVICTION_COMPONENTS.items():
        comp = components.get(name)
        if comp and 'score' in comp:
            weighted_sum += comp['score'] * config['weight']
            total_weight += config['weight']

    if total_weight > 0:
        score = round(weighted_sum / total_weight, 1)
    else:
        score = 50.0

    zone = _get_zone(score)
    zone_details = CONVICTION_ZONES[zone]

    return {
        'score': score,
        'zone': zone,
        'components': components,
        'zone_details': {
            'equity_range': zone_details['equity_range'],
            'daily_vol': zone_details['daily_vol'],
            'max_single_position': zone_details['max_single_position'],
        },
    }
