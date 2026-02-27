"""FinanceDataReader 데이터 프로바이더.

글로벌 시세, 환율, 원자재, FRED 경제지표 전담.
한국 주식 OHLCV는 PyKRX의 폴백으로만 사용.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

import FinanceDataReader as fdr


class FDRProvider:
    """FinanceDataReader 데이터 프로바이더."""

    # 한국 지수 심볼 매핑
    KR_INDEX_MAP = {
        'KOSPI': 'KS11',
        'KOSDAQ': 'KQ11',
        'KOSPI200': 'KS200',
    }

    # 글로벌 지수 심볼 매핑
    GLOBAL_INDEX_MAP = {
        'S&P500': 'US500',
        'NASDAQ': 'IXIC',
        'DOW': 'DJI',
        'NIKKEI': 'N225',
        'SHANGHAI': '000001.SS',
        'HANGSENG': 'HSI',
        'DAX': 'GDAXI',
        'FTSE': 'FTSE',
    }

    # 환율 매핑
    FOREX_MAP = {
        'USD/KRW': 'USD/KRW',
        'EUR/KRW': 'EUR/KRW',
        'JPY/KRW': 'JPY/KRW',
        'CNY/KRW': 'CNY/KRW',
        'EUR/USD': 'EUR/USD',
    }

    # 원자재 매핑
    COMMODITY_MAP = {
        'WTI': 'CL=F',
        'GOLD': 'GC=F',
        'SILVER': 'SI=F',
        'COPPER': 'HG=F',
        'NATGAS': 'NG=F',
    }

    # ─────────────────────────────────────────
    # 시세 (한국 + 글로벌)
    # ─────────────────────────────────────────

    def get_data(self, symbol: str, start: str,
                 end: str = None) -> pd.DataFrame:
        """시세 데이터 조회 (한국/글로벌/환율/원자재).

        Args:
            symbol: 종목코드, 지수심볼, 환율쌍, 원자재 심볼
            start: 시작일 'YYYY-MM-DD'
            end: 종료일 (None이면 오늘)
        """
        try:
            if end:
                return fdr.DataReader(symbol, start, end)
            return fdr.DataReader(symbol, start)
        except Exception as e:
            logger.warning(f"FDR.get_data({symbol}) failed: {e}")
            return pd.DataFrame()

    def get_data_multi(self, symbols: list, start: str,
                       end: str = None) -> pd.DataFrame:
        """복수 종목 종가 비교 (Close만).

        Returns:
            DataFrame(columns=[symbol1, symbol2, ...])
        """
        result = {}
        for symbol in symbols:
            try:
                df = self.get_data(symbol, start, end)
                if not df.empty and 'Close' in df.columns:
                    result[symbol] = df['Close']
            except Exception as e:
                logger.warning(f"FDR.get_data_multi({symbol}) failed: {e}")
                continue

        if result:
            return pd.DataFrame(result)
        return pd.DataFrame()

    # ─────────────────────────────────────────
    # 종목 목록
    # ─────────────────────────────────────────

    def get_stock_listing(self, market: str = 'KRX') -> pd.DataFrame:
        """종목 목록 조회.

        Args:
            market: 'KOSPI', 'KOSDAQ', 'KRX' (KOSPI+KOSDAQ), 'NASDAQ', 'NYSE', 'SP500'
        """
        try:
            return fdr.StockListing(market)
        except Exception as e:
            logger.warning(f"FDR.get_stock_listing({market}) failed: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────
    # FRED 경제지표
    # ─────────────────────────────────────────

    def get_fred(self, series_id: str, start: str = None) -> pd.DataFrame:
        """FRED 경제지표.

        주요 시리즈:
            M2: 통화량
            UNRATE: 실업률
            CPIAUCSL: CPI
            FEDFUNDS: 연준 기준금리
            DGS10: 미국 10년 국채
            DGS2: 미국 2년 국채
            T10Y2Y: 10년-2년 장단기 금리차
        """
        try:
            symbol = f'FRED:{series_id}'
            if start:
                return fdr.DataReader(symbol, start)
            return fdr.DataReader(symbol, '2020-01-01')
        except Exception as e:
            logger.warning(f"FDR.get_fred({series_id}) failed: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────
    # 글로벌 지수
    # ─────────────────────────────────────────

    def get_global_index(self, symbol: str, start: str,
                         end: str = None) -> pd.DataFrame:
        """글로벌 지수 조회. 매핑 테이블에 있으면 자동 변환."""
        # 매핑 테이블에서 심볼 변환
        mapped = (
            self.KR_INDEX_MAP.get(symbol)
            or self.GLOBAL_INDEX_MAP.get(symbol)
            or self.FOREX_MAP.get(symbol)
            or self.COMMODITY_MAP.get(symbol)
            or symbol
        )
        return self.get_data(mapped, start, end)

    # ─────────────────────────────────────────
    # 미국 국채
    # ─────────────────────────────────────────

    def get_us_treasury(self, start: str,
                        end: str = None) -> pd.DataFrame:
        """미국 국채 수익률 (2Y, 5Y, 10Y, 30Y)."""
        symbols = ['FRED:DGS2', 'FRED:DGS5', 'FRED:DGS10', 'FRED:DGS30']
        result = {}
        for sym in symbols:
            try:
                df = self.get_data(sym, start, end)
                if not df.empty:
                    col_name = sym.split(':')[1]
                    if 'Close' in df.columns:
                        result[col_name] = df['Close']
                    elif len(df.columns) > 0:
                        result[col_name] = df.iloc[:, 0]
            except Exception as e:
                logger.warning(f"Failed to get {sym}: {e}")

        if result:
            return pd.DataFrame(result)
        return pd.DataFrame()
