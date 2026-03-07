"""KR Stock Skills 환경 설정."""

import os
from dataclasses import dataclass, field
from pathlib import Path

# .env 파일 자동 로드 (프로젝트 루트)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[2] / '.env'
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 미설치 시 os.getenv() 폴백


@dataclass
class KRConfig:
    """환경 설정.

    Tier 0: KRX Open API (인증키 기반, 일 10,000회)
    Tier 1: PyKRX + FinanceDataReader + OpenDartReader (계좌 불필요)
    Tier 2: 한국투자증권 Open API (선택)
    """

    # Tier 0: KRX Open API
    krx_api_key: str = field(default_factory=lambda: os.getenv('KRX_API_KEY', ''))

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
    def krx_available(self) -> bool:
        return bool(self.krx_api_key)

    @property
    def dart_available(self) -> bool:
        return bool(self.dart_api_key)

    @property
    def kis_available(self) -> bool:
        return bool(self.kis_app_key and self.kis_app_secret)

    @property
    def tier(self) -> int:
        """현재 사용 가능한 최상위 Tier."""
        if self.krx_available:
            return 0
        return 2 if self.kis_available else 1


@dataclass
class EmailConfig:
    """이메일 발송 설정 (Gmail SMTP)."""

    enabled: bool = field(
        default_factory=lambda: os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
    )
    smtp_host: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
    )
    smtp_port: int = field(
        default_factory=lambda: int(os.getenv('EMAIL_SMTP_PORT', '587'))
    )
    smtp_user: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_USER', '')
    )
    smtp_password: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_PASSWORD', '')
    )
    from_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_FROM', '')
    )
    to_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_TO', '')
    )
    cc_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_CC', '')
    )
    subject_prefix: str = field(
        default_factory=lambda: os.getenv('EMAIL_SUBJECT_PREFIX', '[KR-Stock]')
    )

    @property
    def is_configured(self) -> bool:
        """발송에 필요한 최소 설정이 완료되었는지 확인."""
        return bool(self.enabled and self.smtp_user and self.smtp_password and self.to_addr)


# 싱글턴 기본 설정
_default_config = None


def get_config() -> KRConfig:
    """기본 설정 인스턴스 반환."""
    global _default_config
    if _default_config is None:
        _default_config = KRConfig()
    return _default_config


_email_config = None


def get_email_config() -> EmailConfig:
    """이메일 설정 인스턴스 반환."""
    global _email_config
    if _email_config is None:
        _email_config = EmailConfig()
    return _email_config
