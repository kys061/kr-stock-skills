# 한국 전략 드래프트 스키마

## 드래프트 구조

```yaml
id: "draft-001-core"
concept_id: "concept-001"
variant: "core"
hypothesis_type: "breakout"
entry_family: "pivot_breakout"
entry:
  conditions:
    - "52주 신고가 돌파"
    - "거래량 20일 평균 대비 1.5배 이상"
  trend_filter: "20일 이동평균선 위"
risk:
  profile: "balanced"
  risk_per_trade: 0.01
  max_positions: 5
  stop_loss_pct: 0.07
  take_profit_rr: 3.0
exit:
  time_stop_days: 20
  trailing_stop: true
cost_model:
  round_trip_cost: 0.0053
  holding_cost_daily: 0.0
constraints:
  max_sector_exposure: 0.30
```

## 변형(Variant) 타입

| 변형 | risk_multiplier | 설명 |
|------|:---------------:|------|
| core | 1.0 | 기본 드래프트 |
| conservative | 0.75 | 리스크 축소 |
| research_probe | 0.5 | 탐색적 소규모 |

## 전략 타임 스톱

| 전략 유형 | 타임 스톱 |
|----------|:---------:|
| 돌파 전략 (pivot_breakout) | 20일 |
| 기타 | 10일 |
