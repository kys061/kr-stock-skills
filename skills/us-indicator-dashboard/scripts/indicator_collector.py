"""미국 경제지표 데이터 수집 모듈.

21개 지표를 yfinance(국채 2개) + WebSearch context(19개)로 수집한다.
"""

import json
import os
from typing import Optional

# ── 21개 지표 ID ──────────────────────────────────
INDICATOR_IDS = [
    'gdp', 'fed_rate', 'treasury_2y', 'treasury_10y',
    'cpi', 'pce', 'ppi', 'inflation_exp',
    'unemployment', 'weekly_hours', 'hourly_earnings',
    'real_earnings', 'jobless_claims', 'retail_sales',
    'ism_pmi', 'consumer_sentiment', 'consumer_confidence',
    'business_inventories', 'housing_starts', 'auto_sales',
    'current_account',
]

CATEGORY_MAP = {
    'growth': ['gdp'],
    'rates': ['fed_rate', 'treasury_2y', 'treasury_10y'],
    'inflation': ['cpi', 'pce', 'ppi', 'inflation_exp'],
    'economy': ['unemployment', 'weekly_hours', 'hourly_earnings',
                'real_earnings', 'jobless_claims', 'retail_sales'],
    'leading': ['ism_pmi', 'consumer_sentiment', 'consumer_confidence'],
    'coincident': ['business_inventories', 'housing_starts', 'auto_sales'],
    'external': ['current_account'],
}

CATEGORY_NAMES_KR = {
    'growth': '성장',
    'rates': '금리',
    'inflation': '물가',
    'economy': '경기',
    'leading': '경기 선행',
    'coincident': '경기 동행',
    'external': '대외',
}

CATEGORY_ORDER = ['growth', 'rates', 'inflation', 'economy',
                  'leading', 'coincident', 'external']

# ── 의미 역방향 지표 (값 상승이 경기에 부정적) ────
REVERSE_INDICATORS = {'unemployment', 'jobless_claims', 'current_account'}

# ── 물가 지표 (값 하락 = '둔화') ─────────────────
INFLATION_INDICATORS = {'cpi', 'pce', 'ppi', 'inflation_exp'}

# ── 기준선 지표 ──────────────────────────────────
BASELINE_INDICATORS = {
    'ism_pmi': 50.0,
    'consumer_sentiment': 100.0,
    'consumer_confidence': 100.0,
}

# ── yfinance 티커 (국채 2개만) ────────────────────
YFINANCE_TICKERS = {
    'treasury_2y': '^IRX',
    'treasury_10y': '^TNX',
}


def load_indicator_meta() -> list:
    """references/indicator_meta.json 로드."""
    meta_path = os.path.join(
        os.path.dirname(__file__), '..', 'references', 'indicator_meta.json'
    )
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('indicators', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_meta()


def _default_meta() -> list:
    """indicator_meta.json 없을 때 기본 메타데이터."""
    defaults = []
    for ind_id in INDICATOR_IDS:
        category = None
        for cat, ids in CATEGORY_MAP.items():
            if ind_id in ids:
                category = cat
                break
        defaults.append({
            'id': ind_id,
            'name_kr': ind_id,
            'name_en': ind_id,
            'category': category or 'unknown',
            'unit': '',
            'frequency': 'unknown',
            'source': 'unknown',
        })
    return defaults


def get_meta_by_id(meta_list: list, indicator_id: str) -> dict:
    """메타데이터 리스트에서 ID로 검색."""
    for m in meta_list:
        if m.get('id') == indicator_id:
            return m
    return {'id': indicator_id, 'name_kr': indicator_id,
            'name_en': indicator_id, 'category': 'unknown',
            'unit': '', 'source': 'unknown'}


def calc_direction(value: float, prev_value: float,
                   indicator_id: str) -> tuple:
    """변화 방향 화살표와 추세 라벨 계산.

    Returns:
        (direction, trend_label)
    """
    if value is None or prev_value is None:
        return ('→', '데이터 없음')

    change = value - prev_value
    threshold = abs(prev_value) * 0.001 if prev_value != 0 else 0.001

    if abs(change) < threshold:
        direction = '→'
    elif change > 0:
        direction = '↑'
    else:
        direction = '↓'

    # 추세 라벨 결정
    if direction == '→':
        trend_label = '보합'
    elif indicator_id in INFLATION_INDICATORS:
        trend_label = '가속' if direction == '↑' else '둔화'
    elif indicator_id in REVERSE_INDICATORS:
        if indicator_id == 'current_account':
            trend_label = '적자확대' if direction == '↓' else '적자축소'
        else:
            trend_label = '냉각' if direction == '↑' else '개선'
    elif indicator_id in BASELINE_INDICATORS:
        baseline = BASELINE_INDICATORS[indicator_id]
        if indicator_id == 'ism_pmi':
            if value >= baseline:
                trend_label = '확장' if direction == '↑' else '확장둔화'
            else:
                trend_label = '수축완화' if direction == '↑' else '수축'
        else:
            trend_label = '개선' if direction == '↑' else '악화'
    else:
        trend_label = '상승' if direction == '↑' else '하락'

    return (direction, trend_label)


def collect_treasury_yields() -> dict:
    """yfinance로 국채 수익률 수집."""
    results = {}
    try:
        import yfinance as yf
        tickers_str = ' '.join(YFINANCE_TICKERS.values())
        data = yf.download(tickers_str, period='5d', progress=False)

        for ind_id, ticker in YFINANCE_TICKERS.items():
            try:
                if len(YFINANCE_TICKERS) > 1 and ticker in data.columns.get_level_values(1):
                    closes = data['Close'][ticker].dropna()
                else:
                    closes = data['Close'].dropna()

                if len(closes) >= 2:
                    value = float(closes.iloc[-1])
                    prev_value = float(closes.iloc[-2])
                    # ^TNX는 이미 %단위로 표시됨 (4.26 = 4.26%)
                    results[ind_id] = {
                        'value': round(value, 2),
                        'prev_value': round(prev_value, 2),
                        'error': None,
                    }
                elif len(closes) == 1:
                    results[ind_id] = {
                        'value': round(float(closes.iloc[-1]), 2),
                        'prev_value': None,
                        'error': None,
                    }
            except Exception as e:
                results[ind_id] = {'value': None, 'prev_value': None,
                                   'error': str(e)}
    except ImportError:
        for ind_id in YFINANCE_TICKERS:
            results[ind_id] = {'value': None, 'prev_value': None,
                               'error': 'yfinance not installed'}
    except Exception as e:
        for ind_id in YFINANCE_TICKERS:
            results[ind_id] = {'value': None, 'prev_value': None,
                               'error': str(e)}

    return results


def collect_all(websearch_context: dict = None) -> list:
    """21개 지표 전체 수집.

    Args:
        websearch_context: SKILL.md에서 Claude가 주입하는 지표 데이터
            {
                'gdp': {'value': 2.3, 'prev_value': 3.1, 'release_date': '2026-01-30'},
                ...
            }

    Returns:
        list of IndicatorResult dicts
    """
    meta_list = load_indicator_meta()
    treasury_data = collect_treasury_yields()
    ws = websearch_context or {}

    results = []
    for ind_id in INDICATOR_IDS:
        meta = get_meta_by_id(meta_list, ind_id)

        # 데이터 소스 결정
        if ind_id in treasury_data:
            src = treasury_data[ind_id]
        elif ind_id in ws:
            src = ws[ind_id]
        else:
            src = {'value': None, 'prev_value': None, 'error': '미수집'}

        value = src.get('value')
        prev_value = src.get('prev_value')
        error = src.get('error')

        direction, trend_label = calc_direction(value, prev_value, ind_id)
        change = None
        if value is not None and prev_value is not None:
            change = round(value - prev_value, 4)

        result = {
            'id': ind_id,
            'name_kr': meta.get('name_kr', ind_id),
            'name_en': meta.get('name_en', ind_id),
            'category': meta.get('category', 'unknown'),
            'value': value,
            'prev_value': prev_value,
            'change': change,
            'direction': direction,
            'trend_label': trend_label,
            'unit': meta.get('unit', ''),
            'release_date': src.get('release_date'),
            'source': meta.get('source', 'unknown'),
            'baseline': meta.get('baseline'),
            'error': error,
        }
        results.append(result)

    return results


def get_collection_stats(results: list) -> dict:
    """수집 통계."""
    total = len(results)
    collected = sum(1 for r in results if r.get('value') is not None)
    failed_ids = [r['id'] for r in results if r.get('value') is None]
    return {
        'total': total,
        'collected': collected,
        'failed': total - collected,
        'rate': round(collected / total * 100, 1) if total > 0 else 0,
        'failed_ids': failed_ids,
    }
