"""kr-strategy-pivot: 백테스트 반복 정체 감지.

Usage:
    python detect_stagnation.py --history backtest_history.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ─── 정체 트리거 상수 ───

STAGNATION_TRIGGERS = {
    'improvement_plateau': {
        'window': 3,
        'threshold': 3,
        'severity': 'HIGH',
    },
    'overfitting_proxy': {
        'expectancy_min': 15,
        'risk_mgmt_min': 15,
        'robustness_max': 10,
        'severity': 'MEDIUM',
    },
    'cost_defeat': {
        'description': '거래 비용이 얇은 엣지를 초과',
        'severity': 'HIGH',
    },
    'tail_risk_elevation': {
        'description': '꼬리 리스크/드로다운 초과',
        'severity': 'HIGH',
    },
}

# ─── 판정 결과 ───

DIAGNOSIS_OUTCOMES = ['continue', 'pivot', 'abandon']

# ─── tail_risk 기준 ───

MAX_DRAWDOWN_ABANDON = 35
RISK_MGMT_CRITICAL = 5

# ─── abandon 기준 ───

ABANDON_MIN_ITERATIONS = 3
ABANDON_SCORE_THRESHOLD = 30


def check_improvement_plateau(history: list) -> dict:
    """improvement_plateau 트리거 확인.

    최근 window 회 반복의 종합 점수 범위가 threshold 미만이면 발화.

    Args:
        history: 반복 기록 리스트 (각각 {'composite_score': int, ...})

    Returns:
        {'fired': bool, 'trigger': str, 'severity': str, 'detail': str}
    """
    cfg = STAGNATION_TRIGGERS['improvement_plateau']
    window = cfg['window']
    threshold = cfg['threshold']

    if len(history) < window:
        return {'fired': False, 'trigger': 'improvement_plateau',
                'severity': cfg['severity'], 'detail': '데이터 부족'}

    recent = history[-window:]
    scores = [r.get('composite_score', 0) for r in recent]
    score_range = max(scores) - min(scores)

    fired = score_range < threshold
    return {
        'fired': fired,
        'trigger': 'improvement_plateau',
        'severity': cfg['severity'],
        'detail': f'최근 {window}회 점수 범위: {score_range}점 '
                  f'(기준: <{threshold})',
    }


def check_overfitting_proxy(latest: dict) -> dict:
    """overfitting_proxy 트리거 확인.

    Expectancy/Risk 높은데 Robustness 낮으면 과적합 의심.

    Args:
        latest: 최근 백테스트 평가 결과

    Returns:
        {'fired': bool, 'trigger': str, 'severity': str, 'detail': str}
    """
    cfg = STAGNATION_TRIGGERS['overfitting_proxy']

    dimensions = latest.get('dimensions', {})
    expectancy = dimensions.get('expectancy', 0)
    risk_mgmt = dimensions.get('risk_management', 0)
    robustness = dimensions.get('robustness', 0)

    fired = (expectancy >= cfg['expectancy_min']
             and risk_mgmt >= cfg['risk_mgmt_min']
             and robustness < cfg['robustness_max'])

    return {
        'fired': fired,
        'trigger': 'overfitting_proxy',
        'severity': cfg['severity'],
        'detail': f'Expectancy={expectancy}, Risk={risk_mgmt}, '
                  f'Robustness={robustness}',
    }


def check_cost_defeat(latest: dict) -> dict:
    """cost_defeat 트리거 확인.

    Expectancy 또는 Profit Factor가 거래 비용을 못 넘길 때.

    Args:
        latest: 최근 백테스트 평가 결과

    Returns:
        {'fired': bool, 'trigger': str, 'severity': str, 'detail': str}
    """
    expectancy_pct = latest.get('expectancy_pct', 0)
    profit_factor = latest.get('profit_factor', 0)
    slippage_tested = latest.get('slippage_tested', False)

    fired = (expectancy_pct < 0.3
             and profit_factor < 1.3
             and slippage_tested)

    return {
        'fired': fired,
        'trigger': 'cost_defeat',
        'severity': 'HIGH',
        'detail': f'Expectancy={expectancy_pct}%, PF={profit_factor}, '
                  f'Slippage tested={slippage_tested}',
    }


def check_tail_risk(latest: dict) -> dict:
    """tail_risk_elevation 트리거 확인.

    Args:
        latest: 최근 백테스트 평가 결과

    Returns:
        {'fired': bool, 'trigger': str, 'severity': str, 'detail': str}
    """
    max_dd = latest.get('max_drawdown_pct', 0)
    dimensions = latest.get('dimensions', {})
    risk_mgmt = dimensions.get('risk_management', 20)

    fired = max_dd > MAX_DRAWDOWN_ABANDON or risk_mgmt <= RISK_MGMT_CRITICAL

    return {
        'fired': fired,
        'trigger': 'tail_risk_elevation',
        'severity': 'HIGH',
        'detail': f'Max DD={max_dd}%, Risk Mgmt={risk_mgmt}',
    }


def run_all_triggers(history: list) -> list:
    """모든 정체 트리거 실행.

    Args:
        history: 반복 기록 리스트

    Returns:
        트리거 결과 리스트
    """
    results = []

    results.append(check_improvement_plateau(history))

    if history:
        latest = history[-1]
        results.append(check_overfitting_proxy(latest))
        results.append(check_cost_defeat(latest))
        results.append(check_tail_risk(latest))

    return results


def determine_recommendation(history: list, trigger_results: list) -> str:
    """판정 결정.

    Args:
        history: 반복 기록
        trigger_results: 트리거 결과 리스트

    Returns:
        'continue' | 'pivot' | 'abandon'
    """
    if len(history) < ABANDON_MIN_ITERATIONS:
        fired = any(r['fired'] for r in trigger_results)
        return 'pivot' if fired else 'continue'

    # abandon 조건: 3회 이상, 최근 점수 <30, 단조 감소
    recent_scores = [r.get('composite_score', 0)
                     for r in history[-ABANDON_MIN_ITERATIONS:]]
    latest_score = recent_scores[-1] if recent_scores else 0
    monotonic_decrease = all(
        recent_scores[i] >= recent_scores[i + 1]
        for i in range(len(recent_scores) - 1)
    )

    if (latest_score < ABANDON_SCORE_THRESHOLD
            and monotonic_decrease
            and len(history) >= ABANDON_MIN_ITERATIONS):
        return 'abandon'

    fired = any(r['fired'] for r in trigger_results)
    return 'pivot' if fired else 'continue'


def diagnose(history: list) -> dict:
    """정체 진단 실행.

    Args:
        history: 반복 기록 리스트

    Returns:
        진단 결과 dict
    """
    trigger_results = run_all_triggers(history)
    recommendation = determine_recommendation(history, trigger_results)
    fired_triggers = [r for r in trigger_results if r['fired']]

    return {
        'recommendation': recommendation,
        'fired_triggers': fired_triggers,
        'all_triggers': trigger_results,
        'iterations': len(history),
        'latest_score': (history[-1].get('composite_score', 0)
                         if history else 0),
        'diagnosed_at': datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description='백테스트 정체 진단기')
    parser.add_argument('--history', required=True)
    parser.add_argument('--output', default='diagnosis.json')
    args = parser.parse_args()

    with open(args.history, 'r', encoding='utf-8') as f:
        history = json.load(f)

    result = diagnose(history)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'[StrategyPivot] 판정: {result["recommendation"]} '
          f'(트리거 {len(result["fired_triggers"])}개 발화)')


if __name__ == '__main__':
    main()
