---
name: kr-earnings-calendar
description: 한국 상장기업 실적 발표 일정을 DART 공시 API를 통해 조회한다. 잠정실적(D002)과 확정실적(A001/A002/A003) 구분, 시총 1조원+ 필터, 장전/장중/장후 공시시간 분류를 제공한다. 한국 실적 시즌 패턴(잠정→확정, 4분기 사이클) 기반 캘린더.
---

# 한국 실적 캘린더 (kr-earnings-calendar)

## 개요

한국 상장기업의 실적 발표(공시) 일정을 DART API를 통해 조회하고 정리한다.
US `earnings-calendar` (FMP API)를 DART 공시 API로 포팅.

**핵심 기능**:
- DART 정기보고서/잠정실적 공시 조회
- 시총 1조원+ 기업 필터링
- 잠정실적/확정실적 구분
- 장전/장중/장후 공시시간 분류
- 한국 실적 시즌 매핑 (월 → 분기/유형)
- JSON/Markdown 리포트 생성

## 데이터 소스

| US 원본 | KR 대체 |
|---------|---------|
| FMP Earnings Calendar API | DART 공시 API |
| FMP Company Profile (market cap) | KRClient.get_stock_info |
| BMO/AMC/TAS 타이밍 | DART 공시시간 (장전/장중/장후) |

## DART 공시 유형

| 유형 | 코드 | 구분 | 발표 시기 |
|------|------|------|----------|
| 사업보고서 | A001 | 4Q 확정 | 3월 말 마감 |
| 반기보고서 | A002 | 2Q 확정 | 8월 중순 마감 |
| 분기보고서 | A003 | 1Q/3Q 확정 | 5월/11월 중순 마감 |
| 영업(잠정)실적 | D002 | 잠정 | 실적시즌 내 |
| 매출액/손익구조변경 | D001 | 잠정 | 변동 시 |

## 한국 실적 시즌

| 월 | 분기 | 유형 |
|:--:|:----:|------|
| 1-2월 | 4Q | 잠정실적 |
| 3월 | 4Q | 확정실적 (사업보고서) |
| 4-5월 | 1Q | 잠정→확정 |
| 7-8월 | 2Q | 잠정→확정 |
| 10-11월 | 3Q | 잠정→확정 |

## 워크플로우

### Step 1: 실적 캘린더 조회
```bash
python3 skills/kr-earnings-calendar/scripts/kr_earnings_calendar.py \
  --days-back 7 --days-ahead 14 --output-dir ./output
```

### Step 2: 리포트 확인
- `kr_earnings_calendar_report.json`
- `kr_earnings_calendar_report.md`

## 참고 자료
- `references/kr_earnings_season.md` — 한국 실적 시즌 상세 가이드
- `references/dart_disclosure_guide.md` — DART 공시 유형/코드 가이드
