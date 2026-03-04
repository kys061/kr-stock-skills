# 한국 파이프라인 스펙

## edge-finder-candidate/v1 인터페이스

```yaml
id: "kr-breakout-001"
name: "KOSPI200 돌파 전략"
universe:
  market: "KRX"
  index: "kospi200"
  filters:
    - "시가총액 >= 5000억원"
signals:
  entry_family: "pivot_breakout"
  conditions:
    - "52주 신고가 돌파"
    - "거래량 20일 평균 1.5배"
risk:
  risk_per_trade: 0.01
  max_positions: 5
  stop_loss_pct: 0.07
cost_model:
  round_trip_cost: 0.0053
validation:
  method: "full_sample"
  min_trades: 30
promotion_gates:
  min_score: 70
  min_profit_factor: 1.5
```
