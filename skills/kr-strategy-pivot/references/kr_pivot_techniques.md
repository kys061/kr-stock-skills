# 한국 시장 피벗 기법

## 3가지 피벗 기법

### 1. 가정 반전 (Assumption Inversion)

| 트리거 | 반전 방향 |
|--------|----------|
| cost_defeat | 보유 기간 단축 → 고유동성 종목 |
| tail_risk | 리스크 제약 강화 → 시장 중립 |
| improvement_plateau | 거래량 기반 시그널 → 타이밍 변경 |
| overfitting_proxy | 복잡도 축소 → 검증 기간 연장 |

### 2. 아키타입 전환 (Archetype Switch)

| 원본 아키타입 | 전환 대상 |
|-------------|----------|
| trend_following_breakout | mean_reversion_pullback, volatility_contraction |
| mean_reversion_pullback | trend_following_breakout, statistical_pairs |
| earnings_drift_pead | event_driven_fade, sector_rotation_momentum |
| volatility_contraction | trend_following_breakout, regime_conditional_carry |

### 3. 목적 리프레이밍 (Objective Reframe)

| 트리거 | 새 목적함수 |
|--------|-----------|
| tail_risk | max_drawdown_pct < 25%, expected_value > 0 |
| cost_defeat | win_rate > 55%, expected_value > 0 |
| improvement_plateau | risk_adjusted_return > 0.5 |
| overfitting_proxy | expected_value > 0, 레짐 안정성 |

## 한국 시장 특수 고려사항

- ±30% 가격제한폭: 테일 리스크 시나리오에서 고려
- 0.23% 거래세: cost_defeat 판정 시 US보다 높은 기준 적용
- 외국인 수급 영향: 피벗 시 수급 시그널 반영
