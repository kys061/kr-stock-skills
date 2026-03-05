"""kr-growth-outlook: Management/governance quality scorer."""


# --- Execution track record ---

GUIDANCE_ACCURACY = {'high': 80, 'moderate': 55, 'low': 30}
STRATEGY_DELIVERY = {'strong': 85, 'moderate': 55, 'weak': 25}
CRISIS_MANAGEMENT = {'proven': 80, 'untested': 50, 'failed': 15}

# --- Capital allocation ---

DIVIDEND_CONSISTENCY = {'strong': 80, 'moderate': 55, 'weak': 30}
BUYBACK_DISCIPLINE = {'active': 75, 'occasional': 50, 'none': 30}
MA_TRACK_RECORD = {'value_creating': 85, 'neutral': 50, 'value_destroying': 15}

# --- Governance (KR specific) ---

CHAEBOL_DISCOUNT = {'independent': 80, 'partial': 50, 'controlled': 25}
BOARD_INDEPENDENCE = {'high': 80, 'moderate': 55, 'low': 25}
SUCCESSION_PLAN = {'clear': 80, 'developing': 50, 'none': 20}

# --- Management component weights ---

MANAGEMENT_WEIGHTS = {
    'execution': 0.40,
    'capital_allocation': 0.35,
    'governance': 0.25,
}
# Sum: 0.40+0.35+0.25 = 1.00


def score_execution(execution_data):
    """Management execution track record -> 0-100 score."""
    scores = []

    guidance = execution_data.get('guidance_accuracy')
    if guidance:
        scores.append(float(GUIDANCE_ACCURACY.get(str(guidance).lower(), 55)))

    strategy = execution_data.get('strategy_delivery')
    if strategy:
        scores.append(float(STRATEGY_DELIVERY.get(str(strategy).lower(), 55)))

    crisis = execution_data.get('crisis_management')
    if crisis:
        scores.append(float(CRISIS_MANAGEMENT.get(str(crisis).lower(), 50)))

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_capital_allocation(data):
    """Capital allocation quality score."""
    scores = []

    dividend = data.get('dividend_consistency')
    if dividend:
        scores.append(float(DIVIDEND_CONSISTENCY.get(str(dividend).lower(), 55)))

    buyback = data.get('buyback_discipline')
    if buyback:
        scores.append(float(BUYBACK_DISCIPLINE.get(str(buyback).lower(), 50)))

    ma = data.get('ma_track_record')
    if ma:
        scores.append(float(MA_TRACK_RECORD.get(str(ma).lower(), 50)))

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _score_governance(data):
    """Governance quality score (KR-specific)."""
    scores = []

    chaebol = data.get('chaebol_discount')
    if chaebol:
        scores.append(float(CHAEBOL_DISCOUNT.get(str(chaebol).lower(), 50)))

    board = data.get('board_independence')
    if board:
        scores.append(float(BOARD_INDEPENDENCE.get(str(board).lower(), 55)))

    succession = data.get('succession_plan')
    if succession:
        scores.append(float(SUCCESSION_PLAN.get(str(succession).lower(), 50)))

    return round(sum(scores) / len(scores), 1) if scores else 50.0


def analyze_management(mgmt_data):
    """Management comprehensive analysis.

    Args:
        mgmt_data: {guidance_accuracy, strategy_delivery, crisis_management,
                     dividend_consistency, buyback_discipline, ma_track_record,
                     chaebol_discount, board_independence, succession_plan}

    Returns:
        {'execution_score', 'capital_score', 'governance_score', 'score'}
    """
    execution_score = score_execution(mgmt_data)
    capital_score = _score_capital_allocation(mgmt_data)
    governance_score = _score_governance(mgmt_data)

    total = (execution_score * MANAGEMENT_WEIGHTS['execution']
             + capital_score * MANAGEMENT_WEIGHTS['capital_allocation']
             + governance_score * MANAGEMENT_WEIGHTS['governance'])

    return {
        'execution_score': round(execution_score, 1),
        'capital_score': round(capital_score, 1),
        'governance_score': round(governance_score, 1),
        'score': round(total, 1),
    }
