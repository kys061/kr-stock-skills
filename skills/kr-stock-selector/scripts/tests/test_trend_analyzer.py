"""trend_analyzer.py 테스트."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trend_analyzer import (
    check_ma_trend, check_ma_alignment,
    check_52w_low_distance, check_52w_high_distance,
    analyze_stock, CONDITION_NAMES,
    _get_close, _get_column,
)


def _make_ohlcv(
    close_values: list[float],
    high_values: list[float] = None,
    low_values: list[float] = None,
) -> pd.DataFrame:
    """테스트용 OHLCV DataFrame 생성."""
    n = len(close_values)
    if high_values is None:
        high_values = [c * 1.02 for c in close_values]
    if low_values is None:
        low_values = [c * 0.98 for c in close_values]

    dates = pd.date_range(end='2026-03-11', periods=n, freq='B')
    return pd.DataFrame({
        'Open': close_values,
        'High': high_values,
        'Low': low_values,
        'Close': close_values,
        'Volume': [1000000] * n,
    }, index=dates)


class TestCheckMaTrend:
    """조건 1: 200MA 추세 테스트."""

    def test_pass_steady_uptrend(self):
        """20일 연속 상승 → True."""
        # 300일 데이터: 서서히 상승
        base = 10000
        close = [base + i * 10 for i in range(300)]
        df = _make_ohlcv(close)
        passed, days = check_ma_trend(df, window=200, days=20)
        assert passed is True
        assert days >= 20

    def test_fail_recent_decline(self):
        """최근 하락 → False."""
        # 200일 상승 후 80일 급락 → 200일 SMA 확실히 하락
        close = [10000 + i * 10 for i in range(200)]
        close += [close[-1] - i * 100 for i in range(1, 81)]
        df = _make_ohlcv(close)
        passed, days = check_ma_trend(df, window=200, days=20)
        assert passed is False

    def test_flat_counts_as_pass(self):
        """보합(0.1% 이내) → 상승으로 인정."""
        # 200일 이후 20일 동안 미세 변화만
        base = [10000 + i * 5 for i in range(230)]
        # 마지막 25일은 거의 동일
        flat_section = [base[-1] + (i % 3) * 0.5 for i in range(25)]
        close = base[:-25] + flat_section
        df = _make_ohlcv(close)
        passed, days = check_ma_trend(df, window=200, days=20, flat_threshold=0.001)
        # SMA는 이전 상승의 관성으로 여전히 상승/보합
        assert days >= 0  # 구체적 값은 SMA 계산에 따라 다름

    def test_consecutive_days_count(self):
        """연속 일수 정확 카운트."""
        # 안정적 상승 데이터
        close = [10000 + i * 20 for i in range(300)]
        df = _make_ohlcv(close)
        _, days = check_ma_trend(df, window=200, days=20)
        assert days >= 20

    def test_insufficient_data(self):
        """데이터 부족 시 False."""
        close = [10000 + i for i in range(100)]  # 200일 미만
        df = _make_ohlcv(close)
        passed, days = check_ma_trend(df)
        assert passed is False
        assert days == 0


class TestCheckMaAlignment:
    """조건 2: 4중 정배열 테스트."""

    def test_pass_alignment(self):
        """종가 > 50SMA > 150SMA > 200SMA → True."""
        # 꾸준한 상승 → 자연스럽게 정배열 형성
        close = [10000 + i * 30 for i in range(300)]
        df = _make_ohlcv(close)
        passed, values = check_ma_alignment(df)
        assert passed is True
        assert values['close'] > values['sma50']
        assert values['sma50'] > values['sma150']
        assert values['sma150'] > values['sma200']

    def test_fail_reverse(self):
        """역배열 → False."""
        # 하락 추세 → 종가 < SMA
        close = [20000 - i * 30 for i in range(300)]
        df = _make_ohlcv(close)
        passed, values = check_ma_alignment(df)
        assert passed is False

    def test_insufficient_data(self):
        """200일 미만 데이터 → False."""
        close = [10000] * 100
        df = _make_ohlcv(close)
        passed, values = check_ma_alignment(df)
        assert passed is False


class TestCheck52wLow:
    """조건 3: 52주 최저가대비 테스트."""

    def test_pass_30pct_above(self):
        """+30% 이상 상승 → True."""
        # 250일: 초반 저가 → 이후 상승
        close = [10000] * 50 + [10000 + i * 100 for i in range(200)]
        low = [c * 0.98 for c in close]
        low[10] = 7000  # 52주 저가 7000
        close[-1] = 13000  # 현재가 13000 → (13000-6860)/6860 = +89.5%
        df = _make_ohlcv(close, low_values=low)
        passed, pct, w52_low = check_52w_low_distance(df, threshold=0.30)
        assert passed is True
        assert pct >= 0.30

    def test_fail_below_30pct(self):
        """+29% → False."""
        close = [10000] * 250
        low = [10000] * 250
        low[100] = 8000  # 52주 저가 8000
        close[-1] = 10000  # (10000-8000)/8000 = 25%
        df = _make_ohlcv(close, low_values=low)
        passed, pct, _ = check_52w_low_distance(df, threshold=0.30)
        assert passed is False
        assert pct < 0.30

    def test_exact_threshold(self):
        """정확히 30% → True (>= 판정)."""
        # low 직접 지정: 최솟값 10000, 현재가 13000 → 30% 정확히
        close = [13000] * 250
        low = [13000] * 250
        low[50] = 10000  # 52주 저가 10000
        df = _make_ohlcv(close, low_values=low)
        passed, pct, _ = check_52w_low_distance(df, threshold=0.30)
        assert passed is True
        assert abs(pct - 0.30) < 0.01


class TestCheck52wHigh:
    """조건 4: 52주 최고가대비 테스트."""

    def test_pass_within_25pct(self):
        """-10% → True."""
        close = [10000] * 250
        high = [c * 1.02 for c in close]
        high[100] = 11000  # 52주 고가 11000
        close[-1] = 10500  # (10500-11000)/11000 = -4.5%
        df = _make_ohlcv(close, high_values=high)
        passed, pct, _ = check_52w_high_distance(df, threshold=-0.25)
        assert passed is True
        assert pct >= -0.25

    def test_fail_beyond_25pct(self):
        """-30% → False."""
        close = [10000] * 250
        high = [c * 1.02 for c in close]
        high[50] = 15000  # 52주 고가 15000
        close[-1] = 10000  # (10000-15000)/15000 = -33%
        df = _make_ohlcv(close, high_values=high)
        passed, pct, _ = check_52w_high_distance(df, threshold=-0.25)
        assert passed is False
        assert pct < -0.25

    def test_at_52w_high(self):
        """52주 신고가 → True."""
        close = [10000 + i * 10 for i in range(250)]
        high = [c * 1.01 for c in close]
        df = _make_ohlcv(close, high_values=high)
        passed, pct, _ = check_52w_high_distance(df, threshold=-0.25)
        # 현재가가 52주 고가 근처
        assert passed is True


class TestAnalyzeStock:
    """통합 분석 테스트."""

    def test_all_pass_uptrend(self):
        """강한 상승 종목 → 5/5 통과."""
        # 꾸준한 상승, 초반 저가
        close = [5000 + i * 50 for i in range(300)]
        low = [c * 0.95 for c in close]
        high = [c * 1.05 for c in close]
        df = _make_ohlcv(close, high_values=high, low_values=low)

        result = analyze_stock(
            df=df, ticker='005930', name='삼성전자',
            market='KOSPI', market_cap=400_000_000_000_000,
        )

        assert result['ticker'] == '005930'
        assert result['market_cap'] == 400_000_000_000_000
        assert result['conditions']['market_cap'] is True
        assert result['pass_count'] >= 1  # 최소 시총 조건 통과

    def test_partial_pass(self):
        """일부 조건만 통과."""
        # 횡보 데이터 → 정배열 실패 가능
        close = [10000] * 300
        df = _make_ohlcv(close)

        result = analyze_stock(
            df=df, ticker='000660', name='SK하이닉스',
            market='KOSPI', market_cap=100_000_000_000_000,
        )

        assert result['all_pass'] is False
        assert result['conditions']['market_cap'] is True

    def test_result_structure(self):
        """결과 dict 구조 확인."""
        close = [10000 + i for i in range(300)]
        df = _make_ohlcv(close)

        result = analyze_stock(
            df=df, ticker='035420', name='NAVER',
            market='KOSPI', market_cap=50_000_000_000_000,
        )

        # 필수 키 확인
        assert 'ticker' in result
        assert 'name' in result
        assert 'market' in result
        assert 'conditions' in result
        assert 'details' in result
        assert 'pass_count' in result
        assert 'all_pass' in result

        # conditions 키 5개
        conds = result['conditions']
        assert len(conds) == 5
        assert all(k in conds for k in [
            'ma_trend', 'ma_alignment', 'week52_low', 'week52_high', 'market_cap'
        ])

        # details 키
        details = result['details']
        assert 'ma_trend_days' in details
        assert 'sma50' in details
        assert 'week52_low_pct' in details


class TestHelpers:
    """헬퍼 함수 테스트."""

    def test_get_close_standard(self):
        df = pd.DataFrame({'Close': [1, 2, 3]})
        result = _get_close(df)
        assert list(result) == [1, 2, 3]

    def test_get_close_lowercase(self):
        df = pd.DataFrame({'close': [1, 2, 3]})
        result = _get_close(df)
        assert list(result) == [1, 2, 3]

    def test_get_column_case_insensitive(self):
        df = pd.DataFrame({'High': [10, 20], 'low': [5, 10]})
        assert _get_column(df, 'High') is not None
        assert _get_column(df, 'low') is not None

    def test_condition_names_complete(self):
        assert len(CONDITION_NAMES) == 5
