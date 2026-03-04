"""kr-dart-disclosure-monitor: 지분 변동 추적."""


# ─── 지분 변동 추적 ───

STAKE_CHANGE_CONFIG = {
    'major_threshold': 0.05,        # 5% 대량보유 보고 기준
    'significant_change': 0.01,     # 1%p 이상 변동: 유의미
    'accumulation_days': 5,         # 5건 이상 매수: 축적 패턴
    'disposal_days': 5,             # 5건 이상 매도: 매각 패턴
}

STAKE_SIGNALS = {
    'ACCUMULATION': {'label': '지분 축적', 'direction': 'buy', 'sentiment': 'positive'},
    'DISPOSAL': {'label': '지분 매각', 'direction': 'sell', 'sentiment': 'negative'},
    'TREASURY_BUY': {'label': '자사주 매입', 'direction': 'buy', 'sentiment': 'positive'},
    'TREASURY_SELL': {'label': '자사주 매각', 'direction': 'sell', 'sentiment': 'negative'},
    'NEUTRAL': {'label': '변동 없음', 'direction': 'none', 'sentiment': 'neutral'},
}

INSIDER_TYPES = [
    'ceo',               # 대표이사
    'executive',         # 임원
    'major_shareholder', # 최대주주/특수관계인
    'related_party',     # 특수관계법인
]


def track_stake_changes(major_holders_data):
    """대량보유(5%) 지분 변동 추적.

    Args:
        major_holders_data: list of dict
            [{holder, before_pct, after_pct, change_pct, date}]

    Returns:
        dict: {changes, signal, pattern, significant_changes}
    """
    if not major_holders_data:
        return {
            'changes': [],
            'signal': 'NEUTRAL',
            'pattern': None,
            'significant_changes': [],
        }

    cfg = STAKE_CHANGE_CONFIG
    significant = []
    buy_count = 0
    sell_count = 0

    for change in major_holders_data:
        change_pct = change.get('change_pct', 0)
        if change_pct is None:
            # before/after로 계산
            before = change.get('before_pct', 0) or 0
            after = change.get('after_pct', 0) or 0
            change_pct = after - before

        if abs(change_pct) >= cfg['significant_change']:
            significant.append(change)
            if change_pct > 0:
                buy_count += 1
            elif change_pct < 0:
                sell_count += 1

    # 시그널 분류
    if buy_count >= cfg['accumulation_days']:
        signal = 'ACCUMULATION'
        pattern = 'consecutive_buying'
    elif sell_count >= cfg['disposal_days']:
        signal = 'DISPOSAL'
        pattern = 'consecutive_selling'
    elif buy_count > sell_count and buy_count >= 2:
        signal = 'ACCUMULATION'
        pattern = 'net_buying'
    elif sell_count > buy_count and sell_count >= 2:
        signal = 'DISPOSAL'
        pattern = 'net_selling'
    else:
        signal = 'NEUTRAL'
        pattern = None

    return {
        'changes': major_holders_data,
        'signal': signal,
        'pattern': pattern,
        'significant_changes': significant,
    }


def track_insider_trades(officer_data):
    """임원/내부자 거래 추적.

    Args:
        officer_data: list of dict
            [{name, position, type, shares, amount, date}]

    Returns:
        dict: {trades, net_direction, signal, summary}
    """
    if not officer_data:
        return {
            'trades': [],
            'net_direction': 'none',
            'signal': 'NEUTRAL',
            'summary': {'buy_count': 0, 'sell_count': 0, 'net_amount': 0},
        }

    buy_count = 0
    sell_count = 0
    buy_amount = 0
    sell_amount = 0

    for trade in officer_data:
        trade_type = trade.get('type', '').lower()
        amount = trade.get('amount', 0) or 0

        if trade_type in ('buy', '매수', 'acquisition'):
            buy_count += 1
            buy_amount += amount
        elif trade_type in ('sell', '매도', 'disposal'):
            sell_count += 1
            sell_amount += amount

    net_amount = buy_amount - sell_amount
    net_direction = 'buy' if net_amount > 0 else ('sell' if net_amount < 0 else 'none')

    # 시그널
    if buy_count >= 3 and net_amount > 0:
        signal = 'ACCUMULATION'
    elif sell_count >= 3 and net_amount < 0:
        signal = 'DISPOSAL'
    else:
        signal = 'NEUTRAL'

    return {
        'trades': officer_data,
        'net_direction': net_direction,
        'signal': signal,
        'summary': {
            'buy_count': buy_count,
            'sell_count': sell_count,
            'net_amount': net_amount,
        },
    }


def track_treasury_stock(treasury_data):
    """자사주 매매 추적.

    Args:
        treasury_data: list of dict [{type, shares, amount, date}]

    Returns:
        dict: {actions, signal, total_buy, total_sell}
    """
    if not treasury_data:
        return {
            'actions': [],
            'signal': 'NEUTRAL',
            'total_buy': 0,
            'total_sell': 0,
        }

    total_buy = 0
    total_sell = 0

    for action in treasury_data:
        action_type = action.get('type', '').lower()
        shares = action.get('shares', 0) or 0

        if action_type in ('buy', '취득', 'acquisition'):
            total_buy += shares
        elif action_type in ('sell', '처분', 'disposal'):
            total_sell += shares

    if total_buy > total_sell:
        signal = 'TREASURY_BUY'
    elif total_sell > total_buy:
        signal = 'TREASURY_SELL'
    else:
        signal = 'NEUTRAL'

    return {
        'actions': treasury_data,
        'signal': signal,
        'total_buy': total_buy,
        'total_sell': total_sell,
    }
