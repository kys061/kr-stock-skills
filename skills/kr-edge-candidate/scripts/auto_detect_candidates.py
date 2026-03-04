"""kr-edge-candidate: 한국 시장 후보 자동 탐지.

Usage:
    python auto_detect_candidates.py --ohlcv data.csv
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ─── 한국 유니버스 ───

KR_UNIVERSES = {
    'kospi200': 'KOSPI200 구성종목',
    'kosdaq150': 'KOSDAQ150 구성종목',
    'all_kospi': 'KOSPI 전체',
    'all_kosdaq': 'KOSDAQ 전체',
}

# ─── OHLCV 필수 컬럼 ───

REQUIRED_OHLCV_COLUMNS = [
    'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
]

# ─── entry_family → hypothesis 매핑 ───

ENTRY_FAMILY_TO_HYPOTHESIS = {
    'pivot_breakout': 'breakout',
    'gap_up_continuation': 'earnings_drift',
}

# ─── 연구 전용 가설 ───

RESEARCH_ONLY_HYPOTHESES = {
    'panic_reversal', 'regime_shift', 'sector_x_stock',
    'calendar_anomaly', 'news_reaction', 'futures_trigger',
}

# ─── 돌파 후보 스코어링 상수 ───

BREAKOUT_RS_WEIGHT = 0.30
BREAKOUT_VOLUME_WEIGHT = 0.25
BREAKOUT_CLOSE_POS_WEIGHT = 0.25
BREAKOUT_ATR_WEIGHT = 0.10
BREAKOUT_REGIME_WEIGHT = 0.10

# ─── 갭업 후보 스코어링 상수 ───

GAP_SIZE_WEIGHT = 0.30
GAP_VOLUME_WEIGHT = 0.30
GAP_CLOSE_POS_WEIGHT = 0.20
GAP_TREND_WEIGHT = 0.20


def score_breakout_candidate(data: dict) -> float:
    """돌파 후보 스코어링.

    Args:
        data: 후보 데이터 (rs_rank, rel_volume, close_pos, atr_rank, regime)

    Returns:
        0-100 점수
    """
    rs = min(data.get('rs_rank', 0) / 100, 1.0) * 100
    vol = min(data.get('rel_volume', 0) / 3.0, 1.0) * 100
    close = data.get('close_pos', 0) * 100
    atr = min(data.get('atr_rank', 0) / 100, 1.0) * 100
    regime = 100 if data.get('regime', '') == 'RiskOn' else 50

    score = (rs * BREAKOUT_RS_WEIGHT
             + vol * BREAKOUT_VOLUME_WEIGHT
             + close * BREAKOUT_CLOSE_POS_WEIGHT
             + atr * BREAKOUT_ATR_WEIGHT
             + regime * BREAKOUT_REGIME_WEIGHT)

    return round(min(100, max(0, score)), 1)


def score_gap_candidate(data: dict) -> float:
    """갭업 후보 스코어링.

    Args:
        data: 후보 데이터 (gap_pct, rel_volume, close_pos, trend_strength)

    Returns:
        0-100 점수
    """
    gap = min(abs(data.get('gap_pct', 0)) / 10.0, 1.0) * 100
    vol = min(data.get('rel_volume', 0) / 3.0, 1.0) * 100
    close = data.get('close_pos', 0) * 100
    trend = data.get('trend_strength', 0) * 100

    score = (gap * GAP_SIZE_WEIGHT
             + vol * GAP_VOLUME_WEIGHT
             + close * GAP_CLOSE_POS_WEIGHT
             + trend * GAP_TREND_WEIGHT)

    return round(min(100, max(0, score)), 1)


def build_ticket_payload(candidate: dict, entry_family: str) -> dict:
    """후보 → 리서치 티켓 변환.

    Args:
        candidate: 후보 데이터
        entry_family: 진입 패밀리

    Returns:
        리서치 티켓 dict
    """
    hypothesis = ENTRY_FAMILY_TO_HYPOTHESIS.get(entry_family, 'breakout')
    is_research = hypothesis in RESEARCH_ONLY_HYPOTHESES

    return {
        'id': f'kr-{entry_family}-{candidate.get("symbol", "unknown")}',
        'name': f'{candidate.get("symbol", "")} {entry_family}',
        'universe': {
            'market': 'KRX',
            'index': candidate.get('universe', 'kospi200'),
        },
        'signals': {
            'entry_family': entry_family,
            'hypothesis_type': hypothesis,
            'conditions': candidate.get('conditions', []),
        },
        'risk': {
            'risk_per_trade': 0.01,
            'max_positions': 5,
            'stop_loss_pct': 0.07,
        },
        'cost_model': {
            'round_trip_cost': 0.0053,
        },
        'validation': {
            'method': 'full_sample',
            'min_trades': 30,
        },
        'promotion_gates': {
            'min_score': 70,
            'min_profit_factor': 1.5,
        },
        'score': candidate.get('score', 0),
        'research_only': is_research,
    }


def detect_candidates(ohlcv_data: list,
                      universe: str = 'kospi200') -> dict:
    """OHLCV 데이터에서 후보 자동 탐지.

    Args:
        ohlcv_data: OHLCV 데이터 리스트
        universe: 유니버스 이름

    Returns:
        {'exportable': [...], 'research_only': [...], 'meta': {...}}
    """
    exportable = []
    research_only = []

    for row in ohlcv_data:
        symbol = row.get('symbol', '')
        if not symbol:
            continue

        # 돌파 후보 스코어링
        breakout_score = score_breakout_candidate(row)
        if breakout_score >= 60:
            ticket = build_ticket_payload(
                {**row, 'score': breakout_score, 'universe': universe},
                'pivot_breakout')
            if ticket['research_only']:
                research_only.append(ticket)
            else:
                exportable.append(ticket)

        # 갭업 후보 스코어링
        gap_score = score_gap_candidate(row)
        if gap_score >= 60:
            ticket = build_ticket_payload(
                {**row, 'score': gap_score, 'universe': universe},
                'gap_up_continuation')
            if ticket['research_only']:
                research_only.append(ticket)
            else:
                exportable.append(ticket)

    return {
        'exportable': sorted(exportable,
                              key=lambda x: x.get('score', 0),
                              reverse=True),
        'research_only': research_only,
        'meta': {
            'detected_at': datetime.now().isoformat(),
            'universe': universe,
            'total_candidates': len(exportable) + len(research_only),
            'exportable_count': len(exportable),
            'research_only_count': len(research_only),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='한국 후보 자동 탐지기')
    parser.add_argument('--ohlcv', required=True)
    parser.add_argument('--universe', default='kospi200')
    parser.add_argument('--output', default='candidates.json')
    args = parser.parse_args()

    with open(args.ohlcv, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = detect_candidates(data, args.universe)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'[EdgeCandidate] {result["meta"]["total_candidates"]}개 후보 탐지 '
          f'(내보내기: {result["meta"]["exportable_count"]}, '
          f'연구: {result["meta"]["research_only_count"]})')


if __name__ == '__main__':
    main()
