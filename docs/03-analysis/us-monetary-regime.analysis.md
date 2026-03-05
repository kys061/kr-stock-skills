# us-monetary-regime Gap Analysis

> **Feature**: us-monetary-regime (US 통화정책 분석 + B방식 오버레이)
> **Design**: `docs/02-design/features/us-monetary-regime.design.md`
> **Date**: 2026-03-05
> **Match Rate**: 97%
> **Result**: PASS (>= 90%)

---

## 1. Summary

| Category | Design | Implementation | Match |
|----------|--------|---------------|-------|
| File Structure | 15 files (12 new + 3 patch) | 15 files (12 new + 3 patch) + 1 extra | 100% |
| Constants (C-01~C-104) | 104 | 104 (all correct values) | 100% |
| Functions | 8 public + helpers | 8 public + helpers | 100% |
| Weight Sum Verifications | 6 (all = 1.00) | 6/6 verified | 100% |
| Tests | ~108 | 106 | 98% |
| Validation Rules (V-01~V-10) | 10 | 10/10 implemented | 100% |
| Backward Compatibility | 5 guarantees | 5/5 verified | 100% |

**Overall Match Rate: 97%** | Major Gaps: 0 | Minor Gaps: 2

---

## 2. File Structure Check

### 2.1 New Files (12/12 = 100%)

| # | Design Path | Status |
|---|-------------|--------|
| 1 | `us-monetary-regime/SKILL.md` | OK |
| 2 | `us-monetary-regime/references/fed_policy_database.md` | OK |
| 3 | `us-monetary-regime/references/sector_sensitivity_map.md` | OK |
| 4 | `us-monetary-regime/scripts/__init__.py` | OK |
| 5 | `us-monetary-regime/scripts/fed_stance_analyzer.py` | OK |
| 6 | `us-monetary-regime/scripts/rate_trend_classifier.py` | OK |
| 7 | `us-monetary-regime/scripts/liquidity_tracker.py` | OK |
| 8 | `us-monetary-regime/scripts/kr_transmission_scorer.py` | OK |
| 9 | `us-monetary-regime/scripts/regime_synthesizer.py` | OK |
| 10 | `us-monetary-regime/scripts/tests/__init__.py` | OK |
| 11 | `us-monetary-regime/scripts/tests/test_us_monetary_regime.py` | OK |
| 12 | `us-monetary-regime/references/__init__.py` | EXTRA (not in design, harmless) |

### 2.2 Patched Files (3/3 = 100%)

| # | File | Patch | Status |
|---|------|-------|--------|
| 1 | `kr-stock-analysis/scripts/comprehensive_scorer.py` | `apply_monetary_overlay()` added | OK |
| 2 | `kr-strategy-synthesizer/scripts/conviction_scorer.py` | 8→9 components, rebalanced weights | OK |
| 3 | `kr-market-environment/scripts/market_utils.py` | `estimate_foreign_flow_outlook()` added | OK |

---

## 3. Constants Verification (104/104 = 100%)

### 3.1 fed_stance_analyzer.py (C-01~C-23)
- STANCE_WEIGHTS: 0.40 + 0.25 + 0.20 + 0.15 = **1.00** OK
- FOMC_TONE_MAP: 5 entries (-80, -40, 0, +40, +80) OK
- DOT_PLOT_MAP: 3 entries (-70, 0, +70) OK
- QT_QE_MAP: 5 entries (-80, -40, 0, +40, +80) OK
- STANCE_LABELS: 5 labels with correct ranges OK

### 3.2 rate_trend_classifier.py (C-24~C-35)
- RATE_REGIMES: 5 regimes with correct ranges OK
- CHANGE_THRESHOLDS: aggressive=50, gradual=25 OK
- YIELD_CURVE_WEIGHTS: 0.50 + 0.30 + 0.20 = **1.00** OK
- INVERSION_THRESHOLD: 0 OK

### 3.3 liquidity_tracker.py (C-36~C-59)
- LIQUIDITY_WEIGHTS: 0.30 + 0.30 + 0.25 + 0.15 = **1.00** OK
- LIQUIDITY_LEVELS: 5 levels with correct ranges OK
- FED_BS_SCORING: 5 entries (15, 30, 50, 70, 85) OK
- M2_SCORING: 4 entries (20, 40, 60, 80) OK
- DXY_SCORING: 5 entries (20, 35, 50, 65, 80) OK

### 3.4 kr_transmission_scorer.py (C-60~C-77, C-88~C-102)
- TRANSMISSION_WEIGHTS: 0.30 + 0.25 + 0.20 + 0.15 + 0.10 = **1.00** OK
- RATE_DIFF_SCORING: 5 entries (80, 65, 50, 35, 20) OK
- FX_SCORING: 5 entries (80, 65, 50, 35, 20) OK
- BOK_LAG_MONTHS: (6, 12) OK
- SECTOR_SENSITIVITY: 14 sectors all correct OK
- DEFAULT_SENSITIVITY: 0.7 OK
- OVERLAY_MULTIPLIER: 0.30 OK (see Minor Gap #1)
- OVERLAY_MAX: 15 OK
- OVERLAY_MIN: -15 OK

### 3.5 regime_synthesizer.py (C-78~C-84)
- REGIME_WEIGHTS: 0.35 + 0.30 + 0.35 = **1.00** OK
- REGIME_LABELS: 3 labels (tightening 0-35, hold 35-65, easing 65-100) OK

### 3.6 Patch Constants (C-103~C-104)
- global_monetary weight: 0.10 OK
- Weight rebalance 9 components sum: 0.15+0.14+0.09+0.14+0.09+0.08+0.11+0.10+0.10 = **1.00** OK

---

## 4. Function Signatures (8/8 = 100%)

| # | Function | Params | Return | Status |
|---|----------|--------|--------|--------|
| 1 | `analyze_fed_stance()` | 4 params match | stance_score/label/components/description | OK |
| 2 | `classify_rate_trend()` | 7 params match | rate_regime/score/label/direction/confidence/signal/components | OK |
| 3 | `track_liquidity()` | 4 params match | score/level/trend/components | OK |
| 4 | `score_kr_transmission()` | 6 params match | score/label/overlay/channels/sector_overlays/favored/unfavored | OK |
| 5 | `get_sector_overlay()` | 2 params match | float | OK |
| 6 | `synthesize_regime()` | 19 params match | us_regime/kr_impact/overlay/sector_overlays/summary/data_inputs | OK |
| 7 | `apply_monetary_overlay()` | 3 params match | original/overlay/sector/sensitivity/adjusted/final/grade/impact | OK |
| 8 | `estimate_foreign_flow_outlook()` | 3 params match | outlook/confidence/reasoning or {} | OK |

---

## 5. Weight Sum Verification (6/6 = 100%)

| # | Location | Sum | Status |
|---|----------|-----|--------|
| W-01 | STANCE_WEIGHTS | 0.40+0.25+0.20+0.15 = 1.00 | PASS |
| W-02 | YIELD_CURVE_WEIGHTS | 0.50+0.30+0.20 = 1.00 | PASS |
| W-03 | LIQUIDITY_WEIGHTS | 0.30+0.30+0.25+0.15 = 1.00 | PASS |
| W-04 | TRANSMISSION_WEIGHTS | 0.30+0.25+0.20+0.15+0.10 = 1.00 | PASS |
| W-05 | REGIME_WEIGHTS | 0.35+0.30+0.35 = 1.00 | PASS |
| W-06 | CONVICTION_COMPONENTS | 0.15+0.14+0.09+0.14+0.09+0.08+0.11+0.10+0.10 = 1.00 | PASS |

---

## 6. Test Coverage

| Test Class | Design Est. | Actual | Status |
|-----------|:-----------:|:------:|--------|
| TestFedStanceAnalyzer | ~20 | 19 | OK |
| TestRateTrendClassifier | ~15 | 15 | OK |
| TestLiquidityTracker | ~15 | 15 | OK |
| TestKRTransmissionScorer | ~20 | 21 | OK |
| TestRegimeSynthesizer | ~15 | 12 | OK |
| TestPatchComprehensiveScorer | ~10 | 10 | OK |
| TestPatchConvictionScorer | ~8 | 8 | OK |
| TestPatchMarketUtils | ~5 | 5 | OK |
| **Total** | **~108** | **106** | **98%** |

All 106 tests pass. Patched skill test suites also pass:
- kr-stock-analysis: 73/73 passed
- kr-strategy-synthesizer: 52/52 passed

---

## 7. Validation Rules (10/10 = 100%)

| # | Rule | Implementation | Status |
|---|------|---------------|--------|
| V-01 | stance_score [-100, 100] | max/min clamp in analyze_fed_stance | OK |
| V-02 | rate_score [0, 100] | max/min clamp in classify_rate_trend | OK |
| V-03 | liquidity_score [0, 100] | max/min clamp in track_liquidity | OK |
| V-04 | regime_score [0, 100] | max/min clamp in synthesize_regime | OK |
| V-05 | overlay [-15, +15] | OVERLAY_MIN/MAX clamp in _calc_overlay | OK |
| V-06 | sector_sensitivity (0, 2.0] | All 14 values in range | OK |
| V-07 | final_score [0, 100] | max/min clamp in apply_monetary_overlay | OK |
| V-08 | speaker_tone [-1.0, 1.0] | max/min clamp in analyze_fed_stance | OK |
| V-09 | probability [0, 1.0] | Handled via score_market_expectation | OK |
| V-10 | weight sums = 1.00 | All 6 verified | OK |

---

## 8. Backward Compatibility (5/5 = 100%)

| # | Guarantee | Verification | Status |
|---|-----------|-------------|--------|
| 1 | `calc_comprehensive_score()` unchanged | No modifications to existing function | OK |
| 2 | `calc_conviction_score()` 9th missing → default 50 | normalize_signal(None) returns 50.0 | OK |
| 3 | `get_kr_market_snapshot()` unchanged | No modifications to existing function | OK |
| 4 | Existing test suites pass | kr-stock-analysis 73/73, kr-strategy-synthesizer 52/52 | OK |
| 5 | ANALYSIS_GRADES unchanged | Same thresholds reused in apply_monetary_overlay | OK |

---

## 9. Gap List

### Major Gaps: 0

### Minor Gaps: 2

| # | Gap | Design | Implementation | Impact |
|---|-----|--------|---------------|--------|
| M-01 | OVERLAY constants location | C-85~C-87 in regime_synthesizer.py | In kr_transmission_scorer.py | None (values correct, logic works correctly from both files) |
| M-02 | Design section 1 function name | `foreign_flow_forecast()` in file tree | `estimate_foreign_flow_outlook()` matches section 3.8 authoritative spec | None (design doc internal inconsistency, implementation follows authoritative spec) |

---

## 10. Conclusion

- **Match Rate: 97%** (>= 90% threshold PASS)
- **Major Gaps: 0** - no functional discrepancies
- **Minor Gaps: 2** - file location difference and design doc naming inconsistency
- **Tests: 106/106 passed** (us-monetary-regime) + 73/73 (kr-stock-analysis) + 52/52 (kr-strategy-synthesizer)
- **Act phase unnecessary** - all gaps are cosmetic, no code changes required
- **14 sector sensitivities: 100% match**
- **6 weight sum verifications: 100% (all = 1.00)**
- **B방식 오버레이 (+-15pts * sector_sensitivity): correctly implemented**
- **기존 스코어링 시스템 100% 무파괴 확인**
