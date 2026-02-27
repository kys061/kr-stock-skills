"""한국투자증권 Open API 프로바이더 (Tier 2 - 선택적).

python-kis 미설치 또는 환경변수 미설정 시 자동 비활성화.
Tier 1 스킬은 이 Provider 없이도 정상 동작.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class KISProvider:
    """한국투자증권 Open API 프로바이더 (Tier 2)."""

    def __init__(self):
        """python-kis import 시도. 실패하면 self._available = False."""
        self._available = False
        self._kis = None

        # 환경변수 확인
        app_key = os.getenv('KIS_APP_KEY', '')
        app_secret = os.getenv('KIS_APP_SECRET', '')

        if not (app_key and app_secret):
            logger.info("KIS credentials not set. Tier 2 features disabled.")
            return

        try:
            import mojito
            self._kis = mojito
            self._available = True
            logger.info("KIS provider initialized (Tier 2 available)")
        except ImportError:
            try:
                import pykis
                self._kis = pykis
                self._available = True
                logger.info("KIS provider initialized via pykis (Tier 2 available)")
            except ImportError:
                logger.info("KIS SDK not installed. Install 'mojito' or 'pykis'. Tier 2 disabled.")

    @property
    def available(self) -> bool:
        return self._available

    def get_realtime_price(self, ticker: str) -> dict:
        """실시간 현재가 (Tier 2 전용)."""
        if not self._available:
            return {}
        logger.info("KIS realtime price: Tier 2 feature - not yet implemented")
        return {}

    def get_minute_chart(self, ticker: str,
                         period: str = '1') -> pd.DataFrame:
        """분봉 데이터 (Tier 2 전용)."""
        if not self._available:
            return pd.DataFrame()
        logger.info("KIS minute chart: Tier 2 feature - not yet implemented")
        return pd.DataFrame()

    def get_orderbook(self, ticker: str) -> dict:
        """호가 (Tier 2 전용)."""
        if not self._available:
            return {}
        logger.info("KIS orderbook: Tier 2 feature - not yet implemented")
        return {}

    def get_balance(self) -> pd.DataFrame:
        """잔고 조회 (Tier 2 전용)."""
        if not self._available:
            return pd.DataFrame()
        logger.info("KIS balance: Tier 2 feature - not yet implemented")
        return pd.DataFrame()

    def get_available_amount(self, ticker: str) -> dict:
        """매수 가능 금액 (Tier 2 전용)."""
        if not self._available:
            return {}
        logger.info("KIS available amount: Tier 2 feature - not yet implemented")
        return {}
