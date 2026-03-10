"""universe_builder.py 테스트."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from universe_builder import (
    load_config, to_yf_ticker, build_universe, fetch_ohlcv_batch,
    _build_from_krx, _detect_market, CONFIG_PATH,
)


class TestLoadConfig:
    """설정 로드 테스트."""

    def test_load_config_success(self):
        config = load_config()
        assert 'conditions' in config
        assert 'universe' in config
        assert 'report' in config

    def test_config_has_required_conditions(self):
        config = load_config()
        cond = config['conditions']
        assert 'ma_trend' in cond
        assert 'ma_alignment' in cond
        assert 'week52_low' in cond
        assert 'week52_high' in cond
        assert 'market_cap' in cond

    def test_config_market_cap_value(self):
        config = load_config()
        min_cap = config['conditions']['market_cap']['min_krw']
        assert min_cap == 100_000_000_000  # 1,000억원

    def test_config_ma_trend_defaults(self):
        config = load_config()
        ma = config['conditions']['ma_trend']
        assert ma['window'] == 200
        assert ma['days'] == 20
        assert ma['flat_threshold'] == 0.001


class TestToYfTicker:
    """yfinance 티커 변환 테스트."""

    def test_kospi_ticker(self):
        assert to_yf_ticker('005930', 'KOSPI') == '005930.KS'

    def test_kosdaq_ticker(self):
        assert to_yf_ticker('035720', 'KOSDAQ') == '035720.KQ'

    def test_unknown_market_defaults_ks(self):
        assert to_yf_ticker('000000', 'UNKNOWN') == '000000.KS'


class TestDetectMarket:
    """시장 감지 테스트."""

    def test_kospi(self):
        row = pd.Series({'MKT_NM': 'KOSPI'})
        assert _detect_market(row) == 'KOSPI'

    def test_kosdaq(self):
        row = pd.Series({'MKT_NM': 'KOSDAQ'})
        assert _detect_market(row) == 'KOSDAQ'

    def test_empty_defaults_kospi(self):
        row = pd.Series({'MKT_NM': ''})
        assert _detect_market(row) == 'KOSPI'


class TestBuildUniverse:
    """유니버스 구축 테스트."""

    def test_build_from_krx_filters_market_cap(self):
        """KRX 데이터에서 시총 필터 정상 작동."""
        mock_provider = MagicMock()
        mock_provider.get_stock_daily.return_value = pd.DataFrame({
            'ISU_CD': ['005930', '000660', '999999'],
            'ISU_NM': ['삼성전자', 'SK하이닉스', '소형주'],
            'MKT_NM': ['KOSPI', 'KOSPI', 'KOSPI'],
            'MKTCAP': [400_000_000_000_000, 100_000_000_000_000, 50_000_000_000],
            'TDD_CLSPRC': [70000, 240000, 5000],
        })

        result = _build_from_krx(
            mock_provider, '2026-03-11', None, 200_000_000_000_000
        )
        # 시총 200조 이상 → 삼성전자만
        assert len(result) == 1
        assert result[0]['ticker'] == '005930'

    def test_build_universe_with_market_filter(self):
        """시장 필터 KOSPI/KOSDAQ 분리."""
        mock_provider = MagicMock()
        mock_provider.get_stock_daily.return_value = pd.DataFrame({
            'ISU_CD': ['005930', '035720'],
            'ISU_NM': ['삼성전자', '카카오'],
            'MKT_NM': ['KOSPI', 'KOSDAQ'],
            'MKTCAP': [400_000_000_000_000, 20_000_000_000_000],
            'TDD_CLSPRC': [70000, 50000],
        })

        result = _build_from_krx(
            mock_provider, '2026-03-11', 'KOSPI', 100_000_000_000
        )
        # market 파라미터로 필터하지 않고 (get_stock_daily에서 처리),
        # 반환된 데이터에서 시총 필터만 적용
        assert all(r['market_cap'] >= 100_000_000_000 for r in result)

    def test_build_universe_no_provider_returns_empty_or_fallback(self):
        """프로바이더 없으면 폴백 시도 (yfinance 없으면 빈 리스트)."""
        # yfinance/pykrx가 설치되지 않은 환경에서도 에러 없이 빈 리스트 반환
        with patch('universe_builder._build_from_yfinance', return_value=[]):
            result = build_universe(provider=None)
            assert isinstance(result, list)


class TestFetchOhlcvBatch:
    """OHLCV 배치 다운로드 테스트."""

    def test_empty_universe(self):
        """빈 유니버스 → 빈 dict."""
        result = fetch_ohlcv_batch([])
        assert result == {}

    def test_returns_dict(self):
        """반환 타입 확인."""
        universe = [
            {'ticker': '005930', 'yf_ticker': '005930.KS',
             'name': '삼성전자', 'market': 'KOSPI', 'market_cap': 400e12}
        ]
        with patch('universe_builder._fetch_batch_yfinance', return_value={}), \
             patch('universe_builder._fetch_individual_yfinance', return_value={}), \
             patch('universe_builder._fetch_from_pykrx', return_value={}):
            result = fetch_ohlcv_batch(universe)
            assert isinstance(result, dict)
