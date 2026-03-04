---
name: kr-economic-calendar
description: 한국 주요 경제지표 발표 일정을 조회하고 임팩트 분석 리포트를 생성한다. 한국은행 ECOS API + 정적 캘린더를 활용하여 금통위, CPI, GDP, 고용률, 무역수지 등 12개 주요 경제이벤트의 향후 일정을 제공한다. 임팩트 레벨(H/M/L) 분류 포함.
---

# 한국 경제 캘린더 (kr-economic-calendar)

## 개요

한국 주요 경제지표 발표 일정을 조회하여 시장 참여자에게 사전 대비 정보를 제공한다.
US `economic-calendar-fetcher` (FMP API)를 한국은행 ECOS API + 정적 캘린더로 포팅.

**핵심 기능**:
- 한국 12개 주요 경제지표 일정 조회
- 임팩트 레벨 (H/M/L) 3단계 분류
- 금통위 결정일 자동 캘린더
- 향후 7-90일 이벤트 리스트
- JSON/Markdown 리포트 생성

## 데이터 소스

| US 원본 | KR 대체 |
|---------|---------|
| FMP Economic Calendar API | 한국은행 ECOS API + 정적 캘린더 |

**ECOS API 키**: `ECOS_API_KEY` 환경변수 설정 (선택 — 없어도 정적 캘린더로 기본 기능 제공)

## 한국 주요 경제지표 (12개)

### High Impact (5개)
| 지표 | 발표 주기 | 발표 기관 |
|------|:--------:|----------|
| 기준금리 (금통위) | 연 8회 | 한국은행 |
| 소비자물가지수 (CPI) | 매월 | 통계청 |
| GDP 성장률 | 분기 | 한국은행 |
| 고용률/실업률 | 매월 | 통계청 |
| 무역수지 (수출입) | 매월 | 관세청 |

### Medium Impact (4개)
| 지표 | 발표 주기 | 발표 기관 |
|------|:--------:|----------|
| 산업생산지수 | 매월 | 통계청 |
| 소매판매지수 | 매월 | 통계청 |
| 경상수지 | 매월 | 한국은행 |
| PMI (제조업) | 매월 | S&P Global |

### Low Impact (3개)
| 지표 | 발표 주기 | 발표 기관 |
|------|:--------:|----------|
| BSI (기업경기전망) | 매월 | 한국은행 |
| CSI (소비자심리) | 매월 | 한국은행 |
| 생산자물가지수 (PPI) | 매월 | 한국은행 |

## 워크플로우

### Step 1: 경제 캘린더 조회
```bash
python3 skills/kr-economic-calendar/scripts/kr_economic_calendar.py \
  --days-ahead 14 --impact H,M
```

### Step 2: 리포트 확인
- `kr_economic_calendar_report.json` — 구조화된 이벤트 데이터
- `kr_economic_calendar_report.md` — 마크다운 리포트

### Step 3: 시장 대응
- **High Impact** 이벤트 전후 변동성 증가 예상
- 금통위 결정일은 특히 금융주/채권에 영향
- GDP/CPI 발표일은 전체 시장 방향에 영향

## 참고 자료
- `references/kr_economic_indicators.md` — 한국 주요 경제지표 상세 가이드
