"""DART 전자공시 데이터 프로바이더.

dart_api_key가 없으면 초기화 시 warning 로그만 남기고
모든 메서드는 None 또는 빈 DataFrame을 반환.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DARTProvider:
    """DART 전자공시 데이터 프로바이더."""

    def __init__(self, api_key: str = None):
        """api_key가 None이면 DART_API_KEY 환경변수에서 읽음."""
        self._api_key = api_key or os.getenv('DART_API_KEY', '')
        self._dart = None

        if self._api_key:
            try:
                import OpenDartReader
                self._dart = OpenDartReader(self._api_key)
                logger.info("DART provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize DART: {e}")
                self._dart = None
        else:
            logger.info("DART API key not set. DART features disabled.")

    @property
    def available(self) -> bool:
        """DART 기능 사용 가능 여부."""
        return self._dart is not None

    def _check_available(self):
        """사용 가능 여부 확인. 불가능하면 None 반환용."""
        if not self.available:
            return False
        return True

    # ─────────────────────────────────────────
    # 재무제표 (Financial Statements)
    # ─────────────────────────────────────────

    def get_financial_statements(self, corp: str, year: int,
                                  report_type: str = '11011') -> dict:
        """IFRS 재무제표.

        Args:
            corp: 종목코드 또는 기업명
            year: 사업연도
            report_type: '11011'=사업보고서, '11012'=반기, '11013'=1분기, '11014'=3분기

        Returns:
            {
                'income_statement': DataFrame,
                'balance_sheet': DataFrame,
                'cash_flow': DataFrame,
            } or None
        """
        if not self._check_available():
            return None

        try:
            result = {}
            # 손익계산서
            result['income_statement'] = self._dart.finstate(
                corp, year, reprt_code=report_type, fs_div='CFS'
            )
            # 재무상태표
            result['balance_sheet'] = self._dart.finstate(
                corp, year, reprt_code=report_type, fs_div='CFS'
            )
            # 현금흐름표
            result['cash_flow'] = self._dart.finstate(
                corp, year, reprt_code=report_type, fs_div='CFS'
            )
            return result
        except Exception as e:
            logger.warning(f"DART financial statements failed for {corp}: {e}")
            return None

    def get_financial_statements_all(self, corp: str,
                                      year: int) -> pd.DataFrame:
        """전체 재무제표 DataFrame."""
        if not self._check_available():
            return pd.DataFrame()

        try:
            return self._dart.finstate_all(corp, year)
        except Exception as e:
            logger.warning(f"DART finstate_all failed for {corp}: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────
    # 공시 (Disclosure)
    # ─────────────────────────────────────────

    def get_disclosure_list(self, corp: str = None, start: str = None,
                            end: str = None, kind: str = None) -> pd.DataFrame:
        """공시 목록.

        Args:
            corp: 종목코드/기업명 (None이면 전체)
            kind: 'A'=정기보고서, 'B'=주요사항, 'C'=발행공시,
                  'D'=지분공시, 'E'=기타
        """
        if not self._check_available():
            return pd.DataFrame()

        try:
            kwargs = {}
            if start:
                kwargs['start'] = start.replace('-', '')
            if end:
                kwargs['end'] = end.replace('-', '')
            if kind:
                kwargs['kind'] = kind

            if corp:
                return self._dart.list(corp, **kwargs)
            return self._dart.list(**kwargs)
        except Exception as e:
            logger.warning(f"DART disclosure list failed: {e}")
            return pd.DataFrame()

    def get_company_info(self, corp: str) -> dict:
        """기업 개황."""
        if not self._check_available():
            return {}

        try:
            info = self._dart.company(corp)
            if isinstance(info, pd.DataFrame):
                return info.to_dict('records')[0] if not info.empty else {}
            return info if isinstance(info, dict) else {}
        except Exception as e:
            logger.warning(f"DART company info failed for {corp}: {e}")
            return {}

    # ─────────────────────────────────────────
    # 지분 (Shareholding)
    # ─────────────────────────────────────────

    def get_major_shareholders(self, corp: str) -> pd.DataFrame:
        """5% 대량보유자 현황."""
        if not self._check_available():
            return pd.DataFrame()

        try:
            return self._dart.major_shareholders(corp)
        except Exception as e:
            logger.warning(f"DART major shareholders failed for {corp}: {e}")
            return pd.DataFrame()

    def get_executive_shareholding(self, corp: str) -> pd.DataFrame:
        """임원 지분 현황."""
        if not self._check_available():
            return pd.DataFrame()

        try:
            return self._dart.report(corp, '임원현황')
        except Exception as e:
            logger.warning(f"DART executive shareholding failed for {corp}: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────
    # 배당 (Dividend)
    # ─────────────────────────────────────────

    def get_dividend_info(self, corp: str, year: int = None) -> dict:
        """배당 정보."""
        if not self._check_available():
            return {}

        try:
            if year:
                df = self._dart.report(corp, '배당', year)
            else:
                df = self._dart.report(corp, '배당')

            if isinstance(df, pd.DataFrame) and not df.empty:
                return df.to_dict('records')
            return {}
        except Exception as e:
            logger.warning(f"DART dividend info failed for {corp}: {e}")
            return {}

    # ─────────────────────────────────────────
    # 기업 검색
    # ─────────────────────────────────────────

    def search_company(self, name: str) -> list:
        """기업명으로 검색.

        Returns:
            [{'corp_code': '...', 'corp_name': '...', 'stock_code': '...'}, ...]
        """
        if not self._check_available():
            return []

        try:
            result = self._dart.company_by_name(name)
            if isinstance(result, pd.DataFrame) and not result.empty:
                return result.to_dict('records')
            return []
        except Exception as e:
            logger.warning(f"DART company search failed for {name}: {e}")
            return []

    def resolve_corp_code(self, ticker_or_name: str) -> str:
        """종목코드/기업명 → DART corp_code 변환."""
        if not self._check_available():
            return ''

        try:
            result = self._dart.find_corp_code(ticker_or_name)
            return result if result else ''
        except Exception as e:
            logger.warning(f"DART resolve corp code failed for {ticker_or_name}: {e}")
            return ''
