"""5조건 판정 엔진.

5가지 트렌드 조건에 대한 Pass/Fail 판정을 수행한다.
각 함수는 독립적으로 테스트 가능하도록 설계.

조건 1: 200일 SMA 상승+보합 추세 20일 유지
조건 2: 4중 정배열 (종가 > 50SMA > 150SMA > 200SMA)
조건 3: 52주 최저가 대비 +30% 이상
조건 4: 52주 최고가 대비 -25% 이내
조건 5: 시가총액 >= 1,000억원 (유니버스 사전필터)
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 조건명 상수
CONDITION_NAMES = {
    'ma_trend': '200MA 상승+보합 20일',
    'ma_alignment': '4중 정배열',
    'week52_low': '52주 저가 대비 +30%',
    'week52_high': '52주 고가 대비 -25%',
    'market_cap': '시가총액 >= 1,000억원',
}


def check_ma_trend(
    df: pd.DataFrame,
    window: int = 200,
    days: int = 20,
    flat_threshold: float = 0.001,
) -> tuple[bool, int]:
    """조건 1: 200일 SMA 상승+보합 추세 확인.

    Args:
        df: OHLCV DataFrame (Close 컬럼 필수)
        window: SMA 기간 (기본 200)
        days: 연속 확인 기간 (기본 20)
        flat_threshold: 보합 판정 임계값 (기본 0.1%)

    Returns:
        (pass: bool, consecutive_days: int)
    """
    close = _get_close(df)
    if close is None or len(close) < window + days:
        return False, 0

    sma = close.rolling(window=window).mean()
    sma_recent = sma.dropna().iloc[-(days + 1):]

    if len(sma_recent) < days + 1:
        return False, 0

    sma_values = sma_recent.values
    consecutive = 0

    # 최신일부터 역순으로 카운트
    for i in range(len(sma_values) - 1, 0, -1):
        today_val = sma_values[i]
        yesterday_val = sma_values[i - 1]

        if yesterday_val == 0:
            break

        change = (today_val - yesterday_val) / yesterday_val

        # 상승(change > 0) 또는 보합(|change| < threshold)
        if change >= 0 or abs(change) < flat_threshold:
            consecutive += 1
        else:
            break

    return consecutive >= days, consecutive


def check_ma_alignment(
    df: pd.DataFrame,
) -> tuple[bool, dict]:
    """조건 2: 4중 정배열 확인.

    종가 > 50일 SMA > 150일 SMA > 200일 SMA

    Returns:
        (pass: bool, sma_values: dict)
    """
    close = _get_close(df)
    if close is None or len(close) < 200:
        return False, {}

    current_close = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma150 = float(close.rolling(150).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])

    values = {
        'close': current_close,
        'sma50': sma50,
        'sma150': sma150,
        'sma200': sma200,
    }

    # NaN 체크
    if any(np.isnan(v) for v in values.values()):
        return False, values

    passed = current_close > sma50 > sma150 > sma200
    return passed, values


def check_52w_low_distance(
    df: pd.DataFrame,
    threshold: float = 0.30,
    lookback_days: int = 250,
) -> tuple[bool, float, float]:
    """조건 3: 52주 최저가 대비 현재가 상승률 확인.

    Returns:
        (pass: bool, pct_change: float, week52_low: float)
    """
    close = _get_close(df)
    low = _get_column(df, 'Low')

    if close is None or low is None or len(close) < 2:
        return False, 0.0, 0.0

    current_close = float(close.iloc[-1])
    lookback = min(lookback_days, len(low))
    week52_low = float(low.iloc[-lookback:].min())

    if week52_low <= 0:
        return False, 0.0, 0.0

    pct_change = (current_close - week52_low) / week52_low
    return pct_change >= threshold, pct_change, week52_low


def check_52w_high_distance(
    df: pd.DataFrame,
    threshold: float = -0.25,
    lookback_days: int = 250,
) -> tuple[bool, float, float]:
    """조건 4: 52주 최고가 대비 현재가 하락률 확인.

    Returns:
        (pass: bool, pct_change: float, week52_high: float)
    """
    close = _get_close(df)
    high = _get_column(df, 'High')

    if close is None or high is None or len(close) < 2:
        return False, 0.0, 0.0

    current_close = float(close.iloc[-1])
    lookback = min(lookback_days, len(high))
    week52_high = float(high.iloc[-lookback:].max())

    if week52_high <= 0:
        return False, 0.0, 0.0

    pct_change = (current_close - week52_high) / week52_high
    return pct_change >= threshold, pct_change, week52_high


def analyze_stock(
    df: pd.DataFrame,
    ticker: str,
    name: str,
    market: str,
    market_cap: int,
    config: dict = None,
) -> dict:
    """단일 종목 5조건 통합 판정.

    Args:
        df: OHLCV DataFrame (Close, High, Low 컬럼 필수)
        ticker, name, market, market_cap: 종목 정보
        config: selector_config.json의 conditions 딕셔너리

    Returns:
        AnalysisResult dict
    """
    if config is None:
        config = {}

    ma_cfg = config.get('ma_trend', {})
    w52_low_cfg = config.get('week52_low', {})
    w52_high_cfg = config.get('week52_high', {})

    # 조건 1: MA 추세
    c1_pass, c1_days = check_ma_trend(
        df,
        window=ma_cfg.get('window', 200),
        days=ma_cfg.get('days', 20),
        flat_threshold=ma_cfg.get('flat_threshold', 0.001),
    )

    # 조건 2: 정배열
    c2_pass, sma_values = check_ma_alignment(df)

    # 조건 3: 52주 저가대비
    c3_pass, c3_pct, c3_low = check_52w_low_distance(
        df,
        threshold=w52_low_cfg.get('threshold', 0.30),
        lookback_days=w52_low_cfg.get('lookback_days', 250),
    )

    # 조건 4: 52주 고가대비
    c4_pass, c4_pct, c4_high = check_52w_high_distance(
        df,
        threshold=w52_high_cfg.get('threshold', -0.25),
        lookback_days=w52_high_cfg.get('lookback_days', 250),
    )

    # 조건 5: 시가총액 (유니버스 사전필터이므로 항상 True)
    c5_pass = True

    conditions = {
        'ma_trend': c1_pass,
        'ma_alignment': c2_pass,
        'week52_low': c3_pass,
        'week52_high': c4_pass,
        'market_cap': c5_pass,
    }

    pass_count = sum(conditions.values())

    close = _get_close(df)
    current_close = int(float(close.iloc[-1])) if close is not None and len(close) > 0 else 0

    return {
        'ticker': ticker,
        'name': name,
        'market': market,
        'market_cap': market_cap,
        'close': current_close,
        'conditions': conditions,
        'details': {
            'ma_trend_days': c1_days,
            'sma50': sma_values.get('sma50', 0.0),
            'sma150': sma_values.get('sma150', 0.0),
            'sma200': sma_values.get('sma200', 0.0),
            'week52_low_pct': c3_pct,
            'week52_high_pct': c4_pct,
            'week52_low': c3_low,
            'week52_high': c4_high,
        },
        'pass_count': pass_count,
        'all_pass': pass_count == 5,
    }


# ── 헬퍼 ──

def _get_close(df: pd.DataFrame) -> Optional[pd.Series]:
    """Close 컬럼 추출 (대소문자 유연)."""
    for col in ['Close', 'close', 'Adj Close', 'adj close']:
        if col in df.columns:
            return df[col].dropna()
    return None


def _get_column(df: pd.DataFrame, name: str) -> Optional[pd.Series]:
    """컬럼 추출 (대소문자 유연)."""
    for col in [name, name.lower(), name.upper()]:
        if col in df.columns:
            return df[col].dropna()
    return None
