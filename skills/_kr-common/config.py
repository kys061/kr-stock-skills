"""KR Stock Skills 환경 설정."""

import os
from dataclasses import dataclass, field


@dataclass
class KRConfig:
    """환경 설정.

    Tier 1: PyKRX + FinanceDataReader + OpenDartReader (계좌 불필요)
    Tier 2: 한국투자증권 Open API (선택)
    """

    # Tier 1
    dart_api_key: str = field(default_factory=lambda: os.getenv('DART_API_KEY', ''))
    ecos_api_key: str = field(default_factory=lambda: os.getenv('ECOS_API_KEY', ''))

    # Tier 2 (선택)
    kis_app_key: str = field(default_factory=lambda: os.getenv('KIS_APP_KEY', ''))
    kis_app_secret: str = field(default_factory=lambda: os.getenv('KIS_APP_SECRET', ''))
    kis_account_no: str = field(default_factory=lambda: os.getenv('KIS_ACCOUNT_NO', ''))
    kis_mode: str = field(default_factory=lambda: os.getenv('KIS_MODE', 'paper'))

    # 캐시
    cache_dir: str = field(
        default_factory=lambda: os.path.expanduser('~/.cache/kr-stock-skills/')
    )
    cache_enabled: bool = True

    # 크롤링 보호
    request_delay: float = 0.5  # 연속 호출 시 최소 간격 (초)
    max_retries: int = 3        # 실패 시 재시도 횟수

    @property
    def dart_available(self) -> bool:
        return bool(self.dart_api_key)

    @property
    def kis_available(self) -> bool:
        return bool(self.kis_app_key and self.kis_app_secret)

    @property
    def tier(self) -> int:
        """현재 사용 가능한 Tier."""
        return 2 if self.kis_available else 1


# 싱글턴 기본 설정
_default_config = None


def get_config() -> KRConfig:
    """기본 설정 인스턴스 반환."""
    global _default_config
    if _default_config is None:
        _default_config = KRConfig()
    return _default_config
