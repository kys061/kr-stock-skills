# 배당 안전성 모니터링 가이드

## 1. 5대 강제 리뷰 트리거

### T1: 감배 감지
- 전년 대비 주당배당금(DPS) 감소
- DART 배당 공시 또는 사업보고서 비교
- 심각도: CRITICAL → REVIEW 상태 전이

### T2: 무배당 전환
- 배당 결의 없음 or 무배당 공시
- 주주총회 결의 공시 모니터링
- 심각도: CRITICAL → EXIT_REVIEW 상태 전이

### T3: 실적 악화
- 영업이익 적자 전환 or 50% 이상 급감
- 분기보고서 손익계산서 비교
- 2분기 연속 감소 시 심각도 상향

### T4: 배당성향 위험
- 배당성향 100% 초과 (이익보다 많이 배당)
- 계산: DPS × 발행주식수 / 당기순이익
- 지속불가능한 배당 경고

### T5: 지배구조 이슈
- 대주주 지분 5% 이상 매각
- 경영권 분쟁 관련 공시
- 감사의견 비적정 (한정/부적정/거절)
- 관리종목/상장폐지 사유 발생

## 2. 상태 전이

| 현재 | 이벤트 | 다음 |
|------|--------|------|
| OK | T3 minor / T4 / T5 | WARN |
| OK | T1 / T3 major | REVIEW |
| OK | T2 | EXIT_REVIEW |
| WARN | resolved | OK |
| WARN | T1 / T3 major | REVIEW |
| REVIEW | resolved | OK |
| REVIEW | T2 | EXIT_REVIEW |
| EXIT_REVIEW | recovered | REVIEW |

## 3. 배당 안전성 스코어

### 등급 체계
- SAFE (≥80): 안전
- MODERATE (60-79): 보통
- AT_RISK (40-59): 주의
- DANGEROUS (<40): 위험
