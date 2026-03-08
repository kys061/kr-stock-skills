"""kr-stock-analysis: 종합 스코어링 엔진."""


# ─── 종합 분석 스코어링 ───

COMPREHENSIVE_SCORING = {
    'fundamental': {'weight': 0.30, 'label': '펀더멘털'},
    'technical': {'weight': 0.22, 'label': '기술적'},
    'supply_demand': {'weight': 0.22, 'label': '수급'},
    'valuation': {'weight': 0.13, 'label': '밸류에이션'},
    'growth': {'weight': 0.13, 'label': '성장성'},
}

# ─── 분석 유형 ───

ANALYSIS_TYPES = [
    'BASIC',          # 기본 정보
    'FUNDAMENTAL',    # 펀더멘털
    'TECHNICAL',      # 기술적 분석
    'SUPPLY_DEMAND',  # 수급 분석 (KR 고유)
    'COMPREHENSIVE',  # 종합 리포트
]

# ─── 투자 등급 ───

ANALYSIS_GRADES = {
    'STRONG_BUY': 80,
    'BUY': 65,
    'HOLD': 50,
    'SELL': 35,
    'STRONG_SELL': 0,
}


# ─── 매수/매도 타점 상수 ───

BUY_ZONE_CONFIG = {
    'buy1_range': (-0.03, -0.10),
    'buy2_range': (-0.05, -0.15),
    'stop_loss_ma_margin': 0.03,
    'stop_loss_buy2_margin': 0.05,
    'buy2_fallback_ratio': 0.93,
    'week52_low_buffer': 1.05,
}

SELL_TARGET_CONFIG = {
    'sell1_range': (0.05, 0.20),
    'sell2_multiplier': 1.10,
    'trailing_stop_default': 0.10,
    'trailing_stop_high_beta': 0.15,
    'trailing_stop_low_beta': 0.07,
    'beta_high_threshold': 1.5,
    'beta_low_threshold': 0.8,
}

RR_RATIO_LABELS = {
    3.0: '매우 유리',
    2.0: '유리',
    1.0: '보통',
    0.0: '불리 — 진입 재고 필요',
}

GRADE_DISPLAY_RULES = {
    'STRONG_BUY': {'show_buy': True,  'show_sell': True,  'buy_label': '적극 매수구간'},
    'BUY':        {'show_buy': True,  'show_sell': True,  'buy_label': '매수구간'},
    'HOLD':       {'show_buy': False, 'show_sell': True,  'buy_label': '추가 매수 비추, 보유 유지'},
    'SELL':       {'show_buy': False, 'show_sell': True,  'buy_label': None},
    'STRONG_SELL': {'show_buy': False, 'show_sell': True,  'buy_label': None},
}

_LEVEL_TOLERANCE = 0.02

DISCLAIMER = (
    "본 매수/매도 가격은 기술적 분석과 컨센서스 기반 참고 정보이며, "
    "투자 판단의 최종 책임은 투자자 본인에게 있습니다."
)


def _get_grade(score):
    """점수 → 등급 변환."""
    if score >= ANALYSIS_GRADES['STRONG_BUY']:
        return 'STRONG_BUY'
    elif score >= ANALYSIS_GRADES['BUY']:
        return 'BUY'
    elif score >= ANALYSIS_GRADES['HOLD']:
        return 'HOLD'
    elif score >= ANALYSIS_GRADES['SELL']:
        return 'SELL'
    else:
        return 'STRONG_SELL'


def _generate_recommendation(grade, components):
    """등급 및 컴포넌트에 기반한 추천 생성."""
    recommendations = {
        'STRONG_BUY': '적극 매수 권장. 펀더멘털과 수급이 모두 긍정적.',
        'BUY': '매수 고려. 다수 지표가 긍정적.',
        'HOLD': '보유 유지. 추가 시그널 대기.',
        'SELL': '매도 고려. 부정적 지표 다수.',
        'STRONG_SELL': '적극 매도 권장. 대부분 지표가 부정적.',
    }

    rec = recommendations.get(grade, '분석 데이터 부족.')

    # 강점/약점 식별
    strengths = []
    weaknesses = []
    for name, data in components.items():
        score = data.get('score', 50)
        label = COMPREHENSIVE_SCORING.get(name, {}).get('label', name)
        if score >= 70:
            strengths.append(label)
        elif score < 40:
            weaknesses.append(label)

    return {
        'summary': rec,
        'strengths': strengths,
        'weaknesses': weaknesses,
    }


def calc_comprehensive_score(fundamental=None, technical=None,
                             supply_demand=None, valuation_score=None,
                             growth_quick=None):
    """종합 분석 점수 계산.

    Args:
        fundamental: dict from analyze_fundamentals() with 'score' key.
        technical: dict from analyze_technicals() with 'score' key.
        supply_demand: dict from analyze_supply_demand() with 'score' key.
        valuation_score: float, valuation sub-score (0-100).
            If None, uses fundamental's valuation score.
        growth_quick: dict from calc_growth_quick_score() with 'score' key.

    Returns:
        dict: {score, grade, components, recommendation}
    """
    components = {}
    weighted_sum = 0
    total_weight = 0

    # 펀더멘털
    if fundamental and 'score' in fundamental:
        f_score = fundamental['score']
        components['fundamental'] = {'score': f_score, 'weight': 0.30}
        weighted_sum += f_score * 0.30
        total_weight += 0.30

    # 기술적
    if technical and 'score' in technical:
        t_score = technical['score']
        components['technical'] = {'score': t_score, 'weight': 0.22}
        weighted_sum += t_score * 0.22
        total_weight += 0.22

    # 수급
    if supply_demand and 'score' in supply_demand:
        s_score = supply_demand['score']
        components['supply_demand'] = {'score': s_score, 'weight': 0.22}
        weighted_sum += s_score * 0.22
        total_weight += 0.22

    # 밸류에이션
    v_score = valuation_score
    if v_score is None and fundamental:
        val_data = fundamental.get('valuation', {})
        v_score = val_data.get('score') if isinstance(val_data, dict) else None
    if v_score is not None:
        components['valuation'] = {'score': v_score, 'weight': 0.13}
        weighted_sum += v_score * 0.13
        total_weight += 0.13

    # 성장성 (Growth Quick Score)
    if growth_quick and 'score' in growth_quick:
        g_score = growth_quick['score']
        components['growth'] = {'score': g_score, 'weight': 0.13}
        weighted_sum += g_score * 0.13
        total_weight += 0.13

    # 가중 합산 (가용 컴포넌트만으로 정규화)
    if total_weight > 0:
        score = round(weighted_sum / total_weight * 1.0, 1)
    else:
        score = 50.0

    grade = _get_grade(score)
    recommendation = _generate_recommendation(grade, components)

    return {
        'score': score,
        'grade': grade,
        'components': components,
        'recommendation': recommendation,
    }


# --- US Monetary Regime Overlay (B방식) ---

_SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,
    'secondary_battery': 1.3,
    'bio': 1.2,
    'it': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'construction': 0.8,
    'finance': 0.7,
    'insurance': 0.6,
    'retail': 0.5,
    'defense': 0.4,
    'food': 0.3,
    'nuclear': 0.6,
}

_DEFAULT_SENSITIVITY = 0.7


def apply_monetary_overlay(base_score, overlay=None, sector='default'):
    """통화정책 오버레이 적용.

    기존 calc_comprehensive_score() 결과에 us-monetary-regime
    오버레이를 섹터 민감도에 따라 적용한다.
    overlay=None이면 base_score를 그대로 반환.

    Args:
        base_score: float (0~100), calc_comprehensive_score() score.
        overlay: float or None, us-monetary-regime 오버레이 (-15~+15).
        sector: str, 한국 섹터명.

    Returns:
        dict: {original_score, overlay_applied, sector, sector_sensitivity,
               adjusted_overlay, final_score, final_grade, overlay_impact}
    """
    if overlay is None:
        return {
            'original_score': base_score,
            'overlay_applied': None,
            'sector': sector,
            'sector_sensitivity': _SECTOR_SENSITIVITY.get(sector, _DEFAULT_SENSITIVITY),
            'adjusted_overlay': 0,
            'final_score': base_score,
            'final_grade': _get_grade(base_score),
            'overlay_impact': 'neutral',
        }

    sensitivity = _SECTOR_SENSITIVITY.get(sector, _DEFAULT_SENSITIVITY)
    adjusted = round(overlay * sensitivity, 1)
    final = round(max(0, min(100, base_score + adjusted)), 1)

    if adjusted > 0.5:
        impact = 'positive'
    elif adjusted < -0.5:
        impact = 'negative'
    else:
        impact = 'neutral'

    return {
        'original_score': base_score,
        'overlay_applied': overlay,
        'sector': sector,
        'sector_sensitivity': sensitivity,
        'adjusted_overlay': adjusted,
        'final_score': final,
        'final_grade': _get_grade(final),
        'overlay_impact': impact,
    }


# --- 매수구간/매도타점 산출 ---

def _identify_level_name(price, ma_data, bb_data=None, week52_low=None, week52_high=None):
    """가격이 어떤 기술적 레벨에 해당하는지 문자열 반환."""
    tolerance = _LEVEL_TOLERANCE

    if ma_data:
        for key, label in [('ma20', 'MA20'), ('ma60', 'MA60'), ('ma120', 'MA120')]:
            val = ma_data.get(key)
            if val and abs(price - val) / val <= tolerance:
                return f'{label} 지지/저항'

    if bb_data:
        if bb_data.get('lower') and abs(price - bb_data['lower']) / bb_data['lower'] <= tolerance:
            return '볼린저 하단'
        if bb_data.get('upper') and abs(price - bb_data['upper']) / bb_data['upper'] <= tolerance:
            return '볼린저 상단'

    if week52_low and abs(price - week52_low) / week52_low <= tolerance:
        return '52주 저점 근접'
    if week52_high and abs(price - week52_high) / week52_high <= tolerance:
        return '52주 고점 근접'

    return '기술적 레벨'


def calc_rr_ratio(current_price, sell_1_price, stop_loss_price):
    """Risk/Reward Ratio 계산.

    Args:
        current_price: 현재가
        sell_1_price: 1차 목표가
        stop_loss_price: 손절가

    Returns:
        {
            'ratio': float,
            'label': str,
            'expected_profit_pct': float,
            'expected_loss_pct': float,
        }
    """
    expected_profit = sell_1_price - current_price
    expected_loss = current_price - stop_loss_price

    if expected_loss <= 0:
        return {
            'ratio': 99.9,
            'label': '매우 유리',
            'expected_profit_pct': round(expected_profit / current_price * 100, 1),
            'expected_loss_pct': 0.0,
        }

    ratio = round(expected_profit / expected_loss, 2)

    label = '불리 — 진입 재고 필요'
    for threshold in sorted(RR_RATIO_LABELS.keys(), reverse=True):
        if ratio >= threshold:
            label = RR_RATIO_LABELS[threshold]
            break

    return {
        'ratio': ratio,
        'label': label,
        'expected_profit_pct': round(expected_profit / current_price * 100, 1),
        'expected_loss_pct': round(expected_loss / current_price * 100, 1),
    }


def calc_buy_sell_targets(
    current_price,
    grade,
    supports,
    resistances,
    target_mean=None,
    target_high=None,
    target_low=None,
    week52_high=None,
    week52_low=None,
    beta=None,
    ma_data=None,
    bb_data=None,
):
    """매수구간/매도타점 산출.

    Args:
        current_price: 현재가
        grade: 투자 등급 ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL')
        supports: 지지선 목록 (현재가 아래, 내림차순)
        resistances: 저항선 목록 (현재가 위, 오름차순)
        target_mean: 컨센서스 목표가 평균 (None 허용)
        target_high: 컨센서스 목표가 상단 (None 허용)
        target_low: 컨센서스 목표가 하단 (None 허용)
        week52_high: 52주 고가 (None 허용)
        week52_low: 52주 저가 (None 허용)
        beta: 베타 (None 허용)
        ma_data: 이동평균 데이터 (None 허용)
        bb_data: 볼린저 밴드 데이터 (None 허용)

    Returns:
        dict with buy_zone, sell_target, rr_ratio, disclaimer
    """
    display = GRADE_DISPLAY_RULES.get(grade, GRADE_DISPLAY_RULES['HOLD'])
    cfg = BUY_ZONE_CONFIG
    scfg = SELL_TARGET_CONFIG
    ma_data = ma_data or {}
    result = {'disclaimer': DISCLAIMER}

    # ── 매수구간 ──
    buy_zone = None
    buy_1_price = None
    stop_loss_price = None

    if display['show_buy']:
        lo, hi = cfg['buy1_range']
        candidates = []
        for s in supports:
            pct = (s - current_price) / current_price
            if lo >= pct >= hi:
                candidates.append(s)

        if candidates:
            buy_1_price = max(candidates)
            buy_1_reason = _identify_level_name(
                buy_1_price, ma_data, bb_data, week52_low, week52_high)
        else:
            buy_1_price = round(current_price * 0.95)
            buy_1_reason = '현재가 대비 -5% (기본값)'

        # 2차 매수가
        lo2, hi2 = cfg['buy2_range']
        candidates_2 = []
        for s in supports:
            if buy_1_price == 0:
                break
            pct = (s - buy_1_price) / buy_1_price
            if lo2 >= pct >= hi2:
                candidates_2.append(s)

        if candidates_2:
            buy_2_price = max(candidates_2)
            buy_2_reason = _identify_level_name(
                buy_2_price, ma_data, bb_data, week52_low, week52_high)
        else:
            if week52_low and week52_low * cfg['week52_low_buffer'] < buy_1_price:
                buy_2_price = round(week52_low * cfg['week52_low_buffer'])
                buy_2_reason = '52주 저점 × 1.05'
            else:
                buy_2_price = round(buy_1_price * cfg['buy2_fallback_ratio'])
                buy_2_reason = '1차 매수 × 0.93'

        # 손절가
        ma120 = ma_data.get('ma120')
        stop_candidates = []
        if ma120:
            stop_candidates.append(round(ma120 * (1 - cfg['stop_loss_ma_margin'])))
        stop_candidates.append(round(buy_2_price * (1 - cfg['stop_loss_buy2_margin'])))

        stop_loss_price = min(stop_candidates)
        if ma120 and stop_loss_price == round(ma120 * (1 - cfg['stop_loss_ma_margin'])):
            stop_reason = 'MA120 이탈'
        else:
            stop_reason = '2차 매수 -5%'

        buy_zone = {
            'show': True,
            'label': display['buy_label'],
            'buy_1': {
                'price': buy_1_price,
                'pct': round((buy_1_price - current_price) / current_price * 100, 1),
                'reason': buy_1_reason,
            },
            'buy_2': {
                'price': buy_2_price,
                'pct': round((buy_2_price - current_price) / current_price * 100, 1),
                'reason': buy_2_reason,
            },
            'stop_loss': {
                'price': stop_loss_price,
                'pct': round((stop_loss_price - current_price) / current_price * 100, 1),
                'reason': stop_reason,
            },
        }

    result['buy_zone'] = buy_zone

    # ── 매도타점 ──
    sell_target = None

    if display['show_sell']:
        lo_s, hi_s = scfg['sell1_range']

        sell_candidates = []
        if target_mean and target_mean > current_price:
            pct = (target_mean - current_price) / current_price
            if lo_s <= pct <= hi_s:
                sell_candidates.append((target_mean, '컨센서스 목표가 평균'))

        for r in resistances:
            pct = (r - current_price) / current_price
            if lo_s <= pct <= hi_s:
                sell_candidates.append(
                    (r, _identify_level_name(r, ma_data, bb_data, week52_low, week52_high)))

        if sell_candidates:
            sell_candidates.sort(key=lambda x: x[0])
            sell_1_price, sell_1_reason = sell_candidates[0]
        else:
            sell_1_price = round(current_price * 1.10)
            sell_1_reason = '현재가 대비 +10% (기본값)'

        # 2차 목표가
        sell_2_candidates = []
        if target_high and target_high > sell_1_price:
            sell_2_candidates.append((target_high, '컨센서스 목표가 상단'))
        if week52_high and week52_high > sell_1_price:
            sell_2_candidates.append((week52_high, '52주 고가'))
        sell_2_candidates.append(
            (round(sell_1_price * scfg['sell2_multiplier']), '1차 목표 × 1.10'))

        sell_2_candidates.sort(key=lambda x: x[0])
        sell_2_price, sell_2_reason = sell_2_candidates[0]

        # 트레일링 스탑
        if beta and beta > scfg['beta_high_threshold']:
            trailing_pct = scfg['trailing_stop_high_beta']
            trailing_reason = f'고변동성(Beta {beta:.1f}) → 15%'
        elif beta and beta < scfg['beta_low_threshold']:
            trailing_pct = scfg['trailing_stop_low_beta']
            trailing_reason = f'저변동성(Beta {beta:.1f}) → 7%'
        else:
            trailing_pct = scfg['trailing_stop_default']
            trailing_reason = '기본 10%'

        sell_target = {
            'show': True,
            'sell_1': {
                'price': sell_1_price,
                'pct': round((sell_1_price - current_price) / current_price * 100, 1),
                'reason': sell_1_reason,
                'portion': '50%',
            },
            'sell_2': {
                'price': sell_2_price,
                'pct': round((sell_2_price - current_price) / current_price * 100, 1),
                'reason': sell_2_reason,
                'portion': '잔량',
            },
            'trailing_stop': {
                'pct': trailing_pct,
                'reason': trailing_reason,
            },
        }

        # R/R Ratio
        if buy_zone and stop_loss_price:
            rr = calc_rr_ratio(current_price, sell_1_price, stop_loss_price)
        else:
            rr = calc_rr_ratio(current_price, sell_1_price,
                               round(current_price * 0.85))

        result['rr_ratio'] = rr
    else:
        result['rr_ratio'] = None

    result['sell_target'] = sell_target

    return result
