"""market_data_collector 단위 테스트."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from market_data_collector import (
    YFINANCE_TICKERS, WEBSEARCH_ITEMS, CATEGORY_ORDER,
    format_price, format_change,
    collect_yfinance_data, collect_websearch_data, collect_all,
)


# ── 상수 검증 ────────────────────────────────

class TestConstants:

    def test_yfinance_tickers_count(self):
        assert len(YFINANCE_TICKERS) == 17

    def test_websearch_items_count(self):
        assert len(WEBSEARCH_ITEMS) == 10

    def test_category_order_complete(self):
        assert len(CATEGORY_ORDER) == 8

    def test_all_tickers_have_category(self):
        for key, info in YFINANCE_TICKERS.items():
            assert info['category'] in CATEGORY_ORDER, f"{key}: {info['category']} not in CATEGORY_ORDER"

    def test_all_websearch_have_category(self):
        for key, info in WEBSEARCH_ITEMS.items():
            assert info['category'] in CATEGORY_ORDER, f"{key}: {info['category']} not in CATEGORY_ORDER"

    def test_all_tickers_have_required_keys(self):
        for key, info in YFINANCE_TICKERS.items():
            assert 'ticker' in info, f"{key}: missing 'ticker'"
            assert 'name' in info, f"{key}: missing 'name'"
            assert 'unit' in info, f"{key}: missing 'unit'"

    def test_all_websearch_have_query(self):
        for key, info in WEBSEARCH_ITEMS.items():
            assert 'query' in info, f"{key}: missing 'query'"
            assert len(info['query']) > 0, f"{key}: empty query"

    def test_no_duplicate_tickers(self):
        tickers = [v['ticker'] for v in YFINANCE_TICKERS.values()]
        assert len(tickers) == len(set(tickers))

    def test_no_key_overlap(self):
        yf_keys = set(YFINANCE_TICKERS.keys())
        ws_keys = set(WEBSEARCH_ITEMS.keys())
        assert len(yf_keys & ws_keys) == 0, f"Overlap: {yf_keys & ws_keys}"


# ── format_price ─────────────────────────────

class TestFormatPrice:

    def test_won(self):
        assert format_price(1485.0, '원') == '1,485원'

    def test_dollar(self):
        assert format_price(72.5, '$') == '$72.50'

    def test_percent(self):
        assert format_price(4.25, '%') == '4.25%'

    def test_point(self):
        assert format_price(47501.55, 'p') == '47,501.55p'

    def test_cent(self):
        assert format_price(450.75, '¢') == '450.75¢'

    def test_none(self):
        assert format_price(None, '$') == 'N/A'

    def test_empty_unit(self):
        result = format_price(98.99, '')
        assert '98.99' in result


# ── format_change ────────────────────────────

class TestFormatChange:

    def test_negative(self):
        assert format_change(-0.95) == '-0.95% ↓'

    def test_positive(self):
        assert format_change(1.20) == '+1.20% ↑'

    def test_zero(self):
        assert format_change(0.0) == '0.00% -'

    def test_none(self):
        assert format_change(None) == 'N/A'


# ── collect_websearch_data ───────────────────

class TestCollectWebsearchData:

    def test_no_context_all_na(self):
        result = collect_websearch_data(None)
        assert len(result) == 10
        for key, item in result.items():
            assert item['error'] is not None

    def test_with_partial_context(self):
        ctx = {
            'us2y': {'price': 4.25, 'change_pct': -0.02},
            'bdi': {'price': 1850, 'change_pct': 2.3},
        }
        result = collect_websearch_data(ctx)
        assert result['us2y']['price'] == 4.25
        assert result['us2y']['error'] is None
        assert result['bdi']['change_pct'] == 2.3
        assert result['dubai_oil']['error'] is not None

    def test_direction_calculation(self):
        ctx = {'us2y': {'price': 4.25, 'change_pct': -0.5}}
        result = collect_websearch_data(ctx)
        assert result['us2y']['direction'] == '↓'


# ── collect_all ──────────────────────────────

class TestCollectAll:

    def test_without_websearch(self):
        result = collect_all(None)
        assert 'items' in result
        assert 'categories' in result
        assert 'summary' in result
        assert result['summary']['total'] == 27

    def test_categories_structure(self):
        result = collect_all(None)
        for cat in CATEGORY_ORDER:
            assert cat in result['categories']

    def test_summary_fields(self):
        result = collect_all(None)
        s = result['summary']
        assert 'total' in s
        assert 'success' in s
        assert 'failed' in s
        assert 'timestamp' in s

    def test_with_websearch_context(self):
        ctx = {
            'us2y': {'price': 4.25, 'change_pct': -0.02},
            'dubai_oil': {'price': 72.5, 'change_pct': 1.2},
        }
        result = collect_all(ctx)
        assert result['items']['us2y']['price'] == 4.25
        assert result['items']['us2y']['error'] is None
