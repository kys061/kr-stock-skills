"""기술적 분석 유틸리티 - RSI, MACD, 볼린저밴드 등."""

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int) -> pd.Series:
    """단순이동평균 (Simple Moving Average)."""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """지수이동평균 (Exponential Moving Average)."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index).

    Args:
        series: 가격 시계열 (Close)
        period: RSI 기간 (기본 14)

    Returns:
        RSI 값 (0~100)
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence).

    Returns:
        DataFrame(columns=['MACD', 'Signal', 'Histogram'])
    """
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram,
    })


def bollinger_bands(series: pd.Series, period: int = 20,
                    std: int = 2) -> pd.DataFrame:
    """볼린저밴드 (Bollinger Bands).

    Returns:
        DataFrame(columns=['Upper', 'Middle', 'Lower'])
    """
    middle = sma(series, period)
    std_dev = series.rolling(window=period).std()

    return pd.DataFrame({
        'Upper': middle + (std_dev * std),
        'Middle': middle,
        'Lower': middle - (std_dev * std),
    })


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """ATR (Average True Range)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """거래량 비율 (현재 거래량 / 평균 거래량)."""
    avg_vol = sma(volume, period)
    return volume / avg_vol


def disparity(close: pd.Series, period: int = 20) -> pd.Series:
    """이격도 (현재가 / 이동평균 * 100)."""
    ma = sma(close, period)
    return (close / ma) * 100


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """스토캐스틱 (Stochastic Oscillator).

    Returns:
        DataFrame(columns=['%K', '%D'])
    """
    lowest = low.rolling(window=k_period).min()
    highest = high.rolling(window=k_period).max()

    k = ((close - lowest) / (highest - lowest)) * 100
    d = sma(k, d_period)

    return pd.DataFrame({'%K': k, '%D': d})


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    """윌리엄스 %R."""
    highest = high.rolling(window=period).max()
    lowest = low.rolling(window=period).min()
    return ((highest - close) / (highest - lowest)) * -100


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV (On-Balance Volume)."""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


def rate_of_change(series: pd.Series, period: int = 12) -> pd.Series:
    """ROC (Rate of Change) %."""
    return ((series - series.shift(period)) / series.shift(period)) * 100


def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.DataFrame:
    """ADX (Average Directional Index).

    Returns:
        DataFrame(columns=['ADX', '+DI', '-DI'])
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    plus_dm = high - prev_high
    minus_dm = prev_low - low
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    # Smoothed
    atr_val = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr_val)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr_val)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx_val = dx.ewm(alpha=1/period, min_periods=period).mean()

    return pd.DataFrame({
        'ADX': adx_val,
        '+DI': plus_di,
        '-DI': minus_di,
    })
