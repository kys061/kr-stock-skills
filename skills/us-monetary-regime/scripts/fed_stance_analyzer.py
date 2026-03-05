"""us-monetary-regime: Fed 통화정책 기조 분석."""


# --- Stance Weights (sum = 1.00) ---

STANCE_WEIGHTS = {
    'fomc_tone': 0.40,
    'dot_plot': 0.25,
    'qt_qe': 0.20,
    'speakers': 0.15,
}

# --- FOMC Tone Mapping (-100 ~ +100) ---

FOMC_TONE_MAP = {
    'hawkish': -80,
    'slightly_hawkish': -40,
    'neutral': 0,
    'slightly_dovish': 40,
    'dovish': 80,
}

# --- Dot Plot Direction Mapping ---

DOT_PLOT_MAP = {
    'higher': -70,
    'stable': 0,
    'lower': 70,
}

# --- QT/QE Status Mapping ---

QT_QE_MAP = {
    'active_qt': -80,
    'tapering_qt': -40,
    'neutral': 0,
    'tapering_qe': 40,
    'active_qe': 80,
}

# --- Stance Labels ---

STANCE_LABELS = {
    'very_hawkish': (-100, -60),
    'hawkish': (-60, -20),
    'neutral': (-20, 20),
    'dovish': (20, 60),
    'very_dovish': (60, 100),
}

STANCE_DESCRIPTIONS = {
    'very_hawkish': '극단적 긴축 기조. QT 가속, 75bp+ 인상 가능성.',
    'hawkish': '긴축 기조. 25-50bp 인상 또는 QT 유지.',
    'neutral': '중립/관망. 방향 탐색 중.',
    'dovish': '완화 기조. 25-50bp 인하 또는 QT 감속.',
    'very_dovish': '극단적 완화. QE 재개 또는 50bp+ 인하.',
}


def _classify_stance(score):
    """점수 -> 기조 라벨 분류."""
    for label, (low, high) in STANCE_LABELS.items():
        if low <= score <= high:
            return label
    if score < -100:
        return 'very_hawkish'
    return 'very_dovish'


def analyze_fed_stance(fomc_tone='neutral', dot_plot='stable',
                       qt_qe='neutral', speaker_tone=0.0):
    """Fed 통화정책 기조 분석.

    Args:
        fomc_tone: str, FOMC 성명서 톤.
            Options: 'hawkish', 'slightly_hawkish', 'neutral',
                     'slightly_dovish', 'dovish'
        dot_plot: str, 점도표 방향.
            Options: 'higher', 'stable', 'lower'
        qt_qe: str, QT/QE 상태.
            Options: 'active_qt', 'tapering_qt', 'neutral',
                     'tapering_qe', 'active_qe'
        speaker_tone: float, Fed 위원 평균 발언 톤 (-1.0 ~ +1.0).

    Returns:
        dict: {stance_score, stance_label, components, description}
    """
    # 입력 검증
    speaker_tone = max(-1.0, min(1.0, float(speaker_tone)))

    # 각 컴포넌트 점수
    fomc_score = FOMC_TONE_MAP.get(fomc_tone, 0)
    dot_score = DOT_PLOT_MAP.get(dot_plot, 0)
    qt_score = QT_QE_MAP.get(qt_qe, 0)
    speaker_score = speaker_tone * 100  # -1~+1 -> -100~+100

    # 가중 합산
    weighted = (
        fomc_score * STANCE_WEIGHTS['fomc_tone'] +
        dot_score * STANCE_WEIGHTS['dot_plot'] +
        qt_score * STANCE_WEIGHTS['qt_qe'] +
        speaker_score * STANCE_WEIGHTS['speakers']
    )

    # 범위 제한
    stance_score = round(max(-100, min(100, weighted)), 1)

    # 라벨 분류
    stance_label = _classify_stance(stance_score)

    return {
        'stance_score': stance_score,
        'stance_label': stance_label,
        'components': {
            'fomc_tone': {
                'raw': fomc_tone,
                'score': fomc_score,
                'weight': STANCE_WEIGHTS['fomc_tone'],
            },
            'dot_plot': {
                'raw': dot_plot,
                'score': dot_score,
                'weight': STANCE_WEIGHTS['dot_plot'],
            },
            'qt_qe': {
                'raw': qt_qe,
                'score': qt_score,
                'weight': STANCE_WEIGHTS['qt_qe'],
            },
            'speakers': {
                'raw': speaker_tone,
                'score': speaker_score,
                'weight': STANCE_WEIGHTS['speakers'],
            },
        },
        'description': STANCE_DESCRIPTIONS.get(stance_label, ''),
    }
