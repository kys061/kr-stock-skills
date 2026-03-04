# kr-edge-strategy

> 엣지 컨셉을 전략 드래프트로 변환하는 스킬.

## 개요

kr-edge-concept에서 합성된 컨셉을 3가지 리스크 프로파일(보수/균형/공격)의
전략 드래프트 변형으로 변환한다. 한국 거래 비용 모델을 적용하며,
내보내기 가능한 패밀리는 kr-edge-candidate용 티켓으로 변환 가능하다.

## 3가지 리스크 프로파일

| 프로파일 | 리스크/거래 | 최대 포지션 | 손절 | 익절 R:R |
|----------|:-----------:|:-----------:|:----:|:--------:|
| conservative | 0.5% | 3 | 5% | 2.2x |
| balanced | 1.0% | 5 | 7% | 3.0x |
| aggressive | 1.5% | 7 | 9% | 3.5x |

## 한국 비용 모델

| 항목 | 값 | 설명 |
|------|------|------|
| round_trip_cost | 0.53% | 매수 0.015% + 매도 0.015% + 거래세 0.23% + 슬리피지 0.2% |
| holding_cost_daily | 0% | 현물 보유비용 없음 |
| margin_rate | 0% | 신용 미사용 기준 |

## 파이프라인 위치

```
kr-edge-hint → kr-edge-concept → [kr-edge-strategy] → kr-edge-candidate
```

## 사용법

```bash
python design_strategy_drafts.py \
  --concepts edge_concepts.yaml \
  --output-dir strategy_drafts/
```
