# Design: 주식종목선별 스킬

> **Feature**: kr-stock-selector
> **Phase**: Design
> **Created**: 2026-03-11
> **Plan**: `docs/01-plan/features/kr-stock-selector.plan.md`

---

## 1. 아키텍처 개요

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                     kr_stock_selector.py (오케스트레이터)          │
│                                                                  │
│  Step 1: 유니버스 구축                                            │
│  ┌──────────────────────┐                                        │
│  │  universe_builder.py │──→ KRX Open API (get_stock_daily)      │
│  │  build_universe()    │    → 전 종목 시가총액 조회              │
│  │                      │    → 시총 ≥ 1,000억원 필터              │
│  └──────────┬───────────┘    → ~300-400개 종목 + yf 티커 변환     │
│             │                                                     │
│             ▼                                                     │
│  Step 2: OHLCV 배치 다운로드                                      │
│  ┌──────────────────────┐                                        │
│  │  universe_builder.py │──→ yfinance batch download              │
│  │  fetch_ohlcv_batch() │    → period="2y" (300일+ 확보)          │
│  └──────────┬───────────┘    → group_by="ticker"                  │
│             │                                                     │
│             ▼                                                     │
│  Step 3: 5조건 판정                                               │
│  ┌──────────────────────┐                                        │
│  │  trend_analyzer.py   │──→ 각 종목 OHLCV DataFrame              │
│  │  analyze_stock()     │    → SMA 계산 + 5조건 Pass/Fail         │
│  └──────────┬───────────┘    → 결과 dict 반환                     │
│             │                                                     │
│             ▼                                                     │
│  Step 4: 리포트 생성                                              │
│  ┌──────────────────────┐                                        │
│  │  report_generator.py │──→ 마크다운 테이블 생성                  │
│  │  generate_report()   │    → reports/ 저장                      │
│  └──────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 디렉토리 구조

```
skills/kr-stock-selector/
├── SKILL.md                          # 스킬 명세서 (Claude 실행 절차)
├── scripts/
│   ├── kr_stock_selector.py          # 오케스트레이터 (~80 LOC)
│   ├── universe_builder.py           # 유니버스 구축 + OHLCV 수집 (~120 LOC)
│   ├── trend_analyzer.py             # 5조건 판정 엔진 (~200 LOC)
│   ├── report_generator.py           # 마크다운 리포트 생성 (~120 LOC)
│   └── tests/
│       ├── test_universe_builder.py  # 6+ tests
│       ├── test_trend_analyzer.py    # 12+ tests
│       └── test_report_generator.py  # 5+ tests
└── references/
    └── selector_config.json          # 조건별 임계값 설정
```

---

## 3. 데이터 구조

### 3.1 selector_config.json

```json
{
  "conditions": {
    "ma_trend": {
      "window": 200,
      "days": 20,
      "flat_threshold": 0.001
    },
    "ma_alignment": {
      "sma_periods": [50, 150, 200]
    },
    "week52_low": {
      "threshold": 0.30,
      "lookback_days": 250
    },
    "week52_high": {
      "threshold": -0.25,
      "lookback_days": 250
    },
    "market_cap": {
      "min_krw": 100000000000
    }
  },
  "universe": {
    "markets": ["KOSPI", "KOSDAQ"],
    "min_trading_days": 220
  },
  "report": {
    "watch_list_min_pass": 4
  }
}
```

### 3.2 종목 유니버스 레코드

```python
UniverseStock = {
    "ticker": str,        # "005930"
    "name": str,          # "삼성전자"
    "market": str,        # "KOSPI" | "KOSDAQ"
    "market_cap": int,    # 시가총액 (원)
    "yf_ticker": str,     # "005930.KS"
    "close": int,         # 현재 종가
}
```

### 3.3 분석 결과 레코드

```python
AnalysisResult = {
    "ticker": str,
    "name": str,
    "market": str,
    "market_cap": int,
    "close": int,
    "conditions": {
        "ma_trend": bool,         # 조건 1: 200MA 추세
        "ma_alignment": bool,     # 조건 2: 4중 정배열
        "week52_low": bool,       # 조건 3: 52주 저가대비 +30%
        "week52_high": bool,      # 조건 4: 52주 고가대비 -25%
        "market_cap": bool,       # 조건 5: 시총 ≥ 1,000억 (항상 True)
    },
    "details": {
        "ma_trend_days": int,     # 연속 상승+보합 일수
        "sma50": float,
        "sma150": float,
        "sma200": float,
        "week52_low_pct": float,  # 52주 저가 대비 상승률
        "week52_high_pct": float, # 52주 고가 대비 하락률
        "week52_low": float,      # 52주 최저가
        "week52_high": float,     # 52주 최고가
    },
    "pass_count": int,            # 통과 조건 수 (0-5)
    "all_pass": bool,             # 5조건 모두 통과
}
```

---

## 4. 모듈 상세 설계

### 4.1 universe_builder.py

```python
"""유니버스 구축 모듈.

KRX Open API로 시가총액 ≥ 1,000억원 종목을 필터링하고,
yfinance 배치 다운로드로 OHLCV 데이터를 수집한다.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── 설정 로드 ──

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'references', 'selector_config.json'
)

def load_config() -> dict:
    """selector_config.json 로드."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── 유니버스 구축 ──

def build_universe(
    provider=None,
    date: str = None,
    market: str = None,
    min_market_cap: int = None,
) -> list[dict]:
    """시가총액 기준 유니버스 구축.

    Args:
        provider: KRXOpenAPIProvider 인스턴스
        date: 기준일 'YYYY-MM-DD' (기본: 오늘)
        market: 'KOSPI', 'KOSDAQ', None(전체)
        min_market_cap: 최소 시가총액 (원). 기본값 config에서 로드.

    Returns:
        list[UniverseStock] — 시총 필터 통과 종목 리스트
    """

def to_yf_ticker(ticker: str, market: str) -> str:
    """종목코드 → yfinance 티커 변환.

    '005930' + 'KOSPI' → '005930.KS'
    '035720' + 'KOSDAQ' → '035720.KQ'
    """

def fetch_ohlcv_batch(
    universe: list[dict],
    period: str = "2y",
) -> dict[str, pd.DataFrame]:
    """yfinance 배치 다운로드.

    Args:
        universe: build_universe() 결과
        period: yfinance period 문자열

    Returns:
        {ticker: DataFrame(Date, Open, High, Low, Close, Volume)}
        다운로드 실패 종목은 빈 DataFrame.
    """
```

**핵심 로직**:

1. `build_universe()`:
   - KRXOpenAPIProvider.get_stock_daily(date) 호출
   - MKTCAP 컬럼 ≥ min_market_cap 필터
   - MKT_NM으로 KOSPI/KOSDAQ 분류
   - market 파라미터로 필터 (None이면 전체)
   - `to_yf_ticker()` 로 yf_ticker 필드 추가

2. `fetch_ohlcv_batch()`:
   - `yf.download(tickers, period=period, group_by="ticker", threads=True)`
   - 반환된 MultiIndex DataFrame을 종목별 dict로 분리
   - 종목별 데이터가 min_trading_days 미만이면 빈 DataFrame으로 처리

### 4.2 trend_analyzer.py

```python
"""5조건 판정 엔진.

5가지 트렌드 조건에 대한 Pass/Fail 판정을 수행한다.
각 함수는 독립적으로 테스트 가능하도록 설계.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── 조건 1: 200MA 추세 (상승+보합 20일) ──

def check_ma_trend(
    df: pd.DataFrame,
    window: int = 200,
    days: int = 20,
    flat_threshold: float = 0.001,
) -> tuple[bool, int]:
    """200일 SMA 상승+보합 추세 확인.

    Args:
        df: OHLCV DataFrame (Close 컬럼 필수)
        window: SMA 기간 (기본 200)
        days: 연속 확인 기간 (기본 20)
        flat_threshold: 보합 판정 임계값 (기본 0.1%)

    Returns:
        (pass: bool, consecutive_days: int)
        - pass: 20일 연속 상승+보합이면 True
        - consecutive_days: 실제 연속 일수
    """


# ── 조건 2: 4중 정배열 ──

def check_ma_alignment(
    df: pd.DataFrame,
) -> tuple[bool, dict]:
    """종가 > 50일 SMA > 150일 SMA > 200일 SMA 확인.

    Returns:
        (pass: bool, sma_values: {'close': float, 'sma50': float,
                                   'sma150': float, 'sma200': float})
    """


# ── 조건 3: 52주 최저가대비 +30% ──

def check_52w_low_distance(
    df: pd.DataFrame,
    threshold: float = 0.30,
    lookback_days: int = 250,
) -> tuple[bool, float, float]:
    """52주 최저가 대비 현재가 상승률 확인.

    Returns:
        (pass: bool, pct_change: float, week52_low: float)
        - pct_change: (현재가 - 52주저가) / 52주저가
    """


# ── 조건 4: 52주 최고가대비 -25% 이내 ──

def check_52w_high_distance(
    df: pd.DataFrame,
    threshold: float = -0.25,
    lookback_days: int = 250,
) -> tuple[bool, float, float]:
    """52주 최고가 대비 현재가 하락률 확인.

    Returns:
        (pass: bool, pct_change: float, week52_high: float)
        - pct_change: (현재가 - 52주고가) / 52주고가
    """


# ── 통합 분석 ──

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
        AnalysisResult dict (섹션 3.3 참조)
    """
```

**알고리즘 상세**:

#### 조건 1: check_ma_trend

```
1. Close 컬럼으로 200일 SMA 시계열 계산: df['Close'].rolling(200).mean()
2. 최근 (days+1)일의 SMA 값 추출
3. 연속 일수 역순 카운트:
   for i in range(len(sma_values)-1, 0, -1):
     today = sma_values[i]
     yesterday = sma_values[i-1]
     change = (today - yesterday) / yesterday
     if change >= 0 or abs(change) < flat_threshold:
       consecutive += 1
     else:
       break
4. consecutive >= days → Pass
```

#### 조건 2: check_ma_alignment

```
1. 현재 종가 (Close[-1])
2. SMA 계산: sma50, sma150, sma200
3. 판정: close > sma50 > sma150 > sma200
```

#### 조건 3: check_52w_low_distance

```
1. 최근 lookback_days일의 Low 컬럼 최솟값
2. pct = (close - low_52w) / low_52w
3. pct >= threshold → Pass
```

#### 조건 4: check_52w_high_distance

```
1. 최근 lookback_days일의 High 컬럼 최댓값
2. pct = (close - high_52w) / high_52w
3. pct >= threshold → Pass (threshold = -0.25)
```

### 4.3 report_generator.py

```python
"""마크다운 리포트 생성 모듈.

통과 종목, 조건별 통과율, Watch List를 마크다운 테이블로 생성.
report_screener.md 템플릿 기반, report_rules.md 규칙 준수.
"""

import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def generate_report(
    results: list[dict],
    universe_size: int,
    date: str = None,
    market_filter: str = "ALL",
) -> str:
    """마크다운 리포트 문자열 생성.

    Args:
        results: analyze_stock() 결과 리스트
        universe_size: 유니버스 전체 종목 수
        date: 기준일
        market_filter: "KOSPI", "KOSDAQ", "ALL"

    Returns:
        마크다운 문자열
    """


def build_header(date: str, market_filter: str) -> str:
    """리포트 헤더 생성."""


def build_summary(
    results: list[dict],
    universe_size: int,
) -> str:
    """요약 섹션 생성.

    - 분석 대상 N개, 통과 종목 M개 (X%)
    """


def build_pass_table(passed: list[dict]) -> str:
    """통과 종목 테이블 생성.

    컬럼: #, 종목코드, 종목명, 시장, 시총(억), 현재가, 52주대비저, 52주대비고
    정렬: 시가총액 내림차순
    """


def build_condition_stats(results: list[dict]) -> str:
    """조건별 통과율 테이블 생성.

    각 조건의 통과 수와 비율.
    """


def build_watch_list(
    results: list[dict],
    min_pass: int = 4,
) -> str:
    """Watch List 생성 (4/5 통과 종목).

    미충족 조건과 현재/필요 수치를 표시.
    """


def build_footer(date: str) -> str:
    """리포트 풋터."""


def save_report(
    content: str,
    date: str = None,
    output_dir: str = None,
) -> str:
    """리포트 파일 저장.

    경로: reports/kr-stock-selector_market_주식종목선별_{YYYYMMDD}.md
    """
```

**리포트 섹션 구조**:

```markdown
# 주식종목선별 리포트
> 생성일: YYYY-MM-DD HH:MM | 대상: {market} | 시총 ≥ 1,000억원
> 데이터 소스: KRX Open API (Tier 0) + yfinance (Tier 1) | 분석 유형: SCREENING

## 요약
- 분석 대상: {N}개 (시총 ≥ 1,000억원)
- **통과 종목: {M}개** ({X}%)

## 통과 종목
| # | 종목코드 | 종목명 | 시장 | 시총(억) | 현재가 | 52주대비저 | 52주대비고 |
(시가총액 내림차순)

## 조건별 통과율
| 조건 | 설명 | 통과 | 비율 |
(5행)

## Watch List (4/5 통과)
| 종목코드 | 종목명 | 미충족 조건 | 현재 수치 | 필요 수치 |

---
*Generated by kr-stock-selector | YYYY-MM-DD*
```

### 4.4 kr_stock_selector.py (오케스트레이터)

```python
"""kr-stock-selector: 주식종목선별 오케스트레이터.

5가지 트렌드 조건으로 KOSPI/KOSDAQ 종목을 자동 선별한다.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def run(
    market: str = None,
    date: str = None,
    output_dir: str = None,
) -> dict:
    """주식종목선별 실행.

    Args:
        market: 'KOSPI', 'KOSDAQ', None(전체)
        date: 기준일 (기본: 오늘)
        output_dir: 리포트 저장 디렉토리 (기본: reports/)

    Returns:
        {
            'success': bool,
            'report_path': str,
            'universe_size': int,
            'passed_count': int,
            'watch_count': int,
            'pass_rate': float,
            'passed_stocks': list[dict],
            'errors': list[str],
        }
    """
```

**실행 흐름**:

```
1. load_config()
2. KRX API 키 확인 → 없으면 에러 반환
3. build_universe(provider, date, market) → universe[]
4. fetch_ohlcv_batch(universe) → ohlcv_dict{}
5. for stock in universe:
     try:
       df = ohlcv_dict[stock['ticker']]
       result = analyze_stock(df, stock, config)
       results.append(result)
     except Exception:
       errors.append(f"{stock['ticker']}: {error}")
       continue  # fail-safe
6. generate_report(results, len(universe))
7. save_report(report, date, output_dir)
8. 결과 dict 반환
```

---

## 5. 에러 처리 전략

| 에러 유형 | 처리 | 비고 |
|-----------|------|------|
| KRX API 키 없음 | 조기 종료 + 에러 반환 | 유니버스 구축 불가 |
| KRX API 호출 실패 | 에러 반환 | 핵심 데이터 없이 진행 불가 |
| yfinance 배치 실패 | 개별 종목 빈 DataFrame | fail-safe |
| 개별 종목 OHLCV 부족 | skip + errors에 기록 | min_trading_days 미충족 |
| 개별 종목 SMA 계산 불가 | skip + errors에 기록 | NaN 방어 |
| 리포트 저장 실패 | 경고 + 리포트 문자열 반환 | 디렉토리 자동 생성 시도 |

---

## 6. 구현 순서

| Step | 파일 | 설명 | 예상 LOC | 의존성 |
|:----:|------|------|:-------:|--------|
| 1 | `references/selector_config.json` | 조건 임계값 설정 | 30 | - |
| 2 | `scripts/universe_builder.py` | 유니버스 구축 + OHLCV | 120 | KRX API, yfinance |
| 3 | `scripts/trend_analyzer.py` | 5조건 판정 엔진 | 200 | pandas, numpy |
| 4 | `scripts/report_generator.py` | 리포트 생성 | 120 | - |
| 5 | `scripts/kr_stock_selector.py` | 오케스트레이터 | 80 | Step 2-4 |
| 6 | `scripts/tests/test_universe_builder.py` | 유니버스 테스트 | 80 | Step 2 |
| 7 | `scripts/tests/test_trend_analyzer.py` | 5조건 테스트 | 200 | Step 3 |
| 8 | `scripts/tests/test_report_generator.py` | 리포트 테스트 | 80 | Step 4 |
| 9 | `SKILL.md` | 스킬 명세서 | 80 | - |
| | **합계** | | **~990** | |

---

## 7. 테스트 설계

### 7.1 test_universe_builder.py (6+ tests)

| # | 테스트 | 검증 내용 |
|---|--------|----------|
| 1 | test_load_config | selector_config.json 로드 + 필수 키 존재 |
| 2 | test_to_yf_ticker_kospi | KOSPI → .KS 변환 |
| 3 | test_to_yf_ticker_kosdaq | KOSDAQ → .KQ 변환 |
| 4 | test_build_universe_filters | 시총 필터 정상 작동 |
| 5 | test_build_universe_market_filter | KOSPI/KOSDAQ 시장 필터 |
| 6 | test_fetch_ohlcv_batch_empty | 빈 유니버스 → 빈 dict |

### 7.2 test_trend_analyzer.py (12+ tests)

| # | 테스트 | 검증 내용 |
|---|--------|----------|
| 1 | test_check_ma_trend_pass | 20일 연속 상승 → True |
| 2 | test_check_ma_trend_fail_decline | 중간 하락 → False |
| 3 | test_check_ma_trend_flat_pass | 보합(0.1% 이내) → True |
| 4 | test_check_ma_trend_days_count | 연속 일수 정확도 |
| 5 | test_check_ma_alignment_pass | 정배열 → True |
| 6 | test_check_ma_alignment_fail | 역전 → False |
| 7 | test_check_52w_low_pass | +30% 이상 → True |
| 8 | test_check_52w_low_fail | +29% → False |
| 9 | test_check_52w_high_pass | -10% → True |
| 10 | test_check_52w_high_fail | -30% → False |
| 11 | test_analyze_stock_all_pass | 5조건 모두 통과 |
| 12 | test_analyze_stock_partial | 3/5 통과 → all_pass=False |

### 7.3 test_report_generator.py (5+ tests)

| # | 테스트 | 검증 내용 |
|---|--------|----------|
| 1 | test_build_header | 헤더 포맷 + 필수 필드 |
| 2 | test_build_summary | 요약 정확도 (종목 수, 비율) |
| 3 | test_build_pass_table | 통과 종목 테이블 정렬 (시총 내림차순) |
| 4 | test_build_watch_list | 4/5 통과 종목 필터링 |
| 5 | test_save_report | 파일 저장 + 파일명 규칙 |

---

## 8. SKILL.md 실행 절차

Claude가 `/kr-stock-selector` 호출 시 수행할 절차:

```
Step 1: KRX API 키 확인
  → os.environ.get('KRX_API_KEY')
  → 없으면 WebSearch 폴백 안내

Step 2: Python 스크립트 실행
  → cd ~/stock/skills/kr-stock-selector/scripts
  → python kr_stock_selector.py

Step 3: 결과 확인
  → 성공: 리포트 경로 출력 + 요약 표시
  → 실패: 에러 메시지 출력

Step 4: 이메일 발송
  → cd ~/stock && python3 skills/_kr_common/utils/email_sender.py "{report_path}" "kr-stock-selector"
```

---

## 9. 성공 기준

| 기준 | 목표 |
|------|------|
| 5조건 정확도 | 수동 검증 대비 100% 일치 |
| 실행 시간 | ≤ 3분 (전 종목) |
| 테스트 | 23+ tests, 100% pass |
| Match Rate | ≥ 97% (PDCA Check) |
| fail-safe | 개별 종목 실패 → skip, 전체 중단 없음 |

---

## 10. 관련 문서

- Plan: `docs/01-plan/features/kr-stock-selector.plan.md`
- 원본 이미지: `screen_shot/주식종목선별.png`
- 유사 스킬: `skills/kr-vcp-screener/` (Stage 2 + VCP)
- 공통 모듈: `skills/_kr_common/providers/krx_openapi_provider.py`
- 리포트 규칙: `skills/_kr_common/templates/report_rules.md`
- 스크리닝 템플릿: `skills/_kr_common/templates/report_screener.md`
