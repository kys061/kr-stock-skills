"""업종별 업트렌드 비율 계산기.

KRX 업종 분류 기반으로 각 업종의 업트렌드 종목 비율을 계산.
US의 Monty's Uptrend Dashboard CSV 데이터를 KRX 데이터로 대체.
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 한국 업종 그룹 정의 (대표 종목 코드)
KR_SECTOR_GROUPS = {
    'Cyclical': ['반도체', '자동차', '철강', '화학', '건설', '조선', '기계'],
    'Defensive': ['통신', '유틸리티', '필수소비재', '제약/바이오'],
    'Growth': ['2차전지', '인터넷', 'IT서비스'],
    'Financial': ['은행', '보험', '증권'],
}

# 업종 → 그룹 역매핑
SECTOR_TO_GROUP = {}
for group, sectors in KR_SECTOR_GROUPS.items():
    for sector in sectors:
        SECTOR_TO_GROUP[sector] = group

# 업종별 대표 종목 (ticker → name)
# 실제 실행 시 KRClient에서 동적으로 가져오지만, 테스트/기본값으로 사용
KR_SECTOR_STOCKS = {
    '반도체': ['005930', '000660', '042700', '403870'],
    '자동차': ['005380', '000270', '012330'],
    '철강': ['005490', '004020'],
    '화학': ['051910', '011170', '003670'],
    '건설': ['000720', '006360', '047040'],
    '조선': ['329180', '042660', '010620'],
    '기계': ['034020', '298040'],
    '통신': ['017670', '030200', '032640'],
    '유틸리티': ['015760', '036460'],
    '필수소비재': ['097950', '007310'],
    '제약/바이오': ['207940', '068270', '091990'],
    '2차전지': ['373220', '006400', '247540'],
    '인터넷': ['035420', '035720'],
    'IT서비스': ['018260', '034730'],
    '은행': ['105560', '055550', '316140'],
    '보험': ['000810', '001450'],
    '증권': ['039490', '006800'],
}


def is_uptrend(ohlcv_df: pd.DataFrame) -> bool:
    """종목이 업트렌드인지 판정.

    기준:
    1. 종가 > 200일 SMA (필수)
    2. 200일 SMA 기울기 > 0 (필수)

    Args:
        ohlcv_df: OHLCV DataFrame (최소 200일 이상)

    Returns:
        True if uptrend
    """
    if ohlcv_df is None or len(ohlcv_df) < 200:
        return False

    close = ohlcv_df['종가'] if '종가' in ohlcv_df.columns else ohlcv_df.iloc[:, 3]

    sma200 = close.rolling(200).mean()
    if pd.isna(sma200.iloc[-1]):
        return False

    # 조건 1: 종가 > 200SMA
    above_sma200 = close.iloc[-1] > sma200.iloc[-1]

    # 조건 2: SMA 기울기 > 0 (최근 20일 기준)
    if len(sma200.dropna()) < 20:
        return False
    slope = sma200.iloc[-1] - sma200.iloc[-20]
    rising_sma200 = slope > 0

    return above_sma200 and rising_sma200


def is_above_50ma(ohlcv_df: pd.DataFrame) -> bool:
    """종가 > 50일 SMA 확인 (보조 지표)."""
    if ohlcv_df is None or len(ohlcv_df) < 50:
        return False

    close = ohlcv_df['종가'] if '종가' in ohlcv_df.columns else ohlcv_df.iloc[:, 3]
    sma50 = close.rolling(50).mean()
    if pd.isna(sma50.iloc[-1]):
        return False
    return close.iloc[-1] > sma50.iloc[-1]


class UptrendCalculator:
    """업종별 업트렌드 비율 계산기."""

    def __init__(self, client=None, sector_stocks: dict = None):
        """
        Args:
            client: KRClient 인스턴스 (실제 실행용)
            sector_stocks: 업종별 종목 코드 dict (테스트용 오버라이드)
        """
        self.client = client
        self.sector_stocks = sector_stocks or KR_SECTOR_STOCKS

    def calculate_all_sectors(self, lookback_days: int = 250) -> dict:
        """전체 업종 업트렌드 비율 계산.

        Returns:
            {
                '반도체': {'ratio': 72.5, 'total': 4, 'uptrend': 3, 'group': 'Cyclical'},
                ...
            }
        """
        results = {}

        for sector, tickers in self.sector_stocks.items():
            try:
                uptrend_count = 0
                total = len(tickers)

                for ticker in tickers:
                    try:
                        if self.client:
                            ohlcv = self.client.get_ohlcv(ticker, lookback_days=lookback_days)
                        else:
                            continue

                        if is_uptrend(ohlcv):
                            uptrend_count += 1
                    except Exception as e:
                        logger.warning(f"{sector}/{ticker} OHLCV 실패: {e}")
                        total -= 1

                ratio = (uptrend_count / total * 100) if total > 0 else 0.0
                group = SECTOR_TO_GROUP.get(sector, 'Other')

                results[sector] = {
                    'ratio': round(ratio, 1),
                    'total': total,
                    'uptrend': uptrend_count,
                    'group': group,
                }
                logger.info(f"{sector} ({group}): {uptrend_count}/{total} = {ratio:.1f}%")

            except Exception as e:
                logger.error(f"{sector} 계산 실패: {e}")

        return results

    @staticmethod
    def calculate_overall_ratio(sector_data: dict) -> float:
        """전체 시장 업트렌드 비율 (단순 가중 평균)."""
        total_stocks = sum(s['total'] for s in sector_data.values())
        total_uptrend = sum(s['uptrend'] for s in sector_data.values())

        if total_stocks == 0:
            return 0.0
        return round(total_uptrend / total_stocks * 100, 1)

    @staticmethod
    def calculate_group_averages(sector_data: dict) -> dict:
        """그룹별 평균 업트렌드 비율.

        Returns:
            {'Cyclical': 55.2, 'Defensive': 42.0, 'Growth': 60.5, 'Financial': 48.0}
        """
        groups = {}
        for sector, data in sector_data.items():
            group = data['group']
            if group not in groups:
                groups[group] = []
            groups[group].append(data['ratio'])

        return {g: round(np.mean(v), 1) for g, v in groups.items()}

    @staticmethod
    def calculate_sector_spread(sector_data: dict) -> float:
        """업종간 최대-최소 스프레드."""
        if not sector_data:
            return 0.0
        ratios = [s['ratio'] for s in sector_data.values()]
        return round(max(ratios) - min(ratios), 1)

    @staticmethod
    def calculate_group_std(sector_data: dict) -> dict:
        """그룹 내 표준편차.

        Returns:
            {'Cyclical': 15.3, 'Defensive': 8.2, ...}
        """
        groups = {}
        for sector, data in sector_data.items():
            group = data['group']
            if group not in groups:
                groups[group] = []
            groups[group].append(data['ratio'])

        return {g: round(np.std(v), 1) for g, v in groups.items() if len(v) > 1}
