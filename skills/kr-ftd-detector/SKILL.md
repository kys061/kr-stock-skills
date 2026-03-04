---
name: kr-ftd-detector
description: KOSPI/KOSDAQ 이중 지수에서 William O'Neil의 Follow-Through Day(FTD) 신호를 탐지. Rally Attempt→FTD 확인→Post-FTD 건강도 상태 머신.
---

# kr-ftd-detector (한국 FTD 탐지기)

## 개요

| 항목 | 값 |
|------|-----|
| US 원본 | ftd-detector |
| 복잡도 | High |
| 시간 지평 | 수일~수주 (이벤트 기반) |
| 탐지 대상 | 조정 후 바닥 확인 시그널 (Follow-Through Day) |
| 방법론 | William O'Neil FTD 방법론 |
| 관계 | kr-market-top-detector와 공격/방어 쌍 |

## FTD(Follow-Through Day)란?

시장이 의미 있는 조정(-3% 이상) 후 바닥에서 반등할 때,
**Day 4-10 사이에 강한 거래량 동반 상승(+1.5%+)**이 나타나면
이를 Follow-Through Day로 인식. 새로운 상승 추세 시작의 확인 시그널.

## 상태 머신 (State Machine)

```
NO_SIGNAL → CORRECTION → RALLY_ATTEMPT → FTD_WINDOW → FTD_CONFIRMED
                ↑              ↓               ↓              ↓
                └── RALLY_FAILED ←─────────────┘     FTD_INVALIDATED
```

| 상태 | 정의 |
|------|------|
| NO_SIGNAL | 상승 추세, 조정 없음 |
| CORRECTION | 3%+ 하락, 3일 이상 |
| RALLY_ATTEMPT | 스윙 로우에서 반등 (Day 1-3) |
| FTD_WINDOW | Day 4-10, FTD 대기 |
| FTD_CONFIRMED | 유효한 FTD 시그널 |
| RALLY_FAILED | 스윙 로우 이탈 |
| FTD_INVALIDATED | FTD 일 종가 하회 |

## FTD 자격 조건

| 조건 | 값 |
|------|-----|
| 최소 랠리 일수 | Day 4부터 |
| 최대 FTD 윈도우 | Day 10까지 |
| 최소 상승률 | +1.5% |
| 거래량 | 전일 대비 증가 |
| 조정 하한 | 3%+ 하락 |
| 조정 일수 | 최소 3 거래일 |

## 5-컴포넌트 품질 점수 (0-100)

| # | 컴포넌트 | 가중치 | 설명 |
|---|---------|:------:|------|
| 1 | Volume Surge | **25%** | 거래량 급증 정도 |
| 2 | Day Number | **15%** | FTD 발생일 (Day 4-6 선호) |
| 3 | Gain Size | **20%** | 상승 폭 |
| 4 | Breadth Confirmation | **20%** | 시장폭 개선 |
| 5 | Foreign Flow | **20%** | 외국인 순매수 전환 (한국 특화) |

## 노출 가이드

| 품질 점수 | 시그널 | 노출 비율 |
|:--------:|--------|:--------:|
| 80-100 | Strong FTD | 75-100% |
| 60-79 | Moderate FTD | 50-75% |
| 40-59 | Weak FTD | 25-50% |
| < 40 | No FTD / Failed | 0-25% |

## 한국 특화: KOSPI + KOSDAQ 이중 추적

- 각 지수에 독립적 상태 머신 운영
- 둘 중 하나라도 FTD → 시그널 발생
- 두 지수 모두 FTD → 강화 시그널 (품질 +15)

## 한국 특화: 외국인 순매수 전환

FTD 시점에 외국인이 순매수로 전환하면 시그널 신뢰도 대폭 상승.
Component 5에서 20% 가중치로 반영.

## 실행 방법

```bash
cd ~/stock/skills/kr-ftd-detector/scripts
python kr_ftd_detector.py --output-dir ./output
```

## 출력 파일

- `kr_ftd_YYYY-MM-DD_HHMMSS.json`
- `kr_ftd_YYYY-MM-DD_HHMMSS.md`
