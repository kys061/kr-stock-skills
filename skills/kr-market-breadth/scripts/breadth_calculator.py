"""시장폭 지표 계산기.

KOSPI 200 / KOSDAQ 150 구성종목의 시장폭을 계산.
US TraderMonty CSV → PyKRX 원시 데이터로 대체.
"""

import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# 시장별 지수 코드
MARKET_INDEX = {
    'KOSPI200': '0028',
    'KOSDAQ150': '0177',
}

# 시장별 대표 지수 (지수 가격 추적용)
MARKET_MAIN_INDEX = {
    'KOSPI200': '0001',   # KOSPI
    'KOSDAQ150': '1001',  # KOSDAQ
}


class BreadthCalculator:
    """시장폭 지표 계산기."""

    def __init__(self, client, market: str = 'KOSPI200'):
        """
        Args:
            client: KRClient 인스턴스
            market: 'KOSPI200' 또는 'KOSDAQ150'
        """
        self.client = client
        self.market = market
        self.index_code = MARKET_INDEX[market]
        self.main_index_code = MARKET_MAIN_INDEX[market]

    def calculate(self, lookback_days: int = 250) -> dict:
        """시장폭 지표 계산.

        Args:
            lookback_days: 히스토리 기간 (영업일 기준, 기본 250일 ≈ 1년)

        Returns:
            {
                'date': str,
                'market': str,
                'breadth_raw': float,
                'breadth_8ma': float,
                'breadth_200ma': float,
                'trend': str,
                'is_peak': bool,
                'is_trough': bool,
                'bearish_signal': bool,
                'index_price': float,
                'total_stocks': int,
                'above_200ma': int,
                'breadth_history': list,
                'index_history': list,
            }
        """
        from _kr_common.utils import date_utils, ta_utils

        today = date_utils.today()
        start = date_utils.get_n_days_ago(lookback_days + 250)  # 200MA 계산 여유

        # 1. 구성종목 가져오기
        tickers = self._get_constituents()
        logger.info(f"{self.market}: {len(tickers)} 구성종목")

        # 2. 각 종목별 200MA 위 여부 계산
        above_count, total_count = self._count_above_200ma(tickers, start, today)

        # 3. Breadth Raw 계산
        if total_count > 0:
            breadth_raw = round((above_count / total_count) * 100, 2)
        else:
            breadth_raw = 0.0

        # 4. 히스토리 기반 8MA, 200MA 계산 (단일 시점만 계산)
        # 실제 운용 시 히스토리 DB가 있으면 시계열 계산 가능
        # 현재는 단일 시점 Raw만 계산하고, 히스토리가 쌓이면 MA 적용
        breadth_8ma = breadth_raw   # 히스토리 없을 때 Raw = 8MA
        breadth_200ma = breadth_raw  # 히스토리 없을 때 Raw = 200MA

        # 5. 지수 가격
        index_price = self._get_index_price(today)

        # 6. 추세 / 고점 / 저점 / 약세 신호 (히스토리 기반)
        trend = 'flat'
        is_peak = False
        is_trough = False
        bearish_signal = breadth_raw < 40

        result = {
            'date': today,
            'market': self.market,
            'breadth_raw': breadth_raw,
            'breadth_8ma': breadth_8ma,
            'breadth_200ma': breadth_200ma,
            'trend': trend,
            'is_peak': is_peak,
            'is_trough': is_trough,
            'bearish_signal': bearish_signal,
            'index_price': index_price,
            'total_stocks': total_count,
            'above_200ma': above_count,
            'breadth_history': [breadth_raw],
            'index_history': [index_price],
        }

        return result

    def calculate_with_history(self, history: list) -> dict:
        """히스토리가 있을 때 MA, 추세, 고점/저점을 계산.

        Args:
            history: 이전 breadth_raw 값 리스트 (오래된 순)

        Returns:
            업데이트된 결과 dict
        """
        from _kr_common.utils import ta_utils

        result = self.calculate()

        # 히스토리에 현재값 추가
        all_values = history + [result['breadth_raw']]
        series = pd.Series(all_values)

        # 8MA, 200MA 계산
        if len(series) >= 8:
            result['breadth_8ma'] = round(float(ta_utils.sma(series, 8).iloc[-1]), 2)
        if len(series) >= 200:
            result['breadth_200ma'] = round(float(ta_utils.sma(series, 200).iloc[-1]), 2)

        # 추세 판정
        if len(series) >= 10:
            recent = series.tail(10)
            slope = recent.iloc[-1] - recent.iloc[0]
            if slope > 2:
                result['trend'] = 'up'
            elif slope < -2:
                result['trend'] = 'down'

        # 고점/저점 탐지
        if len(series) >= 5:
            result['is_peak'] = self._detect_peak(series)
            result['is_trough'] = self._detect_trough(series)

        # 약세 신호
        result['bearish_signal'] = (
            result['breadth_8ma'] < 40 and result['trend'] == 'down'
        )

        result['breadth_history'] = all_values[-30:]  # 최근 30일 보관

        return result

    def _get_constituents(self) -> list:
        """지수 구성종목 코드 리스트."""
        try:
            tickers = self.client.get_index_constituents(self.index_code)
            return tickers if tickers else []
        except Exception as e:
            logger.error(f"구성종목 조회 실패: {e}")
            return []

    def _count_above_200ma(self, tickers: list, start: str, end: str) -> tuple:
        """200MA 위 종목 수 카운트.

        Returns:
            (above_count, total_count)
        """
        from _kr_common.utils import ta_utils

        above = 0
        total = 0

        for ticker in tickers:
            try:
                df = self.client.get_ohlcv(ticker, start, end)
                if df.empty or len(df) < 200:
                    continue

                close_col = '종가' if '종가' in df.columns else 'Close'
                close = df[close_col]
                ma200 = ta_utils.sma(close, 200)

                if pd.notna(ma200.iloc[-1]) and close.iloc[-1] > ma200.iloc[-1]:
                    above += 1
                total += 1
            except Exception as e:
                logger.debug(f"{ticker} 조회 실패: {e}")
                continue

        return above, total

    def _get_index_price(self, date: str) -> float:
        """대표 지수 현재가."""
        from _kr_common.utils import date_utils
        try:
            recent = date_utils.get_recent_trading_day()
            df = self.client.get_index(self.main_index_code, recent, recent)
            if not df.empty:
                return float(df.iloc[-1].get('종가', df.iloc[-1].get('Close', 0)))
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _detect_peak(series: pd.Series) -> bool:
        """8MA 기준 고점 탐지. 직전값보다 현재값이 낮고, 직전값이 전전값보다 높을 때."""
        if len(series) < 3:
            return False
        return series.iloc[-2] > series.iloc[-1] and series.iloc[-2] > series.iloc[-3]

    @staticmethod
    def _detect_trough(series: pd.Series) -> bool:
        """8MA 기준 저점 탐지."""
        if len(series) < 3:
            return False
        return series.iloc[-2] < series.iloc[-1] and series.iloc[-2] < series.iloc[-3]
