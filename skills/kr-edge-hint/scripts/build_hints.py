"""kr-edge-hint: 한국 시장 관찰에서 구조화된 엣지 힌트 추출.

Usage:
    python build_hints.py --market-summary market_summary.json \
                          --anomalies anomalies.json \
                          --output hints.yaml
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

# ─── 상수 ───

RISK_ON_OFF_THRESHOLD = 10

SUPPORTED_ENTRY_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}

KR_HINT_SOURCES = [
    'foreign_flow',
    'institutional_flow',
    'program_trading',
    'short_interest',
    'credit_balance',
]

VALID_DIRECTIONS = {'bullish', 'bearish', 'neutral'}

VALID_HYPOTHESES = {
    'breakout', 'earnings_drift', 'news_reaction', 'futures_trigger',
    'calendar_anomaly', 'panic_reversal', 'regime_shift', 'sector_x_stock',
}

# 수급 힌트 생성 기준
FOREIGN_CONSECUTIVE_HINT = 5        # 외국인 5일 연속 순매수 → 힌트
INST_CONSECUTIVE_HINT = 5           # 기관 5일 연속 순매수 → 힌트
FOREIGN_STRONG_CONSECUTIVE = 10     # 10일 연속 → 높은 신뢰도
PROGRAM_NET_THRESHOLD = 1_000_000_000_000  # 프로그램 순매수 1조원 → 힌트
SHORT_INTEREST_SPIKE = 0.20         # 공매도 잔고 20% 증가 → 힌트
CREDIT_BALANCE_OVERHEAT = 0.90      # 신용잔고 과열 기준 (90th percentile)


def read_json(filepath: str) -> dict | list | None:
    """JSON 파일 읽기."""
    if not filepath or not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def infer_regime(market_summary: dict) -> str:
    """시장 요약 데이터에서 레짐 추론.

    Args:
        market_summary: risk_on, risk_off 카운트를 포함하는 시장 요약

    Returns:
        'RiskOn' | 'RiskOff' | 'Neutral'
    """
    if not market_summary:
        return 'Neutral'

    risk_on = market_summary.get('risk_on', 0)
    risk_off = market_summary.get('risk_off', 0)

    diff = risk_on - risk_off
    if diff >= RISK_ON_OFF_THRESHOLD:
        return 'RiskOn'
    elif diff <= -RISK_ON_OFF_THRESHOLD:
        return 'RiskOff'
    return 'Neutral'


def normalize_hint(raw: dict) -> dict | None:
    """원시 힌트를 정규화된 스키마로 변환.

    Args:
        raw: 원시 힌트 dict

    Returns:
        정규화된 힌트 dict 또는 유효하지 않으면 None
    """
    symbol = raw.get('symbol', '')
    direction = raw.get('direction', 'neutral')
    hypothesis = raw.get('hypothesis', '')
    source = raw.get('source', '')
    confidence = raw.get('confidence', 0.5)
    memo = raw.get('memo', '')
    entry_family = raw.get('entry_family', '')

    if not symbol or not hypothesis:
        return None

    if direction not in VALID_DIRECTIONS:
        direction = 'neutral'

    if hypothesis not in VALID_HYPOTHESES:
        return None

    confidence = max(0.0, min(1.0, float(confidence)))

    if entry_family and entry_family not in SUPPORTED_ENTRY_FAMILIES:
        entry_family = ''

    hint = {
        'symbol': str(symbol),
        'direction': direction,
        'hypothesis': hypothesis,
        'source': source,
        'confidence': round(confidence, 2),
        'memo': memo,
    }
    if entry_family:
        hint['entry_family'] = entry_family

    return hint


def build_flow_hints(market_summary: dict) -> list:
    """수급 데이터 기반 힌트 생성.

    market_summary.flow_data에서 종목별 수급 정보를 추출하여
    외국인/기관 연속 순매수 등의 패턴을 힌트로 변환한다.

    Args:
        market_summary: 시장 요약 데이터 (flow_data 포함)

    Returns:
        힌트 리스트
    """
    hints = []
    flow_data = market_summary.get('flow_data', [])

    for item in flow_data:
        symbol = item.get('symbol', '')
        if not symbol:
            continue

        # 외국인 수급 힌트
        foreign_consec = item.get('foreign_consecutive_buy', 0)
        if foreign_consec >= FOREIGN_CONSECUTIVE_HINT:
            confidence = 0.8 if foreign_consec >= FOREIGN_STRONG_CONSECUTIVE else 0.6
            hints.append({
                'symbol': symbol,
                'direction': 'bullish',
                'hypothesis': 'breakout',
                'source': 'rule:foreign_flow',
                'confidence': confidence,
                'entry_family': 'pivot_breakout',
                'memo': f'외국인 {foreign_consec}일 연속 순매수',
            })

        # 기관 수급 힌트
        inst_consec = item.get('inst_consecutive_buy', 0)
        if inst_consec >= INST_CONSECUTIVE_HINT:
            confidence = 0.7 if inst_consec >= FOREIGN_STRONG_CONSECUTIVE else 0.5
            hints.append({
                'symbol': symbol,
                'direction': 'bullish',
                'hypothesis': 'breakout',
                'source': 'rule:institutional_flow',
                'confidence': confidence,
                'entry_family': 'pivot_breakout',
                'memo': f'기관 {inst_consec}일 연속 순매수',
            })

        # 외국인 연속 매도 → 약세 힌트
        foreign_consec_sell = item.get('foreign_consecutive_sell', 0)
        if foreign_consec_sell >= FOREIGN_CONSECUTIVE_HINT:
            hints.append({
                'symbol': symbol,
                'direction': 'bearish',
                'hypothesis': 'regime_shift',
                'source': 'rule:foreign_flow',
                'confidence': 0.6,
                'memo': f'외국인 {foreign_consec_sell}일 연속 순매도 — 이탈 경고',
            })

        # 공매도 잔고 급증
        short_change = item.get('short_interest_change', 0)
        if short_change >= SHORT_INTEREST_SPIKE:
            hints.append({
                'symbol': symbol,
                'direction': 'bearish',
                'hypothesis': 'panic_reversal',
                'source': 'rule:short_interest',
                'confidence': 0.5,
                'memo': f'공매도 잔고 {short_change:.0%} 증가',
            })

    return hints


def build_anomaly_hints(anomalies: list) -> list:
    """이상 탐지 결과에서 힌트 생성.

    Args:
        anomalies: 이상 탐지 결과 리스트

    Returns:
        힌트 리스트
    """
    hints = []
    if not anomalies:
        return hints

    for anomaly in anomalies:
        symbol = anomaly.get('symbol', '')
        anomaly_type = anomaly.get('type', '')
        direction = anomaly.get('direction', 'neutral')
        confidence = anomaly.get('confidence', 0.5)

        if not symbol:
            continue

        hypothesis_map = {
            'volume_spike': 'breakout',
            'price_gap': 'earnings_drift',
            'correlation_break': 'regime_shift',
            'sector_divergence': 'sector_x_stock',
            'calendar_pattern': 'calendar_anomaly',
        }

        hypothesis = hypothesis_map.get(anomaly_type, 'breakout')
        entry_family = ''
        if anomaly_type == 'volume_spike' and direction == 'bullish':
            entry_family = 'pivot_breakout'
        elif anomaly_type == 'price_gap' and direction == 'bullish':
            entry_family = 'gap_up_continuation'

        hint = {
            'symbol': symbol,
            'direction': direction,
            'hypothesis': hypothesis,
            'source': f'rule:anomaly_{anomaly_type}',
            'confidence': confidence,
            'memo': anomaly.get('description', f'{anomaly_type} 이상 탐지'),
        }
        if entry_family:
            hint['entry_family'] = entry_family
        hints.append(hint)

    return hints


def build_news_hints(news_reactions: list) -> list:
    """뉴스 반응 데이터에서 힌트 생성.

    Args:
        news_reactions: 뉴스 반응 데이터 리스트

    Returns:
        힌트 리스트
    """
    hints = []
    if not news_reactions:
        return hints

    for news in news_reactions:
        symbol = news.get('symbol', '')
        if not symbol:
            continue

        reaction = news.get('reaction', 'neutral')
        headline = news.get('headline', '')
        magnitude = abs(news.get('price_change_pct', 0))

        if magnitude < 3.0:
            continue

        direction = 'bullish' if reaction == 'positive' else 'bearish'
        confidence = min(0.9, 0.4 + magnitude * 0.05)

        hints.append({
            'symbol': symbol,
            'direction': direction,
            'hypothesis': 'news_reaction',
            'source': 'rule:news_reaction',
            'confidence': round(confidence, 2),
            'memo': f'{headline} (변동 {magnitude:.1f}%)',
        })

    return hints


def dedupe_hints(hints: list) -> list:
    """힌트 중복 제거.

    (symbol, direction, hypothesis) 기준으로 중복 제거하되
    confidence가 더 높은 것을 유지한다.

    Args:
        hints: 정규화된 힌트 리스트

    Returns:
        중복 제거된 힌트 리스트
    """
    seen = {}
    for h in hints:
        key = (h['symbol'], h['direction'], h['hypothesis'])
        if key not in seen or h['confidence'] > seen[key]['confidence']:
            seen[key] = h
    return list(seen.values())


def build_all_hints(market_summary: dict = None,
                    anomalies: list = None,
                    news_reactions: list = None) -> dict:
    """모든 소스에서 힌트를 수집하고 정규화.

    Args:
        market_summary: 시장 요약 데이터
        anomalies: 이상 탐지 결과 리스트
        news_reactions: 뉴스 반응 데이터 리스트

    Returns:
        {
            'hints': [...],
            'meta': {
                'generated_at': str,
                'rule_hints': int,
                'total_hints': int,
                'regime': str,
            }
        }
    """
    all_raw = []

    if market_summary:
        all_raw.extend(build_flow_hints(market_summary))

    if anomalies:
        all_raw.extend(build_anomaly_hints(anomalies))

    if news_reactions:
        all_raw.extend(build_news_hints(news_reactions))

    normalized = []
    for raw in all_raw:
        hint = normalize_hint(raw)
        if hint:
            normalized.append(hint)

    deduped = dedupe_hints(normalized)

    regime = infer_regime(market_summary) if market_summary else 'Neutral'

    return {
        'hints': deduped,
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'rule_hints': len(deduped),
            'total_hints': len(deduped),
            'regime': regime,
        },
    }


def write_yaml(data: dict, filepath: str) -> str:
    """YAML 파일 출력.

    Args:
        data: 출력할 데이터
        filepath: 출력 파일 경로

    Returns:
        출력 파일 경로
    """
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)

    if yaml:
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def main():
    parser = argparse.ArgumentParser(description='한국 시장 엣지 힌트 추출기')
    parser.add_argument('--market-summary', default=None)
    parser.add_argument('--anomalies', default=None)
    parser.add_argument('--news-reactions', default=None)
    parser.add_argument('--output', default='hints.yaml')
    args = parser.parse_args()

    market_summary = read_json(args.market_summary)
    anomalies = read_json(args.anomalies)
    news_reactions = read_json(args.news_reactions)

    result = build_all_hints(market_summary, anomalies, news_reactions)

    outpath = write_yaml(result, args.output)
    print(f'[EdgeHint] {len(result["hints"])}개 힌트 생성 → {outpath}')
    print(f'  regime={result["meta"]["regime"]}')


if __name__ == '__main__':
    main()
