#!/usr/bin/env python3
"""Recovery Tracker — Track post-crash market recovery via yfinance.

Auto-fetchable (yfinance Tier 1):
  KOSPI (^KS11), VIX (^VIX), EWY, USD/KRW (KRW=X)

WebSearch required:
  CNN Fear & Greed, 외국인 수급, 뉴스 톤
"""

import argparse
import json
import os
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

_REF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'references')
_STAGES_PATH = os.path.join(_REF_DIR, 'recovery_stages.json')


def load_recovery_stages():
    """Load recovery stage definitions from references/recovery_stages.json."""
    if not os.path.exists(_STAGES_PATH):
        return _default_stages()
    with open(_STAGES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _default_stages():
    """Fallback stage definitions when reference file is missing."""
    return {
        'stages': [
            {'stage': 1, 'name': '패닉', 'vix_range': [35, 999],
             'recovery_ratio_range': [0, 10]},
            {'stage': 2, 'name': '기술적 반등', 'vix_range': [25, 35],
             'recovery_ratio_range': [10, 50]},
            {'stage': 3, 'name': '안정화', 'vix_range': [20, 25],
             'recovery_ratio_range': [50, 75]},
            {'stage': 4, 'name': '추세 회복', 'vix_range': [15, 20],
             'recovery_ratio_range': [75, 95]},
            {'stage': 5, 'name': '완전 회복', 'vix_range': [0, 15],
             'recovery_ratio_range': [95, 100]},
        ],
        'stage3_conditions': {
            'conditions': [
                {'id': 'vix', 'operator': '<', 'threshold': 25},
                {'id': 'usdkrw_pct', 'operator': '<', 'threshold': 3},
                {'id': 'cnn_fg', 'operator': '>', 'threshold': 35},
                {'id': 'foreign_flow', 'operator': '==', 'threshold': '순매수'},
                {'id': 'recovery_ratio', 'operator': '>', 'threshold': 60},
                {'id': 'daily_volatility', 'operator': '<', 'threshold': 3},
            ],
            'min_conditions_met': 4,
        },
    }


# ---------------------------------------------------------------------------
# RSI calculation (standalone)
# ---------------------------------------------------------------------------

def calculate_rsi(closes, period=14):
    """Calculate RSI(14) from a list of closing prices.

    Uses Wilder's smoothing. Returns None if insufficient data.
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
# Recovery calculations
# ---------------------------------------------------------------------------

def calculate_recovery(pre_crisis, bottom, current):
    """Calculate recovery metrics.

    Args:
        pre_crisis: KOSPI value before the crisis.
        bottom: KOSPI lowest point during crisis.
        current: Current KOSPI value.

    Returns:
        dict with total_drop, recovery_amount, recovery_ratio,
        remaining_loss_pct, drop_pct, rebound_pct.
    """
    if pre_crisis is None or bottom is None or current is None:
        return None
    if pre_crisis <= 0 or bottom <= 0:
        return None

    total_drop = pre_crisis - bottom
    recovery_amount = current - bottom
    recovery_ratio = (recovery_amount / total_drop * 100) if total_drop > 0 else 0
    drop_pct = (bottom - pre_crisis) / pre_crisis * 100
    rebound_pct = (current - bottom) / bottom * 100
    remaining_pct = (current - pre_crisis) / pre_crisis * 100

    return {
        'pre_crisis': pre_crisis,
        'bottom': bottom,
        'current': current,
        'total_drop': round(total_drop, 2),
        'recovery_amount': round(recovery_amount, 2),
        'recovery_ratio': round(recovery_ratio, 1),
        'drop_pct': round(drop_pct, 1),
        'rebound_pct': round(rebound_pct, 1),
        'remaining_loss_pct': round(remaining_pct, 1),
    }


def classify_stage(vix, recovery_ratio, stages_data=None):
    """Classify current recovery stage (1-5).

    Uses VIX and recovery ratio as primary classification inputs.
    Returns (stage_number, stage_name) tuple.
    """
    if stages_data is None:
        stages_data = _default_stages()

    stages = stages_data.get('stages', [])

    # Primary: VIX-based classification
    for stage in stages:
        vix_min, vix_max = stage['vix_range']
        if vix_min <= vix < vix_max:
            return stage['stage'], stage['name']

    # Fallback: recovery ratio based
    if recovery_ratio is not None:
        for stage in stages:
            rr_min, rr_max = stage['recovery_ratio_range']
            if rr_min <= recovery_ratio < rr_max:
                return stage['stage'], stage['name']

    # Default to stage 2 if unclassifiable
    return 2, '기술적 반등'


def check_stage3_conditions(conditions_data, current_values):
    """Check how many Stage 3 conditions are met.

    Args:
        conditions_data: dict with 'conditions' list and 'min_conditions_met'.
        current_values: dict with current indicator values keyed by condition id.

    Returns:
        dict with met_count, total, required, conditions_detail list.
    """
    conditions = conditions_data.get('conditions', [])
    required = conditions_data.get('min_conditions_met', 4)
    results = []

    for cond in conditions:
        cid = cond['id']
        current = current_values.get(cid)
        threshold = cond['threshold']
        op = cond['operator']

        if current is None:
            met = False
        elif op == '<':
            met = current < threshold
        elif op == '>':
            met = current > threshold
        elif op == '==':
            met = current == threshold
        elif op == '>=':
            met = current >= threshold
        elif op == '<=':
            met = current <= threshold
        else:
            met = False

        results.append({
            'id': cid,
            'name': cond.get('name', cid),
            'current': current,
            'threshold': threshold,
            'operator': op,
            'met': met,
        })

    met_count = sum(1 for r in results if r['met'])
    return {
        'met_count': met_count,
        'total': len(conditions),
        'required': required,
        'stage3_reached': met_count >= required,
        'conditions': results,
    }


# ---------------------------------------------------------------------------
# Signal classification
# ---------------------------------------------------------------------------

SIGNAL_THRESHOLDS = {
    'VIX': {'green': 20, 'yellow': 25, 'orange': 35, 'red': 40},
    'USDKRW': {'green': 1200, 'yellow': 1350, 'orange': 1450, 'red': 1500},
    'RECOVERY': {'red': 20, 'orange': 40, 'yellow': 60, 'green': 80},
}

SIGNAL_EMOJI = {
    'green': '🟢',
    'yellow': '🟡',
    'orange': '🟠',
    'red': '🔴',
}


def classify_signal(indicator, value):
    """Classify signal color for a recovery indicator.

    Returns one of: 'green', 'yellow', 'orange', 'red', or None.
    """
    if indicator == 'VIX':
        t = SIGNAL_THRESHOLDS['VIX']
        if value < t['green']:
            return 'green'
        elif value < t['yellow']:
            return 'yellow'
        elif value < t['orange']:
            return 'orange'
        return 'red'
    elif indicator == 'USDKRW':
        t = SIGNAL_THRESHOLDS['USDKRW']
        if value < t['green']:
            return 'green'
        elif value < t['yellow']:
            return 'yellow'
        elif value < t['orange']:
            return 'orange'
        elif value < t['red']:
            return 'orange'
        return 'red'
    elif indicator == 'RECOVERY':
        t = SIGNAL_THRESHOLDS['RECOVERY']
        if value < t['red']:
            return 'red'
        elif value < t['orange']:
            return 'orange'
        elif value < t['yellow']:
            return 'yellow'
        return 'green'
    return None


# ---------------------------------------------------------------------------
# yfinance data fetching
# ---------------------------------------------------------------------------

YFINANCE_TICKERS = {
    'KOSPI': '^KS11',
    'VIX': '^VIX',
    'EWY': 'EWY',
    'USDKRW': 'KRW=X',
}


def fetch_recovery_data(tickers=None, period='3mo'):
    """Fetch recovery indicator data from yfinance.

    Returns dict with indicator data including current, prev, change_pct, history.
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
                'period_high': round(float(hist['Close'].max()), 2),
                'period_low': round(float(hist['Close'].min()), 2),
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
# Recovery analysis builder
# ---------------------------------------------------------------------------

def build_recovery_analysis(data, pre_crisis=None, bottom=None):
    """Build complete recovery analysis from fetched data.

    Args:
        data: dict from fetch_recovery_data().
        pre_crisis: pre-crisis KOSPI value (optional, auto-detected from period_high).
        bottom: crisis bottom KOSPI value (optional, auto-detected from period_low).

    Returns:
        dict with recovery metrics, stage classification, conditions check.
    """
    kospi_data = data.get('KOSPI', {})
    vix_data = data.get('VIX', {})

    # Auto-detect pre_crisis and bottom if not provided
    if pre_crisis is None and 'period_high' in kospi_data:
        pre_crisis = kospi_data['period_high']
    if bottom is None and 'period_low' in kospi_data:
        bottom = kospi_data['period_low']

    current_kospi = kospi_data.get('current')
    current_vix = vix_data.get('current', 25)

    # Recovery calculation
    recovery = calculate_recovery(pre_crisis, bottom, current_kospi)

    # Stage classification
    stages_data = load_recovery_stages()
    recovery_ratio = recovery['recovery_ratio'] if recovery else 0
    stage_num, stage_name = classify_stage(current_vix, recovery_ratio, stages_data)

    # Stage 3 conditions
    usdkrw_data = data.get('USDKRW', {})
    usdkrw_current = usdkrw_data.get('current')
    usdkrw_pct = None
    if usdkrw_current and pre_crisis:
        # Approximate pre-crisis exchange rate from period low
        pre_crisis_krw = usdkrw_data.get('period_low', usdkrw_current)
        if pre_crisis_krw > 0:
            usdkrw_pct = (usdkrw_current - pre_crisis_krw) / pre_crisis_krw * 100

    daily_vol = abs(kospi_data.get('change_pct', 0))

    conditions_data = stages_data.get('stage3_conditions', {})
    current_values = {
        'vix': current_vix,
        'usdkrw_pct': usdkrw_pct,
        'cnn_fg': None,  # Requires WebSearch
        'foreign_flow': None,  # Requires WebSearch
        'recovery_ratio': recovery_ratio,
        'daily_volatility': daily_vol,
    }
    conditions_check = check_stage3_conditions(conditions_data, current_values)

    # Signals
    indicators_signals = {}
    if current_vix:
        sig = classify_signal('VIX', current_vix)
        indicators_signals['VIX'] = {
            'value': current_vix, 'signal': sig,
            'emoji': SIGNAL_EMOJI.get(sig, '⚪'),
        }
    if usdkrw_current:
        sig = classify_signal('USDKRW', usdkrw_current)
        indicators_signals['USDKRW'] = {
            'value': usdkrw_current, 'signal': sig,
            'emoji': SIGNAL_EMOJI.get(sig, '⚪'),
        }
    if recovery:
        sig = classify_signal('RECOVERY', recovery['recovery_ratio'])
        indicators_signals['RECOVERY'] = {
            'value': recovery['recovery_ratio'], 'signal': sig,
            'emoji': SIGNAL_EMOJI.get(sig, '⚪'),
        }

    return {
        'recovery': recovery,
        'stage': stage_num,
        'stage_name': stage_name,
        'conditions_check': conditions_check,
        'signals': indicators_signals,
        'rsi': kospi_data.get('rsi'),
        'raw_data': data,
    }


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------

def format_change(value):
    """Format a percentage change with sign."""
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def main():
    parser = argparse.ArgumentParser(
        description='Recovery Tracker — Post-crash market recovery monitor')
    parser.add_argument('--format', choices=['json', 'markdown'],
                        default='markdown',
                        help='Output format (default: markdown)')
    parser.add_argument('--pre-crisis', type=float, default=None,
                        help='Pre-crisis KOSPI value')
    parser.add_argument('--bottom', type=float, default=None,
                        help='Crisis bottom KOSPI value')
    args = parser.parse_args()

    # Fetch data
    data = fetch_recovery_data()
    if not data:
        sys.exit(1)

    # Build analysis
    analysis = build_recovery_analysis(data, args.pre_crisis, args.bottom)

    if args.format == 'json':
        output = {
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
        }
        # Convert non-serializable values
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"# Recovery Tracker Auto-Fetch — {now}")
        print()

        # Dashboard
        print("## yfinance 자동 수집 결과")
        print()
        print("| 지표 | 현재값 | 전일 대비 | 시그널 |")
        print("|------|:------:|:---------:|:------:|")
        for name in ['KOSPI', 'VIX', 'EWY', 'USDKRW']:
            d = data.get(name, {})
            if 'error' in d:
                print(f"| {name} | ERROR | - | {d['error']} |")
                continue
            val = d['current']
            if name == 'KOSPI' and d.get('rsi') is not None:
                val = f"{d['current']} (RSI {d['rsi']})"
            sig = analysis['signals'].get(name, {})
            emoji = sig.get('emoji', '⚪')
            print(f"| {name} | {val} | {format_change(d['change_pct'])} | {emoji} |")

        # Recovery
        rec = analysis.get('recovery')
        if rec:
            print()
            print("## KOSPI 회복률")
            print(f"- 위기전: {rec['pre_crisis']} | 바닥: {rec['bottom']} "
                  f"| 현재: {rec['current']}")
            print(f"- 총 하락: {rec['total_drop']} ({rec['drop_pct']}%)")
            print(f"- 회복: {rec['recovery_amount']} ({rec['rebound_pct']}%)")
            print(f"- **회복 비율: {rec['recovery_ratio']}%**")
            print(f"- 잔여 손실: {rec['remaining_loss_pct']}%")

        # Stage
        print()
        print(f"## 회복 단계: **{analysis['stage']}단계 ({analysis['stage_name']})**")

        # Conditions
        cc = analysis['conditions_check']
        print()
        print(f"### 3단계 진입 조건 ({cc['met_count']}/{cc['total']} 충족, "
              f"필요: {cc['required']}개)")
        for c in cc['conditions']:
            mark = '✅' if c['met'] else '❌'
            print(f"  {mark} {c['name']}: {c['current']} "
                  f"({c['operator']} {c['threshold']})")

        print()
        print("> 나머지 지표(CNN F&G, 외국인 수급, 뉴스 톤)는 WebSearch로 수집 필요")


if __name__ == '__main__':
    main()
