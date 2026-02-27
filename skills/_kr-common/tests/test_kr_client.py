"""KRClient 통합 테스트.

실행: python3 -m pytest ~/.claude/skills/_kr-common/tests/ -v
또는: python3 ~/.claude/skills/_kr-common/tests/test_kr_client.py
"""

import sys
import os

# 모듈 경로 추가
sys.path.insert(0, os.path.expanduser('~/.claude/skills/_kr-common'))
sys.path.insert(0, os.path.expanduser('~/.claude/skills'))

import unittest
import pandas as pd


class TestKRClientImport(unittest.TestCase):
    """모듈 임포트 테스트."""

    def test_import_kr_client(self):
        from _kr_common.kr_client import KRClient
        client = KRClient()
        self.assertIsNotNone(client)
        self.assertEqual(client.tier, 1)  # Tier 2 환경변수 없으므로

    def test_import_config(self):
        from _kr_common.config import KRConfig, get_config
        config = get_config()
        self.assertIsInstance(config, KRConfig)

    def test_import_providers(self):
        from _kr_common.providers import PyKRXProvider, FDRProvider, DARTProvider, KISProvider
        self.assertIsNotNone(PyKRXProvider)
        self.assertIsNotNone(FDRProvider)

    def test_import_utils(self):
        from _kr_common.utils import date_utils, ticker_utils, ta_utils
        self.assertIsNotNone(date_utils)
        self.assertIsNotNone(ta_utils)


class TestDateUtils(unittest.TestCase):
    """날짜 유틸 테스트."""

    def test_to_krx_format(self):
        from _kr_common.utils.date_utils import to_krx_format
        self.assertEqual(to_krx_format('2026-02-27'), '20260227')
        self.assertEqual(to_krx_format('20260227'), '20260227')

    def test_from_krx_format(self):
        from _kr_common.utils.date_utils import from_krx_format
        self.assertEqual(from_krx_format('20260227'), '2026-02-27')
        self.assertEqual(from_krx_format('2026-02-27'), '2026-02-27')

    def test_today(self):
        from _kr_common.utils.date_utils import today
        result = today()
        self.assertEqual(len(result), 10)  # YYYY-MM-DD
        self.assertIn('-', result)

    def test_get_recent_trading_day(self):
        from _kr_common.utils.date_utils import get_recent_trading_day
        result = get_recent_trading_day()
        self.assertIsNotNone(result)

    def test_get_n_days_ago(self):
        from _kr_common.utils.date_utils import get_n_days_ago
        result = get_n_days_ago(5, '2026-02-27')
        self.assertIsNotNone(result)

    def test_date_range(self):
        from _kr_common.utils.date_utils import date_range
        result = date_range('2026-02-23', '2026-02-27')
        self.assertTrue(len(result) > 0)
        # 주말 제외 확인
        self.assertTrue(len(result) <= 5)


class TestTAUtils(unittest.TestCase):
    """기술적 분석 유틸 테스트."""

    def setUp(self):
        import numpy as np
        np.random.seed(42)
        self.prices = pd.Series(np.random.randn(100).cumsum() + 100)
        self.high = self.prices + abs(pd.Series(np.random.randn(100)))
        self.low = self.prices - abs(pd.Series(np.random.randn(100)))
        self.volume = pd.Series(np.random.randint(1000, 10000, 100).astype(float))

    def test_sma(self):
        from _kr_common.utils.ta_utils import sma
        result = sma(self.prices, 20)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.iloc[19:].notna().all())

    def test_ema(self):
        from _kr_common.utils.ta_utils import ema
        result = ema(self.prices, 20)
        self.assertEqual(len(result), 100)

    def test_rsi(self):
        from _kr_common.utils.ta_utils import rsi
        result = rsi(self.prices, 14)
        valid = result.dropna()
        self.assertTrue((valid >= 0).all() and (valid <= 100).all())

    def test_macd(self):
        from _kr_common.utils.ta_utils import macd
        result = macd(self.prices)
        self.assertIn('MACD', result.columns)
        self.assertIn('Signal', result.columns)
        self.assertIn('Histogram', result.columns)

    def test_bollinger_bands(self):
        from _kr_common.utils.ta_utils import bollinger_bands
        result = bollinger_bands(self.prices)
        self.assertIn('Upper', result.columns)
        self.assertIn('Middle', result.columns)
        self.assertIn('Lower', result.columns)

    def test_stochastic(self):
        from _kr_common.utils.ta_utils import stochastic
        result = stochastic(self.high, self.low, self.prices)
        self.assertIn('%K', result.columns)
        self.assertIn('%D', result.columns)


class TestCache(unittest.TestCase):
    """캐시 테스트."""

    def setUp(self):
        import tempfile
        self.cache_dir = tempfile.mkdtemp()
        from _kr_common.utils.cache import FileCache
        self.cache = FileCache(self.cache_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_set_and_get(self):
        self.cache.set('test_key', {'value': 42}, ttl='permanent')
        result = self.cache.get('test_key')
        self.assertEqual(result, {'value': 42})

    def test_cache_miss(self):
        result = self.cache.get('nonexistent_key')
        self.assertIsNone(result)

    def test_invalidate(self):
        self.cache.set('key1', 'val1', ttl='permanent')
        self.cache.set('key2', 'val2', ttl='permanent')
        self.cache.invalidate()
        self.assertIsNone(self.cache.get('key1'))
        self.assertIsNone(self.cache.get('key2'))

    def test_dataframe_cache(self):
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        self.cache.set('df_key', df, ttl='permanent')
        result = self.cache.get('df_key')
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertEqual(len(result), 3)


class TestDARTFallback(unittest.TestCase):
    """DART 키 없을 때 graceful fallback."""

    def test_dart_unavailable(self):
        from _kr_common.kr_client import KRClient
        client = KRClient(dart_api_key='')
        result = client.get_financial_statements('005930', 2025)
        self.assertIsNone(result)

    def test_dart_disclosures_fallback(self):
        from _kr_common.kr_client import KRClient
        client = KRClient(dart_api_key='')
        result = client.get_disclosures('005930')
        self.assertTrue(isinstance(result, pd.DataFrame))


class TestModels(unittest.TestCase):
    """데이터 모델 테스트."""

    def test_stock_price_model(self):
        from _kr_common.models.stock import StockPrice
        price = StockPrice(
            ticker='005930', name='삼성전자', close=72000,
            open=71500, high=72500, low=71000, volume=12345678,
        )
        d = price.to_dict()
        self.assertEqual(d['ticker'], '005930')
        self.assertEqual(d['close'], 72000)

    def test_financial_statement_model(self):
        from _kr_common.models.financial import FinancialStatement
        fs = FinancialStatement(
            ticker='005930', year=2025,
            revenue=302_000_000_000_000,
            operating_income=36_000_000_000_000,
            net_income=27_000_000_000_000,
            total_equity=350_000_000_000_000,
        )
        self.assertAlmostEqual(fs.operating_margin, 11.92, places=1)
        self.assertTrue(fs.roe > 0)

    def test_index_codes(self):
        from _kr_common.models.market import INDEX_CODES
        self.assertEqual(INDEX_CODES['KOSPI'], '0001')
        self.assertEqual(INDEX_CODES['KOSDAQ'], '1001')


if __name__ == '__main__':
    unittest.main(verbosity=2)
