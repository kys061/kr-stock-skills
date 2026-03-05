# us-monetary-regime PDCA Completion Report

> **Feature**: US Monetary Regime Analysis + B-Overlay Integration
> **Date**: 2026-03-05
> **Match Rate**: 97%
> **Status**: COMPLETED

---

## 1. Executive Summary

US 통화정책 분석 독립 스킬(`us-monetary-regime`)을 구현하고, B방식 오버레이로 기존 3개 kr-스킬에 통합 완료.

- **5 Core Modules**: Fed 기조(-100~+100) + 금리 5단계(0~100) + 유동성(0~100) + 한국 전이(5채널) + 종합 레짐
- **B방식 Overlay**: 기존 종합 스코어 불변, `overlay * sector_sensitivity` 가산 (+-15pts)
- **14 Sector Sensitivities**: semiconductor(1.3) ~ food(0.3)
- **3 Patches**: comprehensive_scorer, conviction_scorer(9th component), market_utils
- **97% Match Rate**, 0 Major Gaps, 106 tests passed

---

## 2. PDCA Cycle Summary

| Phase | Date | Key Output |
|-------|------|-----------|
| Plan | 2026-03-05 | B방식 오버레이 확정, 15파일(12신규+3수정), ~100테스트 |
| Design | 2026-03-05 | 104 상수, 8 함수, 6 가중치합계, 11-Step 순서 |
| Do | 2026-03-05 | 12 new + 3 patched files, 106/106 tests |
| Check | 2026-03-05 | 97% Match Rate, 0 Major + 2 Minor gaps |
| Act | - | 불필요 (97% >= 90%) |
| Report | 2026-03-05 | 본 문서 |

---

## 3. Architecture

```
                    ┌──────────────────────┐
                    │  INPUT (WebSearch /   │
                    │  수동입력 / API)       │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              v                v                v
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │fed_stance    │ │rate_trend    │ │liquidity     │
     │_analyzer     │ │_classifier   │ │_tracker      │
     │              │ │              │ │              │
     │-100 ~ +100   │ │  0 ~ 100     │ │  0 ~ 100     │
     │(normalize    │ │              │ │              │
     │ to 0-100)    │ │              │ │              │
     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
            │ *0.35          │ *0.30          │ *0.35
            └────────────────┼────────────────┘
                             v
                    ┌──────────────────┐
                    │regime_synthesizer│
                    │regime_score 0~100│
                    │tightening/hold/  │
                    │easing            │
                    └────────┬─────────┘
                             │
                             v
                    ┌──────────────────┐
                    │kr_transmission   │
                    │_scorer           │
                    │5채널 + overlay   │
                    │+-15 * sensitivity│
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            v                v                v
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │kr-stock-     │ │kr-strategy-  │ │kr-market-    │
   │analysis      │ │synthesizer   │ │environment   │
   │              │ │              │ │              │
   │apply_monetary│ │9th component │ │foreign flow  │
   │_overlay()    │ │global_       │ │outlook       │
   │base + adj    │ │monetary 0.10 │ │estimation    │
   └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 4. Deliverables

### 4.1 New Files (12)

| File | Lines | Purpose |
|------|:-----:|---------|
| `SKILL.md` | - | 스킬 사용법 문서 |
| `references/fed_policy_database.md` | - | FOMC 일정, FFR 이력, 정책 키워드 |
| `references/sector_sensitivity_map.md` | - | 14섹터 민감도 근거 |
| `scripts/fed_stance_analyzer.py` | 138 | Fed 기조 4요소 가중 분석 |
| `scripts/rate_trend_classifier.py` | 182 | 금리 5단계 + 수익률곡선 분류 |
| `scripts/liquidity_tracker.py` | 179 | 유동성 4요소 추적 |
| `scripts/kr_transmission_scorer.py` | 261 | 한국 전이 5채널 + 14섹터 오버레이 |
| `scripts/regime_synthesizer.py` | 158 | 종합 레짐 오케스트레이터 |
| `scripts/__init__.py` | 0 | Package init |
| `scripts/tests/__init__.py` | 0 | Package init |
| `scripts/tests/test_us_monetary_regime.py` | 733 | 8 test classes, 106 tests |
| `references/__init__.py` | 0 | Package init |

### 4.2 Patched Files (3)

| File | Change | Impact |
|------|--------|--------|
| `comprehensive_scorer.py` | `apply_monetary_overlay()` + `_SECTOR_SENSITIVITY` dict | 기존 `calc_comprehensive_score()` 불변 |
| `conviction_scorer.py` | 8→9 components, `global_monetary` 0.10, weight rebalance | 기존 8 component 로직 보존 |
| `market_utils.py` | `estimate_foreign_flow_outlook()` | 기존 함수 불변 |

### 4.3 Updated Test Files (2)

| File | Change | Reason |
|------|--------|--------|
| `test_stock_analysis.py` | 4→5 components, weight assertions | growth-patch에서 이미 변경된 값 반영 |
| `test_strategy_synthesizer.py` | 7→9 components, weight assertions | growth-patch + monetary-patch 반영 |

---

## 5. Constants & Weights

### 5.1 Weight Sum Verifications (6/6 = 1.00)

| # | Dict | Sum |
|---|------|:---:|
| W-01 | STANCE_WEIGHTS (fomc 0.40 + dot 0.25 + qt 0.20 + speakers 0.15) | 1.00 |
| W-02 | YIELD_CURVE_WEIGHTS (level 0.50 + direction 0.30 + expectation 0.20) | 1.00 |
| W-03 | LIQUIDITY_WEIGHTS (fed_bs 0.30 + m2 0.30 + dxy 0.25 + rrp 0.15) | 1.00 |
| W-04 | TRANSMISSION_WEIGHTS (rate_diff 0.30 + fx 0.25 + risk 0.20 + sector 0.15 + bok 0.10) | 1.00 |
| W-05 | REGIME_WEIGHTS (stance 0.35 + rate 0.30 + liquidity 0.35) | 1.00 |
| W-06 | CONVICTION_COMPONENTS (9 weights: 0.15+0.14+0.09+0.14+0.09+0.08+0.11+0.10+0.10) | 1.00 |

### 5.2 Conviction Scorer Rebalance

| Component | Before | After | Delta |
|-----------|:------:|:-----:|:-----:|
| market_structure | 0.16 | 0.15 | -0.01 |
| distribution_risk | 0.16 | 0.14 | -0.02 |
| bottom_confirmation | 0.10 | 0.09 | -0.01 |
| macro_alignment | 0.16 | 0.14 | -0.02 |
| theme_quality | 0.10 | 0.09 | -0.01 |
| setup_availability | 0.09 | 0.08 | -0.01 |
| signal_convergence | 0.11 | 0.11 | 0 |
| growth_outlook | 0.12 | 0.10 | -0.02 |
| **global_monetary** | - | **0.10** | **NEW** |

### 5.3 14 Sector Sensitivities

| Tier | Sectors | Sensitivity |
|------|---------|:-----------:|
| High | semiconductor, secondary_battery | 1.3 |
| High | bio, it | 1.2 |
| Medium-High | auto | 1.1 |
| Neutral | shipbuilding | 1.0 |
| Medium-Low | steel, chemical | 0.9 |
| Low | construction | 0.8 |
| Low | finance (default) | 0.7 |
| Defensive | insurance | 0.6 |
| Defensive | retail | 0.5 |
| Defensive | defense | 0.4 |
| Defensive | food | 0.3 |

---

## 6. Test Results

### 6.1 us-monetary-regime Tests (106/106 passed)

| Test Class | Tests | Coverage |
|-----------|:-----:|---------|
| TestFedStanceAnalyzer | 19 | 5 labels, all maps, bounds, mixed signals |
| TestRateTrendClassifier | 15 | 5 regimes, yield curve, market expectations |
| TestLiquidityTracker | 15 | 5 levels, 4 scoring dicts, inverse relationships |
| TestKRTransmissionScorer | 21 | 5 channels, 14 sectors, overlay clamp, favored/unfavored |
| TestRegimeSynthesizer | 12 | 3 regimes, sub-module integration, data_inputs |
| TestPatchComprehensiveScorer | 10 | overlay apply, clamp, grade change, backward compat |
| TestPatchConvictionScorer | 8 | 9 components, weight sum, global_monetary |
| TestPatchMarketUtils | 5 | outlook logic, backward compat, rate diff adjustment |

### 6.2 Patched Skill Tests

| Skill | Tests | Result |
|-------|:-----:|:------:|
| kr-stock-analysis | 73/73 | PASS |
| kr-strategy-synthesizer | 52/52 | PASS |

---

## 7. Gap Analysis Summary

| Category | Score |
|----------|:-----:|
| File Structure | 100% (15/15) |
| Constants (104) | 100% |
| Functions (8) | 100% |
| Weight Sums (6) | 100% |
| Validation Rules (10) | 100% |
| Backward Compatibility (5) | 100% |
| Tests (106/~108) | 98% |
| **Overall Match Rate** | **97%** |

**Minor Gaps (2)**: OVERLAY constants file location (cosmetic), design doc function name inconsistency (doc-only).

---

## 8. Cumulative Project Statistics

| Metric | Value |
|--------|:-----:|
| Total Skill Modules | 46 (44 Phase 1-9 + growth-patch + us-monetary-regime) |
| Total Tests | 1,848+ (1,742 Phase 1-9 + 106 us-monetary-regime) |
| Consecutive 97% Match Rate | **10회** (Phase 3-9 + growth-patch + us-monetary-regime) |
| Major Gaps (cumulative) | 0 (last 10 checks) |

---

## 9. B방식 Overlay Integration Verification

| Check | Status |
|-------|:------:|
| `calc_comprehensive_score()` 기존 로직 불변 | PASS |
| `overlay = (regime_score - 50) * 0.30` | PASS |
| `overlay` 범위 [-15, +15] clamp | PASS |
| `adjusted = overlay * sector_sensitivity` | PASS |
| `final_score = clamp(base + adjusted, 0, 100)` | PASS |
| overlay=None → base_score 그대로 반환 | PASS |
| 14 sectors 각각 올바른 adjusted overlay | PASS |
| 기존 ANALYSIS_GRADES 등급 체계 재사용 | PASS |

---

## 10. Usage Example

```python
from regime_synthesizer import synthesize_regime
from comprehensive_scorer import calc_comprehensive_score, apply_monetary_overlay

# 1. US 통화정책 레짐 분석
regime = synthesize_regime(
    fomc_tone='slightly_dovish',
    dot_plot='lower',
    qt_qe='tapering_qt',
    speaker_tone=0.3,
    current_ffr=3.50,
    ffr_6m_ago=4.00,
    ffr_12m_ago=4.50,
    last_change_bp=-25,
    next_meeting_cut_prob=0.7,
    fed_bs_change_pct=0.5,
    m2_growth_yoy=4.0,
    dxy_change_3m=-2.0,
    rrp_change_pct=-10.0,
    kr_rate=3.00,
    usdkrw_change_3m=-1.5,
    foreign_flow_5d=3000,
    bok_direction='cutting',
)
# regime['us_regime']['regime_score'] → ~65 (easing)
# regime['overlay'] → ~4.5

# 2. 기존 종합 스코어에 오버레이 적용
base = calc_comprehensive_score(
    fundamental={'score': 70},
    technical={'score': 55},
    supply_demand={'score': 60},
)
# base['score'] → ~62 (BUY)

result = apply_monetary_overlay(
    base_score=base['score'],
    overlay=regime['overlay'],
    sector='semiconductor',
)
# result['final_score'] → ~68 (BUY, 반도체 민감도 1.3 적용)
```
