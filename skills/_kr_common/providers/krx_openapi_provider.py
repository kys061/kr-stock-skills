"""KRX Open API 데이터 프로바이더.

KRX 정보데이터시스템 공식 REST API (https://openapi.krx.co.kr).
인증키 기반, 일 10,000회 호출 제한.

Base URL: https://data-dbg.krx.co.kr/svc/apis
인증: AUTH_KEY 헤더

승인 완료 엔드포인트 (2026-03-06 확인):
  - /sto/stk_bydd_trd      : 주식 일별 시세 (OHLCV, 시가총액)
  - /sto/stk_isu_base_info  : 종목 상장 기본정보 (종목코드, 상장일, 액면가)
  - /idx/kospi_dd_trd       : KOSPI 지수 일별 시세
  - /idx/kosdaq_dd_trd      : KOSDAQ 지수 일별 시세

미제공/미승인:
  - 투자자별 매매동향: 엔드포인트 미존재 (404)
  - PER/PBR: stk_isu_base_info에 미포함 → yfinance/PyKRX 폴백 필요
  - 채권/선물: 엔드포인트 존재하나 미승인 (401)

컬럼명 주의:
  - stk_bydd_trd: ISU_CD (6자리, e.g. '078600')
  - stk_isu_base_info: ISU_SRT_CD (6자리), ISU_CD (ISIN, e.g. 'KR7078600005')
"""

import logging
import time
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# KRX Open API 엔드포인트
BASE_URL = "https://data-dbg.krx.co.kr/svc/apis"

ENDPOINTS = {
    # 주식 (승인 완료)
    "stk_bydd_trd": f"{BASE_URL}/sto/stk_bydd_trd",            # KOSPI 주식 일별시세
    "ksq_bydd_trd": f"{BASE_URL}/sto/ksq_bydd_trd",            # KOSDAQ 주식 일별시세
    "stk_isu_base_info": f"{BASE_URL}/sto/stk_isu_base_info",  # 종목 상장정보
    # 지수 (승인 완료)
    "kospi_dd_trd": f"{BASE_URL}/idx/kospi_dd_trd",             # KOSPI 지수 일별시세
    "kosdaq_dd_trd": f"{BASE_URL}/idx/kosdaq_dd_trd",           # KOSDAQ 지수 일별시세
}


class KRXOpenAPIError(Exception):
    """KRX Open API 오류."""


class KRXOpenAPIProvider:
    """KRX Open API 프로바이더."""

    def __init__(self, api_key: str, request_delay: float = 0.3):
        self._api_key = api_key
        self._delay = request_delay
        self._last_request = 0.0
        self._session = requests.Session()
        self._session.headers.update({"AUTH_KEY": self._api_key})

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def _throttle(self):
        """연속 호출 방지."""
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    @staticmethod
    def _to_krx(date_str: str) -> str:
        """'YYYY-MM-DD' → 'YYYYMMDD'."""
        if date_str and '-' in date_str:
            return date_str.replace('-', '')
        return date_str

    def _request(self, endpoint_key: str, params: dict) -> list:
        """API 호출 후 OutBlock_1 반환."""
        url = ENDPOINTS.get(endpoint_key)
        if not url:
            raise KRXOpenAPIError(f"Unknown endpoint: {endpoint_key}")

        self._throttle()

        try:
            resp = self._session.get(url, params=params, timeout=15)
        except requests.RequestException as e:
            raise KRXOpenAPIError(f"Request failed: {e}") from e

        if resp.status_code == 401:
            raise KRXOpenAPIError(
                "401 Unauthorized - API 인증키 미승인 또는 해당 서비스 이용 미신청. "
                "openapi.krx.co.kr에서 개별 서비스 이용신청 필요."
            )
        if resp.status_code != 200:
            raise KRXOpenAPIError(
                f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        if "respCode" in data and data["respCode"] != "200":
            raise KRXOpenAPIError(
                f"API Error: {data.get('respMsg', 'Unknown')}"
            )

        return data.get("OutBlock_1", [])

    # ─────────────────────────────────────────
    # 주식 시세
    # ─────────────────────────────────────────

    def get_stock_daily(self, date: str, market: str = None) -> pd.DataFrame:
        """전종목 일별 시세 (특정일). KOSPI + KOSDAQ 통합.

        Args:
            date: 'YYYY-MM-DD' 형식
            market: 'KOSPI', 'KOSDAQ', None(양쪽 통합)

        Returns DataFrame with columns:
            BAS_DD, ISU_CD (6자리), ISU_NM, MKT_NM, SECT_TP_NM,
            TDD_CLSPRC, CMPPREVDD_PRC, FLUC_RT,
            TDD_OPNPRC, TDD_HGPRC, TDD_LWPRC, ACC_TRDVOL, ACC_TRDVAL,
            MKTCAP, LIST_SHRS
        """
        krx_date = self._to_krx(date)
        frames = []

        if market in (None, 'KOSPI'):
            kospi = self._request("stk_bydd_trd", {"basDd": krx_date})
            if kospi:
                frames.append(pd.DataFrame(kospi))

        if market in (None, 'KOSDAQ'):
            kosdaq = self._request("ksq_bydd_trd", {"basDd": krx_date})
            if kosdaq:
                frames.append(pd.DataFrame(kosdaq))

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        # 숫자 컬럼 변환
        numeric_cols = [
            "TDD_CLSPRC", "CMPPREVDD_PRC", "TDD_OPNPRC", "TDD_HGPRC",
            "TDD_LWPRC", "ACC_TRDVOL", "ACC_TRDVAL", "MKTCAP", "LIST_SHRS"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""), errors="coerce"
                )
        if "FLUC_RT" in df.columns:
            df["FLUC_RT"] = pd.to_numeric(
                df["FLUC_RT"].astype(str).str.replace(",", ""), errors="coerce"
            )

        return df

    def get_stock_base_info(self, date: str) -> pd.DataFrame:
        """전종목 상장 기본정보.

        NOTE: PER/PBR/EPS는 미포함. 상장정보(종목코드, 상장일, 액면가)만 반환.
              PER/PBR은 yfinance 또는 PyKRX 폴백 필요.

        Returns DataFrame with columns:
            ISU_CD (ISIN), ISU_SRT_CD (6자리), ISU_NM, ISU_ABBRV,
            LIST_DD, MKT_TP_NM, PARVAL, LIST_SHRS
        """
        records = self._request("stk_isu_base_info", {"basDd": self._to_krx(date)})
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        numeric_cols = ["PARVAL", "LIST_SHRS"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""), errors="coerce"
                )
        return df

    # NOTE: 투자자별 매매동향 엔드포인트 미존재 (404, 2026-03-06 확인)
    # PER/PBR 데이터도 KRX Open API에 미포함
    # → yfinance 또는 PyKRX 폴백 사용

    # ─────────────────────────────────────────
    # 지수
    # ─────────────────────────────────────────

    def get_kospi_daily(self, date: str) -> pd.DataFrame:
        """KOSPI 일별 시세."""
        records = self._request("kospi_dd_trd", {"basDd": self._to_krx(date)})
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)

    def get_kosdaq_daily(self, date: str) -> pd.DataFrame:
        """KOSDAQ 일별 시세."""
        records = self._request("kosdaq_dd_trd", {"basDd": self._to_krx(date)})
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)

    # ─────────────────────────────────────────
    # 통합 조회 헬퍼
    # ─────────────────────────────────────────

    def get_stock_by_ticker(self, date: str, ticker: str) -> Optional[dict]:
        """특정 종목의 일별 시세 조회.

        전종목 데이터에서 ticker(6자리)로 필터링.
        stk_bydd_trd의 컬럼: ISU_CD (6자리), ISU_NM
        """
        df = self.get_stock_daily(date)
        if df.empty:
            return None

        row = df[df["ISU_CD"] == ticker]
        if row.empty:
            return None

        r = row.iloc[0]
        return {
            "ticker": ticker,
            "name": r.get("ISU_NM", ""),
            "close": int(r.get("TDD_CLSPRC", 0)),
            "open": int(r.get("TDD_OPNPRC", 0)),
            "high": int(r.get("TDD_HGPRC", 0)),
            "low": int(r.get("TDD_LWPRC", 0)),
            "volume": int(r.get("ACC_TRDVOL", 0)),
            "change_pct": float(r.get("FLUC_RT", 0)),
            "market_cap": int(r.get("MKTCAP", 0)),
            "listed_shares": int(r.get("LIST_SHRS", 0)),
            "market": r.get("MKT_NM", ""),
            "date": date,
        }

    def get_listing_info_by_ticker(self, ticker: str, date: str) -> Optional[dict]:
        """특정 종목의 상장 기본정보 (종목코드, 상장일, 액면가).

        NOTE: PER/PBR 미포함. stk_isu_base_info의 ISU_SRT_CD(6자리)로 필터링.
        """
        df = self.get_stock_base_info(date)
        if df.empty:
            return None

        row = df[df["ISU_SRT_CD"] == ticker]
        if row.empty:
            return None

        r = row.iloc[0]
        return {
            "ticker": ticker,
            "name": r.get("ISU_ABBRV", ""),
            "isin": r.get("ISU_CD", ""),
            "list_date": r.get("LIST_DD", ""),
            "market": r.get("MKT_TP_NM", ""),
            "par_value": int(r.get("PARVAL", 0)),
            "listed_shares": int(r.get("LIST_SHRS", 0)),
        }

    def test_connection(self) -> dict:
        """API 연결 테스트. 성공 시 샘플 데이터 반환."""
        try:
            records = self._request("kospi_dd_trd", {"basDd": "20260304"})
            return {
                "status": "ok",
                "records": len(records),
                "sample": records[0] if records else None,
            }
        except KRXOpenAPIError as e:
            return {
                "status": "error",
                "message": str(e),
            }
