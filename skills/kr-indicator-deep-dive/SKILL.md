---
name: kr-indicator-deep-dive
description: 주요 시장 지표(VIX/CNN F&G/EWY/KOSPI RSI/USD-KRW/HY OAS/Put-Call/VKOSPI 등)를 개별 심층 분석. 역대 극단값, 역사적 위치, 이후 수익률, 초보자 요약 포함.
---

# kr-indicator-deep-dive: 특정 지표 심층 분석

> 개별 시장 지표를 **5가지 분석 항목**으로 심층 해부합니다.
> 수치만 나열하는 것이 아니라, 역사적 맥락과 함의까지 제공합니다.
> 초보자도 이해할 수 있는 "한 문장 요약"을 필수 포함합니다.

## 사용 시점

- 특정 지표가 극단값에 도달했을 때 맥락 파악
- 시장 공포/과열 구간에서 역사적 비교가 필요할 때
- 여러 지표를 한 번에 비교하여 종합 판단이 필요할 때
- 초보 투자자에게 지표의 의미를 설명할 때

## 데이터 소스 우선순위

```
1순위: yfinance (VIX, EWY, USD/KRW 등 프로그래밍 조회)
2순위: WebSearch (CNN F&G, VKOSPI, HY OAS, Put/Call 등 검색 기반)
3순위: WebFetch (특정 URL 직접 접근, JS 렌더링 제한 있음)
```

### 주요 데이터 소스 URL

| 지표 | 1순위 소스 | 2순위 소스 |
|------|-----------|-----------|
| VIX | yfinance `^VIX` | CNBC, CBOE |
| CNN F&G | WebSearch | CNN Markets |
| EWY | yfinance `EWY` | Yahoo Finance |
| KOSPI RSI | yfinance `^KS11` + ta 계산 | Investing.com |
| USD/KRW | yfinance `KRW=X` | Trading Economics |
| HY OAS | WebSearch (FRED) | FRED API |
| Put/Call Ratio | WebSearch | MacroMicro, CBOE |
| VKOSPI | WebSearch | Investing.com, KRX |

## 분석 대상 지표 (기본 8개)

| # | 지표 | 카테고리 | 설명 |
|:-:|------|---------|------|
| 1 | VIX | 변동성 | CBOE 변동성지수 (S&P 500 옵션 내재변동성) |
| 2 | CNN Fear & Greed | 심리 | 7개 시장 지표 기반 공포-탐욕 0~100 |
| 3 | EWY | 한국 프록시 | iShares MSCI South Korea ETF |
| 4 | KOSPI RSI(14) | 기술적 | KOSPI 지수 14일 RSI |
| 5 | USD/KRW | 환율 | 원달러 환율 |
| 6 | HY OAS | 신용 | ICE BofA 하이일드 스프레드 |
| 7 | Put/Call Ratio | 포지셔닝 | CBOE Equity/Index 옵션 비율 |
| 8 | VKOSPI | 한국 변동성 | KOSPI200 옵션 내재변동성 |

### 확장 가능 지표 (사용자 요청 시 추가)

| 지표 | 카테고리 | 설명 |
|------|---------|------|
| AAII Sentiment | 심리 | 개인투자자 Bull/Bear 비율 |
| 10Y-2Y Spread | 채권 | 장단기 금리차 (경기침체 신호) |
| DXY | 통화 | 달러 인덱스 |
| MOVE Index | 채권변동성 | 채권시장 변동성 (금리 불확실성) |
| Margin Debt | 레버리지 | NYSE 신용잔고 |
| SKEW Index | 꼬리위험 | OTM 풋 수요 기반 블랙스완 확률 |

## 5가지 분석 항목 (지표당 필수)

모든 지표에 대해 아래 5개 항목을 **반드시** 포함한다:

### ① 현재 수치 및 최근 추이

```markdown
| 날짜 | {지표명} | 변동 |
|------|:-------:|------|
| MM/DD | **현재값** | 변동률 |
| MM/DD | 전일값 | - |
| MM/DD | 전전일값 | - |
```

- 최근 3~5일 데이터 테이블
- 일간 변동률 또는 절대 변동값

### ② 역대 극단값 (종가 기준)

```markdown
| 순위 | 날짜 | {지표명} | 상황 |
|:----:|------|:-------:|------|
| 1 | YYYY-MM-DD | 값 | 이벤트명 |
| 2 | ... | ... | ... |
```

- 상위/하위 극단값 Top 5
- 해당 시점의 이벤트/맥락 기재
- 현재값이 역대 기록에 근접하면 강조

### ③ 역사적 위치 (백분위 or 구간)

```markdown
| 구간 | 범위 | 현재 위치 |
|------|------|----------|
| 하위 25% | X~Y | |
| 25~50% | Y~Z | |
| 50~75% | Z~W | |
| 상위 25% | W+ | ← 현재값 |
```

- 장기 분포 기준 현재값의 백분위 표시
- 구간별 해석 (안정/보통/경계/공포 등)

### ④ 이후 시장 수익률 (해당 구간 진입 시 역사적 평균)

```markdown
| 기간 | 시장 평균 | 승률 |
|------|:--------:|:----:|
| 1주 후 | +X.X% | XX% |
| 1개월 후 | +X.X% | XX% |
| 3개월 후 | +X.X% | XX% |
```

- 현재값과 유사한 구간 진입 후 시장 수익률
- 1주/1개월/3개월 시계열
- 승률(양수 수익 확률) 병기

### ⑤ 핵심 포인트 + 한 문장 요약

```markdown
### 핵심 포인트
- 포인트 1
- 포인트 2
- 관전 포인트 (X 돌파 시 → A, Y 이탈 시 → B)

> **한 문장 요약**: 초보자도 이해할 수 있는 비유적 표현으로 현재 상태를 설명.
```

- 2~3개 핵심 포인트 (현재 상태 + 향후 시나리오)
- 기술적 전환점 (지지/저항, 임계값) 명시
- **한 문장 요약**: 비유나 쉬운 표현으로 초보자도 이해 가능하게

## 종합 대시보드 (복수 지표 분석 시)

2개 이상 지표 분석 시 리포트 말미에 종합 대시보드를 추가한다:

```markdown
## 종합 대시보드

| 지표 | 현재값 | 시그널 | 역사적 수준 |
|------|:------:|:------:|:----------:|
| VIX | 29.49 | 🟡 경계 | 상위 15% |
| CNN F&G | 27 | 🟠 공포 | Extreme Fear 직전 |
| ... | ... | ... | ... |

### 종합 판단
**현재 상태: "{요약 제목}"**

- 🔴 **공포 시그널**: {해당 지표 나열}
- 🟢 **안정 시그널**: {해당 지표 나열}
- 🟡 **핵심 관전 포인트**: {향후 시나리오 분기점}

> **초보자 한 줄 요약**: 한 문장으로 전체 시장 상태 요약
```

### 시그널 색상 기준

| 색상 | 의미 | 예시 |
|:----:|------|------|
| 🟢 | 안정/긍정 | HY OAS 낮음, F&G Greed |
| 🟡 | 경계/중립 | VIX 20~30, P/C Ratio 0.7~0.9 |
| 🟠 | 주의/약한 공포 | F&G Fear, VIX 30~40 |
| 🔴 | 위험/강한 공포 | RSI<20, VKOSPI 60+, VIX 40+ |

## 스크립트 실행 (1순위)

yfinance로 자동 수집 가능한 4개 지표(VIX, EWY, USD/KRW, KOSPI RSI)를 먼저 수집한다.

```bash
cd ~/stock/skills/kr-indicator-deep-dive/scripts
python3 indicator_fetcher.py                        # 전체 4개 지표
python3 indicator_fetcher.py --indicators VIX KOSPI # 특정 지표만
python3 indicator_fetcher.py --format json          # JSON 출력
```

나머지 4개 지표(CNN F&G, HY OAS, Put/Call, VKOSPI)는 WebSearch로 보완한다.

### 정적 참조 데이터

`references/historical_extremes.json`에 7개 지표의 역대 극단값 Top 5를 보관한다.
스크립트가 자동 로드하여 분석에 활용.

### 오류 핸들링

| 상황 | 대응 |
|------|------|
| yfinance 타임아웃 | 해당 지표 `error` 표시, 나머지 계속 수집 |
| 데이터 부족 (< 2일) | `Insufficient data` 반환, RSI 계산 생략 |
| references 파일 누락 | 빈 dict 반환, 극단값 없이 분석 계속 |

## 실행 방법

```
/kr-indicator-deep-dive
/kr-indicator-deep-dive VIX 심층 분석해줘
/kr-indicator-deep-dive VIX CNN공포탐욕 KOSPI RSI 분석
/kr-indicator-deep-dive 전체 8개 지표 심층 분석
```

### 인수 파싱

| 인수 | 동작 |
|------|------|
| (없음) | 기본 8개 지표 전체 분석 |
| 지표명 1개 | 해당 지표만 심층 분석 |
| 지표명 N개 | 지정 지표 분석 + 종합 대시보드 |
| `전체` / `all` | 기본 8개 + 확장 지표 전체 |

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| daily-market-check | 6개 지표 수치 요약 (빠른 체크용) |
| kr-rebound-signal | 14개 반등 시그널 YES/NO 체크리스트 |
| kr-bubble-detector | 6개 버블 지표 0-100 스코어링 |
| kr-market-environment | 글로벌+한국 종합 진단 |
| kr-crisis-compare | 역사적 위기 유사도 비교 |

### 스킬 간 차이점

| 스킬 | 초점 | 깊이 | 출력 |
|------|------|:----:|------|
| daily-market-check | 6개 지표 수치 확인 | 얕음 | 상태 판정 테이블 |
| kr-rebound-signal | 14개 시그널 YES/NO | 보통 | 매수 시그널 판정 |
| **kr-indicator-deep-dive** | **개별 지표 5항목 해부** | **깊음** | **역대값+백분위+수익률+요약** |

## Output Rule (마크다운 리포트 저장)

- **템플릿**: `_kr_common/templates/report_macro.md` 구조를 따른다
- **공통 규칙**: `_kr_common/templates/report_rules.md` 참조
- 저장 경로: `reports/indicator-deep-dive_{YYYYMMDD}.md`
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)
