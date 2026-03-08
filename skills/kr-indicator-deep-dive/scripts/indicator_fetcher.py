#!/usr/bin/env python3
"""Indicator Deep-Dive Fetcher - Auto-fetch market indicators via yfinance.

Auto-fetchable (yfinance Tier 1):
  VIX (^VIX), EWY, USD/KRW (KRW=X), KOSPI RSI (^KS11)

WebSearch required:
  CNN Fear & Greed, HY OAS, Put/Call Ratio, VKOSPI
"""

import argparse
import json
import os
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Historical extremes (static reference data)
# ---------------------------------------------------------------------------

_REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'references')
_EXTREMES_PATH = os.path.join(_REF_DIR, 'historical_extremes.json')


def load_historical_extremes():
    """Load historical extreme values from references/historical_extremes.json."""
    if not os.path.exists(_EXTREMES_PATH):
        return {}
    with open(_EXTREMES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# RSI calculation (standalone, no ta library dependency)
# ---------------------------------------------------------------------------

def calculate_rsi(closes, period=14):
    """Calculate RSI(14) from a list of closing prices.

    Uses Wilder's smoothing (exponential moving average).
    Returns None if insufficient data.
    """
    if not closes or len(closes) < period + 1:
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
    return round(100 - (100 / (1 + rs)), 2)


# ---------------------------------------------------------------------------
# Percentile & zone classification
# ---------------------------------------------------------------------------

# Zone definitions per indicator
INDICATOR_ZONES = {
    'VIX': {
        'zones': [
            {'label': '하위 25% (안정)', 'min': 0, 'max': 15},
            {'label': '25~50% (보통)', 'min': 15, 'max': 20},
            {'label': '50~75% (경계)', 'min': 20, 'max': 25},
            {'label': '상위 25% (공포)', 'min': 25, 'max': 999},
        ],
        'signal_thresholds': {'green': 15, 'yellow': 25, 'orange': 35, 'red': 40},
    },
    'EWY': {
        'zones': [],  # EWY uses relative positioning (52w high/low)
        'signal_thresholds': {},
    },
    'USDKRW': {
        'zones': [
            {'label': '안정 (강세)', 'min': 0, 'max': 1100},
            {'label': '보통', 'min': 1100, 'max': 1250},
            {'label': '경계 (약세)', 'min': 1250, 'max': 1400},
            {'label': '위험 (극약세)', 'min': 1400, 'max': 9999},
        ],
        'signal_thresholds': {'green': 1100, 'yellow': 1250, 'orange': 1400, 'red': 1500},
    },
    'KOSPI_RSI': {
        'zones': [
            {'label': '극단적 과매도', 'min': 0, 'max': 20},
            {'label': '과매도', 'min': 20, 'max': 30},
            {'label': '중립', 'min': 30, 'max': 70},
            {'label': '과매수', 'min': 70, 'max': 80},
            {'label': '극단적 과매수', 'min': 80, 'max': 100},
        ],
        'signal_thresholds': {'green': 70, 'yellow': 30, 'orange': 20, 'red': 20},
    },
}


def classify_zone(indicator_name, value):
    """Classify current value into a zone for the given indicator.

    Returns the zone label string, or None if not defined.
    """
    config = INDICATOR_ZONES.get(indicator_name)
    if not config or not config['zones']:
        return None
    for zone in config['zones']:
        if zone['min'] <= value < zone['max']:
            return zone['label']
    return None


def classify_signal(indicator_name, value):
    """Classify signal color (green/yellow/orange/red) for the given indicator.

    Returns one of: 'green', 'yellow', 'orange', 'red', or None.
    """
    config = INDICATOR_ZONES.get(indicator_name)
    if not config or not config['signal_thresholds']:
        return None
    thresholds = config['signal_thresholds']

    if indicator_name == 'VIX':
        if value < thresholds['green']:
            return 'green'
        elif value < thresholds['yellow']:
            return 'yellow'
        elif value < thresholds['orange']:
            return 'orange'
        else:
            return 'red'
    elif indicator_name == 'USDKRW':
        if value < thresholds['green']:
            return 'green'
        elif value < thresholds['yellow']:
            return 'yellow'
        elif value < thresholds['orange']:
            return 'orange'
        else:
            return 'red'
    elif indicator_name == 'KOSPI_RSI':
        if value < thresholds['red']:
            return 'red'
        elif value < thresholds['yellow']:
            return 'orange'
        elif value <= thresholds['green']:
            return 'green'
        else:
            return 'yellow'
    return None


SIGNAL_EMOJI = {
    'green': '🟢',
    'yellow': '🟡',
    'orange': '🟠',
    'red': '🔴',
}

SIGNAL_LABEL_KR = {
    'green': '안정',
    'yellow': '경계',
    'orange': '주의',
    'red': '위험',
}


# ---------------------------------------------------------------------------
# Historical return expectations (static data by zone)
# ---------------------------------------------------------------------------

HISTORICAL_RETURNS = {
    'VIX': {
        '상위 25% (공포)': {
            '1w': {'avg': 0.8, 'win_rate': 58},
            '1m': {'avg': 2.1, 'win_rate': 62},
            '3m': {'avg': 5.4, 'win_rate': 68},
        },
    },
    'KOSPI_RSI': {
        '극단적 과매도': {
            '1w': {'avg': 2.5, 'win_rate': 65},
            '1m': {'avg': 6.0, 'win_rate': 70},
            '3m': {'avg': 12.0, 'win_rate': 75},
        },
        '과매도': {
            '1w': {'avg': 1.2, 'win_rate': 60},
            '1m': {'avg': 3.5, 'win_rate': 65},
            '3m': {'avg': 7.2, 'win_rate': 72},
        },
    },
    'USDKRW': {
        '위험 (극약세)': {
            '1w': {'avg': -0.3, 'win_rate': 45},
            '1m': {'avg': -1.0, 'win_rate': 42},
            '3m': {'avg': -2.5, 'win_rate': 40},
        },
    },
}


def get_historical_returns(indicator_name, zone_label):
    """Get historical return expectations for an indicator in a given zone.

    Returns dict with 1w/1m/3m keys, or None if not available.
    """
    indicator_data = HISTORICAL_RETURNS.get(indicator_name, {})
    return indicator_data.get(zone_label)


# ---------------------------------------------------------------------------
# yfinance data fetching
# ---------------------------------------------------------------------------

YFINANCE_TICKERS = {
    'VIX': '^VIX',
    'EWY': 'EWY',
    'USDKRW': 'KRW=X',
    'KOSPI': '^KS11',
}


def fetch_indicator_data(tickers=None, period='3mo'):
    """Fetch indicator data from yfinance.

    Args:
        tickers: dict of {name: ticker_symbol} or None for all defaults.
        period: yfinance period string (default '3mo' for RSI calculation).

    Returns:
        dict with indicator data including current, prev, change_pct, history.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance",
              file=sys.stderr)
        return None

    if tickers is None:
        tickers = YFINANCE_TICKERS

    results = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period=period)
            if hist.empty or len(hist) < 2:
                results[name] = {'error': f'Insufficient data for {ticker}'}
                continue

            closes = hist['Close'].tolist()
            current = closes[-1]
            prev = closes[-2]
            change_pct = (current - prev) / prev * 100 if prev != 0 else 0

            result = {
                'ticker': ticker,
                'current': round(float(current), 2),
                'prev': round(float(prev), 2),
                'change_pct': round(float(change_pct), 2),
                'week52_high': round(float(hist['Close'].max()), 2),
                'week52_low': round(float(hist['Close'].min()), 2),
                'recent_5d': [round(float(c), 2) for c in closes[-5:]],
            }

            # RSI for KOSPI
            if name == 'KOSPI' and len(closes) >= 15:
                rsi = calculate_rsi(closes)
                result['rsi'] = rsi

            results[name] = result
        except Exception as e:
            results[name] = {'error': str(e)}

    return results


# ---------------------------------------------------------------------------
# Analysis builder
# ---------------------------------------------------------------------------

def build_indicator_analysis(name, data, extremes=None):
    """Build structured analysis for a single indicator.

    Returns dict with keys: name, current, zone, signal, historical_returns, extremes.
    """
    if 'error' in data:
        return {'name': name, 'error': data['error']}

    analysis = {
        'name': name,
        'current': data['current'],
        'prev': data['prev'],
        'change_pct': data['change_pct'],
        'recent_5d': data.get('recent_5d', []),
        'week52_high': data.get('week52_high'),
        'week52_low': data.get('week52_low'),
    }

    # For KOSPI, use RSI value for zone/signal classification
    indicator_key = name
    classify_value = data['current']
    if name == 'KOSPI':
        indicator_key = 'KOSPI_RSI'
        classify_value = data.get('rsi')
        analysis['rsi'] = data.get('rsi')
        if classify_value is None:
            analysis['zone'] = None
            analysis['signal'] = None
            analysis['historical_returns'] = None
            analysis['extremes'] = extremes or []
            return analysis

    # Zone classification
    zone = classify_zone(indicator_key, classify_value)
    analysis['zone'] = zone

    # Signal classification
    signal = classify_signal(indicator_key, classify_value)
    analysis['signal'] = signal
    analysis['signal_emoji'] = SIGNAL_EMOJI.get(signal, '⚪')
    analysis['signal_label'] = SIGNAL_LABEL_KR.get(signal, '미정')

    # Historical returns for current zone
    returns = get_historical_returns(indicator_key, zone)
    analysis['historical_returns'] = returns

    # Historical extremes from reference data
    analysis['extremes'] = extremes or []

    return analysis


def build_dashboard(analyses):
    """Build summary dashboard from multiple indicator analyses.

    Returns dict with indicators list, fear/stable signals, overall assessment.
    """
    fear_signals = []
    stable_signals = []
    caution_signals = []

    for a in analyses:
        if 'error' in a:
            continue
        sig = a.get('signal')
        display = f"{a['name']} ({a['current']})"
        if sig == 'red':
            fear_signals.append(display)
        elif sig == 'orange':
            caution_signals.append(display)
        elif sig == 'green':
            stable_signals.append(display)

    return {
        'indicators': analyses,
        'fear_signals': fear_signals,
        'stable_signals': stable_signals,
        'caution_signals': caution_signals,
        'total': len(analyses),
        'errors': sum(1 for a in analyses if 'error' in a),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_change(value):
    """Format a percentage change with sign."""
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def main():
    parser = argparse.ArgumentParser(
        description='Indicator Deep-Dive Fetcher - Market indicator auto-collection')
    parser.add_argument('--format', choices=['json', 'markdown'],
                        default='markdown',
                        help='Output format (default: markdown)')
    parser.add_argument('--indicators', nargs='*',
                        choices=['VIX', 'EWY', 'USDKRW', 'KOSPI', 'all'],
                        default=['all'],
                        help='Indicators to fetch (default: all)')
    args = parser.parse_args()

    # Select tickers
    if 'all' in args.indicators:
        tickers = YFINANCE_TICKERS
    else:
        tickers = {k: v for k, v in YFINANCE_TICKERS.items()
                   if k in args.indicators}

    # Fetch data
    data = fetch_indicator_data(tickers)
    if not data:
        sys.exit(1)

    # Load historical extremes
    extremes_db = load_historical_extremes()

    # Build analyses
    analyses = []
    for name in tickers:
        if name in data:
            ext = extremes_db.get(name, [])
            analysis = build_indicator_analysis(name, data[name], ext)
            analyses.append(analysis)

    # Build dashboard
    dashboard = build_dashboard(analyses)

    if args.format == 'json':
        output = {
            'dashboard': dashboard,
            'raw_data': data,
            'timestamp': datetime.now().isoformat(),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"# Indicator Deep-Dive Auto-Fetch - {now}")
        print()
        print("## yfinance 자동 수집 결과")
        print()
        print("| 지표 | 현재값 | 전일 대비 | 시그널 | 구간 |")
        print("|------|:------:|:---------:|:------:|------|")
        for a in analyses:
            if 'error' in a:
                print(f"| {a['name']} | ERROR | - | - | {a['error']} |")
                continue
            emoji = a.get('signal_emoji', '⚪')
            label = a.get('signal_label', '-')
            zone = a.get('zone') or '-'
            val = a['current']
            if a['name'] == 'KOSPI' and a.get('rsi') is not None:
                val = f"{a['current']} (RSI {a['rsi']})"
            print(f"| {a['name']} | {val} | "
                  f"{format_change(a['change_pct'])} | "
                  f"{emoji} {label} | {zone} |")

        print()
        if dashboard['fear_signals']:
            print(f"> 🔴 공포 시그널: {', '.join(dashboard['fear_signals'])}")
        if dashboard['stable_signals']:
            print(f"> 🟢 안정 시그널: {', '.join(dashboard['stable_signals'])}")
        print()
        print("> 나머지 지표(CNN F&G, HY OAS, Put/Call, VKOSPI)는 "
              "WebSearch로 수집 필요")


if __name__ == '__main__':
    main()
