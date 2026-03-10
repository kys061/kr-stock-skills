"""indicator_collector.py 테스트."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from indicator_collector import (
    INDICATOR_IDS, CATEGORY_MAP, CATEGORY_ORDER,
    REVERSE_INDICATORS, INFLATION_INDICATORS, BASELINE_INDICATORS,
    YFINANCE_TICKERS,
    load_indicator_meta, get_meta_by_id, calc_direction,
    collect_all, get_collection_stats,
)


class TestConstants:
    """상수 정의 테스트."""

    def test_indicator_count(self):
        """21개 지표 ID 확인."""
        assert len(INDICATOR_IDS) == 21

    def test_category_map_coverage(self):
        """카테고리 맵이 21개 지표를 모두 커버."""
        all_ids = []
        for ids in CATEGORY_MAP.values():
            all_ids.extend(ids)
        assert set(all_ids) == set(INDICATOR_IDS)

    def test_category_order(self):
        """7개 카테고리 순서 확인."""
        assert len(CATEGORY_ORDER) == 7
        assert set(CATEGORY_ORDER) == set(CATEGORY_MAP.keys())

    def test_reverse_indicators(self):
        """역방향 지표 확인."""
        assert 'unemployment' in REVERSE_INDICATORS
        assert 'jobless_claims' in REVERSE_INDICATORS
        assert 'current_account' in REVERSE_INDICATORS

    def test_inflation_indicators(self):
        """물가 지표 확인."""
        assert 'cpi' in INFLATION_INDICATORS
        assert 'pce' in INFLATION_INDICATORS
        assert 'ppi' in INFLATION_INDICATORS
        assert 'inflation_exp' in INFLATION_INDICATORS

    def test_yfinance_tickers(self):
        """yfinance 티커 2개 확인."""
        assert len(YFINANCE_TICKERS) == 2
        assert 'treasury_2y' in YFINANCE_TICKERS
        assert 'treasury_10y' in YFINANCE_TICKERS


class TestLoadMeta:
    """메타데이터 로드 테스트."""

    def test_load_indicator_meta(self):
        """indicator_meta.json 로드."""
        meta = load_indicator_meta()
        assert len(meta) == 21

    def test_get_meta_by_id_found(self):
        """ID로 메타 조회 — 존재."""
        meta = load_indicator_meta()
        result = get_meta_by_id(meta, 'gdp')
        assert result['id'] == 'gdp'
        assert result['category'] == 'growth'

    def test_get_meta_by_id_not_found(self):
        """ID로 메타 조회 — 미존재."""
        result = get_meta_by_id([], 'unknown_id')
        assert result['id'] == 'unknown_id'


class TestCalcDirection:
    """방향/추세 계산 테스트."""

    def test_cpi_up(self):
        """CPI 상승 → 가속."""
        d, t = calc_direction(3.0, 2.9, 'cpi')
        assert d == '↑'
        assert t == '가속'

    def test_cpi_down(self):
        """CPI 하락 → 둔화."""
        d, t = calc_direction(2.8, 2.9, 'cpi')
        assert d == '↓'
        assert t == '둔화'

    def test_unemployment_up(self):
        """실업률 상승 → 냉각."""
        d, t = calc_direction(4.2, 4.0, 'unemployment')
        assert d == '↑'
        assert t == '냉각'

    def test_unemployment_down(self):
        """실업률 하락 → 개선."""
        d, t = calc_direction(3.8, 4.0, 'unemployment')
        assert d == '↓'
        assert t == '개선'

    def test_ism_above_baseline_up(self):
        """ISM PMI 50 이상 + 상승 → 확장."""
        d, t = calc_direction(52.0, 51.0, 'ism_pmi')
        assert d == '↑'
        assert t == '확장'

    def test_ism_below_baseline_up(self):
        """ISM PMI 50 미만 + 상승 → 수축완화."""
        d, t = calc_direction(49.0, 48.0, 'ism_pmi')
        assert d == '↑'
        assert t == '수축완화'

    def test_ism_below_baseline_down(self):
        """ISM PMI 50 미만 + 하락 → 수축."""
        d, t = calc_direction(47.0, 48.0, 'ism_pmi')
        assert d == '↓'
        assert t == '수축'

    def test_flat_direction(self):
        """변화 없음 → 보합."""
        d, t = calc_direction(4.0, 4.0, 'fed_rate')
        assert d == '→'
        assert t == '보합'

    def test_none_value(self):
        """None 값 → 데이터 없음."""
        d, t = calc_direction(None, 4.0, 'gdp')
        assert d == '→'
        assert t == '데이터 없음'

    def test_current_account_down(self):
        """경상수지 하락 → 적자확대."""
        d, t = calc_direction(-250.0, -200.0, 'current_account')
        assert d == '↓'
        assert t == '적자확대'

    def test_current_account_up(self):
        """경상수지 상승 → 적자축소."""
        d, t = calc_direction(-180.0, -200.0, 'current_account')
        assert d == '↑'
        assert t == '적자축소'

    def test_general_indicator_up(self):
        """일반 지표 상승."""
        d, t = calc_direction(3.0, 2.5, 'gdp')
        assert d == '↑'
        assert t == '상승'

    def test_general_indicator_down(self):
        """일반 지표 하락."""
        d, t = calc_direction(2.0, 2.5, 'gdp')
        assert d == '↓'
        assert t == '하락'


class TestCollectAll:
    """전체 수집 테스트."""

    def test_collect_all_no_context(self):
        """WebSearch 컨텍스트 없이 수집."""
        results = collect_all()
        assert len(results) == 21

    def test_collect_all_with_context(self):
        """WebSearch 컨텍스트로 수집."""
        ctx = {
            'gdp': {'value': 2.3, 'prev_value': 3.1},
            'cpi': {'value': 2.9, 'prev_value': 3.0},
        }
        results = collect_all(websearch_context=ctx)
        gdp = next(r for r in results if r['id'] == 'gdp')
        assert gdp['value'] == 2.3
        assert gdp['prev_value'] == 3.1

    def test_result_structure(self):
        """결과 구조 검증."""
        results = collect_all()
        for r in results:
            assert 'id' in r
            assert 'name_kr' in r
            assert 'category' in r
            assert 'value' in r
            assert 'direction' in r
            assert 'trend_label' in r


class TestCollectionStats:
    """수집 통계 테스트."""

    def test_stats_all_collected(self):
        """전체 수집 성공."""
        results = [{'id': f'ind_{i}', 'value': i} for i in range(21)]
        stats = get_collection_stats(results)
        assert stats['total'] == 21
        assert stats['collected'] == 21
        assert stats['rate'] == 100.0

    def test_stats_partial(self):
        """부분 수집."""
        results = [
            {'id': 'gdp', 'value': 2.3},
            {'id': 'cpi', 'value': None},
        ]
        stats = get_collection_stats(results)
        assert stats['total'] == 2
        assert stats['collected'] == 1
        assert stats['failed'] == 1
        assert 'cpi' in stats['failed_ids']
