"""kr-stochastic-filter 단위 테스트."""

import os
import sys

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from stochastic_checker import check_stochastic, _classify_zone
from _kr_common.utils.ta_utils import stochastic_slow


def _make_ohlcv(n=80, base=50000, trend=100):
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


def _make_ohlcv_monotonic_up(n=80, base=50000, step=500):
    """완벽한 상승 추세 OHLCV (테스트 확정용)."""
    dates = pd.date_range('2025-01-01', periods=n, freq='B')
    closes = [base + i * step for i in range(n)]
    highs = [c + 200 for c in closes]
    lows = [c - 200 for c in closes]
    opens = [c - 100 for c in closes]
    volumes = [500000] * n

    return pd.DataFrame({
        'Open': opens, 'High': highs, 'Low': lows,
        'Close': closes, 'Volume': volumes,
    }, index=dates)


def _make_ohlcv_monotonic_down(n=80, base=100000):
    """가속 하락 추세 OHLCV (테스트 확정용)."""
    dates = pd.date_range('2025-01-01', periods=n, freq='B')
    # 가속 하락: 처음 횡보 후 점점 강한 하락
    closes = []
    for i in range(n):
        if i < 30:
            closes.append(base - i * 100)
        else:
            closes.append(base - 30 * 100 - (i - 30) * 800)
    highs = [c + 200 for c in closes]
    lows = [c - 200 for c in closes]
    opens = [c + 150 for c in closes]
    volumes = [500000] * n

    return pd.DataFrame({
        'Open': opens, 'High': highs, 'Low': lows,
        'Close': closes, 'Volume': volumes,
    }, index=dates)


# ── stochastic_slow ta_utils 테스트 ────────────────────────

class TestStochasticSlowTaUtils:

    def test_default_params(self):
        df = _make_ohlcv()
        result = stochastic_slow(df['High'], df['Low'], df['Close'])
        assert list(result.columns) == ['Slow%K', 'Slow%D']

    def test_custom_params_18_10_10(self):
        df = _make_ohlcv(n=100)
        result = stochastic_slow(df['High'], df['Low'], df['Close'],
                                  k_period=18, slow_k_period=10, slow_d_period=10)
        valid = result.dropna()
        assert len(valid) > 0

    def test_range_0_100(self):
        df = _make_ohlcv(n=100)
        result = stochastic_slow(df['High'], df['Low'], df['Close'])
        valid = result.dropna()
        assert valid['Slow%K'].min() >= 0
        assert valid['Slow%K'].max() <= 100
        assert valid['Slow%D'].min() >= 0
        assert valid['Slow%D'].max() <= 100

    def test_slow_d_lags_slow_k(self):
        """Slow %D는 Slow %K의 이동평균이므로 더 느리게 반응."""
        df = _make_ohlcv(n=100)
        result = stochastic_slow(df['High'], df['Low'], df['Close'])
        # NaN 아닌 행의 수가 다름 (D가 더 적음)
        k_valid = result['Slow%K'].dropna()
        d_valid = result['Slow%D'].dropna()
        assert len(d_valid) <= len(k_valid)


# ── classify_zone 테스트 ───────────────────────────────────

class TestClassifyZone:

    def test_overbought(self):
        assert _classify_zone(85) == '과매수'
        assert _classify_zone(100) == '과매수'

    def test_oversold(self):
        assert _classify_zone(15) == '과매도'
        assert _classify_zone(0) == '과매도'

    def test_neutral(self):
        assert _classify_zone(50) == '중립'
        assert _classify_zone(20) == '중립'
        assert _classify_zone(80) == '중립'


# ── check_stochastic 테스트 ────────────────────────────────

class TestCheckStochastic:

    def test_result_fields(self):
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        required = ['ticker', 'pass', 'slow_k', 'slow_d', 'diff', 'zone',
                     'prev_slow_k', 'prev_slow_d', 'cross_up', 'date', 'params', 'error']
        for key in required:
            assert key in result, f'Missing key: {key}'

    def test_pass_condition(self):
        """Slow %K >= Slow %D = PASS."""
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        if result['error'] is None:
            if result['slow_k'] >= result['slow_d']:
                assert result['pass'] is True
            else:
                assert result['pass'] is False

    def test_diff_calculation(self):
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        if result['error'] is None:
            assert abs(result['diff'] - (result['slow_k'] - result['slow_d'])) < 0.1

    def test_insufficient_data(self):
        df = _make_ohlcv(n=10)
        result = check_stochastic('TEST', ohlcv=df)
        assert result['error'] is not None
        assert '부족' in result['error']

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = check_stochastic('TEST', ohlcv=df)
        assert result['error'] is not None

    def test_params_string(self):
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        assert result['params'] == '(18,10,10)'

    def test_custom_params(self):
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df, k_period=14, slow_k_period=3, slow_d_period=3)
        assert result['params'] == '(14,3,3)'

    def test_uptrend_pass(self):
        """강한 상승 추세에서 PASS."""
        df = _make_ohlcv_monotonic_up(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        assert result['error'] is None
        assert result['pass'] is True

    def test_downtrend_oversold(self):
        """강한 하락 추세에서 과매도 영역."""
        df = _make_ohlcv_monotonic_down(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        assert result['error'] is None
        # 일정 하락에서 %K=%D 수렴은 수학적 정상
        # 핵심: 과매도 영역에 위치해야 함
        assert result['slow_k'] < 20
        assert result['zone'] == '과매도'

    def test_lowercase_columns(self):
        """소문자 컬럼명도 지원."""
        df = _make_ohlcv(n=80)
        df.columns = [c.lower() for c in df.columns]
        result = check_stochastic('TEST', ohlcv=df)
        assert result['error'] is None

    def test_cross_up_detection(self):
        """골든크로스 감지."""
        df = _make_ohlcv(n=80)
        result = check_stochastic('TEST', ohlcv=df)
        if result['error'] is None:
            assert isinstance(result['cross_up'], bool)
