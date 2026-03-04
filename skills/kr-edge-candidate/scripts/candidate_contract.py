"""kr-edge-candidate: edge-finder-candidate/v1 인터페이스 검증.

Usage:
    python candidate_contract.py --ticket ticket.yaml --validate
"""

import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None

# ─── 인터페이스 버전 ───

INTERFACE_VERSION = 'edge-finder-candidate/v1'

# ─── 필수 키 ───

CANDIDATE_REQUIRED_KEYS = [
    'id', 'name', 'universe', 'signals',
    'risk', 'cost_model', 'validation', 'promotion_gates',
]

# ─── 지원 entry family ───

SUPPORTED_ENTRY_FAMILIES = {'pivot_breakout', 'gap_up_continuation'}

# ─── 검증 규칙 ───

VALIDATION_RULES = {
    'risk_per_trade_max': 0.10,
    'max_positions_min': 1,
    'max_sector_exposure_max': 1.0,
    'validation_method': 'full_sample',
}


def validate_ticket_payload(ticket: dict) -> dict:
    """리서치 티켓 최소 스키마 검증.

    Args:
        ticket: 티켓 dict

    Returns:
        {'valid': bool, 'errors': [...], 'warnings': [...]}
    """
    errors = []
    warnings = []

    for key in CANDIDATE_REQUIRED_KEYS:
        if key not in ticket:
            errors.append(f'필수 키 누락: {key}')

    # signals 검증
    signals = ticket.get('signals', {})
    entry_family = signals.get('entry_family', '')
    if entry_family and entry_family not in SUPPORTED_ENTRY_FAMILIES:
        warnings.append(f'미지원 entry_family: {entry_family}')

    # risk 검증
    risk = ticket.get('risk', {})
    rpt = risk.get('risk_per_trade', 0)
    if rpt > VALIDATION_RULES['risk_per_trade_max']:
        errors.append(f'risk_per_trade ({rpt}) > '
                      f'{VALIDATION_RULES["risk_per_trade_max"]}')

    max_pos = risk.get('max_positions', 0)
    if max_pos < VALIDATION_RULES['max_positions_min']:
        errors.append(f'max_positions ({max_pos}) < '
                      f'{VALIDATION_RULES["max_positions_min"]}')

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'interface_version': INTERFACE_VERSION,
    }


def validate_interface_contract(candidate: dict) -> dict:
    """edge-finder-candidate/v1 전체 계약 검증.

    Args:
        candidate: 후보 dict

    Returns:
        {'valid': bool, 'errors': [...], 'warnings': [...]}
    """
    result = validate_ticket_payload(candidate)

    # 추가 계약 검증
    validation = candidate.get('validation', {})
    method = validation.get('method', '')
    if method != VALIDATION_RULES['validation_method']:
        result['warnings'].append(
            f'Phase I에는 full_sample 검증 권장 (현재: {method})')

    promotion = candidate.get('promotion_gates', {})
    if 'min_score' not in promotion:
        result['warnings'].append('promotion_gates에 min_score 없음')
    if 'min_profit_factor' not in promotion:
        result['warnings'].append('promotion_gates에 min_profit_factor 없음')

    return result


def main():
    parser = argparse.ArgumentParser(
        description='edge-finder-candidate/v1 검증기')
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()

    filepath = args.ticket
    with open(filepath, 'r', encoding='utf-8') as f:
        if yaml and filepath.endswith(('.yaml', '.yml')):
            ticket = yaml.safe_load(f)
        else:
            ticket = json.load(f)

    if args.validate:
        result = validate_interface_contract(ticket)
    else:
        result = validate_ticket_payload(ticket)

    if result['valid']:
        print(f'[Contract] VALID — {INTERFACE_VERSION}')
    else:
        print(f'[Contract] INVALID — {len(result["errors"])}개 오류')
        for err in result['errors']:
            print(f'  ERROR: {err}')
    for warn in result.get('warnings', []):
        print(f'  WARN: {warn}')


if __name__ == '__main__':
    main()
