# Design: 한국 증시 장 초반 브리핑 스킬

> **Feature**: kr-morning-briefing
> **Phase**: Design
> **Created**: 2026-03-09
> **Plan Reference**: `docs/01-plan/features/kr-morning-briefing.plan.md`

---

## 1. 설계 개요

KST 08:00~09:00에 실행하여 **글로벌 시장 현황(27개 항목) + 당월 주요 일정 + 핫 키워드 2-3개**를
하나의 리포트로 제공하는 장 초반 브리핑 스킬.

### 설계 원칙

1. **2분 이내 완료** — yfinance 배치 다운로드(17개) + WebSearch(10개) 병렬 수집
2. **모듈 독립성** — 3개 Section 각각 독립 모듈, 개별 실패가 전체를 중단하지 않음
3. **기존 인프라 재활용** — `_kr_common/utils/`, `report_rules.md`, `email_sender.py`
4. **fail-safe** — WebSearch 실패 항목은 `N/A` 표시, 이전 캐시 폴백

---

## 2. 디렉토리 구조

```
skills/kr-morning-briefing/
├── SKILL.md
├── scripts/
│   ├── kr_morning_briefing.py      # 메인 오케스트레이터
│   ├── market_data_collector.py    # Section 1: 글로벌 시장 27개 항목
│   ├── monthly_calendar.py         # Section 2: 당월 주요 일정
│   ├── hot_keyword_analyzer.py     # Section 3: 핫 키워드 + 관련주
│   ├── report_generator.py         # 마크다운 리포트 조합
│   └── tests/
│       ├── test_market_data.py
│       ├── test_monthly_calendar.py
│       ├── test_hot_keyword.py
│       └── test_report_generator.py
└── references/
    └── monthly_events.json         # 정기 일정 (FOMC, BOK, 만기일 등)
```

---

## 3. 모듈 상세 설계

### 3.1 market_data_collector.py — Section 1

#### 3.1.1 상수 정의

```python
"""글로벌 시장 데이터 수집 모듈."""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from _kr_common.utils import date_utils

# ── yfinance 티커 매핑 (17개) ──────────────────
YFINANCE_TICKERS = {
    # 미국 지수 (3)
    'dow': {'ticker': '^DJI', 'name': '다우지수', 'category': '미국지수', 'unit': 'p'},
    'nasdaq': {'ticker': '^IXIC', 'name': '나스닥', 'category': '미국지수', 'unit': 'p'},
    'sp500': {'ticker': '^GSPC', 'name': 'S&P500', 'category': '미국지수', 'unit': 'p'},
    # 환율 (3)
    'usd_krw': {'ticker': 'KRW=X', 'name': '원/달러', 'category': '환율', 'unit': '원'},
    'usd_jpy': {'ticker': 'JPY=X', 'name': '엔/달러', 'category': '환율', 'unit': '엔'},
    'dxy': {'ticker': 'DX-Y.NYB', 'name': '달러인덱스', 'category': '환율', 'unit': ''},
    # 국채 (1)
    'us10y': {'ticker': '^TNX', 'name': '국고채 10년', 'category': '미국국채', 'unit': '%'},
    # 유가 (2)
    'wti': {'ticker': 'CL=F', 'name': 'WTI', 'category': '유가', 'unit': '$'},
    'brent': {'ticker': 'BZ=F', 'name': '브렌트유', 'category': '유가', 'unit': '$'},
    # 안전자산 (2)
    'gold': {'ticker': 'GC=F', 'name': '금', 'category': '안전자산', 'unit': '$'},
    'btc_krw': {'ticker': 'BTC-KRW', 'name': '비트코인', 'category': '안전자산', 'unit': '원'},
    # 광물 (1)
    'copper': {'ticker': 'HG=F', 'name': '구리', 'category': '광물', 'unit': '$'},
    # 농산물 (5)
    'corn': {'ticker': 'ZC=F', 'name': '옥수수', 'category': '농산물', 'unit': '¢'},
    'wheat': {'ticker': 'ZW=F', 'name': '소맥', 'category': '농산물', 'unit': '¢'},
    'soybean': {'ticker': 'ZS=F', 'name': '대두', 'category': '농산물', 'unit': '¢'},
    'coffee': {'ticker': 'KC=F', 'name': '커피', 'category': '농산물', 'unit': '¢'},
    'cotton': {'ticker': 'CT=F', 'name': '원면', 'category': '농산물', 'unit': '¢'},
}

# ── WebSearch 항목 (10개) ──────────────────────
WEBSEARCH_ITEMS = {
    'us2y': {'name': '국고채 2년', 'category': '미국국채', 'unit': '%',
             'query': '미국 국채 2년 수익률 오늘'},
    'dubai_oil': {'name': '두바이유', 'category': '유가', 'unit': '$',
                  'query': '두바이유 가격 오늘'},
    'aluminum': {'name': '알루미늄', 'category': '광물', 'unit': '$/톤',
                 'query': 'LME 알루미늄 가격'},
    'nickel': {'name': '니켈', 'category': '광물', 'unit': '$/톤',
               'query': 'LME 니켈 가격'},
    'iron_ore': {'name': '철광석', 'category': '광물', 'unit': '$/톤',
                 'query': '철광석 가격 오늘'},
    'coal': {'name': '유연탄', 'category': '광물', 'unit': '$/톤',
             'query': '호주 유연탄 가격 Newcastle'},
    'lithium': {'name': '리튬', 'category': '광물', 'unit': '$/kg',
                'query': '리튬 카보네이트 가격'},
    'rice': {'name': '쌀', 'category': '농산물', 'unit': '$/톤',
             'query': '쌀 국제 가격 CBOT'},
    'scfi': {'name': 'SCFI', 'category': '운임지수', 'unit': '',
             'query': 'SCFI 상하이 컨테이너 운임지수 최신'},
    'bdi': {'name': 'BDI', 'category': '운임지수', 'unit': '',
            'query': 'BDI 발틱운임지수 오늘'},
}

# ── 카테고리 출력 순서 ────────────────────────
CATEGORY_ORDER = [
    '미국지수', '환율', '미국국채', '유가',
    '안전자산', '광물', '농산물', '운임지수',
]
```

#### 3.1.2 함수 시그니처

```python
def collect_yfinance_data(days: int = 5) -> dict:
    """yfinance 배치 다운로드로 17개 항목 수집.

    Args:
        days: 조회 기간 (최근 N 거래일, 기본 5일 — 등락률 계산용)

    Returns:
        {
            'dow': {'name': '다우지수', 'category': '미국지수',
                    'price': 47501.55, 'change_pct': -0.95,
                    'direction': '↓', 'unit': 'p', 'error': None},
            ...
        }

    Logic:
        1. YFINANCE_TICKERS에서 티커 리스트 추출
        2. yf.download(tickers, period=f'{days}d', group_by='ticker')
        3. 각 항목별 마지막 종가, 전일 대비 등락률 계산
        4. 실패 항목은 error에 메시지 기록
    """


def collect_websearch_data() -> dict:
    """WebSearch로 10개 항목 수집.

    Returns:
        {
            'us2y': {'name': '국고채 2년', 'category': '미국국채',
                     'price': 4.25, 'change_pct': -0.02,
                     'direction': '↓', 'unit': '%', 'error': None},
            ...
        }

    Note:
        - 이 함수는 SKILL.md 실행 시 Claude가 WebSearch 도구로 수집
        - 스크립트 단독 실행 시에는 빈 dict 반환 (WebSearch 불가)
        - websearch_context 파라미터로 외부 주입 가능
    """


def collect_all(websearch_context: dict = None) -> dict:
    """27개 항목 전체 수집 — yfinance + WebSearch 결합.

    Args:
        websearch_context: WebSearch 결과 외부 주입 (SKILL.md 실행 시)
            {
                'us2y': {'price': 4.25, 'change_pct': -0.02},
                'dubai_oil': {'price': 72.5, 'change_pct': 1.2},
                ...
            }

    Returns:
        {
            'items': {key: MarketItem, ...},  # 27개 항목
            'categories': {category: [items], ...},  # 카테고리별 그룹
            'summary': {
                'total': 27,
                'success': 22,
                'failed': 5,
                'timestamp': '2026-03-09 08:15',
            },
        }
    """


def format_price(price: float, unit: str) -> str:
    """가격을 단위에 맞게 포맷팅.

    Examples:
        format_price(47501.55, 'p')  → '47,501.55p'
        format_price(1485.0, '원')   → '1,485원'
        format_price(4.25, '%')      → '4.25%'
        format_price(72.5, '$')      → '$72.50'
    """


def format_change(change_pct: float) -> str:
    """등락률 + 방향 아이콘 포맷팅.

    Examples:
        format_change(-0.95)  → '-0.95% ↓'
        format_change(1.20)   → '+1.20% ↑'
        format_change(0.0)    → '0.00% -'
    """
```

#### 3.1.3 yfinance 배치 다운로드 패턴

```python
# daily-market-check 스킬과 동일한 패턴
ticker_list = [v['ticker'] for v in YFINANCE_TICKERS.values()]
ticker_str = ' '.join(ticker_list)

data = yf.download(ticker_str, period='5d', group_by='ticker', progress=False)

for key, info in YFINANCE_TICKERS.items():
    ticker = info['ticker']
    try:
        close = data[ticker]['Close']
        last_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        change_pct = round((last_close - prev_close) / prev_close * 100, 2)
        direction = '↑' if change_pct > 0 else '↓' if change_pct < 0 else '-'
        # ... 결과 저장
    except (KeyError, IndexError) as e:
        # ... error 기록
```

---

### 3.2 monthly_calendar.py — Section 2

#### 3.2.1 상수 정의

```python
"""당월 주요 일정 수집 모듈."""

import json
import os
from datetime import datetime, date
from typing import Optional

# 정적 일정 파일 경로
EVENTS_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'references', 'monthly_events.json'
)

# 일정 카테고리 아이콘
CATEGORY_ICONS = {
    '경제정책': '',
    '시장이벤트': '',
    '산업': '',
    '정책': '',
    '기업': '',
    '문화': '',
}
```

#### 3.2.2 함수 시그니처

```python
def load_static_events(year: int, month: int) -> list:
    """정적 일정 파일에서 당월 일정 로드.

    Args:
        year: 연도 (2026)
        month: 월 (3)

    Returns:
        [
            {'date': '2026-03-12', 'event': '한국 선물옵션 동시만기일',
             'category': '시장이벤트', 'source': 'static'},
            ...
        ]

    Logic:
        1. monthly_events.json 로드
        2. 'recurring' 항목에서 해당 월에 해당하는 정기 일정 추출
           - FOMC: 3월 → 해당
           - BOK: 3월 → 해당 없음 (1,2,4,5,7,8,10,11)
        3. '{year}.{month:02d}' 키에서 해당 연월 특수 일정 추출
        4. date 기준 정렬하여 반환
    """


def get_recurring_date(year: int, month: int, rule: str) -> Optional[str]:
    """반복 일정의 실제 날짜를 계산.

    Args:
        year: 연도
        month: 월
        rule: '2nd_thursday', '3rd_friday' 등

    Returns:
        '2026-03-13' 형식 날짜 문자열, 해당 없으면 None
    """


def merge_events(static: list, dynamic: list) -> list:
    """정적 + 동적 일정을 병합하고 중복 제거.

    Args:
        static: load_static_events() 결과
        dynamic: WebSearch 또는 다른 스킬에서 가져온 일정
            [{'date': '...', 'event': '...', 'category': '...', 'source': 'websearch'}, ...]

    Returns:
        date 순 정렬된 병합 일정 리스트

    중복 제거:
        - 같은 날짜 + event 키워드 유사도 > 80% → 정적 일정 우선
    """


def format_calendar(events: list, month: int) -> str:
    """일정 리스트를 마크다운 체크리스트로 포맷팅.

    Returns:
        '**3월 주요일정 체크리스트**\n'
        '- 3/10 노란봉투법 시행\n'
        '- 3/12 한국 선물옵션 동시만기일\n'
        ...
    """
```

#### 3.2.3 monthly_events.json 구조

```json
{
  "recurring": {
    "fomc": {
      "months": [1, 3, 5, 6, 7, 9, 11, 12],
      "description": "미국 FOMC 정례회의",
      "category": "경제정책",
      "importance": "high"
    },
    "bok": {
      "months": [1, 2, 4, 5, 7, 8, 10, 11],
      "description": "한국은행 금통위",
      "category": "경제정책",
      "importance": "high"
    },
    "boj": {
      "months": [1, 3, 4, 6, 7, 9, 10, 12],
      "description": "일본 BOJ 금융정책위원회",
      "category": "경제정책",
      "importance": "medium"
    },
    "ecb": {
      "months": [1, 3, 4, 6, 7, 9, 10, 12],
      "description": "유럽 ECB 금리결정",
      "category": "경제정책",
      "importance": "medium"
    },
    "quad_witching": {
      "months": [3, 6, 9, 12],
      "day_rule": "3rd_friday",
      "description": "선물옵션 동시만기일 (Quadruple Witching)",
      "category": "시장이벤트",
      "importance": "high"
    },
    "futures_expiry": {
      "months": "all",
      "day_rule": "2nd_thursday",
      "description": "KOSPI200 선물 만기일",
      "category": "시장이벤트",
      "importance": "medium"
    }
  },
  "2026": {
    "03": [
      {"date": "2026-03-10", "event": "노란봉투법 시행", "category": "정책"},
      {"date": "2026-03-11", "event": "인터배터리 2026", "category": "산업"},
      {"date": "2026-03-16", "event": "엔비디아 GTC 2026", "category": "산업"},
      {"date": "2026-03-20", "event": "BTS 완전체 컴백", "category": "문화"}
    ]
  }
}
```

---

### 3.3 hot_keyword_analyzer.py — Section 3

#### 3.3.1 함수 시그니처

```python
"""장 초반 핫 키워드 분석 모듈."""

import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def analyze_hot_keywords(websearch_context: dict = None) -> dict:
    """핫 키워드 2-3개를 분석하고 관련주를 매핑.

    Args:
        websearch_context: WebSearch로 수집된 뉴스 데이터
            {
                'headlines': ['이란 전쟁 위기 고조...', 'AI 반도체 수요 폭증...'],
                'sources': ['한경', '매경', ...],
                'broker_reports': ['삼성증권: 원전주 주목', ...],
            }

    Returns:
        {
            'keywords': [
                {
                    'rank': 1,
                    'headline': '이란-이스라엘 긴장 고조',
                    'summary': '미국과 이스라엘의 이란 공습...',
                    'impact': '방산주 강세, 원유 급등 우려로 정유주 주목',
                    'related_stocks': ['한화에어로스페이스', 'LIG넥스원', 'S-Oil'],
                    'sentiment': 'negative',  # positive/negative/neutral
                },
                ...
            ],
            'one_liner': '미국·이란 긴장으로 방산주 강세 예상, 원유 급등시 정유·운송 부담',
            'keyword_count': 3,
        }

    Note:
        - WebSearch 결과를 SKILL.md 실행 시 Claude가 분석하여 주입
        - 스크립트 단독 실행 시에는 빈 결과 반환
    """


def extract_keywords_from_news(headlines: list, max_keywords: int = 3) -> list:
    """뉴스 헤드라인에서 핵심 키워드를 추출.

    Args:
        headlines: 뉴스 헤드라인 리스트
        max_keywords: 최대 키워드 수 (기본 3)

    Returns:
        [{'headline': str, 'category': str}, ...]

    Logic:
        1. 중복 헤드라인 제거
        2. 주요 카테고리 분류 (지정학/원자재/기술/정책/실적)
        3. 카테고리 다양성 확보 (같은 카테고리 최대 2개)
        4. 중요도 순 정렬
    """


def map_related_stocks(keyword: str, category: str) -> list:
    """키워드/카테고리에서 관련주를 매핑.

    Args:
        keyword: 핫 키워드
        category: 카테고리 (지정학/원자재/기술/정책/실적)

    Returns:
        ['한화에어로스페이스', 'LIG넥스원', ...]

    Note:
        - 기본 매핑 테이블 + WebSearch 보완
        - kr-theme-detector 연동 가능 (Phase 2)
    """


# ── 기본 테마 매핑 테이블 ────────────────────
THEME_STOCK_MAP = {
    '방산': ['한화에어로스페이스', 'LIG넥스원', '한화시스템', '현대로템'],
    'AI반도체': ['삼성전자', 'SK하이닉스', '한미반도체', '리노공업'],
    '원전': ['두산에너빌리티', '한전기술', 'HD현대일렉트릭', 'LS ELECTRIC'],
    '2차전지': ['LG에너지솔루션', '삼성SDI', '에코프로비엠', 'POSCO홀딩스'],
    '정유': ['SK이노베이션', 'S-Oil', 'GS칼텍스', 'HD현대오일뱅크'],
    '바이오': ['삼성바이오로직스', '셀트리온', 'SK바이오팜', '유한양행'],
    '건설': ['현대건설', 'DL이앤씨', 'GS건설', 'HDC현대산업개발'],
    '금융': ['KB금융', '신한지주', '하나금융지주', '우리금융지주'],
    '조선': ['HD한국조선해양', '한화오션', '삼성중공업'],
    '게임/엔터': ['하이브', 'SM', 'JYP Ent.', '크래프톤', '넷마블'],
}
```

---

### 3.4 report_generator.py — 리포트 조합

#### 3.4.1 함수 시그니처

```python
"""장 초반 브리핑 리포트 생성 모듈."""

import os
from datetime import datetime
from pathlib import Path


def generate_report(
    market_data: dict,
    calendar_events: list,
    hot_keywords: dict,
    execution_time: str = None,
) -> dict:
    """3개 Section을 조합하여 마크다운 리포트를 생성.

    Args:
        market_data: collect_all() 결과
        calendar_events: merge_events() 결과
        hot_keywords: analyze_hot_keywords() 결과
        execution_time: 실행 시각 (None이면 현재 시각)

    Returns:
        {
            'md_content': str,      # 마크다운 전체 텍스트
            'file_path': str,       # 저장 경로
            'sections': {
                'market_data': bool,     # Section 1 생성 성공
                'calendar': bool,        # Section 2 생성 성공
                'hot_keywords': bool,    # Section 3 생성 성공
            },
        }
    """


def _build_header(execution_time: str) -> str:
    """리포트 헤더 생성.

    Returns:
        '# 장 초반 브리핑\n'
        '> 생성일: 2026-03-09 08:15 | 대상: 글로벌 시장 + 국내 증시\n'
        '> 데이터 소스: yfinance (Tier 1) + WebSearch (Tier 4)\n'
    """


def _build_section1_market(market_data: dict) -> str:
    """Section 1: 글로벌 시장 현황 마크다운 생성.

    출력 포맷:
        ## Section 1: 글로벌 시장 현황

        [미국지수]
        다우지수: 47,501.55p -0.95% ↓
        나스닥: 22,387.68p -1.59% ↓
        S&P500: 6,740.02p -1.33% ↓

        [환율]
        원/달러: 1,485원 +0.41% ↑
        ...
    """


def _build_section2_calendar(events: list, month: int) -> str:
    """Section 2: 당월 주요 일정 마크다운 생성.

    출력 포맷:
        ## Section 2: 3월 주요 일정

        **3월 주요일정 체크리스트**
        - 3/10 노란봉투법 시행
        - 3/12 한국 선물옵션 동시만기일
        ...
    """


def _build_section3_keywords(hot_keywords: dict) -> str:
    """Section 3: 핫 키워드 마크다운 생성.

    출력 포맷:
        ## Section 3: 장초반 핫 키워드

        ### 핫 키워드 1: 이란-이스라엘 긴장 고조
        **핵심 요약**: ...
        **시장 영향**: ...
        **관련주**: 한화에어로스페이스, LIG넥스원, S-Oil
        ...

        ## 장초반 한줄평
        ...
    """


def _build_footer() -> str:
    """리포트 푸터 생성.

    Returns:
        '---\n*Generated by kr-morning-briefing*'
    """


def save_report(md_content: str, date_str: str = None) -> str:
    """리포트를 reports/ 디렉토리에 저장.

    파일명: reports/kr-morning-briefing_market_장초반브리핑_{YYYYMMDD}.md

    Returns:
        저장된 파일의 절대 경로
    """
```

---

### 3.5 kr_morning_briefing.py — 메인 오케스트레이터

#### 3.5.1 함수 시그니처

```python
"""kr-morning-briefing 메인 오케스트레이터.

Usage (standalone — yfinance only):
    python kr_morning_briefing.py

Usage (SKILL.md — Claude 실행):
    /kr-morning-briefing
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from market_data_collector import collect_all
from monthly_calendar import load_static_events, merge_events
from hot_keyword_analyzer import analyze_hot_keywords
from report_generator import generate_report, save_report


def run_briefing(
    websearch_market: dict = None,
    websearch_calendar: list = None,
    websearch_keywords: dict = None,
) -> dict:
    """장 초반 브리핑 전체 실행.

    Args:
        websearch_market: WebSearch 시장 데이터 (10개 항목)
        websearch_calendar: WebSearch 동적 일정
        websearch_keywords: WebSearch 핫 키워드 뉴스

    Returns:
        {
            'success': True,
            'report_path': 'reports/kr-morning-briefing_market_장초반브리핑_20260309.md',
            'execution_time_sec': 45.2,
            'sections': {
                'market_data': {'total': 27, 'success': 22, 'failed': 5},
                'calendar': {'events': 8},
                'hot_keywords': {'count': 3},
            },
        }

    Flow:
        1. market_data_collector.collect_all(websearch_market)
        2. monthly_calendar: load_static_events() + merge_events(websearch_calendar)
        3. hot_keyword_analyzer.analyze_hot_keywords(websearch_keywords)
        4. report_generator.generate_report(...)
        5. save_report()
        6. email_sender (EMAIL_ENABLED=true 시)
    """


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='장 초반 브리핑')
    parser.add_argument('--no-websearch', action='store_true',
                        help='WebSearch 없이 yfinance만 사용')
    parser.add_argument('--month', type=int, default=None,
                        help='일정 조회 월 (기본: 현재 월)')
    args = parser.parse_args()

    result = run_briefing()
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

## 4. 에러 핸들링 및 폴백 전략

### 4.1 모듈별 에러 처리

| 모듈 | 실패 시나리오 | 처리 | 리포트 표시 |
|------|-------------|------|------------|
| market_data (yfinance) | 개별 티커 실패 | 해당 항목만 skip | `N/A` |
| market_data (yfinance) | 전체 배치 실패 | 모든 항목 `N/A` | Section 1 축소 |
| market_data (WebSearch) | 개별 항목 실패 | `N/A` 표시 | `N/A` |
| monthly_calendar | JSON 파일 없음 | 빈 리스트 반환 | "일정 없음" |
| monthly_calendar | WebSearch 실패 | 정적 일정만 사용 | 정적 일정만 표시 |
| hot_keyword_analyzer | WebSearch 실패 | 빈 결과 | "핫 키워드 수집 실패" |
| report_generator | 전체 실패 | 에러 메시지 리포트 | 에러 리포트 |

### 4.2 fail-safe 원칙

```python
# 각 모듈은 예외를 내부 처리하고 항상 결과를 반환
try:
    market_data = collect_all(websearch_context)
except Exception as e:
    logger.error(f"[Section 1] 시장 데이터 수집 실패: {e}")
    market_data = {'items': {}, 'categories': {}, 'summary': {'total': 27, 'success': 0, 'failed': 27}}

# Section 1 실패해도 Section 2, 3은 정상 실행
```

---

## 5. 데이터 흐름도

```
[SKILL.md 실행 — Claude]
      │
      ├─ WebSearch "글로벌 시장 데이터"      ───┐
      ├─ WebSearch "3월 증시 주요 일정"       ──┤
      ├─ WebSearch "장 전 핫 키워드"          ──┤
      │                                        │
      ▼                                        ▼
┌─────────────────────────────────────────────────────┐
│ kr_morning_briefing.py (오케스트레이터)                │
│                                                     │
│  ┌─────────────────────┐  websearch_market           │
│  │ market_data_collector├──────────────────────────┐  │
│  │  yfinance(17) + WS(10)│                        │  │
│  └─────────────────────┘                          │  │
│                                                   │  │
│  ┌─────────────────────┐  websearch_calendar       │  │
│  │ monthly_calendar     ├──────────────────────┐  │  │
│  │  JSON + WS 병합      │                     │  │  │
│  └─────────────────────┘                      │  │  │
│                                               │  │  │
│  ┌─────────────────────┐  websearch_keywords   │  │  │
│  │ hot_keyword_analyzer ├──────────────────┐  │  │  │
│  │  뉴스 분석 + 관련주   │                 │  │  │  │
│  └─────────────────────┘                  │  │  │  │
│                                           ▼  ▼  ▼  │
│  ┌─────────────────────────────────────────────┐   │
│  │ report_generator.py                          │   │
│  │  Section 1 + 2 + 3 → 마크다운 리포트          │   │
│  └─────────────────────────────────────────────┘   │
│                          │                          │
│                          ▼                          │
│               reports/ 저장 + 이메일 발송            │
└─────────────────────────────────────────────────────┘
```

---

## 6. 테스트 설계

### 6.1 test_market_data.py (10+ tests)

| # | 테스트명 | 입력 | 기대 결과 |
|:-:|---------|------|----------|
| T-01 | `test_yfinance_tickers_count` | YFINANCE_TICKERS | len == 17 |
| T-02 | `test_websearch_items_count` | WEBSEARCH_ITEMS | len == 10 |
| T-03 | `test_category_order_complete` | CATEGORY_ORDER | 8개 카테고리 모두 포함 |
| T-04 | `test_collect_yfinance_returns_dict` | 실제 yfinance 호출 | dict, 키 존재 |
| T-05 | `test_collect_yfinance_item_structure` | 결과 항목 | name/price/change_pct/direction/unit/error 키 |
| T-06 | `test_collect_all_with_websearch_context` | mock websearch | 27개 항목 통합 |
| T-07 | `test_collect_all_without_websearch` | None | yfinance 17개만 |
| T-08 | `test_format_price_won` | 1485.0, '원' | '1,485원' |
| T-09 | `test_format_price_dollar` | 72.5, '$' | '$72.50' |
| T-10 | `test_format_change_negative` | -0.95 | '-0.95% ↓' |
| T-11 | `test_format_change_positive` | 1.20 | '+1.20% ↑' |
| T-12 | `test_all_tickers_have_category` | YFINANCE_TICKERS | 모든 항목 category in CATEGORY_ORDER |

### 6.2 test_monthly_calendar.py (8+ tests)

| # | 테스트명 | 입력 | 기대 결과 |
|:-:|---------|------|----------|
| T-13 | `test_load_static_events_march` | 2026, 3 | FOMC, 만기일 포함 |
| T-14 | `test_load_static_events_no_bok_march` | 2026, 3 | BOK 미포함 (3월 해당 없음) |
| T-15 | `test_get_recurring_date_3rd_friday` | 2026, 3, '3rd_friday' | '2026-03-20' |
| T-16 | `test_get_recurring_date_2nd_thursday` | 2026, 3, '2nd_thursday' | '2026-03-12' |
| T-17 | `test_merge_events_dedup` | static + 중복 dynamic | 중복 제거 |
| T-18 | `test_merge_events_sorted` | 비정렬 입력 | date 오름차순 |
| T-19 | `test_format_calendar_output` | events, 3 | '3/' 형식, 체크리스트 |
| T-20 | `test_empty_events` | 빈 리스트 | 에러 없이 빈 문자열 |

### 6.3 test_hot_keyword.py (5+ tests)

| # | 테스트명 | 입력 | 기대 결과 |
|:-:|---------|------|----------|
| T-21 | `test_analyze_empty_context` | None | 빈 keywords, one_liner |
| T-22 | `test_analyze_with_headlines` | mock headlines | 1-3개 키워드 |
| T-23 | `test_map_related_stocks_defense` | '방산' | 4개 종목 |
| T-24 | `test_map_related_stocks_unknown` | '알 수 없는 카테고리' | 빈 리스트 |
| T-25 | `test_theme_stock_map_completeness` | THEME_STOCK_MAP | 10개 테마 |

### 6.4 test_report_generator.py (6+ tests)

| # | 테스트명 | 입력 | 기대 결과 |
|:-:|---------|------|----------|
| T-26 | `test_build_header` | '2026-03-09 08:15' | '# 장 초반 브리핑' 포함 |
| T-27 | `test_build_section1` | mock market_data | '[미국지수]' 포함 |
| T-28 | `test_build_section2` | mock events | '주요일정 체크리스트' 포함 |
| T-29 | `test_build_section3` | mock keywords | '핫 키워드' 포함 |
| T-30 | `test_generate_report_all_sections` | 전체 mock | 3개 섹션 모두 True |
| T-31 | `test_save_report_filename` | date '20260309' | '장초반브리핑_20260309.md' |

**총 테스트: 31개** (Plan 목표 28개 초과 달성)

### 6.5 테스트 실행

```bash
cd ~/stock/skills/kr-morning-briefing/scripts && python -m pytest tests/ -v
```

---

## 7. 수정 파일 목록

### 7.1 신규 생성 파일

| # | 파일 | 설명 | LOC 예상 |
|:-:|------|------|:-------:|
| F-01 | `skills/kr-morning-briefing/SKILL.md` | 스킬 명세서 | ~80 |
| F-02 | `skills/kr-morning-briefing/scripts/kr_morning_briefing.py` | 오케스트레이터 | ~80 |
| F-03 | `skills/kr-morning-briefing/scripts/market_data_collector.py` | 시장 데이터 수집 | ~150 |
| F-04 | `skills/kr-morning-briefing/scripts/monthly_calendar.py` | 월간 일정 | ~100 |
| F-05 | `skills/kr-morning-briefing/scripts/hot_keyword_analyzer.py` | 핫 키워드 분석 | ~100 |
| F-06 | `skills/kr-morning-briefing/scripts/report_generator.py` | 리포트 생성 | ~120 |
| F-07 | `skills/kr-morning-briefing/scripts/tests/test_market_data.py` | 테스트 | ~120 |
| F-08 | `skills/kr-morning-briefing/scripts/tests/test_monthly_calendar.py` | 테스트 | ~80 |
| F-09 | `skills/kr-morning-briefing/scripts/tests/test_hot_keyword.py` | 테스트 | ~60 |
| F-10 | `skills/kr-morning-briefing/scripts/tests/test_report_generator.py` | 테스트 | ~80 |
| F-11 | `skills/kr-morning-briefing/references/monthly_events.json` | 정적 일정 | ~60 |

### 7.2 수정 파일

| # | 파일 | 변경 내용 |
|:-:|------|----------|
| M-01 | `README.md` | 스킬 수 54→55, Skills Reference에 kr-morning-briefing 추가 |
| M-02 | `install.sh` | 스킬 수 54→55 |
| M-03 | `CLAUDE.md` | 스킬 수 54→55 |
| M-04 | `_kr_common/templates/report_rules.md` | 스킬-템플릿 매핑에 kr-morning-briefing 추가 (report_macro.md) |

### 7.3 비수정 파일

- `_kr_common/kr_client.py` — 미사용 (yfinance 직접 사용)
- `_kr_common/utils/ta_utils.py` — 기술적 지표 미사용
- `_kr_common/providers/` — 프로바이더 추가 없음

---

## 8. 구현 순서

| Step | 작업 | 의존성 |
|:----:|------|--------|
| 1 | `references/monthly_events.json` 작성 | - |
| 2 | `market_data_collector.py` 구현 | yfinance |
| 3 | `test_market_data.py` 작성 + 실행 | Step 2 |
| 4 | `monthly_calendar.py` 구현 | Step 1 |
| 5 | `test_monthly_calendar.py` 작성 + 실행 | Step 4 |
| 6 | `hot_keyword_analyzer.py` 구현 | - |
| 7 | `test_hot_keyword.py` 작성 + 실행 | Step 6 |
| 8 | `report_generator.py` 구현 | Step 2, 4, 6 |
| 9 | `test_report_generator.py` 작성 + 실행 | Step 8 |
| 10 | `kr_morning_briefing.py` 오케스트레이터 | Step 2, 4, 6, 8 |
| 11 | `SKILL.md` 작성 | Step 10 |
| 12 | `README.md`, `install.sh`, `CLAUDE.md` 업데이트 | Step 11 |
| 13 | `install.sh` 실행 + 동기화 검증 | Step 12 |
| 14 | Git commit & push | Step 13 |

---

## 9. 검증 기준 (Check Phase용)

| ID | 검증 항목 | 기준 | 가중치 |
|:--:|----------|------|:------:|
| V-01 | 디렉토리 구조 | Plan과 일치하는 파일 구조 | 5% |
| V-02 | yfinance 17개 티커 매핑 | YFINANCE_TICKERS 상수 17개 | 10% |
| V-03 | WebSearch 10개 항목 매핑 | WEBSEARCH_ITEMS 상수 10개 | 5% |
| V-04 | 카테고리 8개 순서 | CATEGORY_ORDER 8개 | 5% |
| V-05 | collect_yfinance_data() | 배치 다운로드, 등락률 계산, 방향 | 10% |
| V-06 | monthly_events.json | recurring + 연월 구조 | 5% |
| V-07 | load_static_events() | FOMC/BOK/만기일 정상 추출 | 8% |
| V-08 | get_recurring_date() | 2nd_thursday, 3rd_friday 계산 | 7% |
| V-09 | THEME_STOCK_MAP | 10개 테마, 각 3-4개 종목 | 5% |
| V-10 | report_generator 출력 | 3-Section 포맷 일치 | 10% |
| V-11 | 오케스트레이터 통합 | 3개 모듈 순차 실행, fail-safe | 10% |
| V-12 | 리포트 파일명 규칙 | `report_rules.md` 준수 | 5% |
| V-13 | 테스트 통과 | 31 tests passed | 10% |
| V-14 | README/install.sh/CLAUDE.md 동기화 | 스킬 수 55개 일치 | 5% |

---

## 10. 하위호환성

| 대상 | 영향 |
|------|------|
| 기존 54개 스킬 | **영향 없음** — 새 스킬 추가만, 공통 모듈 수정 없음 |
| `_kr_common/` | **수정 없음** — yfinance 직접 사용 |
| `report_rules.md` | 매핑 테이블 1줄 추가만 (기존 규칙 불변) |
| `install.sh` | 스킬 수 숫자만 변경 |

---

## 11. 변경 이력

| 날짜 | 버전 | 작업 내용 | 관련 섹션 |
|------|:----:|----------|----------|
| 2026-03-09 | 1.0 | 초안 작성 | 전체 |
