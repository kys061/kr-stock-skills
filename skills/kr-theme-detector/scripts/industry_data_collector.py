"""KRX 업종/종목 데이터 수집기.

FINVIZ 업종별 데이터를 KRX 데이터로 대체.
각 테마 대표종목의 OHLCV, 시총, 거래량 데이터를 수집.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class IndustryDataCollector:
    """테마별 종목 데이터 수집기."""

    def __init__(self, client=None):
        """
        Args:
            client: KRClient 인스턴스 (실제 실행용, None이면 mock)
        """
        self.client = client

    def collect(self, themes: dict) -> dict:
        """테마별 종목 데이터 수집.

        Args:
            themes: kr_themes.yaml에서 로드한 테마 정의

        Returns:
            {
                'ai_semiconductor': {
                    'name': 'AI/반도체',
                    'stocks': [
                        {
                            'ticker': '005930',
                            'name': '삼성전자',
                            'role': 'core',
                            'close': 72000,
                            'change_1w': 2.5,
                            'change_1m': -3.2,
                            'volume_ratio': 1.35,
                            'above_200ma': True,
                            'above_50ma': True,
                            'positive_5d': 3,  # 최근 5일 양봉 수
                            'market_cap': 430_000_000_000_000,
                        },
                        ...
                    ],
                },
                ...
            }
        """
        results = {}

        for theme_id, theme_def in themes.items():
            stocks_data = []
            stocks = theme_def.get('representative_stocks', [])

            for stock in stocks:
                ticker = stock['ticker']
                try:
                    data = self._collect_stock_data(
                        ticker, stock['name'], stock.get('role', 'sub')
                    )
                    if data:
                        stocks_data.append(data)
                except Exception as e:
                    logger.warning(f"{theme_def['name']}/{ticker} 수집 실패: {e}")

            results[theme_id] = {
                'name': theme_def['name'],
                'description': theme_def.get('description', ''),
                'stocks': stocks_data,
            }

        return results

    def _collect_stock_data(self, ticker: str, name: str, role: str) -> dict:
        """단일 종목 데이터 수집."""
        if self.client is None:
            return None

        ohlcv = self.client.get_ohlcv(ticker, lookback_days=250)
        if ohlcv is None or len(ohlcv) < 20:
            return None

        close_col = '종가' if '종가' in ohlcv.columns else ohlcv.columns[3]
        volume_col = '거래량' if '거래량' in ohlcv.columns else ohlcv.columns[4]

        close = ohlcv[close_col]
        volume = ohlcv[volume_col]

        # 수익률
        change_1w = self._calc_return(close, 5)
        change_1m = self._calc_return(close, 20)

        # 거래량 비율 (5일 평균 / 20일 평균)
        vol_5 = volume.tail(5).mean()
        vol_20 = volume.tail(20).mean()
        volume_ratio = round(vol_5 / vol_20, 2) if vol_20 > 0 else 1.0

        # 이동평균 위치
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None

        # 최근 5일 양봉 수
        positive_5d = sum(
            1 for i in range(-5, 0) if close.iloc[i] > close.iloc[i - 1]
        ) if len(close) > 5 else 0

        return {
            'ticker': ticker,
            'name': name,
            'role': role,
            'close': float(close.iloc[-1]),
            'change_1w': round(change_1w, 2),
            'change_1m': round(change_1m, 2),
            'volume_ratio': volume_ratio,
            'above_200ma': bool(close.iloc[-1] > sma200) if sma200 else False,
            'above_50ma': bool(close.iloc[-1] > sma50) if sma50 else False,
            'positive_5d': positive_5d,
            'market_cap': 0,  # 실제 실행 시 get_market_cap() 사용
        }

    @staticmethod
    def _calc_return(close_series, days: int) -> float:
        """수익률 계산 (%)."""
        if len(close_series) <= days:
            return 0.0
        prev = close_series.iloc[-days - 1]
        curr = close_series.iloc[-1]
        if prev == 0:
            return 0.0
        return (curr - prev) / prev * 100
