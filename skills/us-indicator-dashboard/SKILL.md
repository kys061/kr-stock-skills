# us-indicator-dashboard

미국 경제지표 21개를 자동 수집하여 5-컴포넌트 레짐 판정 + 한국 시장 영향 분석 + 발표 일정 캘린더를 포함한 4-Section 대시보드 리포트를 생성한다.

## 트리거

- `/us-indicator-dashboard` 또는 "미국 경제지표", "미국 지표 대시보드"

## 데이터 소스 우선순위

| 우선순위 | 소스 | 대상 지표 | 비고 |
|:--------:|------|----------|------|
| 1 | yfinance | 국채 2Y/10Y | 자동 수집 |
| 2 | WebSearch | 나머지 19개 | 9배치 검색 |
| 3 | FRED API | 모든 지표 | (미래 확장) |

## 21개 지표 (7개 카테고리)

| 카테고리 | 지표 |
|---------|------|
| 성장 | GDP |
| 금리 | 기준금리, 국채 2Y, 국채 10Y |
| 물가 | CPI, PCE, PPI, 인플레 기대 |
| 경기 | 실업률, 주당근무시간, 시간당소득, 실질임금, 실업수당, 소매판매 |
| 경기선행 | ISM PMI, 소비자심리, 소비자신뢰 |
| 경기동행 | 기업재고, 주택착공, 자동차판매 |
| 대외 | 경상수지 |

## 실행 절차

### Step 1: WebSearch — 물가 지표 수집

다음 검색어로 최신 물가 지표를 수집한다:
```
"US CPI PPI PCE latest {current_month} {current_year}"
```

추출 대상:
- CPI (YoY %): 현재값 + 이전값 + 발표일
- PPI (YoY %): 현재값 + 이전값 + 발표일
- Core PCE (YoY %): 현재값 + 이전값 + 발표일
- UMich 인플레이션 기대 (1Y %): 현재값 + 이전값

### Step 2: WebSearch — 고용/경기 지표 수집

```
"US jobs report unemployment rate weekly hours earnings {current_month} {current_year}"
```

추출 대상:
- 실업률 (%): 현재값 + 이전값
- 평균 주당 근무시간 (hrs): 현재값 + 이전값
- 평균 시간당 소득 (MoM %): 현재값 + 이전값
- 실질임금 (MoM %): 현재값 + 이전값

```
"initial jobless claims latest week"
```
- 신규 실업수당 (K): 현재값 + 이전값

### Step 3: WebSearch — 성장/소비/금리 지표 수집

```
"US GDP growth rate Q{quarter} {year} retail sales latest"
```
- GDP (연율화 %): 현재값 + 이전값
- 소매판매 (MoM %): 현재값 + 이전값

```
"federal funds rate FOMC decision {year}"
```
- 기준금리 (%): 현재값 + 이전값

### Step 4: WebSearch — 선행/심리 지표 수집

```
"ISM manufacturing PMI UMich consumer sentiment CB consumer confidence {current_month} {current_year}"
```
- ISM 제조업 PMI (index): 현재값 + 이전값
- 소비자심리 UMich (index): 현재값 + 이전값
- 소비자신뢰 CB (index): 현재값 + 이전값

### Step 5: WebSearch — 동행/대외 지표 + 일정 수집

```
"US housing starts business inventories auto sales current account {year}"
```
- 주택착공 (MoM %): 현재값 + 이전값
- 기업재고 (MoM %): 현재값 + 이전값
- 자동차판매 (SAAR M): 현재값 + 이전값
- 경상수지 ($B): 현재값 + 이전값

```
"US economic calendar this week next week"
```
- 향후 14일간 주요 지표 발표 일정 + 컨센서스 + 이전값

### Step 6: Python 스크립트 실행

Step 1-5에서 수집한 데이터를 다음 형식으로 정리한 뒤 스크립트에 주입한다:

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/stock/skills/us-indicator-dashboard/scripts'))
from us_indicator_dashboard import run

websearch_context = {
    'gdp': {'value': <float>, 'prev_value': <float>, 'release_date': '<YYYY-MM-DD>'},
    'fed_rate': {'value': <float>, 'prev_value': <float>},
    'cpi': {'value': <float>, 'prev_value': <float>, 'release_date': '<YYYY-MM-DD>'},
    'pce': {'value': <float>, 'prev_value': <float>, 'release_date': '<YYYY-MM-DD>'},
    'ppi': {'value': <float>, 'prev_value': <float>, 'release_date': '<YYYY-MM-DD>'},
    'inflation_exp': {'value': <float>, 'prev_value': <float>},
    'unemployment': {'value': <float>, 'prev_value': <float>},
    'weekly_hours': {'value': <float>, 'prev_value': <float>},
    'hourly_earnings': {'value': <float>, 'prev_value': <float>},
    'real_earnings': {'value': <float>, 'prev_value': <float>},
    'jobless_claims': {'value': <float>, 'prev_value': <float>},
    'retail_sales': {'value': <float>, 'prev_value': <float>},
    'ism_pmi': {'value': <float>, 'prev_value': <float>},
    'consumer_sentiment': {'value': <float>, 'prev_value': <float>},
    'consumer_confidence': {'value': <float>, 'prev_value': <float>},
    'business_inventories': {'value': <float>, 'prev_value': <float>},
    'housing_starts': {'value': <float>, 'prev_value': <float>},
    'auto_sales': {'value': <float>, 'prev_value': <float>},
    'current_account': {'value': <float>, 'prev_value': <float>},
}

calendar_context = {
    'events': [
        {'date': '<YYYY-MM-DD>', 'indicator': '<id>', 'name': '<이름>', 'forecast': '<값>', 'previous': '<값>'},
    ]
}

result = run(websearch_context=websearch_context, calendar_context=calendar_context)
print(f"Report saved: {result['report_path']}")
print(f"Regime: {result['regime']}")
print(f"Net Impact: {result['net_impact']}")
print(f"Collection: {result['collection_stats']}")
```

> **주의**: 수집 실패한 지표는 value에 None을 넣는다. 스크립트가 알아서 N/A 처리한다.

### Step 7: 이메일 발송

```bash
cd ~/stock && python3 skills/_kr_common/utils/email_sender.py "{report_path}" "us-indicator-dashboard"
```

## Output Rule

- **파일명**: `reports/us-indicator-dashboard_macro_미국경제지표_{YYYYMMDD}.md`
- **타입**: Type C (매크로/전략)
- **리포트 구조**: 4-Section
  - Section 1: 지표 대시보드 (7개 카테고리 × 21개 지표 테이블)
  - Section 2: 종합 진단 (4-레짐 판정 + 5-컴포넌트 스코어)
  - Section 3: 한국 시장 영향 분석 (긍정/부정/중립 분류)
  - Section 4: 향후 2주 발표 일정 (컨센서스 포함)

## 4-레짐 분류

| 레짐 | 조건 | 한국 영향 |
|------|------|----------|
| Goldilocks | 물가 안정 + 경기 양호 | 위험자산 강세, 유리 |
| Overheating | 물가 상승 + 경기 강세 | 금리 인상 우려, 부정적 |
| Stagflation | 물가 상승 + 경기 약세 | 최악 시나리오, 급락 |
| Recession | 물가 안정 + 경기 약세 | 긴급 인하 기대 |

## 5-컴포넌트 가중치

| 컴포넌트 | 가중치 | 구성 지표 |
|---------|:------:|----------|
| 물가 | 30% | CPI, PCE, PPI, 인플레 기대 |
| 경기 | 25% | GDP, ISM PMI, 소매판매, 주택착공, 기업재고 |
| 고용 | 25% | 실업률, 근무시간, 시간당소득, 실업수당 |
| 심리 | 10% | 소비자심리, 소비자신뢰 |
| 대외 | 10% | 경상수지 |

## US 통화정책 오버레이

이 스킬 자체가 미국 경제지표 분석이므로 오버레이 불필요 (자체 내장).
