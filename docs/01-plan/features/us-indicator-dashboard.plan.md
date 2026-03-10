# 미국 경제지표 대시보드 스킬 개발 계획

> **Feature**: us-indicator-dashboard
> **Created**: 2026-03-10
> **Status**: Plan Phase
> **Author**: Claude Code + User

---

## 1. 프로젝트 개요

### 1.1 목적

사용자가 수동으로 텍스트 파일(`경제지표.txt`)에 관리하던 **미국 경제지표 21개 항목**을
자동 수집 + 분석하여 대시보드 리포트를 생성하는 스킬을 개발한다.

> **사용자 원본 이미지 참조**:
> - `/home/saisei/screen_shot/미국지표.jpg` — 4개 카테고리(성장/금리/물가/경기) 14개 지표
> - `/home/saisei/screen_shot/미국지표02.jpg` — 3개 카테고리(선행/동행/대외) 7개 추가 지표
> - 각 지표별 최신 발표값 + 발표일을 괄호로 관리
> - 네이버 검색으로 하나씩 확인하는 방식 → 자동화 필요

### 1.2 기존 스킬과의 차별점

| 기존 스킬 | 역할 | 한계 |
|----------|------|------|
| us-monetary-regime | Fed 통화정책 기조 레짐 분류 | GDP/CPI/실업률은 포함하나 개별 지표 대시보드 아님 |
| daily-market-check | 6개 매크로 지표 | PPI, PCE, 실업수당, 소매판매 미포함 |
| kr-morning-briefing | 글로벌 시장 + 한국 브리핑 | 미국 지표 개별 추적 아닌 시장 가격 중심 |

**us-indicator-dashboard**는:
- 사용자가 수동 관리하던 **정확히 21개 지표**를 자동화
- 각 지표의 **최신 발표값 + 발표일 + 이전값 대비 변화 + 추세**를 한 눈에 제공
- **한국 시장 영향도**를 각 지표별로 평가
- **다음 발표 일정**까지 포함하여 캘린더 기능 겸비

### 1.3 핵심 원칙

- **이미지 원본 충실**: 사용자의 `미국지표.jpg` + `미국지표02.jpg`에 나열된 21개 지표를 정확히 추적
- **최신값 자동 수집**: WebSearch + FRED(가능 시) + yfinance 조합
- **변화 추적**: 이전 발표 대비 방향(↑↓→) + 변동폭
- **액션 지향**: 각 지표가 한국 주식시장에 미치는 영향 해석

---

## 2. 추적 대상 지표 (21개)

### 2.1 카테고리 1: 성장 (1개)

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 |
|:-:|--------|------|----------|----------|----------|
| 1 | 경제성장률 (실질GDP 증가율) | Real GDP Growth Rate | 분기 (연율화) | BEA | 미국 경기 방향 → 한국 수출 영향 |

### 2.2 카테고리 2: 금리 (3개)

| # | 지표명 | 영문 | 발표/갱신 주기 | 소스 | 한국 영향 |
|:-:|--------|------|-------------|------|----------|
| 2 | 미국 기준금리 | Fed Funds Rate | FOMC (연 8회) | Fed | 한미 금리차 → 환율/외국인 수급 |
| 3 | 국고채 2년 | 2-Year Treasury Yield | 실시간 | yfinance `^IRX`/WebSearch | 단기 금리 전망 반영 |
| 4 | 국고채 10년 | 10-Year Treasury Yield | 실시간 | yfinance `^TNX` | 장기 금리 → 성장주 밸류에이션 |

### 2.3 카테고리 3: 물가 (4개)

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 |
|:-:|--------|------|----------|----------|----------|
| 5 | CPI (소비자물가지수) | CPI YoY | 월간 | BLS | 금리 인하/인상 기대 → 글로벌 위험자산 |
| 6 | PCE (개인소비지출) | Core PCE YoY | 월간 | BEA | Fed 선호 물가 지표 → 금리 결정 핵심 |
| 7 | PPI (생산자물가지수) | PPI YoY | 월간 | BLS | CPI 선행 지표 → 기업 비용 압력 |
| 8 | 인플레이션 기대심리 | UMich Inflation Expectations | 월간 | U of Michigan | 기대 인플레 → Fed 정책 판단 |

### 2.4 카테고리 4: 경기 (6개)

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 |
|:-:|--------|------|----------|----------|----------|
| 9 | 실업률 | Unemployment Rate | 월간 (고용보고서) | BLS | 고용 냉각→인하 기대→신흥국 유리 |
| 10 | 평균주당근무시간 | Avg Weekly Hours (Production) | 월간 (고용보고서) | BLS | 노동시장 건강도, GDP 선행 |
| 11 | 평균시간당소득 (전월대비) | Avg Hourly Earnings MoM | 월간 (고용보고서) | BLS | 임금-물가 스파이럴 리스크 |
| 12 | 실질임금 (전월대비) | Real Earnings MoM | 월간 | BLS | 소비력 → 소매판매 선행 |
| 13 | 신규 실업수당청구건수 | Initial Jobless Claims | 주간 (매주 목요일) | DOL | 가장 빠른 고용 동향 신호 |
| 14 | 소매판매 (전년/전월대비) | Retail Sales YoY/MoM | 월간 | Census Bureau | 미국 소비 경기 → 글로벌 수요 |

### 2.5 카테고리 5: 경기 선행 (3개) — `미국지표02.jpg`

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 | 기준값 |
|:-:|--------|------|----------|----------|----------|:------:|
| 15 | ISM 제조업 PMI | ISM Manufacturing PMI | 월간 (매월 1영업일) | ISM | 글로벌 제조업 사이클 → 한국 수출 선행 | *50 기준 |
| 16 | 소비자심리지수 | UMich Consumer Sentiment | 월간 (예비+확정) | U of Michigan | 미국 소비 전망 → 글로벌 수요 | *100 기준 |
| 17 | 소비자신뢰지수 | CB Consumer Confidence | 월간 | Conference Board | 소비 의향 → 소매판매 선행 | *100 기준 |

### 2.6 카테고리 6: 경기 동행 (3개) — `미국지표02.jpg`

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 |
|:-:|--------|------|----------|----------|----------|
| 18 | 기업재고 (전월대비) | Business Inventories MoM | 월간 | Census Bureau | 재고 순환 → 수출 주문 사이클 |
| 19 | 주택착공건수 (전월대비) | Housing Starts MoM | 월간 | Census Bureau | 건설/원자재 수요 → 철강/구리 |
| 20 | 자동차등록건수 | Auto Sales (SAAR) | 월간 | BEA | 내구재 소비 → 자동차 부품 수출 |

### 2.7 카테고리 7: 대외 (1개) — `미국지표02.jpg`

| # | 지표명 | 영문 | 발표 주기 | 발표 기관 | 한국 영향 |
|:-:|--------|------|----------|----------|----------|
| 21 | 경상수지 | Current Account Balance | 분기 | BEA | 달러 수급 → 환율/신흥국 자금 흐름 |

---

## 3. 리포트 구조 (4-Section)

### Section 1: 미국 경제지표 대시보드 (핵심)

사용자의 `경제지표.txt`와 동일한 레이아웃으로 21개 지표를 테이블 형태로 출력한다.

```
## 미국 경제지표 대시보드
> 기준일: 2026-03-10 | 자동 수집

### 🔹 성장
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| 실질GDP 증가율 | 2.3% | 2026-01-30 | 3.1% | -0.8%p | ↓ 감속 |

### 🔹 금리
| 지표 | 최신값 | 기준일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| 기준금리 | 4.50% | 2026-01-29 | 4.75% | -0.25%p | ↓ 인하 |
| 국고채 2년 | 4.15% | 2026-03-07 | 4.20% | -0.05%p | ↓ |
| 국고채 10년 | 4.26% | 2026-03-07 | 4.30% | -0.04%p | ↓ |

### 🔹 물가
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| CPI | 2.9% | 2026-02-12 | 3.0% | -0.1%p | ↓ 둔화 |
| PCE | 2.5% | 2026-01-31 | 2.6% | -0.1%p | ↓ 둔화 |
| PPI | 2.2% | 2026-02-13 | 2.3% | -0.1%p | ↓ 둔화 |
| 인플레이션 기대심리 | 2.8% | 2026-02-14 | 2.9% | -0.1%p | ↓ |

### 🔹 경기
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| 실업률 | 4.3% | 2026-03-07 | 4.1% | +0.2%p | ↑ 냉각 |
| 평균주당근무시간 | 34.1hrs | 2026-03-07 | 34.2hrs | -0.1 | ↓ |
| 평균시간당소득 MoM | 0.6% | 2026-03-07 | 0.4% | +0.2%p | ↑ |
| 실질임금 MoM | -0.3% | 2026-03-12 | 0.1% | -0.4%p | ↓ |
| 신규실업수당청구 | 212K | 2026-02-27 | 219K | -7K | ↓ 양호 |
| 소매판매 MoM | -0.8% | 2026-03-17 | 0.2% | -1.0%p | ↓ 급락 |

### 🔹 경기 선행
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 | 기준 |
|------|--------|--------|--------|------|------|:----:|
| ISM 제조업 PMI | 46.8 | 2026-03-01 | 47.5 | -0.7 | ↓ 수축 | *50 |
| 소비자심리지수 | 67.8 | 2026-02-16 | 71.1 | -3.3 | ↓ | *100 |
| 소비자신뢰지수 | 103.3 | 2026-02-25 | 106.1 | -2.8 | ↓ | *100 |

### 🔹 경기 동행
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| 기업재고 MoM | 0.0% | 2026-02-14 | 0.1% | -0.1%p | → 정체 |
| 주택착공 MoM | 3.9% | 2026-02-20 | -2.3% | +6.2%p | ↑ 반등 |
| 자동차판매 (SAAR) | 15.8M | 2026-03-05 | 15.6M | +0.2M | ↑ |

### 🔹 대외
| 지표 | 최신값 | 발표일 | 이전값 | 변화 | 추세 |
|------|--------|--------|--------|------|------|
| 경상수지 | -$200.3B | 2026-03-20 | -$194.8B | -$5.5B | ↓ 적자확대 |
```

### Section 2: 종합 진단

21개 지표를 종합하여 현재 미국 경제 상태를 4단계로 판정한다:

| 레짐 | 설명 | 한국 영향 |
|------|------|----------|
| **Goldilocks** (골디락스) | 물가 안정 + 완만한 성장 + 적정 고용 | 위험자산 강세, 한국 유리 |
| **Overheating** (과열) | 물가 상승 + 강한 성장 + 과열 고용 | 금리 인상 우려, 한국 부정적 |
| **Stagflation** (스태그) | 물가 상승 + 성장 둔화 + 고용 냉각 | 최악 시나리오, 위험자산 급락 |
| **Recession** (침체) | 물가 안정 + 성장 역성장 + 고용 악화 | 긴급 인하 기대, 초기 부정→후반 긍정 |

판정 로직:
```
물가 스코어 = f(CPI, PCE, PPI, 기대심리)  → 높으면 인플레 압력
경기 스코어 = f(GDP, 실업률, 근무시간, 소매판매, ISM PMI, 기업재고, 주택착공) → 높으면 경기 강세
고용 스코어 = f(실업률, 시간당소득, 실업수당) → 높으면 고용 과열
심리 스코어 = f(소비자심리, 소비자신뢰) → 높으면 소비 낙관
대외 스코어 = f(경상수지) → 적자 확대 시 달러 약세 압력

Goldilocks: 물가 Low + 경기 Moderate + 고용 Moderate + 심리 High
Overheating: 물가 High + 경기 High + 고용 High
Stagflation: 물가 High + 경기 Low + 심리 Low
Recession: 물가 Low + 경기 Low + 고용 Low + 심리 Low
```

### Section 3: 한국 시장 영향 분석

각 지표 변화가 한국 시장에 미치는 영향을 해석한다:

```
## 한국 시장 영향 분석

### 긍정 요인
- CPI 둔화 → Fed 인하 기대 유지 → 외국인 자금 유입 환경
- 신규실업수당 하락 → 미국 경기 양호 → 한국 수출 지지

### 부정 요인
- 시간당소득 가속 → 임금발 인플레 우려 → 인하 지연 가능
- 소매판매 급락 → 미국 소비 둔화 → 한국 IT 수출 부담

### 중립 요인
- GDP 감속이나 여전히 잠재성장률 상회
- 2Y/10Y 스프레드 정상화 진행 중
```

### Section 4: 다음 발표 일정

향후 2주간 예정된 지표 발표 일정을 표시한다:

```
## 다음 발표 일정

| 날짜 | 지표 | 예상 | 이전 | 중요도 |
|------|------|------|------|:------:|
| 3/12 | CPI (2월) | 2.8% | 2.9% | ★★★ |
| 3/13 | PPI (2월) | 2.1% | 2.2% | ★★ |
| 3/14 | UMich 기대심리 | 2.7% | 2.8% | ★★ |
| 3/17 | 소매판매 (2월) | -0.2% | -0.8% | ★★★ |
| 3/19 | FOMC 금리 결정 | 4.50% (동결) | 4.50% | ★★★★★ |
```

---

## 4. 데이터 소스 아키텍처

### 4.1 데이터 수집 전략

```
═══════════════════════════════════════════════════
  Tier A: yfinance (실시간 시장 데이터) — 2개 지표
═══════════════════════════════════════════════════
국고채 10년 (^TNX), 국고채 2년 (^IRX 또는 2YY=F)

═══════════════════════════════════════════════════
  Tier B: WebSearch (최신 발표값) — 19개 지표
═══════════════════════════════════════════════════
[기존 12] GDP, 기준금리, CPI, PCE, PPI, 기대심리,
          실업률, 근무시간, 시간당소득, 실질임금, 실업수당, 소매판매
[추가 7]  ISM PMI, 소비자심리, 소비자신뢰,
          기업재고, 주택착공, 자동차판매, 경상수지

═══════════════════════════════════════════════════
  Tier C: FRED API (향후 확장) — 전체 21개
═══════════════════════════════════════════════════
FRED API 키 등록 시 1차 소스로 승격 가능
(현재 미등록 → Tier B로 운영)
```

### 4.2 지표별 데이터 소스 매핑

| # | 지표 | 1차 소스 | 폴백 소스 | FRED Series ID |
|:-:|------|---------|----------|---------------|
| 1 | 실질GDP | WebSearch "US GDP growth rate latest" | - | A191RL1Q225SBEA |
| 2 | 기준금리 | WebSearch "federal funds rate current" | - | FEDFUNDS |
| 3 | 국고채 2년 | yfinance `2YY=F` or WebSearch | yfinance `^IRX` | DGS2 |
| 4 | 국고채 10년 | yfinance `^TNX` | WebSearch | DGS10 |
| 5 | CPI | WebSearch "US CPI latest release" | - | CPIAUCSL |
| 6 | PCE | WebSearch "US core PCE latest" | - | PCEPILFE |
| 7 | PPI | WebSearch "US PPI latest release" | - | PPIACO |
| 8 | 기대심리 | WebSearch "UMich inflation expectations" | - | MICH |
| 9 | 실업률 | WebSearch "US unemployment rate latest" | - | UNRATE |
| 10 | 주당근무시간 | WebSearch "average weekly hours production" | - | AWHMAN |
| 11 | 시간당소득 | WebSearch "average hourly earnings MoM" | - | CES0500000008 |
| 12 | 실질임금 | WebSearch "US real earnings MoM" | - | CES0500000013 |
| 13 | 실업수당 | WebSearch "initial jobless claims latest" | - | ICSA |
| 14 | 소매판매 | WebSearch "US retail sales latest" | - | RSAFS |
| 15 | ISM 제조업 PMI | WebSearch "ISM manufacturing PMI latest" | - | MANEMP |
| 16 | 소비자심리 | WebSearch "UMich consumer sentiment latest" | - | UMCSENT |
| 17 | 소비자신뢰 | WebSearch "CB consumer confidence latest" | - | - |
| 18 | 기업재고 | WebSearch "US business inventories latest" | - | BUSINV |
| 19 | 주택착공 | WebSearch "US housing starts latest" | - | HOUST |
| 20 | 자동차판매 | WebSearch "US auto sales SAAR latest" | - | TOTALSA |
| 21 | 경상수지 | WebSearch "US current account balance latest" | - | NETFI |

### 4.3 WebSearch 쿼리 전략

21개 지표를 개별 검색하면 시간이 오래 걸리므로 **배치 검색** 전략을 사용한다:

| 배치 | WebSearch 쿼리 | 커버 지표 |
|:----:|---------------|----------|
| 1 | "US economic indicators latest 2026" | 전체 개요 |
| 2 | "US CPI PPI PCE latest {month} 2026" | CPI, PPI, PCE |
| 3 | "US jobs report unemployment {month} 2026" | 실업률, 근무시간, 시간당소득, 실질임금 |
| 4 | "initial jobless claims latest week" | 실업수당 (주간) |
| 5 | "US retail sales GDP growth latest" | GDP, 소매판매 |
| 6 | "fed funds rate FOMC decision latest" | 기준금리 |
| 7 | "university michigan inflation expectations consumer sentiment" | 기대심리, 소비자심리 |
| 8 | "ISM manufacturing PMI consumer confidence latest" | ISM PMI, 소비자신뢰 |
| 9 | "US housing starts business inventories auto sales current account" | 주택착공, 기업재고, 자동차판매, 경상수지 |

**목표**: 9회 WebSearch로 21개 지표 전부 수집 (개별 21회 → 9회 배치)

---

## 5. 스킬 구조

### 5.1 디렉토리 레이아웃

```
skills/us-indicator-dashboard/
├── SKILL.md                        # 스킬 명세서 (6-Step 실행 절차)
├── scripts/
│   ├── us_indicator_dashboard.py   # 메인 오케스트레이터
│   ├── indicator_collector.py      # 14개 지표 데이터 수집
│   ├── regime_classifier.py        # 4-레짐 종합 판정
│   ├── kr_impact_analyzer.py       # 한국 시장 영향 분석
│   ├── calendar_tracker.py         # 다음 발표 일정 추적
│   ├── report_generator.py         # 마크다운 4-Section 리포트 생성
│   └── tests/
│       ├── test_indicator_collector.py
│       ├── test_regime_classifier.py
│       ├── test_kr_impact_analyzer.py
│       ├── test_calendar_tracker.py
│       └── test_report_generator.py
└── references/
    ├── indicator_meta.json         # 21개 지표 메타데이터 (임계값, 발표주기 등)
    └── release_calendar.json       # 정기 발표 일정 (BLS, BEA, Fed 등)
```

### 5.2 모듈별 역할

| 모듈 | 역할 | 입력 | 출력 |
|------|------|------|------|
| indicator_collector.py | 21개 지표 최신값 + 이전값 수집 | WebSearch 결과, yfinance | dict(21 indicators) |
| regime_classifier.py | 물가/경기/고용/심리/대외 스코어 → 4-레짐 판정 | 21개 지표값 | regime(Goldilocks/Overheating/Stagflation/Recession) |
| kr_impact_analyzer.py | 각 지표 변화 → 한국 영향 긍정/부정/중립 분류 | 21개 지표 + 변화량 | list[{indicator, impact, reason}] |
| calendar_tracker.py | 향후 2주 발표 일정 + 시장 예상치 | release_calendar.json + WebSearch | list[{date, indicator, forecast}] |
| report_generator.py | 4-Section 마크다운 조합 | 위 4개 결과 | .md 파일 |

### 5.3 기존 스킬 연동

| 연동 스킬 | 활용 방법 |
|----------|----------|
| us-monetary-regime | 레짐 분류 결과 참조/비교 가능 |
| daily-market-check | 국채 수익률(^TNX) 재활용 |
| kr-morning-briefing | 금리/지표 변화 인용 가능 |
| kr-economic-calendar | 한국 대응 일정 매핑 |

---

## 6. 실행 흐름

```
/us-indicator-dashboard
     │
     ├─ [1] indicator_collector.py
     │   ├─ yfinance.download(["^TNX", "2YY=F"])   ← 국채 실시간
     │   ├─ WebSearch(9 batches)                     ← 19개 지표
     │   └─ parse + validate                         ← 21개 완성
     │
     ├─ [2] regime_classifier.py
     │   ├─ calc_inflation_score(CPI, PCE, PPI, 기대심리)
     │   ├─ calc_growth_score(GDP, 소매판매, ISM PMI, 주택착공, 기업재고)
     │   ├─ calc_employment_score(실업률, 근무시간, 소득)
     │   ├─ calc_sentiment_score(소비자심리, 소비자신뢰)
     │   └─ classify_regime()                        ← 4-레짐 판정
     │
     ├─ [3] kr_impact_analyzer.py
     │   ├─ 각 지표별 변화 방향 + 임계값 비교
     │   └─ 긍정/부정/중립 분류 + 한국 영향 해석
     │
     ├─ [4] calendar_tracker.py
     │   ├─ release_calendar.json 로드              ← 정기 일정
     │   ├─ WebSearch("economic calendar this week")  ← 동적 일정
     │   └─ 시장 예상치(consensus) 수집
     │
     └─ [5] report_generator.py
         ├─ Section 1: 대시보드 테이블
         ├─ Section 2: 종합 진단 (레짐)
         ├─ Section 3: 한국 영향 분석
         ├─ Section 4: 다음 발표 일정
         ├─ reports/ 저장
         └─ 이메일 발송
```

### 6.1 예상 실행 시간

| 단계 | 소요 시간 | 비고 |
|------|:--------:|------|
| yfinance (국채 2개) | ~3초 | 빠름 |
| WebSearch (9 배치) | ~75초 | 주요 병목 |
| 레짐 판정 | ~1초 | 계산만 |
| 한국 영향 분석 | ~1초 | 룰 기반 |
| 발표 일정 | ~10초 | JSON + WebSearch 1회 |
| 리포트 생성 | ~3초 | 마크다운 조합 |
| **합계** | **~95초** | 1.5분 이내 |

---

## 7. 핵심 참조 데이터: indicator_meta.json

```json
{
  "indicators": [
    {
      "id": "gdp",
      "name_kr": "경제성장률 (실질GDP 증가율)",
      "name_en": "Real GDP Growth Rate (Annualized)",
      "category": "growth",
      "unit": "%",
      "frequency": "quarterly",
      "source": "BEA",
      "target": 2.0,
      "thresholds": {"strong": 3.0, "moderate": 2.0, "weak": 1.0, "recession": 0.0}
    },
    {
      "id": "fed_rate",
      "name_kr": "기준금리",
      "name_en": "Federal Funds Rate",
      "category": "rates",
      "unit": "%",
      "frequency": "fomc",
      "source": "Fed"
    },
    {
      "id": "treasury_2y",
      "name_kr": "국고채 2년",
      "name_en": "2-Year Treasury Yield",
      "category": "rates",
      "unit": "%",
      "frequency": "daily",
      "source": "yfinance",
      "ticker": "2YY=F"
    },
    {
      "id": "treasury_10y",
      "name_kr": "국고채 10년",
      "name_en": "10-Year Treasury Yield",
      "category": "rates",
      "unit": "%",
      "frequency": "daily",
      "source": "yfinance",
      "ticker": "^TNX"
    },
    {
      "id": "cpi",
      "name_kr": "CPI (소비자물가지수)",
      "name_en": "CPI YoY",
      "category": "inflation",
      "unit": "%",
      "frequency": "monthly",
      "source": "BLS",
      "target": 2.0,
      "thresholds": {"low": 2.0, "moderate": 3.0, "high": 4.0, "very_high": 5.0}
    },
    {
      "id": "pce",
      "name_kr": "PCE (개인소비지출)",
      "name_en": "Core PCE YoY",
      "category": "inflation",
      "unit": "%",
      "frequency": "monthly",
      "source": "BEA",
      "target": 2.0,
      "note": "Fed preferred inflation gauge"
    },
    {
      "id": "ppi",
      "name_kr": "PPI (생산자물가지수)",
      "name_en": "PPI YoY",
      "category": "inflation",
      "unit": "%",
      "frequency": "monthly",
      "source": "BLS"
    },
    {
      "id": "inflation_exp",
      "name_kr": "인플레이션 기대심리",
      "name_en": "UMich Inflation Expectations 1Y",
      "category": "inflation",
      "unit": "%",
      "frequency": "monthly",
      "source": "University of Michigan"
    },
    {
      "id": "unemployment",
      "name_kr": "실업률",
      "name_en": "Unemployment Rate",
      "category": "economy",
      "unit": "%",
      "frequency": "monthly",
      "source": "BLS",
      "thresholds": {"tight": 3.5, "balanced": 4.0, "loose": 5.0, "recession": 6.0}
    },
    {
      "id": "weekly_hours",
      "name_kr": "평균주당근무시간 (생산량)",
      "name_en": "Average Weekly Hours (Production)",
      "category": "economy",
      "unit": "hrs",
      "frequency": "monthly",
      "source": "BLS",
      "baseline": 34.0
    },
    {
      "id": "hourly_earnings",
      "name_kr": "평균시간당소득 (전월대비)",
      "name_en": "Average Hourly Earnings MoM",
      "category": "economy",
      "unit": "%",
      "frequency": "monthly",
      "source": "BLS",
      "thresholds": {"moderate": 0.3, "elevated": 0.4, "hot": 0.5}
    },
    {
      "id": "real_earnings",
      "name_kr": "실질임금 (전월대비)",
      "name_en": "Real Earnings MoM",
      "category": "economy",
      "unit": "%",
      "frequency": "monthly",
      "source": "BLS"
    },
    {
      "id": "jobless_claims",
      "name_kr": "신규 실업수당청구건수",
      "name_en": "Initial Jobless Claims",
      "category": "economy",
      "unit": "K",
      "frequency": "weekly",
      "source": "DOL",
      "thresholds": {"healthy": 200, "moderate": 250, "concerning": 300, "recession": 350}
    },
    {
      "id": "retail_sales",
      "name_kr": "소매판매",
      "name_en": "Retail Sales MoM",
      "category": "economy",
      "unit": "%",
      "frequency": "monthly",
      "source": "Census Bureau"
    },
    {
      "id": "ism_pmi",
      "name_kr": "ISM 제조업 PMI",
      "name_en": "ISM Manufacturing PMI",
      "category": "leading",
      "unit": "index",
      "frequency": "monthly",
      "source": "ISM",
      "baseline": 50.0,
      "thresholds": {"expansion": 50.0, "strong": 55.0, "contraction": 45.0, "deep_contraction": 40.0},
      "note": "50 이상 확장, 50 이하 수축"
    },
    {
      "id": "consumer_sentiment",
      "name_kr": "소비자심리지수",
      "name_en": "UMich Consumer Sentiment",
      "category": "leading",
      "unit": "index",
      "frequency": "monthly",
      "source": "University of Michigan",
      "baseline": 100.0,
      "note": "예비(월중) + 확정(월말) 2회 발표"
    },
    {
      "id": "consumer_confidence",
      "name_kr": "소비자신뢰지수",
      "name_en": "CB Consumer Confidence Index",
      "category": "leading",
      "unit": "index",
      "frequency": "monthly",
      "source": "Conference Board",
      "baseline": 100.0,
      "note": "1985=100 기준"
    },
    {
      "id": "business_inventories",
      "name_kr": "기업재고 (전월대비)",
      "name_en": "Business Inventories MoM",
      "category": "coincident",
      "unit": "%",
      "frequency": "monthly",
      "source": "Census Bureau"
    },
    {
      "id": "housing_starts",
      "name_kr": "주택착공건수 (전월대비)",
      "name_en": "Housing Starts MoM",
      "category": "coincident",
      "unit": "%",
      "frequency": "monthly",
      "source": "Census Bureau",
      "note": "건설/원자재 수요 선행 지표"
    },
    {
      "id": "auto_sales",
      "name_kr": "자동차등록건수",
      "name_en": "Auto Sales (SAAR)",
      "category": "coincident",
      "unit": "M",
      "frequency": "monthly",
      "source": "BEA",
      "thresholds": {"strong": 17.0, "moderate": 15.0, "weak": 13.0}
    },
    {
      "id": "current_account",
      "name_kr": "경상수지",
      "name_en": "Current Account Balance",
      "category": "external",
      "unit": "$B",
      "frequency": "quarterly",
      "source": "BEA",
      "note": "적자 확대 → 달러 약세 압력 → 신흥국 자금 유입"
    }
  ]
}
```

---

## 8. Output Rule

### 8.1 리포트 저장

```
reports/us-indicator-dashboard_macro_미국경제지표_{YYYYMMDD}.md
```

### 8.2 이메일 발송

```bash
cd ~/stock && python3 skills/_kr_common/utils/email_sender.py \
  "reports/us-indicator-dashboard_macro_미국경제지표_20260310.md" \
  "us-indicator-dashboard"
```

### 8.3 리포트 헤더

```markdown
# 미국 경제지표 대시보드
> 생성일: 2026-03-10 | 지표 수: 21개 | 레짐: Goldilocks

## Section 1: 경제지표 현황
(21개 지표 테이블 — 7개 카테고리)

## Section 2: 종합 진단
(4-레짐 판정 + 근거)

## Section 3: 한국 시장 영향
(긍정/부정/중립 분류)

## Section 4: 다음 발표 일정
(향후 2주 캘린더)

---
*Generated by us-indicator-dashboard*
```

---

## 9. 구현 우선순위

### Phase 1: Core (MVP)

| 순서 | 모듈 | 테스트 목표 | 설명 |
|:----:|------|:---------:|------|
| 1 | indicator_collector.py | 15+ | 21개 지표 수집 + 파싱 |
| 2 | regime_classifier.py | 10+ | 5-컴포넌트 스코어 + 4-레짐 판정 |
| 3 | kr_impact_analyzer.py | 8+ | 21개 지표 한국 영향 분류 |
| 4 | calendar_tracker.py | 5+ | 발표 일정 조회 |
| 5 | report_generator.py | 6+ | 4-Section 리포트 (7카테고리) |
| 6 | us_indicator_dashboard.py | 3+ | 오케스트레이터 |
| **합계** | | **47+** | |

### Phase 2: Enhancement

- FRED API 연동 (API 키 등록 시 1차 소스로 승격)
- 히스토리 저장: 매 실행 시 `references/history.json`에 값 축적 → 추세 차트
- kr-morning-briefing 연동: 브리핑에 "미국 지표 요약" 섹션 삽입
- cron 자동 실행: 미국 고용보고서 발표일(매월 첫째 금) 자동 실행

---

## 10. 리스크 및 제약

| 리스크 | 영향 | 대응 |
|--------|------|------|
| WebSearch 결과에서 최신값 파싱 실패 | 지표값 누락 | 정규식 다중 패턴 + "N/A" 폴백 |
| 지표 발표 직후 아직 반영 안 됨 | 구 데이터 표시 | 발표일 명시로 사용자 판단 지원 |
| FRED API 미사용 | WebSearch 의존도 높음 | Phase 2에서 FRED 키 등록 시 전환 |
| 레짐 판정 주관성 | 경계값 논란 | 스코어 + 임계값 투명 공개 |
| 21개 지표 전부 수집 시 시간 | 2분 초과 가능 | 배치 WebSearch로 9회 이내 |

---

## 11. 성공 기준

| 지표 | 목표 |
|------|------|
| 실행 시간 | 2분 이내 |
| 지표 수집률 | 21개 중 17개+ (80%+) |
| 레짐 판정 | 4개 레짐 정확 분류 |
| 한국 영향 분석 | 긍정/부정 최소 3개씩 |
| 다음 발표 일정 | 5개 이상 |
| 테스트 커버리지 | 47+ tests |

---

## 12. 참조

- **원본 이미지**:
  - `/home/saisei/screen_shot/미국지표.jpg` — 14개 지표 (성장/금리/물가/경기)
  - `/home/saisei/screen_shot/미국지표02.jpg` — 7개 추가 지표 (선행/동행/대외)
- **기존 스킬**: us-monetary-regime (레짐 분류), daily-market-check (매크로 6개)
- **데이터 소스**: WebSearch (1차), yfinance (국채), FRED API (향후)
- **발표 기관**: BLS, BEA, Fed, DOL, Census Bureau, University of Michigan, ISM, Conference Board
