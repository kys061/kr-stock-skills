# 한국 증시 장 초반 브리핑 스킬 개발 계획

> **Feature**: kr-morning-briefing
> **Created**: 2026-03-09
> **Status**: Plan Phase
> **Author**: Claude Code + User

---

## 1. 프로젝트 개요

### 1.1 목적

한국 장 초반(KST 08:00~09:00)에 실행하여
**글로벌 시장 현황 + 당월 주요 일정 + 핫 키워드 분석**을 원스톱으로 제공하는 브리핑 스킬을 개발한다.

> **실행 시간대 근거 (KST 08:00~09:00)**:
> - 미국 시장 마감 완료 (KST 05:00~06:00) → 전일 종가/등락률 확정
> - 증권사 모닝 리포트 발행 시간대 (07:00~08:30) → 핫 키워드 수집 가능
> - 장 개장(09:00) 전 브리핑 완료 → 트레이딩 준비 시간 확보

### 1.2 기존 스킬과의 차별점

| 기존 스킬 | 역할 | 한계 |
|----------|------|------|
| daily-market-check | VIX/KOSPI/S&P500 등 6개 매크로 지표 | 원자재/운임/농산물 미포함, 월간 일정 없음 |
| kr-market-environment | 글로벌+한국 종합 진단 | 핫 키워드/관련주 미포함, 실행 시간 김 |
| kr-news-tone-analyzer | 뉴스 센티먼트 분석 | 지수/원자재 수치 미포함 |
| kr-market-news-analyst | 뉴스 임팩트 스코어링 | 시장 수치 테이블 미포함 |

**kr-morning-briefing**은 위 4개 스킬의 핵심 요소를 결합하되,
"장 초반 브리핑" 포맷에 최적화하여 **1개 리포트에 모든 정보**를 담는다.

### 1.3 핵심 원칙

- **빠른 실행**: 2분 이내 리포트 생성 (장 전 시간 압박 고려)
- **한눈에 파악**: 수치 + 등락 방향(↑↓) + 변동률 테이블 형식
- **액션 지향**: 핫 키워드 → 관련주 → 당일 트레이딩 힌트
- **자동 데이터**: API 기반 수집 (수동 입력 최소화)

---

## 2. 리포트 구조 (3-Section)

### Section 1: 글로벌 시장 현황

이미지 참조 기반으로 **8개 카테고리**의 글로벌 시장 데이터를 수집/표시한다.

#### 2.1.1 미국 지수 (3개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 다우지수 | `^DJI` (yfinance) | 종가, 등락률 |
| 나스닥 | `^IXIC` (yfinance) | 종가, 등락률 |
| S&P500 | `^GSPC` (yfinance) | 종가, 등락률 |

#### 2.1.2 환율 (3개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 원/달러 | `KRW=X` (yfinance) | 환율, 등락률 |
| 엔/달러 | `JPY=X` (yfinance) | 환율, 방향 |
| 달러인덱스 | `DX-Y.NYB` (yfinance) | 지수, 등락률 |

#### 2.1.3 미국 국채 (2개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 국고채 2년 | `^IRX` / WebSearch | 수익률, 변동 |
| 국고채 10년 | `^TNX` (yfinance) | 수익률, 변동 |

#### 2.1.4 유가 (3개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| WTI | `CL=F` (yfinance) | 가격, 등락률 |
| 두바이유 | WebSearch | 가격, 등락률 |
| 브렌트유 | `BZ=F` (yfinance) | 가격, 등락률 |

#### 2.1.5 안전자산 (2개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 금 | `GC=F` (yfinance) | 가격, 등락률 |
| 비트코인 | `BTC-KRW` (yfinance) | 원화 가격, 등락률 |

#### 2.1.6 광물 (6개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 구리 | `HG=F` (yfinance) | $/톤, 등락률 |
| 알루미늄 | WebSearch (LME) | $/톤, 등락률 |
| 니켈 | WebSearch (LME) | $/톤, 등락률 |
| 철광석 | WebSearch | $/톤, 등락률 |
| 유연탄 | WebSearch | $/톤, 등락률 |
| 리튬 | WebSearch | $/kg, 등락률 |

#### 2.1.7 농산물 (6개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| 옥수수 | `ZC=F` (yfinance) | 센트, 등락률 |
| 소맥 | `ZW=F` (yfinance) | 센트, 등락률 |
| 대두 | `ZS=F` (yfinance) | 센트, 등락률 |
| 커피 | `KC=F` (yfinance) | 센트, 등락률 |
| 원면 | `CT=F` (yfinance) | 센트, 등락률 |
| 쌀 | WebSearch | $/톤, 등락률 |

#### 2.1.8 운임지수 (2개)

| 항목 | 티커/소스 | 데이터 |
|------|----------|--------|
| SCFI (상하이컨테이너운임) | WebSearch | 지수, 등락률 |
| BDI (발틱운임) | `^BDIY` / WebSearch | 지수, 등락률 |

**총 27개 항목** — yfinance 가능 17개 + WebSearch 필요 10개

#### 2.1.9 출력 포맷

```
[미국지수]
다우지수: 47,501.55p -0.95% ↓
나스닥: 22,387.68p -1.59% ↓
S&P500: 6,740.02p -1.33% ↓

[환율]
원/달러: 1,485원 +0.41% ↑
엔/달러: 158.34엔 ↑
달러인덱스: 98.99 -0.33% ↓

... (이하 동일 패턴)
```

---

### Section 2: 당월 주요 일정 체크리스트

실행 월 기준으로 주요 경제/산업/이벤트 일정을 표시한다.

#### 2.2.1 일정 소스

| 우선순위 | 소스 | 데이터 |
|:-------:|------|--------|
| 1 | `references/monthly_events.json` (정적) | 정기 일정 (FOMC, BOK, 선물만기 등) |
| 2 | kr-economic-calendar 스킬 | ECOS 기반 경제지표 발표일 |
| 3 | kr-earnings-calendar 스킬 | DART 기반 실적 발표일 |
| 4 | WebSearch | 산업 이벤트, 정책 시행일, 문화 이벤트 |

#### 2.2.2 일정 유형

| 유형 | 예시 | 수집 방법 |
|------|------|----------|
| 경제정책 | FOMC, BOK 금통위, BOJ | 정적 + ECOS |
| 시장 이벤트 | 선물옵션 만기, IPO | 정적 + WebSearch |
| 산업 전시 | CES, MWC, 인터배터리 | WebSearch |
| 정책 시행 | 법률 시행, 규제 변경 | WebSearch |
| 기업 이벤트 | 실적 발표, 주총 | DART |
| 문화/사회 | BTS 컴백 등 시장 영향 이벤트 | WebSearch |

#### 2.2.3 출력 포맷

```
**3월 주요일정 체크리스트**
- 3/10 노란봉투법 시행
- 3/11 인터배터리 2026
- 3/12 한국 선물옵션 동시만기일
- 3/16 엔비디아 GTC 2026
- 3/17 미국 FOMC 및 경제발표
- 3/18 일본 BOJ 금융정책위원회
- 3/20 BTS 완전체 컴백
```

#### 2.2.4 정적 일정 파일 구조

```json
// references/monthly_events.json
{
  "recurring": {
    "fomc": {"months": [1,3,5,6,7,9,11,12], "description": "미국 FOMC 정례회의"},
    "bok": {"months": [1,2,4,5,7,8,10,11], "description": "한국은행 금통위"},
    "boj": {"months": [1,3,4,6,7,9,10,12], "description": "일본 BOJ 금융정책위원회"},
    "quad_witching": {"months": [3,6,9,12], "day": "3rd_friday", "description": "선물옵션 동시만기일"},
    "futures_expiry": {"months": "all", "day": "2nd_thursday", "description": "선물 만기일"}
  },
  "2026": {
    "03": [
      {"date": "2026-03-10", "event": "노란봉투법 시행", "category": "정책"},
      {"date": "2026-03-11", "event": "인터배터리 2026", "category": "산업"}
    ]
  }
}
```

---

### Section 3: 장 초반 핫 키워드

장 초반 시장을 움직이는 핵심 이슈 2~3개를 분석하고 관련주를 제시한다.

#### 2.3.1 핫 키워드 수집 소스

| 우선순위 | 소스 | 수집 방법 |
|:-------:|------|----------|
| 1 | WebSearch "한국 증시 오늘 장 전 핫 키워드" | 최신 기사 수집 |
| 2 | WebSearch "코스피 오늘 전망 {날짜}" | 증권사 리포트 |
| 3 | kr-news-tone-analyzer 결과 활용 | 이미 수집된 뉴스 재활용 |
| 4 | 전일 미국 시장 주요 뉴스 | yfinance 뉴스 또는 WebSearch |

#### 2.3.2 핫 키워드 구조

각 키워드별 다음 항목을 포함한다:

```
## 장초반 핫 키워드 1: {헤드라인}

### 핵심 요약
{2-3문장 요약}

### 시장 영향 분석
{어떤 영향을 주는지, 위험/기회 요인}

### 관련주
{종목명 나열 — 직접 수혜주 + 간접 수혜주}

### 전문가 코멘트 (있는 경우)
{증권사 의견 요약}
```

#### 2.3.3 핫 키워드 예시 유형

| 유형 | 예시 | 관련 섹터 |
|------|------|----------|
| 지정학 리스크 | 중동 긴장, 이란 전쟁 | 방산, 에너지, 금 |
| 원자재 급변 | WTI 100달러 돌파 | 정유, 화학, 운송 |
| 기술 이벤트 | 엔비디아 GTC, AI | 반도체, AI, 소프트웨어 |
| 정책 변화 | 금리 동결, 세제 개편 | 금융, 건설, 부동산 |
| 실적 서프라이즈 | 삼성전자 잠정실적 | 해당 섹터 |

#### 2.3.4 장초반 한줄평

리포트 마지막에 **한줄평** (종합 판단)을 추가한다:

```
**장초반 한줄평**: 미국·이스라엘과 이란 간의 갈등이 격화되면서 국내 증시에서
외국인 투자자들의 매도 공세가 거세지고 있지만, 원전 관련 종목으로 오히려
자금이 유입되는 차별화 현상이 나타나고 있습니다.
장중 매수사인은 흐름보면서 천천히 드리도록 하겠습니다.
```

---

## 3. 데이터 소스 아키텍처

### 3.1 데이터 수집 전략

```
═══════════════════════════════════════════════════
  Layer 1: yfinance (자동, 빠름) — 17/27 항목
═══════════════════════════════════════════════════
미국지수(3) + 환율(3) + 국채(1) + 유가(2) + 금(1)
+ 비트코인(1) + 구리(1) + 농산물(5)

═══════════════════════════════════════════════════
  Layer 2: WebSearch (폴백) — 10/27 항목
═══════════════════════════════════════════════════
국채2년(1) + 두바이유(1) + 광물(5) + 쌀(1) + 운임(2)

═══════════════════════════════════════════════════
  Layer 3: 정적 + API (일정/키워드)
═══════════════════════════════════════════════════
월간일정: references/monthly_events.json + kr-economic-calendar
핫키워드: WebSearch (뉴스 수집)
```

### 3.2 티커 매핑 테이블

```python
TICKERS = {
    # 미국 지수
    'dow': '^DJI',
    'nasdaq': '^IXIC',
    'sp500': '^GSPC',
    # 환율
    'usd_krw': 'KRW=X',
    'usd_jpy': 'JPY=X',
    'dxy': 'DX-Y.NYB',
    # 국채
    'us10y': '^TNX',
    # 유가
    'wti': 'CL=F',
    'brent': 'BZ=F',
    # 안전자산
    'gold': 'GC=F',
    'btc_krw': 'BTC-KRW',
    # 광물
    'copper': 'HG=F',
    # 농산물
    'corn': 'ZC=F',
    'wheat': 'ZW=F',
    'soybean': 'ZS=F',
    'coffee': 'KC=F',
    'cotton': 'CT=F',
}
```

---

## 4. 스킬 구조

### 4.1 디렉토리 레이아웃

```
skills/kr-morning-briefing/
├── SKILL.md                    # 스킬 명세서
├── scripts/
│   ├── kr_morning_briefing.py  # 메인 오케스트레이터
│   ├── market_data_collector.py # Section 1: 글로벌 시장 수집
│   ├── monthly_calendar.py     # Section 2: 월간 일정
│   ├── hot_keyword_analyzer.py # Section 3: 핫 키워드
│   ├── report_generator.py     # 마크다운 리포트 생성
│   └── tests/
│       ├── test_market_data.py
│       ├── test_monthly_calendar.py
│       ├── test_hot_keyword.py
│       └── test_report_generator.py
└── references/
    └── monthly_events.json     # 정기 일정 데이터
```

### 4.2 모듈별 역할

| 모듈 | 역할 | 입력 | 출력 |
|------|------|------|------|
| market_data_collector.py | 27개 항목 yfinance+WebSearch 수집 | 없음 | dict(8카테고리 x N항목) |
| monthly_calendar.py | 당월 일정 조합 (정적+동적) | 월 (int) | list[{date, event, category}] |
| hot_keyword_analyzer.py | 뉴스 수집 → 키워드 추출 → 관련주 매핑 | 없음 | list[{headline, summary, stocks}] |
| report_generator.py | 3개 Section 조합 → 마크다운 | 위 3개 결과 | .md 파일 |

### 4.3 기존 스킬 연동

| 연동 스킬 | 활용 방법 |
|----------|----------|
| daily-market-check | VIX/CNN F&G 값 재활용 가능 |
| kr-economic-calendar | 경제지표 발표 일정 |
| kr-earnings-calendar | 실적 발표 일정 |
| kr-news-tone-analyzer | 뉴스 톤 분석 결과 |
| kr-theme-detector | 테마주 매핑 (핫키워드 → 관련주) |

---

## 5. 실행 흐름

```
/kr-morning-briefing
     │
     ├─ [1] market_data_collector.py
     │   ├─ yfinance.download(17 tickers)    ← 배치 다운로드 (빠름)
     │   └─ WebSearch(10 items)               ← 폴백 항목
     │
     ├─ [2] monthly_calendar.py
     │   ├─ monthly_events.json 로드          ← 정적 일정
     │   ├─ kr-economic-calendar 결과          ← API 일정
     │   └─ WebSearch("3월 증시 주요 일정")    ← 동적 일정
     │
     ├─ [3] hot_keyword_analyzer.py
     │   ├─ WebSearch("한국 증시 장 전 핫 키워드")
     │   ├─ 키워드 추출 + 분석
     │   └─ 관련주 매핑 (kr-theme-detector 참조)
     │
     └─ [4] report_generator.py
         ├─ Section 1 + 2 + 3 조합
         ├─ 한줄평 생성
         ├─ reports/ 저장
         └─ 이메일 발송
```

### 5.1 예상 실행 시간

| 단계 | 소요 시간 | 비고 |
|------|:--------:|------|
| yfinance 배치 | ~5초 | 17개 티커 동시 |
| WebSearch (시장데이터) | ~30초 | 10개 항목 |
| WebSearch (일정) | ~10초 | 1-2회 |
| WebSearch (핫키워드) | ~30초 | 2-3회 |
| 리포트 생성 | ~5초 | - |
| **합계** | **~80초** | 2분 이내 목표 달성 |

---

## 6. Output Rule

### 6.1 리포트 저장

```
reports/kr-morning-briefing_market_장초반브리핑_{YYYYMMDD}.md
```

### 6.2 이메일 발송

```bash
cd ~/stock && python3 skills/_kr_common/utils/email_sender.py \
  "reports/kr-morning-briefing_market_장초반브리핑_20260309.md" \
  "kr-morning-briefing"
```

### 6.3 리포트 구조

```markdown
# 장 초반 브리핑
> 생성일: 2026-03-09 08:45 | 대상: 글로벌 시장 + 국내 증시

## Section 1: 글로벌 시장 현황
(8개 카테고리 테이블)

## Section 2: 3월 주요 일정
(체크리스트)

## Section 3: 장초반 핫 키워드
(2-3개 키워드 + 관련주)

## 장초반 한줄평
(종합 판단 1-2문장)

---
*Generated by kr-morning-briefing*
```

---

## 7. 구현 우선순위

### Phase 1: Core (MVP)

| 순서 | 모듈 | 테스트 | 설명 |
|:----:|------|:------:|------|
| 1 | market_data_collector.py | 10+ | yfinance 17개 + WebSearch 10개 |
| 2 | report_generator.py | 5+ | Section 1 포맷팅 |
| 3 | monthly_calendar.py | 5+ | 정적 일정 + ECOS |
| 4 | hot_keyword_analyzer.py | 5+ | WebSearch 기반 키워드 |
| 5 | kr_morning_briefing.py | 3+ | 오케스트레이터 통합 |

### Phase 2: Enhancement

- WebSearch 실패 시 캐시 폴백 (전일 데이터 재사용)
- 핫 키워드 → 관련주 자동 매핑 (kr-theme-detector 연동)
- cron 자동 실행 (매일 08:00 KST)
- 전일 대비 변화량 하이라이트

---

## 8. 리스크 및 제약

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 두바이유/광물/운임 yfinance 미지원 | 10개 항목 WebSearch 의존 | WebSearch 실패 시 "N/A" 표시 + 캐시 |
| 장 전 시간 WebSearch 속도 | 2분 초과 가능 | yfinance 항목 먼저 출력, WebSearch 비동기 |
| 핫 키워드 추출 품질 | LLM 의존적 | 뉴스 헤드라인 그대로 사용 + 분석 보완 |
| 월간 일정 업데이트 | 수동 관리 필요 | 정적 파일 + WebSearch 자동 보완 |

---

## 9. 성공 기준

| 지표 | 목표 |
|------|------|
| 실행 시간 | 2분 이내 |
| 시장 데이터 수집률 | 27개 중 22개+ (80%+) |
| 핫 키워드 | 2개 이상 + 관련주 포함 |
| 월간 일정 | 5개 이상 이벤트 |
| 테스트 커버리지 | 28+ tests |

---

## 10. 참조

- 이미지: 장 초반 브리핑 예시 (사용자 제공, 2026-03-09)
- 기존 스킬: daily-market-check, kr-market-environment, kr-news-tone-analyzer
- 데이터: yfinance, WebSearch, kr-economic-calendar, kr-earnings-calendar
