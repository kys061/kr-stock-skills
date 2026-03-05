"""kr-strategy-synthesizer: 4 패턴 분류."""


# ─── 시장 패턴 분류 ───

MARKET_PATTERNS = {
    'PANIC_BUY': {
        'name': '공포 매수 기회',
        'trigger': 'easing_regime + sharp_decline + no_forced_liquidation',
        'principle': '금리 인하기의 급락은 최고의 매수 기회',
        'equity_range': (80, 100),
    },
    'POLICY_PIVOT': {
        'name': '정책 전환 예측',
        'trigger': 'transitional_regime + high_transition_prob',
        'principle': '중앙은행과 유동성에 집중하라',
        'equity_range': (70, 90),
    },
    'UNSUSTAINABLE_DISTORTION': {
        'name': '지속불가 왜곡',
        'trigger': 'top_risk >= 60 + contraction_or_inflationary',
        'principle': '틀렸을 때 얼마나 잃느냐가 가장 중요하다',
        'equity_range': (30, 50),
    },
    'EXTREME_CONTRARIAN': {
        'name': '극단 역발상',
        'trigger': 'ftd_confirmed + high_top_risk + bearish_breadth',
        'principle': '가장 큰 수익은 약세장에서 나온다',
        'equity_range': (25, 40),
    },
    'WAIT_OBSERVE': {
        'name': '관망',
        'trigger': 'low_conviction + mixed_signals',
        'principle': '보이지 않으면 스윙하지 마라',
        'equity_range': (0, 20),
    },
}

# --- PANIC_BUY Trigger Thresholds ---

PANIC_BUY_TRIGGERS = {
    'us_regime_min_score': 65,       # US regime score >= 65 (easing)
    'market_decline_pct': -10.0,     # KOSPI 20일 수익률 <= -10%
    'vkospi_min': 25.0,              # VKOSPI >= 25 (공포 확인)
}


def _check_panic_buy(components, reports):
    """공포 매수 기회 패턴 감지.

    3조건 동시 충족:
    1. US regime score >= 65 (easing)
    2. KOSPI 20일 수익률 <= -10%
    3. VKOSPI >= 25
    """
    monetary = reports.get('us-monetary-regime', {})
    breadth = reports.get('kr-market-breadth', {})
    bubble = reports.get('kr-bubble-detector', {})

    us_score = float(monetary.get('regime_score', 0))
    kospi_20d = float(breadth.get('kospi_20d_return', 0))
    vkospi = float(bubble.get('vkospi', 0))

    triggers = PANIC_BUY_TRIGGERS
    if (us_score >= triggers['us_regime_min_score']
            and kospi_20d <= triggers['market_decline_pct']
            and vkospi >= triggers['vkospi_min']):
        confidence = 70.0
        if us_score >= 80:
            confidence += 10
        if kospi_20d <= -15:
            confidence += 10
        if vkospi >= 30:
            confidence += 10
        return True, min(100, confidence)

    return False, 0


def _check_policy_pivot(components, reports):
    """정책 전환 패턴 감지."""
    macro = reports.get('kr-macro-regime', {})
    regime = str(macro.get('regime', '')).lower()
    trans_prob = float(macro.get('transition_probability', 0))

    if regime == 'transitional' and trans_prob >= 0.5:
        return True, round(trans_prob * 100, 1)
    return False, 0


def _check_unsustainable_distortion(components, reports):
    """지속불가 왜곡 패턴 감지."""
    top = reports.get('kr-market-top-detector', {})
    macro = reports.get('kr-macro-regime', {})

    top_risk = float(top.get('top_risk_score', 0))
    regime = str(macro.get('regime', '')).lower()

    if top_risk >= 60 and regime in ('contraction', 'inflationary'):
        confidence = min(100, top_risk + 10)
        return True, round(confidence, 1)
    return False, 0


def _check_extreme_contrarian(components, reports):
    """극단 역발상 패턴 감지."""
    ftd = reports.get('kr-ftd-detector', {})
    top = reports.get('kr-market-top-detector', {})
    breadth = reports.get('kr-market-breadth', {})

    ftd_confirmed = ftd.get('ftd_confirmed', False)
    top_risk = float(top.get('top_risk_score', 0))
    breadth_score = float(breadth.get('breadth_score', 50))

    if ftd_confirmed and top_risk >= 50 and breadth_score < 40:
        confidence = min(100, (top_risk + (100 - breadth_score)) / 2)
        return True, round(confidence, 1)
    return False, 0


def classify_pattern(components, reports):
    """시장 패턴 분류.

    Args:
        components: dict from calc_component_scores().
        reports: dict from load_skill_reports().

    Returns:
        dict: {pattern, name, confidence, principle, equity_range}
    """
    # 우선순위: PANIC_BUY > POLICY_PIVOT > UNSUSTAINABLE_DISTORTION > EXTREME_CONTRARIAN > WAIT_OBSERVE

    detected, confidence = _check_panic_buy(components, reports)
    if detected:
        p = MARKET_PATTERNS['PANIC_BUY']
        return {
            'pattern': 'PANIC_BUY',
            'name': p['name'],
            'confidence': confidence,
            'principle': p['principle'],
            'equity_range': p['equity_range'],
        }

    detected, confidence = _check_policy_pivot(components, reports)
    if detected:
        p = MARKET_PATTERNS['POLICY_PIVOT']
        return {
            'pattern': 'POLICY_PIVOT',
            'name': p['name'],
            'confidence': confidence,
            'principle': p['principle'],
            'equity_range': p['equity_range'],
        }

    detected, confidence = _check_unsustainable_distortion(components, reports)
    if detected:
        p = MARKET_PATTERNS['UNSUSTAINABLE_DISTORTION']
        return {
            'pattern': 'UNSUSTAINABLE_DISTORTION',
            'name': p['name'],
            'confidence': confidence,
            'principle': p['principle'],
            'equity_range': p['equity_range'],
        }

    detected, confidence = _check_extreme_contrarian(components, reports)
    if detected:
        p = MARKET_PATTERNS['EXTREME_CONTRARIAN']
        return {
            'pattern': 'EXTREME_CONTRARIAN',
            'name': p['name'],
            'confidence': confidence,
            'principle': p['principle'],
            'equity_range': p['equity_range'],
        }

    # 기본: WAIT_OBSERVE
    p = MARKET_PATTERNS['WAIT_OBSERVE']
    return {
        'pattern': 'WAIT_OBSERVE',
        'name': p['name'],
        'confidence': 50.0,
        'principle': p['principle'],
        'equity_range': p['equity_range'],
    }
