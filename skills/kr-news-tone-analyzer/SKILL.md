---
name: kr-news-tone-analyzer
description: 한국 증시 관련 최근 24시간 뉴스 헤드라인을 수집하고 공포/중립/안정 톤을 분류하여 시장 센티먼트 전환 여부를 판단.
---

# kr-news-tone-analyzer: 뉴스 톤 분석

> 한국 증시(KOSPI/KOSDAQ) 관련 **최근 24시간 뉴스**를 수집합니다.
> 각 헤드라인의 톤을 **공포/중립/안정**으로 분류합니다.
> 톤 비율을 집계하여 **시장 센티먼트 전환 여부**를 판단합니다.
> 정부/당국 발언을 별도 추적합니다.

## 사용 시점

- 시장 급락 후 뉴스 톤 전환 여부를 모니터링할 때
- 정부/당국 긴급 대책 발표 여부를 확인할 때
- 시장 센티먼트 변화를 정량적으로 추적할 때
- kr-recovery-tracker 보완 데이터로 활용할 때

## 데이터 소스

### 검색 키워드

```
한국어: "KOSPI 시장", "증시 반등", "금융위원회 시장", "코스피 폭락", "코스닥 증시"
영어: "KOSPI", "KOSDAQ", "Korea stock market"
```

### 뉴스 소스 우선순위

| 카테고리 | 소스 | 수집 방법 |
|---------|------|----------|
| **한국어 뉴스** | 네이버 뉴스, 한국경제, 매일경제, 서울경제, 파이낸셜뉴스 | WebSearch |
| **영어 뉴스** | CNBC Asia, Bloomberg, Reuters, Seeking Alpha | WebSearch |
| **통신사** | 연합뉴스(en.yna.co.kr) | WebSearch |
| **정부/당국** | 금융위원회(fsc.go.kr), 기획재정부(moef.go.kr), 한국은행(bok.or.kr) | WebSearch |

### 검색 쿼리 패턴

```
# 한국어
"KOSPI 시장 {YYYY}년 {M}월"
"증시 반등 회복 {YYYY} {M}월"
"금융위원회 시장 안정 {YYYY} {M}월"

# 영어
"KOSPI KOSDAQ Korea stock market {Month} {YYYY}"
"Korea KOSPI rebound {Month} {YYYY}"

# 정부
"금융위원회 한국은행 시장 안정 긴급 대책 {YYYY} {M}월"
```

## 분석 프레임워크

### 톤 분류 기준

| 톤 | 키워드 (한국어) | 키워드 (영어) |
|:--:|----------------|--------------|
| **공포** | 폭락, 패닉, 서킷브레이커, 위기, 급락, 붕괴, 마진콜, 투매 | crash, panic, plunge, circuit breaker, crisis, rout, selloff |
| **중립** | 보합, 혼조, 관망, 횡보, 등락, 변동성 | mixed, flat, cautious, volatile, sideways, uncertain |
| **안정** | 반등, 회복, 저가매수, 안정화, 대책, 지원, 순매수, 상승 | rebound, recovery, rally, stabilize, support, surge, bounce |

### 톤 분류 알고리즘

1. 헤드라인에서 톤 키워드를 매칭
2. 복수 톤 키워드 존재 시 우선순위: 제목 내 첫 등장 키워드 우선
3. 키워드 미매칭 시 → 중립으로 분류
4. "반등" + "폭락 만회" 같은 복합 표현 → 안정으로 분류

### 정부/당국 추적

아래 소스에서 최근 발표를 별도 수집한다:

| 기관 | URL | 추적 항목 |
|------|-----|----------|
| 금융위원회 | fsc.go.kr/no010101 | 긴급 대책, 시장 안정 조치 |
| 기획재정부 | moef.go.kr | 경제 대책, 재정 지원 |
| 한국은행 | bok.or.kr | 긴급 금리 결정, 시장 안정 |

## 스크립트 실행

```bash
cd ~/stock/skills/kr-news-tone-analyzer/scripts
python3 tone_classifier.py --headline "코스피 역대급 반등, 외국인 순매수 전환"
python3 tone_classifier.py --headlines-file headlines.json
python3 tone_classifier.py --demo  # 데모 실행 (내장 샘플)
```

### 정적 참조 데이터

`references/tone_keywords.json`에 3개 톤별 한국어/영어 키워드 사전을 보관한다.

### 오류 핸들링

| 상황 | 대응 |
|------|------|
| WebSearch 결과 부족 | 최소 3개 헤드라인 확보 시 분석 진행, 미만 시 경고 |
| 키워드 미매칭 | 중립으로 분류, 수동 판단 권고 |
| 정부 소스 접근 불가 | "정부 발언: 미확인" 표시 |

## 출력 형식

### 1. 헤드라인 테이블 (필수)

```markdown
## 주요 헤드라인 (N개)

| # | 헤드라인 | 소스 | 톤 |
|:-:|---------|------|:--:|
| 1 | **제목** | 출처 | 공포/중립/안정 |
```

### 2. 톤 비율 집계 (필수)

```markdown
## 톤 분류 집계

| 톤 | 건수 | 비율 |
|:--:|:----:|:----:|
| 공포 | N | __% |
| 중립 | N | __% |
| 안정 | N | __% |
```

### 3. 정부/당국 발언 (필수)

```markdown
## 정부/당국 발언

### {기관명}
- **대책 내용 요약**
- 발언자, 일시
```

정부 발언이 없을 경우: `> 정부/당국 공식 발언: 없음`

### 4. 핵심 판단 (필수)

```markdown
## 핵심 판단

| 항목 | 판단 |
|------|------|
| 정부/당국 발언 | 있음/없음 — 내용 요약 |
| 안정 톤 50% 이상 | 충족/미충족 |
| 톤 전환 완료 여부 | 완료/진행 중/미전환 |
```

### 5. 한 줄 요약 (필수)

```markdown
> **한 줄 요약**: 뉴스 톤이 [공포/전환 중/안정]으로 판단됩니다. 근거: ___
```

#### 판단 기준

| 안정 톤 비율 | 공포 톤 비율 | 판단 |
|:-----------:|:-----------:|------|
| ≥ 70% | < 20% | **안정** (톤 전환 완료) |
| 50~69% | 20~40% | **전환 중** |
| < 50% | ≥ 50% | **공포** (전환 안 됨) |

## 실행 방법

```
/kr-news-tone-analyzer
/kr-news-tone-analyzer 오늘 뉴스 톤 분석
/kr-news-tone-analyzer 이란 사태 뉴스 톤
```

### 인수 파싱

| 인수 | 동작 |
|------|------|
| (없음) | 기본 키워드로 최근 24시간 뉴스 수집 + 톤 분석 |
| 키워드 | 추가 검색 키워드 지정 |
| `추이` / `trend` | 시계열 톤 변화 추이 포함 |

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-recovery-tracker | 회복 대시보드에 뉴스 톤 항목 제공 |
| kr-rebound-signal | 14개 시그널 중 "뉴스 톤 전환" 체크 |
| kr-market-news-analyst | 10일 뉴스 임팩트 스코어링 (깊이 우선) |
| daily-market-check | 6개 지표 일일 확인 (뉴스 톤 미포함) |

### 스킬 간 차이점

| 스킬 | 초점 | 시간 범위 | 출력 |
|------|------|----------|------|
| kr-market-news-analyst | 개별 이벤트 임팩트 1-10 스코어 | 10일 | 이벤트별 영향도 |
| **kr-news-tone-analyzer** | **헤드라인 톤 비율 + 전환 판단** | **24시간** | **공포/중립/안정 비율** |

## Output Rule (마크다운 리포트 저장 + 이메일 발송)

- **템플릿**: `_kr_common/templates/report_macro.md` 구조를 따른다
- **공통 규칙**: `_kr_common/templates/report_rules.md` 참조
- 저장 경로: `reports/news-tone-analyzer_{YYYYMMDD}.md`
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)

### 이메일 자동 발송 (필수)

리포트 MD 파일 저장 후 **반드시** 이메일을 발송한다:

```bash
cd ~/stock && python3 skills/_kr_common/utils/email_sender.py "reports/news-tone-analyzer_{YYYYMMDD}.md" "kr-news-tone-analyzer"
```

- `.env`의 `EMAIL_ENABLED=true` 설정 시 자동 발송
- 발송 실패 시에도 리포트 생성은 정상 완료로 간주 (fail-safe)
