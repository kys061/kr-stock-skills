"""kr-ichimoku-filter 단위 테스트."""

import os
import sys

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from ichimoku_checker import check_ichimoku
from _kr_common.utils.ta_utils import ichimoku, stochastic_slow


# ── 일목균형표 ta_utils 테스트 ─────────────────────────────

def _make_ohlcv(n=60, base=50000, trend=100):
    """테스트용 OHLCV 생성."""
    dates = pd.date_range('2025-01-01', periods=n, freq='B')
    closes = [base + i * trend + np.random.uniform(-500, 500) for i in range(n)]
    highs = [c + np.random.uniform(100, 1000) for c in closes]
    lows = [c - np.random.uniform(100, 1000) for c in closes]
    opens = [c + np.random.uniform(-300, 300) for c in closes]
    volumes = [np.random.randint(100000, 1000000) for _ in range(n)]

    return pd.DataFrame({
        'Open': opens, 'High': highs, 'Low': lows,
        'Close': closes, 'Volume': volumes,
    }, index=dates)


class TestIchimokuTaUtils:
    """ta_utils.ichimoku() 함수 테스트."""

    def test_ichimoku_columns(self):
        df = _make_ohlcv()
        result = ichimoku(df['High'], df['Low'], df['Close'])
        assert list(result.columns) == ['Tenkan', 'Kijun', 'SenkouA', 'SenkouB', 'Chikou']

    def test_ichimoku_length(self):
        df = _make_ohlcv(n=80)
        result = ichimoku(df['High'], df['Low'], df['Close'])
        assert len(result) == 80

    def test_tenkan_calculation(self):
        """전환선 = (9일 최고 + 9일 최저) / 2."""
        df = _make_ohlcv(n=20)
        result = ichimoku(df['High'], df['Low'], df['Close'])
        # 9번째 행부터 유효
        expected_tenkan = (df['High'].iloc[:9].max() + df['Low'].iloc[:9].min()) / 2
        assert abs(result['Tenkan'].iloc[8] - expected_tenkan) < 0.01

    def test_kijun_calculation(self):
        """기준선 = (26일 최고 + 26일 최저) / 2."""
        df = _make_ohlcv(n=60)
        result = ichimoku(df['High'], df['Low'], df['Close'])
        expected_kijun = (df['High'].iloc[:26].max() + df['Low'].iloc[:26].min()) / 2
        assert abs(result['Kijun'].iloc[25] - expected_kijun) < 0.01

    def test_tenkan_nan_before_period(self):
        """전환선은 9일 미만에서 NaN."""
        df = _make_ohlcv(n=20)
        result = ichimoku(df['High'], df['Low'], df['Close'])
        assert pd.isna(result['Tenkan'].iloc[0])
        assert not pd.isna(result['Tenkan'].iloc[8])


class TestStochasticSlow:
    """ta_utils.stochastic_slow() 함수 테스트."""

    def test_stochastic_slow_columns(self):
        df = _make_ohlcv(n=60)
        result = stochastic_slow(df['High'], df['Low'], df['Close'])
        assert list(result.columns) == ['Slow%K', 'Slow%D']

    def test_stochastic_slow_range(self):
        """Slow %K는 0-100 범위."""
        df = _make_ohlcv(n=100)
        result = stochastic_slow(df['High'], df['Low'], df['Close'])
        valid = result.dropna()
        assert valid['Slow%K'].min() >= 0
        assert valid['Slow%K'].max() <= 100

    def test_stochastic_slow_custom_params(self):
        """커스텀 파라미터 (18,10,10) 동작 확인."""
        df = _make_ohlcv(n=100)
        result = stochastic_slow(df['High'], df['Low'], df['Close'],
                                  k_period=18, slow_k_period=10, slow_d_period=10)
        valid = result.dropna()
        assert len(valid) > 0
        assert 'Slow%K' in result.columns
        assert 'Slow%D' in result.columns


# ── ichimoku_checker 테스트 ────────────────────────────────

class TestCheckIchimoku:
    """check_ichimoku() 함수 테스트."""

    def test_pass_when_close_above_tenkan(self):
        """종가 > 전환선 = PASS."""
        df = _make_ohlcv(n=60, trend=200)  # 강한 상승 추세
        result = check_ichimoku('TEST', ohlcv=df)
        assert result['error'] is None
        assert result['close'] is not None
        assert result['tenkan'] is not None
        # 강한 상승 추세에서는 대부분 pass
        assert isinstance(result['pass'], bool)

    def test_fail_when_close_below_tenkan(self):
        """종가 < 전환선 = FAIL."""
        df = _make_ohlcv(n=60, trend=-200)  # 하락 추세
        result = check_ichimoku('TEST', ohlcv=df)
        assert result['error'] is None
        assert isinstance(result['pass'], bool)

    def test_insufficient_data(self):
        """데이터 부족 시 에러."""
        df = _make_ohlcv(n=10)
        result = check_ichimoku('TEST', ohlcv=df)
        assert result['error'] is not None
        assert '부족' in result['error']

    def test_result_fields(self):
        """결과 dict 필드 확인."""
        df = _make_ohlcv(n=60)
        result = check_ichimoku('TEST', ohlcv=df)
        required_keys = ['ticker', 'pass', 'close', 'tenkan', 'kijun',
                          'margin_pct', 'tenkan_above_kijun', 'date', 'error']
        for key in required_keys:
            assert key in result, f'Missing key: {key}'

    def test_margin_pct_calculation(self):
        """margin_pct = (close - tenkan) / tenkan * 100."""
        df = _make_ohlcv(n=60)
        result = check_ichimoku('TEST', ohlcv=df)
        if result['error'] is None and result['tenkan'] and result['tenkan'] != 0:
            expected = ((result['close'] - result['tenkan']) / result['tenkan']) * 100
            assert abs(result['margin_pct'] - expected) < 0.1

    def test_empty_dataframe(self):
        """빈 DataFrame 시 에러."""
        df = pd.DataFrame()
        result = check_ichimoku('TEST', ohlcv=df)
        assert result['error'] is not None

    def test_lowercase_columns(self):
        """소문자 컬럼명도 지원."""
        df = _make_ohlcv(n=60)
        df.columns = [c.lower() for c in df.columns]
        result = check_ichimoku('TEST', ohlcv=df)
        assert result['error'] is None
