---
name: kr-dart-disclosure-monitor
description: DART 전자공시 10유형(실적/배당/자본/M&A/지배구조/지분/법적/IPO/규제/기타) 자동 분류, 이벤트 영향도 1-10 스코어링, 지분 변동 추적.
---

# kr-dart-disclosure-monitor

DART 전자공시 10유형 분류, 이벤트 영향도 5단계, 지분 변동 추적, 리스크 스코어링 스킬.

## 개요

금융감독원 DART 전자공시를 10가지 유형으로 자동 분류하고,
이벤트 영향도를 5단계로 평가하며, 대량보유/임원 거래/자사주 등 지분 변동을 추적한다.
기존 kr-earnings-calendar(실적 5유형)과 달리 전체 공시 10유형 + 영향도 스코어링.

## 핵심 기능

1. **10유형 공시 분류** — 키워드 기반 자동 분류 (EARNINGS~OTHER)
2. **이벤트 영향도** — 1(Info)~5(Critical) 5단계 + 보정 요인
3. **지분 변동 추적** — 5% 대량보유, 임원 거래, 자사주 매매
4. **공시 리스크 스코어** — 4 컴포넌트 종합 (0-100)

## 스코어링

### 가중치
| 팩터 | 가중치 | 설명 |
|------|:------:|------|
| Event Severity | 35% | 이벤트 심각도 |
| Frequency | 20% | 공시 빈도 이상 |
| Stake Change | 25% | 지분 변동 방향 |
| Governance | 20% | 지배구조 안정성 |

### 등급
| 등급 | 점수 범위 | 의미 |
|------|:--------:|------|
| NORMAL | 0-24 | 정상 |
| ATTENTION | 25-49 | 주의 |
| WARNING | 50-74 | 경고 |
| CRITICAL | 75-100 | 위험 |

## 사용법

```bash
cd skills/kr-dart-disclosure-monitor/scripts
python -m pytest tests/ -v
```
