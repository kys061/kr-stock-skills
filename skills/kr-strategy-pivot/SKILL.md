---
name: kr-strategy-pivot
description: 백테스트 반복 최적화 정체를 감지하고 구조적으로 다른 전략 방향(피봇)을 제안. 로컬 옵티멈 탈출 지원.
---

# kr-strategy-pivot

> 백테스트 반복 정체를 감지하고 구조적 피벗을 제안하는 스킬.

## 개요

백테스트 반복 최적화 과정에서 파라미터 튜닝이 국소 최적에 수렴하면,
4가지 정체 트리거를 통해 이를 감지하고 continue/pivot/abandon 판정을 내린다.
pivot 판정 시 가정 반전, 아키타입 전환, 목적 리프레이밍 기법으로 새 전략을 제안한다.

## 4가지 정체 트리거

| 트리거 | 심각도 | 조건 |
|--------|:------:|------|
| improvement_plateau | HIGH | 최근 3회 점수 범위 < 3점 |
| overfitting_proxy | MEDIUM | Expectancy ≥15, Risk ≥15, Robustness <10 |
| cost_defeat | HIGH | 거래 비용이 엣지를 초과 |
| tail_risk_elevation | HIGH | Max DD >35% 또는 Risk Management ≤5 |

## 판정 결과

| 판정 | 조건 |
|------|------|
| abandon | 3회 이상 반복 + 최근 점수 <30 + 단조 감소 |
| pivot | 트리거 1개 이상 발화 |
| continue | 기본값 |

## 파이프라인 위치

```
kr-backtest-expert ←→ [kr-strategy-pivot] → (새 전략 드래프트)
```

## 사용법

```bash
python detect_stagnation.py --history backtest_history.json
python generate_pivots.py --diagnosis diagnosis.json --draft current_draft.yaml
```
