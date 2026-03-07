#!/usr/bin/env python3
"""Crisis Compare - Historical crisis pattern comparison for Korean market.

Compares current market conditions against 5 reference crises:
  #1 Global Financial Crisis (2008.10)
  #2 COVID Pandemic (2020.03)
  #3 Rate Hike Shock (2022.01-09)
  #4 Trump Tariff Shock (2025.04)
  #5 Iran Crisis (2026.03)

Automated data (yfinance):
  - KOSPI level & 6-month drawdown
  - VIX level
  - S&P 500 level & drawdown
  - USD/KRW

Manual/WebSearch required:
  - VKOSPI
  - Exact peak/trough dates
  - News sentiment
"""

import argparse
import json
import sys
from datetime import datetime


# Historical reference data for 5 major crises
HISTORICAL_CRISES = {
    'gfc_2008': {
        'name': '글로벌 금융위기',
        'name_en': 'Global Financial Crisis',
        'date': '2008-10',
        'trigger': '리먼브라더스 파산, 서브프라임 모기지 붕괴',
        'crisis_type': 'financial',
        'kospi_peak': 1997,
        'kospi_trough': 905,
        'kospi_drop_pct': -54.5,
        'vix_peak': 89.53,
        'sp500_drop_pct': -56.8,
        'days_to_bottom': 155,
        'recovery_1w_pct': 7.2,
        'recovery_1m_pct': 18.4,
        'recovery_3m_pct': 40.1,
        'recovery_6m_pct': 54.3,
        'key_features': [
            'systemic_risk', 'bank_failures',
            'credit_freeze', 'global_contagion',
        ],
    },
    'covid_2020': {
        'name': '코로나 팬데믹',
        'name_en': 'COVID-19 Pandemic',
        'date': '2020-03',
        'trigger': '글로벌 락다운, 경제활동 중단',
        'crisis_type': 'pandemic',
        'kospi_peak': 2267,
        'kospi_trough': 1457,
        'kospi_drop_pct': -33.9,
        'vix_peak': 82.69,
        'sp500_drop_pct': -33.9,
        'days_to_bottom': 23,
        'recovery_1w_pct': 12.8,
        'recovery_1m_pct': 24.1,
        'recovery_3m_pct': 40.5,
        'recovery_6m_pct': 58.7,
        'key_features': [
            'exogenous_shock', 'v_shaped',
            'massive_stimulus', 'rapid_recovery',
        ],
    },
    'rate_hike_2022': {
        'name': '금리인상 충격',
        'name_en': 'Rate Hike Shock',
        'date': '2022-01~09',
        'trigger': 'Fed 425bp 급속 금리인상, 인플레이션 대응',
        'crisis_type': 'monetary',
        'kospi_peak': 2988,
        'kospi_trough': 2155,
        'kospi_drop_pct': -24.9,
        'vix_peak': 36.45,
        'sp500_drop_pct': -25.4,
        'days_to_bottom': 270,
        'recovery_1w_pct': 5.4,
        'recovery_1m_pct': 8.9,
        'recovery_3m_pct': 12.1,
        'recovery_6m_pct': 18.5,
        'key_features': [
            'gradual_decline', 'valuation_reset',
            'growth_to_value', 'slow_recovery',
        ],
    },
    'tariff_2025': {
        'name': '트럼프 관세 쇼크',
        'name_en': 'Trump Tariff Shock',
        'date': '2025-04',
        'trigger': '"해방의 날" 보편관세 발표, 글로벌 무역전쟁',
        'crisis_type': 'trade',
        'kospi_peak': 2650,
        'kospi_trough': 2280,
        'kospi_drop_pct': -14.0,
        'vix_peak': 52.33,
        'sp500_drop_pct': -20.0,
        'days_to_bottom': 5,
        'recovery_1w_pct': 8.5,
        'recovery_1m_pct': 14.2,
        'recovery_3m_pct': 18.7,
        'recovery_6m_pct': 22.1,
        'key_features': [
            'policy_shock', 'rapid_selloff',
            'negotiation_dependent', 'partial_reversal',
        ],
    },
    'iran_2026': {
        'name': '이란 위기',
        'name_en': 'Iran Crisis',
        'date': '2026-03',
        'trigger': '미-이스라엘 이란 핵시설 공습, 중동 확전 우려',
        'crisis_type': 'geopolitical',
        'kospi_peak': 2600,
        'kospi_trough': 2130,
        'kospi_drop_pct': -18.0,
        'vix_peak': 45.0,
        'sp500_drop_pct': -14.0,
        'days_to_bottom': 5,
        'recovery_1w_pct': None,  # Ongoing
        'recovery_1m_pct': None,
        'recovery_3m_pct': None,
        'recovery_6m_pct': None,
        'key_features': [
            'geopolitical_shock', 'oil_spike',
            'flight_to_safety', 'military_conflict',
        ],
    },
}

# Crisis type similarity matrix (keys in sorted order)
CRISIS_TYPE_SIMILARITY = {
    ('financial', 'geopolitical'): 35,
    ('financial', 'monetary'): 50,
    ('financial', 'pandemic'): 30,
    ('financial', 'trade'): 40,
    ('geopolitical', 'monetary'): 30,
    ('geopolitical', 'pandemic'): 45,
    ('geopolitical', 'trade'): 60,
    ('monetary', 'pandemic'): 20,
    ('monetary', 'trade'): 55,
    ('pandemic', 'trade'): 25,
}


def get_type_similarity(type_a, type_b):
    """Get similarity score (0-100) between two crisis types."""
    if type_a == type_b:
        return 100
    key = tuple(sorted([type_a, type_b]))
    return CRISIS_TYPE_SIMILARITY.get(key, 30)


def calculate_drawdown(current, peak):
    """Calculate drawdown percentage from peak."""
    if peak <= 0:
        return None
    return round((current - peak) / peak * 100, 2)


def calculate_decline_speed(drawdown_pct, days):
    """Calculate decline speed (% per day). Higher = faster decline."""
    if days <= 0:
        return None
    return round(abs(drawdown_pct) / days, 2)


def classify_speed(days_to_bottom):
    """Classify decline speed category."""
    if days_to_bottom <= 10:
        return 'flash'
    elif days_to_bottom <= 30:
        return 'rapid'
    elif days_to_bottom <= 90:
        return 'moderate'
    elif days_to_bottom <= 180:
        return 'gradual'
    else:
        return 'prolonged'


def dimension_similarity(current_val, historical_val, scale):
    """Calculate similarity for a single dimension (0-100).

    Scale defines the range where difference maps to ~50% similarity.
    At diff = 2*scale, similarity = 0%.
    """
    if current_val is None or historical_val is None:
        return None
    diff = abs(current_val - historical_val)
    sim = max(0, 100 * (1 - diff / (2 * scale)))
    return round(sim, 1)


def calculate_overall_similarity(current_data, crisis):
    """Calculate weighted overall similarity score (0-100).

    Weights: VIX 20%, KOSPI drawdown 25%, S&P500 15%, speed 15%, type 25%.
    """
    scores = {}
    weights = {
        'vix': 0.20,
        'kospi_drop': 0.25,
        'sp500_drop': 0.15,
        'speed': 0.15,
        'type': 0.25,
    }

    # VIX similarity (scale=25: 50-point diff -> 0%)
    if current_data.get('vix') is not None:
        scores['vix'] = dimension_similarity(
            current_data['vix'], crisis['vix_peak'], 25)

    # KOSPI drawdown similarity (scale=15: 30pp diff -> 0%)
    if current_data.get('kospi_drop_pct') is not None:
        scores['kospi_drop'] = dimension_similarity(
            abs(current_data['kospi_drop_pct']),
            abs(crisis['kospi_drop_pct']), 15)

    # S&P 500 drawdown similarity (scale=15)
    if current_data.get('sp500_drop_pct') is not None:
        scores['sp500_drop'] = dimension_similarity(
            abs(current_data['sp500_drop_pct']),
            abs(crisis['sp500_drop_pct']), 15)

    # Speed similarity (scale=5: 10 %/day diff -> 0%)
    if (current_data.get('decline_speed') is not None
            and crisis['days_to_bottom'] > 0):
        hist_speed = abs(crisis['kospi_drop_pct']) / crisis['days_to_bottom']
        scores['speed'] = dimension_similarity(
            current_data['decline_speed'], hist_speed, 5)

    # Crisis type similarity
    if current_data.get('crisis_type') is not None:
        scores['type'] = get_type_similarity(
            current_data['crisis_type'], crisis['crisis_type'])

    if not scores:
        return 0

    total_weight = sum(weights[k] for k in scores if scores[k] is not None)
    if total_weight == 0:
        return 0

    weighted_sum = sum(
        scores[k] * weights[k] for k in scores if scores[k] is not None
    )
    return round(weighted_sum / total_weight, 1)


def rank_crises_by_similarity(current_data):
    """Rank all historical crises by similarity to current situation.

    Returns list of (crisis_key, similarity_score, crisis_data) sorted desc.
    """
    rankings = []
    for key, crisis in HISTORICAL_CRISES.items():
        score = calculate_overall_similarity(current_data, crisis)
        rankings.append((key, score, crisis))
    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings


def get_recovery_pattern(crisis_key):
    """Get recovery pattern data for a specific crisis."""
    crisis = HISTORICAL_CRISES.get(crisis_key)
    if not crisis:
        return None
    return {
        'name': crisis['name'],
        'days_to_bottom': crisis['days_to_bottom'],
        'recovery_1w': crisis['recovery_1w_pct'],
        'recovery_1m': crisis['recovery_1m_pct'],
        'recovery_3m': crisis['recovery_3m_pct'],
        'recovery_6m': crisis['recovery_6m_pct'],
        'speed_category': classify_speed(crisis['days_to_bottom']),
    }


def generate_scenarios(most_similar_key, current_data):
    """Generate 3 scenarios (optimistic/base/conservative) based on
    the most similar historical pattern.
    """
    crisis = HISTORICAL_CRISES.get(most_similar_key)
    if not crisis:
        return None

    kospi_current = current_data.get('kospi_current')
    if kospi_current is None:
        return None

    rec_1m = crisis.get('recovery_1m_pct')
    rec_3m = crisis.get('recovery_3m_pct')

    # If most similar crisis has no recovery data (ongoing), use average
    if rec_1m is None or rec_3m is None:
        available = [c for c in HISTORICAL_CRISES.values()
                     if c['recovery_1m_pct'] is not None]
        if not available:
            return None
        rec_1m = sum(c['recovery_1m_pct'] for c in available) / len(available)
        rec_3m = sum(c['recovery_3m_pct'] for c in available) / len(available)

    return {
        'optimistic': {
            'label': '낙관',
            'condition': '조기 외교적 해결 / 대규모 부양책 / VIX 급락',
            'recovery_factor': 1.3,
            'kospi_1m': round(kospi_current * (1 + rec_1m * 1.3 / 100)),
            'kospi_3m': round(kospi_current * (1 + rec_3m * 1.3 / 100)),
        },
        'base': {
            'label': '기본',
            'condition': '점진적 안정화 / 과거 패턴 반복',
            'recovery_factor': 1.0,
            'kospi_1m': round(kospi_current * (1 + rec_1m / 100)),
            'kospi_3m': round(kospi_current * (1 + rec_3m / 100)),
        },
        'conservative': {
            'label': '보수',
            'condition': '위기 장기화 / 추가 악재 / 신용경색',
            'recovery_factor': 0.5,
            'kospi_1m': round(kospi_current * (1 + rec_1m * 0.5 / 100)),
            'kospi_3m': round(kospi_current * (1 + rec_3m * 0.5 / 100)),
        },
    }


def identify_unique_risks(current_data, crisis):
    """Identify risks unique to current situation vs the most similar crisis."""
    current_features = set(current_data.get('key_features', []))
    historical_features = set(crisis.get('key_features', []))
    return {
        'unique_to_current': sorted(current_features - historical_features),
        'shared': sorted(current_features & historical_features),
        'unique_to_historical': sorted(historical_features - current_features),
    }


def format_pct(value):
    """Format a percentage value with sign."""
    if value is None:
        return "진행중"
    return f"{value:+.1f}%"


def format_number(value):
    """Format a number with comma separators."""
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"


def fetch_yfinance_data():
    """Fetch current market data from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance",
              file=sys.stderr)
        return None

    results = {}
    tickers = {
        'KOSPI': '^KS11',
        'VIX': '^VIX',
        'SP500': '^GSPC',
        'USDKRW': 'KRW=X',
    }

    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period='6mo')
            if len(hist) >= 2:
                current = float(hist['Close'].iloc[-1])
                peak = float(hist['Close'].max())
                prev = float(hist['Close'].iloc[-2])
                change_1d = (current - prev) / prev * 100
                drawdown = (current - peak) / peak * 100
                results[name] = {
                    'current': round(current, 2),
                    'peak_6m': round(peak, 2),
                    'prev': round(prev, 2),
                    'change_1d_pct': round(change_1d, 2),
                    'drawdown_pct': round(drawdown, 2),
                }
        except Exception as e:
            results[name] = {'error': str(e)}

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Crisis Compare - Historical crisis pattern comparison')
    parser.add_argument('--format', choices=['json', 'markdown'],
                        default='markdown')
    parser.add_argument('--crisis-type',
                        choices=['financial', 'pandemic', 'monetary',
                                 'trade', 'geopolitical'],
                        help='Override auto-detected crisis type')
    args = parser.parse_args()

    raw = fetch_yfinance_data()
    if not raw:
        sys.exit(1)

    # Build current_data dict
    current_data = {}

    if 'KOSPI' in raw and 'error' not in raw['KOSPI']:
        current_data['kospi_current'] = raw['KOSPI']['current']
        current_data['kospi_peak'] = raw['KOSPI']['peak_6m']
        current_data['kospi_drop_pct'] = raw['KOSPI']['drawdown_pct']

    if 'VIX' in raw and 'error' not in raw['VIX']:
        current_data['vix'] = raw['VIX']['current']

    if 'SP500' in raw and 'error' not in raw['SP500']:
        current_data['sp500_drop_pct'] = raw['SP500']['drawdown_pct']

    # Estimate decline speed (default 5 days for rapid drops)
    if current_data.get('kospi_drop_pct') is not None:
        current_data['decline_speed'] = abs(
            current_data['kospi_drop_pct']) / 5

    if args.crisis_type:
        current_data['crisis_type'] = args.crisis_type
    else:
        # Default; SKILL.md guides manual override
        current_data['crisis_type'] = 'geopolitical'

    # Rank similarities
    rankings = rank_crises_by_similarity(current_data)
    most_similar_key = rankings[0][0]
    most_similar = rankings[0][2]

    # Recovery pattern
    recovery = get_recovery_pattern(most_similar_key)

    # Scenarios
    scenarios = generate_scenarios(most_similar_key, current_data)

    if args.format == 'json':
        output = {
            'current_data': current_data,
            'rankings': [
                {'key': k, 'score': s, 'name': c['name']}
                for k, s, c in rankings
            ],
            'most_similar': most_similar_key,
            'recovery': recovery,
            'scenarios': scenarios,
            'raw': raw,
            'timestamp': datetime.now().isoformat(),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"# 역사적 위기 비교 분석 — {now}")
        print()

        # Current situation
        print("## 현재 시장 상황")
        print()
        print("| 지표 | 현재값 | 6개월 고점 | 고점대비 하락 |")
        print("|------|--------|-----------|-------------|")
        for name, label in [('KOSPI', 'KOSPI'), ('VIX', 'VIX'),
                            ('SP500', 'S&P 500'), ('USDKRW', 'USD/KRW')]:
            if name in raw and 'error' not in raw[name]:
                d = raw[name]
                print(f"| {label} | {format_number(d['current'])} | "
                      f"{format_number(d['peak_6m'])} | "
                      f"{format_pct(d['drawdown_pct'])} |")
        print()

        # Similarity ranking
        print("## 유사도 순위")
        print()
        print("| 순위 | 위기 사례 | 유사도 | VIX | KOSPI 하락 | 속도 |")
        print("|------|----------|--------|-----|-----------|------|")
        for i, (key, score, crisis) in enumerate(rankings, 1):
            speed_cat = classify_speed(crisis['days_to_bottom'])
            print(f"| {i} | {crisis['name']} ({crisis['date']}) | "
                  f"{score}% | {crisis['vix_peak']} | "
                  f"{format_pct(crisis['kospi_drop_pct'])} | {speed_cat} |")
        print()

        # Most similar comparison table
        print(f"## 가장 유사한 사례: "
              f"{most_similar['name']} ({most_similar['date']})")
        print()
        print("| 항목 | 가장 유사한 과거 사례 | 현재 상황 |")
        print("|------|---------------------|----------|")
        print(f"| 위기 유형 | {most_similar['crisis_type']} | "
              f"{current_data.get('crisis_type', '-')} |")
        print(f"| 트리거 | {most_similar['trigger']} | 현재 진행중 |")
        print(f"| VIX 최고 | {most_similar['vix_peak']} | "
              f"{current_data.get('vix', '-')} |")
        print(f"| KOSPI 하락폭 | "
              f"{format_pct(most_similar['kospi_drop_pct'])} | "
              f"{format_pct(current_data.get('kospi_drop_pct'))} |")
        print(f"| S&P500 하락폭 | "
              f"{format_pct(most_similar['sp500_drop_pct'])} | "
              f"{format_pct(current_data.get('sp500_drop_pct'))} |")
        print(f"| 바닥까지 | {most_similar['days_to_bottom']}일 | 진행중 |")
        print()

        # Recovery pattern
        if recovery:
            print("## 유사 사례 회복 패턴")
            print()
            print(f"- 바닥까지 소요: **{recovery['days_to_bottom']}일** "
                  f"({recovery['speed_category']})")
            print(f"- 바닥 대비 1주 후: "
                  f"**{format_pct(recovery['recovery_1w'])}**")
            print(f"- 바닥 대비 1개월 후: "
                  f"**{format_pct(recovery['recovery_1m'])}**")
            print(f"- 바닥 대비 3개월 후: "
                  f"**{format_pct(recovery['recovery_3m'])}**")
            print(f"- 바닥 대비 6개월 후: "
                  f"**{format_pct(recovery['recovery_6m'])}**")
            print()

        # Scenarios
        if scenarios:
            print("## 과거 패턴 기반 예상 시나리오")
            print()
            for key in ['optimistic', 'base', 'conservative']:
                s = scenarios[key]
                print(f"- **{s['label']}**: ({s['condition']}) → "
                      f"KOSPI 1개월 {format_number(s['kospi_1m'])}, "
                      f"3개월 {format_number(s['kospi_3m'])}")
            print()
            print("> 주의: 과거 패턴은 미래를 보장하지 않습니다. "
                  "참고용으로만 활용하세요.")


if __name__ == '__main__':
    main()
