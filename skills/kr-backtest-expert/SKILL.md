---
name: kr-backtest-expert
description: 5차원 스코어링(수익성/안정성/리스크/거래특성/강건성)으로 백테스트 결과를 100점 만점 평가하고 DEPLOY/REFINE/INCUBATE/ABANDON 판정. 한국 비용 모델(수수료 0.015%+거래세 0.23%+슬리피지 0.1%) 적용.
---

# kr-backtest-expert

> 5차원 스코어링으로 백테스트 결과를 평가하고 DEPLOY/REFINE/ABANDON 판정.

## 5차원 평가 (각 20점, 총 100점)

| 차원 | 항목 | 만점 조건 |
|------|------|----------|
| 1 | Sample Size | ≥200 거래 |
| 2 | Expectancy | ≥1.5% 기대값 |
| 3 | Risk Management | DD<20% + PF≥3.0 |
| 4 | Robustness | ≥10년 + ≤4 파라미터 |
| 5 | Execution Realism | 슬리피지 테스트 완료 |

## 판정 기준

| 판정 | 점수 |
|------|:----:|
| DEPLOY | ≥70 |
| REFINE | 40-69 |
| ABANDON | <40 |

## 한국 특화

- **거래 비용**: 수수료 0.015% + 거래세 0.23% + 슬리피지 0.1%
- **가격제한**: ±30% 시나리오 미테스트 시 Red Flag
- **세금 미반영**: 거래세/배당세 미반영 시 Red Flag

## 사용법

```bash
python evaluate_backtest.py --input backtest_results.json
```
