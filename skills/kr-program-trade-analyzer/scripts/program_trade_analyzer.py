"""kr-program-trade-analyzer: 프로그램 매매 분석."""


# ─── 프로그램 매매 ───

PROGRAM_TRADE_CONFIG = {
    'trade_types': ['arbitrage', 'non_arbitrage'],
    'flow_periods': [1, 5, 20],  # 일, 주, 월
}

# 차익거래 기준 (KOSPI200 선물-현물)
ARBITRAGE_CONFIG = {
    'significant_amount': 500_000_000_000,   # 5000억: 유의미한 차익거래
    'large_amount': 1_000_000_000_000,       # 1조: 대규모
    'direction_signals': {
        'buy_arb': '선물 매도 + 현물 매수 (콘탱고 해소)',
        'sell_arb': '선물 매수 + 현물 매도 (백워데이션 해소)',
    },
}

# 비차익거래 기준
NON_ARBITRAGE_CONFIG = {
    'significant_amount': 300_000_000_000,   # 3000억: 유의미한 바스켓 매매
    'large_amount': 500_000_000_000,         # 5000억: 대규모
    'warning_consecutive': 5,                # 5일 연속 매도 → 경고
}

PROGRAM_FLOW_SIGNALS = {
    'STRONG_BUY': {'min_score': 80, 'label': '강한 프로그램 매수'},
    'BUY': {'min_score': 60, 'label': '프로그램 매수'},
    'NEUTRAL': {'min_score': 40, 'label': '중립'},
    'SELL': {'min_score': 20, 'label': '프로그램 매도'},
    'STRONG_SELL': {'min_score': 0, 'label': '강한 프로그램 매도'},
}


def _classify_arb_flow(net_amount):
    """차익거래 순매수 강도 분류."""
    if net_amount is None:
        return 'neutral', 50
    abs_val = abs(net_amount)
    is_buy = net_amount > 0

    if abs_val >= ARBITRAGE_CONFIG['large_amount']:
        return ('strong_buy' if is_buy else 'strong_sell'), (90 if is_buy else 10)
    elif abs_val >= ARBITRAGE_CONFIG['significant_amount']:
        return ('buy' if is_buy else 'sell'), (70 if is_buy else 30)
    return 'neutral', 50


def _classify_non_arb_flow(net_amount):
    """비차익거래 순매수 강도 분류."""
    if net_amount is None:
        return 'neutral', 50
    abs_val = abs(net_amount)
    is_buy = net_amount > 0

    if abs_val >= NON_ARBITRAGE_CONFIG['large_amount']:
        return ('strong_buy' if is_buy else 'strong_sell'), (90 if is_buy else 10)
    elif abs_val >= NON_ARBITRAGE_CONFIG['significant_amount']:
        return ('buy' if is_buy else 'sell'), (70 if is_buy else 30)
    return 'neutral', 50


def _count_consecutive_sell(program_data, trade_type='non_arbitrage'):
    """비차익 연속 매도 일수.

    Args:
        program_data: list of dict (최근순).
        trade_type: 'arbitrage' 또는 'non_arbitrage'.

    Returns:
        int: 연속 매도 일수.
    """
    count = 0
    buy_key = f'{trade_type.replace("_", "")}_buy' if '_' in trade_type else f'{trade_type}_buy'
    sell_key = f'{trade_type.replace("_", "")}_sell' if '_' in trade_type else f'{trade_type}_sell'

    # 단순화: non_arb_buy, non_arb_sell 키 사용
    for d in program_data:
        buy = d.get('non_arb_buy', d.get('nonarbitrage_buy', 0)) or 0
        sell = d.get('non_arb_sell', d.get('nonarbitrage_sell', 0)) or 0
        if sell > buy:
            count += 1
        else:
            break
    return count


def classify_program_signal(arb_net, non_arb_net):
    """프로그램 매매 시그널 분류.

    Args:
        arb_net: 차익 순매수 금액.
        non_arb_net: 비차익 순매수 금액.

    Returns:
        str: 'STRONG_BUY' / 'BUY' / 'NEUTRAL' / 'SELL' / 'STRONG_SELL'
    """
    _, arb_score = _classify_arb_flow(arb_net)
    _, non_arb_score = _classify_non_arb_flow(non_arb_net)

    # 비차익 비중 더 높음 (60:40)
    combined = arb_score * 0.40 + non_arb_score * 0.60

    for signal, cfg in PROGRAM_FLOW_SIGNALS.items():
        if combined >= cfg['min_score']:
            return signal
    return 'STRONG_SELL'


def analyze_program_trades(program_data):
    """프로그램 매매 종합 분석.

    Args:
        program_data: list of dict [{date, arb_buy, arb_sell, non_arb_buy, non_arb_sell}]
                      최근순 정렬.

    Returns:
        dict: {arbitrage, non_arbitrage, total, signal, consecutive_sell,
               arb_score, non_arb_score, combined_score}
    """
    if not program_data:
        return {
            'arbitrage': {'net': 0, 'classification': 'neutral', 'score': 50},
            'non_arbitrage': {'net': 0, 'classification': 'neutral', 'score': 50},
            'total': 0,
            'signal': 'NEUTRAL',
            'consecutive_sell': 0,
            'combined_score': 50,
        }

    latest = program_data[0]

    # 차익
    arb_buy = latest.get('arb_buy', 0) or 0
    arb_sell = latest.get('arb_sell', 0) or 0
    arb_net = arb_buy - arb_sell
    arb_class, arb_score = _classify_arb_flow(arb_net)

    # 비차익
    non_arb_buy = latest.get('non_arb_buy', 0) or 0
    non_arb_sell = latest.get('non_arb_sell', 0) or 0
    non_arb_net = non_arb_buy - non_arb_sell
    non_arb_class, non_arb_score = _classify_non_arb_flow(non_arb_net)

    total = arb_net + non_arb_net

    # 시그널
    signal = classify_program_signal(arb_net, non_arb_net)

    # 비차익 연속 매도
    consecutive_sell = _count_consecutive_sell(program_data)

    combined = round(arb_score * 0.40 + non_arb_score * 0.60, 1)

    return {
        'arbitrage': {'net': arb_net, 'classification': arb_class, 'score': arb_score},
        'non_arbitrage': {'net': non_arb_net, 'classification': non_arb_class, 'score': non_arb_score},
        'total': total,
        'signal': signal,
        'consecutive_sell': consecutive_sell,
        'combined_score': combined,
    }
