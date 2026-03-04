"""kr-strategy-synthesizer: 4 패턴 분류."""


# ─── 시장 패턴 분류 ───

MARKET_PATTERNS = {
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
    # 우선순위: POLICY_PIVOT > UNSUSTAINABLE_DISTORTION > EXTREME_CONTRARIAN > WAIT_OBSERVE

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
