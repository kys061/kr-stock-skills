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


def stochastic_slow(high: pd.Series, low: pd.Series, close: pd.Series,
                    k_period: int = 18, slow_k_period: int = 10,
                    slow_d_period: int = 10) -> pd.DataFrame:
    """스토캐스틱 슬로우 (Stochastic Slow).

    Fast %K를 slow_k_period으로 평활화한 Slow %K와
    Slow %K를 slow_d_period으로 평활화한 Slow %D를 계산.

    Args:
        high: 고가 시계열
        low: 저가 시계열
        close: 종가 시계열
        k_period: Fast %K 기간 (기본 18)
        slow_k_period: Slow %K 평활 기간 (기본 10)
        slow_d_period: Slow %D 평활 기간 (기본 10)

    Returns:
        DataFrame(columns=['Slow%K', 'Slow%D'])
    """
    lowest = low.rolling(window=k_period).min()
    highest = high.rolling(window=k_period).max()

    fast_k = ((close - lowest) / (highest - lowest)) * 100
    slow_k = sma(fast_k, slow_k_period)
    slow_d = sma(slow_k, slow_d_period)

    return pd.DataFrame({'Slow%K': slow_k, 'Slow%D': slow_d})


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan_period: int = 9, kijun_period: int = 26,
             senkou_b_period: int = 52) -> pd.DataFrame:
    """일목균형표 (Ichimoku Kinko Hyo).

    Args:
        high: 고가 시계열
        low: 저가 시계열
        close: 종가 시계열
        tenkan_period: 전환선 기간 (기본 9)
        kijun_period: 기준선 기간 (기본 26)
        senkou_b_period: 선행스팬B 기간 (기본 52)

    Returns:
        DataFrame(columns=['Tenkan', 'Kijun', 'SenkouA', 'SenkouB', 'Chikou'])
        - Tenkan: 전환선 (9일 고저 중값)
        - Kijun: 기준선 (26일 고저 중값)
        - SenkouA: 선행스팬A ((전환선+기준선)/2, 26일 선행)
        - SenkouB: 선행스팬B (52일 고저 중값, 26일 선행)
        - Chikou: 후행스팬 (종가, 26일 후행)
    """
    tenkan = (high.rolling(window=tenkan_period).max()
              + low.rolling(window=tenkan_period).min()) / 2

    kijun = (high.rolling(window=kijun_period).max()
             + low.rolling(window=kijun_period).min()) / 2

    senkou_a = ((tenkan + kijun) / 2).shift(kijun_period)

    senkou_b = ((high.rolling(window=senkou_b_period).max()
                 + low.rolling(window=senkou_b_period).min()) / 2).shift(kijun_period)

    chikou = close.shift(-kijun_period)

    return pd.DataFrame({
        'Tenkan': tenkan,
        'Kijun': kijun,
        'SenkouA': senkou_a,
        'SenkouB': senkou_b,
        'Chikou': chikou,
    })


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
