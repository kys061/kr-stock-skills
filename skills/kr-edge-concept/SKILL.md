# kr-edge-concept

> 엣지 힌트와 리서치 티켓을 재사용 가능한 엣지 컨셉으로 합성하는 스킬.

## 개요

kr-edge-hint에서 생성된 힌트와 분석 티켓을 클러스터링하여
가설(thesis), 무효화 시그널(invalidation), 전략 플레이북(playbook)을 포함하는
엣지 컨셉으로 추상화한다. 엣지 파이프라인의 두 번째 단계.

## 8개 가설 유형

| 유형 | 설명 |
|------|------|
| breakout | 참여 확대 기반 추세 돌파 |
| earnings_drift | 이벤트 기반 지속 드리프트 |
| news_reaction | 뉴스 과반응 드리프트 |
| futures_trigger | 교차 자산 전파 |
| calendar_anomaly | 계절성 수요 불균형 |
| panic_reversal | 충격 과도 반전 |
| regime_shift | 레짐 전환 기회 |
| sector_x_stock | 리더-래거드 섹터 릴레이 |

## 핵심 상수

| 상수 | 값 | 설명 |
|------|------|------|
| MIN_TICKET_SUPPORT | 2 | 컨셉 합성 최소 티켓 수 |
| EXPORTABLE_FAMILIES | pivot_breakout, gap_up_continuation | 내보내기 가능 패밀리 |

## 파이프라인 위치

```
kr-edge-hint → [kr-edge-concept] → kr-edge-strategy → kr-edge-candidate
```

## 사용법

```bash
python synthesize_concepts.py \
  --hints hints.yaml \
  --tickets tickets/ \
  --output edge_concepts.yaml
```
