# us-monetary-regime

US 통화정책 기조, 금리 방향성, 글로벌 유동성을 종합 분석하여 한국 주식시장 영향도를 오버레이 점수로 제공한다.

## Usage

```
/us-monetary-regime
```

## Modules

| Module | Function | Output |
|--------|----------|--------|
| fed_stance_analyzer | `analyze_fed_stance()` | Fed 기조 점수 (-100~+100) |
| rate_trend_classifier | `classify_rate_trend()` | 금리 5단계 분류 + 점수 (0~100) |
| liquidity_tracker | `track_liquidity()` | 유동성 점수 (0~100) |
| kr_transmission_scorer | `score_kr_transmission()` | 한국 전이 점수 + 오버레이 (+-15) |
| regime_synthesizer | `synthesize_regime()` | 종합 레짐 + 섹터별 오버레이 |

## Integration (B방식 Overlay)

기존 kr-스킬의 점수 체계를 변경하지 않고, 오버레이로 적용:

```python
# kr-stock-analysis
from comprehensive_scorer import apply_monetary_overlay
result = apply_monetary_overlay(base_score=60.0, overlay=8.5, sector='semiconductor')
# → 60.0 + 8.5 * 1.3 = 71.05

# overlay=None이면 기존과 동일
result = apply_monetary_overlay(base_score=60.0, overlay=None)
# → 60.0
```

## Scoring

### US Regime Score (0~100)
- stance * 0.35 + rate * 0.30 + liquidity * 0.35
- 0~35: Tightening / 35~65: Hold / 65~100: Easing

### Overlay Calculation
- `(regime_score - 50) * 0.30` = base overlay (+-15)
- `base_overlay * sector_sensitivity` = final overlay per sector

### 14 Sector Sensitivities
| Sector | Sensitivity |
|--------|:-----------:|
| semiconductor, secondary_battery | 1.3 |
| bio, it | 1.2 |
| auto | 1.1 |
| shipbuilding | 1.0 |
| steel, chemical | 0.9 |
| construction | 0.8 |
| finance | 0.7 |
| insurance | 0.6 |
| retail | 0.5 |
| defense | 0.4 |
| food | 0.3 |
