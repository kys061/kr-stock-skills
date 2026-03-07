#!/usr/bin/env python3
"""Rebound Signal Checker - 14 bounce signals for Korean market crash recovery.

Automated checks (yfinance):
  #1  VIX -10% reversal
  #4  EWY +1% rebound
  #5  S&P futures positive
  #11 USD/KRW decline
  #12 KOSPI RSI < 30

Manual/WebSearch required:
  #2  CNN Fear & Greed < 20
  #3  Put/Call Ratio > 1.0
  #6  Insider cluster buys >= 10
  #7  Foreign net buy reversal
  #8  Short selling balance decline
  #9  Credit balance -30% from peak
  #10 HY spread contraction
  #13 Government stabilization measures
  #14 News tone shift
"""

import argparse
import json
import sys
from datetime import datetime


def check_vix_reversal(current, prev):
    """Check if VIX dropped more than 10% from previous day."""
    if prev == 0:
        return None
    change_pct = (current - prev) / prev * 100
    return change_pct <= -10.0, round(change_pct, 2)


def check_ewy_rebound(change_pct):
    """Check if EWY rebounded more than 1%."""
    return change_pct >= 1.0


def check_sp_futures_positive(change_pct):
    """Check if S&P 500 futures are positive."""
    return change_pct > 0


def check_cnn_fg_extreme_fear(fg_value):
    """Check if CNN Fear & Greed Index is below 20 (Extreme Fear)."""
    return fg_value < 20


def check_put_call_ratio(pc_ratio):
    """Check if CBOE Put/Call Ratio exceeds 1.0."""
    return pc_ratio > 1.0


def check_usdkrw_decline(change_pct):
    """Check if USD/KRW is declining (KRW strengthening)."""
    return change_pct < 0


def check_kospi_rsi(rsi_value):
    """Check if KOSPI RSI(14) is below 30 (oversold)."""
    return rsi_value < 30


def check_hy_spread_contraction(current, prev):
    """Check if High Yield spread is contracting."""
    return current < prev


def check_credit_balance_drop(current, peak, threshold=30):
    """Check if credit balance dropped threshold% or more from peak."""
    if peak == 0:
        return None
    drop_pct = (peak - current) / peak * 100
    return drop_pct >= threshold, round(drop_pct, 2)


def check_insider_cluster(buy_count, threshold=10):
    """Check if insider cluster buys exceed threshold (7-day window)."""
    return buy_count >= threshold


def calculate_rsi(closes, period=14):
    """Calculate RSI from a list of closing prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def overall_judgment(yes_count):
    """Return overall judgment based on YES count."""
    if yes_count >= 7:
        return "역사적 반등 가능성"
    elif yes_count >= 5:
        return "적극 매수 고려"
    elif yes_count >= 3:
        return "분할 매수 고려"
    else:
        return "관망 유지"


def format_change(value):
    """Format a percentage change with sign."""
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def fetch_yfinance_data():
    """Fetch automated signals from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance",
              file=sys.stderr)
        return None

    results = {}
    tickers = {
        'VIX': '^VIX',
        'EWY': 'EWY',
        'ES': 'ES=F',
        'USDKRW': 'KRW=X',
        'KOSPI': '^KS11',
    }

    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period='1mo')
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change_pct = (current - prev) / prev * 100
                results[name] = {
                    'current': round(float(current), 2),
                    'prev': round(float(prev), 2),
                    'change_pct': round(float(change_pct), 2),
                }
                if name == 'KOSPI' and len(hist) >= 15:
                    rsi = calculate_rsi(hist['Close'].tolist())
                    results[name]['rsi'] = rsi
        except Exception as e:
            results[name] = {'error': str(e)}

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Rebound Signal Checker - 14 bounce signals')
    parser.add_argument('--format', choices=['json', 'markdown'],
                        default='markdown')
    args = parser.parse_args()

    data = fetch_yfinance_data()
    if not data:
        sys.exit(1)

    signals = {}

    # #1 VIX reversal
    if 'VIX' in data and 'error' not in data['VIX']:
        vix = data['VIX']
        result = vix['change_pct'] <= -10.0
        signals['vix_reversal'] = {
            'num': 1, 'name': 'VIX -10% 급락', 'category': '공포 심리',
            'result': result, 'value': vix['current'],
            'detail': format_change(vix['change_pct']), 'source': 'yfinance',
        }

    # #4 EWY rebound
    if 'EWY' in data and 'error' not in data['EWY']:
        ewy = data['EWY']
        result = ewy['change_pct'] >= 1.0
        signals['ewy_rebound'] = {
            'num': 4, 'name': 'EWY +1% 반등', 'category': '야간 선행',
            'result': result, 'value': ewy['current'],
            'detail': format_change(ewy['change_pct']), 'source': 'yfinance',
        }

    # #5 S&P futures positive
    if 'ES' in data and 'error' not in data['ES']:
        es = data['ES']
        result = es['change_pct'] > 0
        signals['sp_futures'] = {
            'num': 5, 'name': 'S&P선물 양전', 'category': '야간 선행',
            'result': result, 'value': es['current'],
            'detail': format_change(es['change_pct']), 'source': 'yfinance',
        }

    # #11 USD/KRW decline
    if 'USDKRW' in data and 'error' not in data['USDKRW']:
        usdkrw = data['USDKRW']
        result = usdkrw['change_pct'] < 0
        signals['usdkrw_decline'] = {
            'num': 11, 'name': 'USD/KRW 하락', 'category': '채권',
            'result': result, 'value': usdkrw['current'],
            'detail': format_change(usdkrw['change_pct']), 'source': 'yfinance',
        }

    # #12 KOSPI RSI < 30
    if 'KOSPI' in data and 'error' not in data['KOSPI']:
        kospi = data['KOSPI']
        rsi = kospi.get('rsi')
        if rsi is not None:
            result = rsi < 30
            signals['kospi_rsi'] = {
                'num': 12, 'name': 'KOSPI RSI<30', 'category': '기술적',
                'result': result, 'value': kospi['current'],
                'detail': f"RSI={rsi}", 'source': 'yfinance',
            }

    if args.format == 'json':
        output = {'signals': signals, 'raw': data,
                  'timestamp': datetime.now().isoformat()}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"# Rebound Signal Check - {now}")
        print()
        print("## yfinance 자동 수집 결과 (5/14)")
        print()
        print("| # | 카테고리 | 시그널 | 결과 | 근거 데이터 | 출처 |")
        print("|---|----------|--------|------|------------|------|")
        for sig in sorted(signals.values(), key=lambda x: x['num']):
            r = "YES" if sig['result'] else "NO"
            print(f"| {sig['num']} | {sig['category']} | {sig['name']} "
                  f"| {r} | {sig['value']} ({sig['detail']}) | {sig['source']} |")
        print()
        yes_count = sum(1 for s in signals.values() if s['result'])
        print(f"> 자동 수집 YES: {yes_count}/{len(signals)}")
        print(f"> 나머지 9개 시그널(#2,3,6,7,8,9,10,13,14)은 "
              f"WebSearch/WebFetch로 수집 필요")


if __name__ == '__main__':
    main()
