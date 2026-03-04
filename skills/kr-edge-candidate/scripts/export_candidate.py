"""kr-edge-candidate: 후보 내보내기 (strategy.yaml 생성).

Usage:
    python export_candidate.py --candidate candidate.json \
                                --output-dir strategies/
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

# ─── 기본값 ───

DEFAULT_UNIVERSE = {
    'market': 'KRX',
    'index': 'kospi200',
    'filters': ['시가총액 >= 5000억원'],
}

DEFAULT_DATA = {
    'timeframe': 'daily',
    'lookback_years': 8,
}

DEFAULT_RISK = {
    'risk_per_trade': 0.01,
    'max_positions': 5,
    'stop_loss_pct': 0.07,
    'trailing_stop': True,
    'max_sector_exposure': 0.30,
}

DEFAULT_EXIT = {
    'stop_loss': True,
    'trailing_stop': True,
    'take_profit_rr': 3.0,
    'time_stop_days': 20,
}

DEFAULT_COST_MODEL = {
    'round_trip_cost': 0.0053,
    'holding_cost_daily': 0.0,
    'slippage': 0.001,
}

DEFAULT_PROMOTION_GATES = {
    'min_score': 70,
    'min_profit_factor': 1.5,
    'min_trades': 30,
}


def build_strategy_spec(candidate: dict) -> dict:
    """후보 → Phase I strategy.yaml 생성.

    Args:
        candidate: 후보 데이터

    Returns:
        strategy spec dict
    """
    return {
        'version': 'edge-finder-candidate/v1',
        'id': candidate.get('id', 'unknown'),
        'name': candidate.get('name', ''),
        'universe': candidate.get('universe', DEFAULT_UNIVERSE),
        'data': DEFAULT_DATA,
        'signals': candidate.get('signals', {}),
        'risk': {**DEFAULT_RISK, **candidate.get('risk', {})},
        'exit': DEFAULT_EXIT,
        'cost_model': {**DEFAULT_COST_MODEL,
                       **candidate.get('cost_model', {})},
        'validation': candidate.get('validation',
                                     {'method': 'full_sample'}),
        'promotion_gates': candidate.get('promotion_gates',
                                          DEFAULT_PROMOTION_GATES),
    }


def build_metadata(candidate: dict) -> dict:
    """메타데이터 생성.

    Args:
        candidate: 후보 데이터

    Returns:
        메타데이터 dict
    """
    return {
        'interface_version': 'edge-finder-candidate/v1',
        'source': 'kr-edge-candidate',
        'exported_at': datetime.now().isoformat(),
        'candidate_id': candidate.get('id', ''),
        'score': candidate.get('score', 0),
    }


def export_candidate(candidate: dict, output_dir: str) -> dict:
    """후보를 strategy.yaml + metadata.json으로 내보내기.

    Args:
        candidate: 후보 데이터
        output_dir: 출력 디렉토리

    Returns:
        {'strategy_path': str, 'metadata_path': str}
    """
    candidate_id = candidate.get('id', 'unknown')
    candidate_dir = os.path.join(output_dir, candidate_id)
    os.makedirs(candidate_dir, exist_ok=True)

    strategy = build_strategy_spec(candidate)
    metadata = build_metadata(candidate)

    strategy_path = os.path.join(candidate_dir, 'strategy.yaml')
    metadata_path = os.path.join(candidate_dir, 'metadata.json')

    if yaml:
        with open(strategy_path, 'w', encoding='utf-8') as f:
            yaml.dump(strategy, f, allow_unicode=True,
                      default_flow_style=False, sort_keys=False)
    else:
        strategy_path = strategy_path.replace('.yaml', '.json')
        with open(strategy_path, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return {
        'strategy_path': strategy_path,
        'metadata_path': metadata_path,
    }


def main():
    parser = argparse.ArgumentParser(description='한국 후보 내보내기')
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output-dir', default='strategies')
    args = parser.parse_args()

    with open(args.candidate, 'r', encoding='utf-8') as f:
        candidate = json.load(f)

    result = export_candidate(candidate, args.output_dir)
    print(f'[Export] {result["strategy_path"]}')


if __name__ == '__main__':
    main()
