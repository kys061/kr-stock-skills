# us-monetary-regime Planning Document

> **Summary**: US 통화정책 기조/금리방향/유동성 분석 독립 스킬 + 기존 kr-스킬 오버레이 통합
>
> **Project**: Korean Stock Skills
> **Version**: 10.0 (Phase 10)
> **Author**: Claude
> **Date**: 2026-03-05
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

미국 연준(Fed)의 통화정책 기조(긴축/완화), 금리 방향성(인상/인하/동결), 글로벌 유동성 흐름을 종합 분석하여 한국 주식시장에 대한 영향을 정량적 오버레이 점수로 제공한다.

### 1.2 Background

- 한국 주식시장은 미국 통화정책에 높은 민감도를 가짐 (외국인 비중 KOSPI ~30%)
- 기존 kr-스킬 44개 모듈은 한국 내부 데이터만 분석, 글로벌 통화정책 컨텍스트 부재
- Fed 긴축기 → 원화약세 + 외국인 이탈, Fed 완화기 → 원화강세 + 외국인 유입의 구조적 패턴
- 2024-2026 Fed 금리 인하 사이클 진행 중 → 실시간 레짐 판단 필요성

### 1.3 Related Documents

- 기존 스킬: `skills/kr-macro-regime/`, `skills/kr-market-environment/`, `skills/kr-stock-analysis/`, `skills/kr-strategy-synthesizer/`
- 참고: Phase 1-9 PDCA 보고서 (`docs/04-report/`)

---

## 2. Scope

### 2.1 In Scope

- [ ] Fed 통화정책 기조 판단 (Hawkish/Dovish 스코어링)
- [ ] 금리 방향성 분류 (5단계: aggressive_hike ~ aggressive_cut)
- [ ] 글로벌 유동성 추적 (Fed B/S, M2, DXY 등)
- [ ] 한국 전이 메커니즘 (한미금리차, 환율, 외국인수급, 섹터민감도)
- [ ] 종합 레짐 판단 및 오버레이 점수 생성
- [ ] 기존 kr-스킬 통합 (B방식 오버레이: base_score + overlay x sensitivity)
- [ ] 과거 1-2년 데이터 기반 분석 (뉴스 + 정량 데이터)

### 2.2 Out of Scope

- ECB, BOJ 등 타국 중앙은행 분석 (향후 확장 가능)
- 실시간 자동 알림/모니터링
- Fed 발언 자연어 처리 (AI 레이어에서 WebSearch로 대체)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Fed 기조 스코어 산출 (-100~+100, 긴축~완화) | High | Pending |
| FR-02 | 금리 트렌드 5단계 분류 (aggressive_hike/gradual_hike/hold/gradual_cut/aggressive_cut) | High | Pending |
| FR-03 | 유동성 스코어 산출 (0~100) - Fed B/S, M2, DXY 반영 | High | Pending |
| FR-04 | 한국 전이 스코어 산출 - 5채널 가중 (금리차0.30 + 환율0.25 + 위험선호0.20 + 섹터회전0.15 + BOK후행0.10) | High | Pending |
| FR-05 | 종합 US Monetary Regime 판정 (tightening/hold/easing) + regime_score (0~100) | High | Pending |
| FR-06 | 오버레이 점수 생성 (+-15점 범위, 섹터별 민감도 차등) | High | Pending |
| FR-07 | 14개 한국 섹터별 민감도 계수 정의 (0.0~1.5) | Medium | Pending |
| FR-08 | 기존 kr-stock-analysis comprehensive_scorer 오버레이 통합 | High | Pending |
| FR-09 | 기존 kr-strategy-synthesizer 글로벌 컨텍스트 반영 | Medium | Pending |
| FR-10 | 기존 kr-market-environment 외국인 수급 예측 반영 | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Data Freshness | WebSearch 기반 최신 데이터 수집 | 분석 시점 기준 1주 이내 |
| Scoring Accuracy | 가중치 합계 검증 = 1.00 | 단위 테스트 |
| Performance | 전체 분석 10초 이내 (WebSearch 제외) | 스크립트 실행 시간 |
| Compatibility | 기존 5요소 점수 체계 무변경 | 기존 테스트 전체 통과 |

---

## 4. Architecture

### 4.1 Skill Structure

```
skills/us-monetary-regime/
  SKILL.md
  references/
    fed_policy_database.py          # FOMC 일정, 역사적 금리 데이터, 정책 키워드
    sector_sensitivity_map.py       # 14개 한국 섹터별 US 정책 민감도 계수
  scripts/
    fed_stance_analyzer.py          # Fed 기조 판단 (-100~+100)
    rate_trend_classifier.py        # 금리 5단계 분류
    liquidity_tracker.py            # 유동성 스코어 (0~100)
    kr_transmission_scorer.py       # 한국 전이 5채널 스코어
    regime_synthesizer.py           # 종합 레짐 판정 + 오버레이 생성
    tests/
      test_us_monetary_regime.py    # 전체 테스트
```

### 4.2 통합 대상 기존 스킬 (패치)

```
skills/kr-stock-analysis/scripts/
  comprehensive_scorer.py           # 오버레이 적용 로직 추가 (기존 5요소 가중치 불변)

skills/kr-strategy-synthesizer/scripts/
  conviction_scorer.py              # global_monetary_context 반영

skills/kr-market-environment/scripts/
  (해당 스크립트)                     # 외국인 수급 예측에 US 유동성 반영
```

### 4.3 스코어링 체계 (B방식 오버레이)

```python
# Step 1: US Monetary Regime Score (0~100)
us_regime_score = (
    fed_stance_normalized * 0.35 +   # Fed 기조 (-100~+100 → 0~100 정규화)
    rate_trend_score * 0.30 +         # 금리 방향 (0~100)
    liquidity_score * 0.35            # 유동성 (0~100)
)
# 가중치 합계: 0.35 + 0.30 + 0.35 = 1.00

# Step 2: KR Transmission Score
kr_transmission = (
    interest_rate_diff * 0.30 +       # 한미 금리차
    fx_impact * 0.25 +                # 원달러 환율 영향
    risk_appetite * 0.20 +            # 글로벌 위험선호
    sector_rotation * 0.15 +          # 섹터 회전 효과
    bok_policy_lag * 0.10             # 한은 정책 후행
)
# 가중치 합계: 0.30 + 0.25 + 0.20 + 0.15 + 0.10 = 1.00

# Step 3: Overlay Calculation
# regime_score > 50 → positive overlay (easing)
# regime_score < 50 → negative overlay (tightening)
# regime_score = 50 → neutral (0)
raw_overlay = (us_regime_score - 50) * 0.30   # +-15점 범위

# Step 4: Sector Sensitivity Application
SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,    # 수출+성장 → 고민감
    'secondary_battery': 1.3,
    'bio': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'it': 1.2,
    'finance': 0.7,          # 내수 금융 → 저민감
    'insurance': 0.6,
    'construction': 0.8,
    'retail': 0.5,            # 내수 소비 → 최저민감
    'food': 0.3,
    'defense': 0.4,
}

final_overlay = raw_overlay * SECTOR_SENSITIVITY[sector]

# Step 5: Apply to existing score (기존 점수 체계 불변)
base_score = comprehensive_score(fundamental, technical, supply_demand, valuation, growth)
final_score = clamp(base_score + final_overlay, 0, 100)
```

### 4.4 데이터 흐름

```
[WebSearch: Fed news/data]
        |
        v
[fed_stance_analyzer] ──→ stance_score (-100~+100)
[rate_trend_classifier] ──→ rate_regime (5단계) + rate_score (0~100)
[liquidity_tracker] ──→ liquidity_score (0~100)
        |
        v
[regime_synthesizer] ──→ us_regime_score (0~100) + regime_label
        |
        v
[kr_transmission_scorer] ──→ kr_impact_score + overlay (+-15)
        |
        v
[kr-stock-analysis] ──→ base_score + overlay * sector_sensitivity = final_score
[kr-strategy-synthesizer] ──→ conviction에 global context 반영
[kr-market-environment] ──→ 외국인 수급 예측 반영
```

---

## 5. Module Design Summary

### 5.1 fed_stance_analyzer.py

| Item | Detail |
|------|--------|
| Input | fomc_tone (hawkish/neutral/dovish), dot_plot_direction (up/flat/down), qt_qe_status (qt/neutral/qe), fed_speaker_tone (-1~+1) |
| Output | stance_score (-100~+100), stance_label (very_hawkish/hawkish/neutral/dovish/very_dovish) |
| Key Logic | 4요소 가중 평균: fomc_tone(0.40) + dot_plot(0.25) + qt_qe(0.20) + speakers(0.15) = 1.00 |

**Stance Labels:**

| Score Range | Label | Description |
|-------------|-------|-------------|
| -100 ~ -60 | very_hawkish | 극단적 긴축 (QT 가속, 75bp+ 인상) |
| -60 ~ -20 | hawkish | 긴축 기조 (25-50bp 인상, QT 유지) |
| -20 ~ +20 | neutral | 중립/관망 (동결, 방향 탐색) |
| +20 ~ +60 | dovish | 완화 기조 (25-50bp 인하, QT 감속) |
| +60 ~ +100 | very_dovish | 극단적 완화 (QE 재개, 50bp+ 인하) |

### 5.2 rate_trend_classifier.py

| Item | Detail |
|------|--------|
| Input | current_ffr, ffr_12m_ago, last_change_bp, market_expectation (next meeting prob), yield_curve_2y10y |
| Output | rate_regime (5단계), rate_score (0~100), direction_confidence (0~1) |

**Rate Regimes:**

| Regime | Criteria | Score Range |
|--------|----------|-------------|
| aggressive_hike | last_change >= +50bp, 연속 인상 | 0~20 |
| gradual_hike | last_change = +25bp, 인상 기조 | 20~40 |
| hold | 동결 유지 3개월+, 방향 불확실 | 40~60 |
| gradual_cut | last_change = -25bp, 인하 기조 | 60~80 |
| aggressive_cut | last_change >= -50bp, 연속 인하 | 80~100 |

### 5.3 liquidity_tracker.py

| Item | Detail |
|------|--------|
| Input | fed_bs_change_pct (MoM), m2_growth_yoy, dxy_trend (rising/flat/falling), rrp_change |
| Output | liquidity_score (0~100), liquidity_trend (contracting/stable/expanding) |
| Key Logic | 4요소 가중: fed_bs(0.30) + m2(0.30) + dxy(0.25) + rrp(0.15) = 1.00 |

**Liquidity Levels:**

| Score Range | Label | Description |
|-------------|-------|-------------|
| 0~20 | severe_contraction | 급격한 유동성 축소 |
| 20~40 | contraction | 유동성 축소 |
| 40~60 | stable | 안정/중립 |
| 60~80 | expansion | 유동성 확대 |
| 80~100 | severe_expansion | 급격한 유동성 확대 |

### 5.4 kr_transmission_scorer.py

| Item | Detail |
|------|--------|
| Input | us_regime_score, kr_us_rate_diff, usdkrw_trend, foreign_flow_momentum, bok_rate, bok_direction |
| Output | kr_impact_score (0~100), impact_label (negative/neutral/positive), overlay (+-15), favored_sectors[], unfavored_sectors[] |
| Key Logic | 5채널 가중: 금리차(0.30) + 환율(0.25) + 위험선호(0.20) + 섹터회전(0.15) + BOK후행(0.10) = 1.00 |

**Transmission Channels:**

| Channel | Weight | Logic |
|---------|--------|-------|
| interest_rate_diff | 0.30 | KR > US → 자본유입↑, KR < US → 자본유출↑ |
| fx_impact | 0.25 | 달러약세(US완화) → 원화강세 → 외국인유입 |
| risk_appetite | 0.20 | US완화 → Risk-on → EM유입 → KOSPI↑ |
| sector_rotation | 0.15 | US인하 → 성장주↑/가치주↓, US인상 → 반대 |
| bok_policy_lag | 0.10 | Fed 방향 → BOK 6-12개월 후행 |

### 5.5 regime_synthesizer.py

| Item | Detail |
|------|--------|
| Input | stance_score, rate_score, liquidity_score, kr_transmission inputs |
| Output | complete regime report (us_regime_score, regime_label, kr_impact, overlay, sector_overlays{}) |
| Key Logic | 3요소 가중 → regime_score, 전이 계산 → overlay, 14섹터별 overlay 생성 |

---

## 6. Reference Data

### 6.1 fed_policy_database.py

```python
# FOMC 스케줄 (연 8회)
FOMC_SCHEDULE_2026 = [...]

# 역사적 금리 데이터 (최근 2년)
FFR_HISTORY = {
    '2024-01': 5.50, '2024-06': 5.50, '2024-09': 5.25,  # 첫 인하
    '2024-12': 4.75, '2025-03': 4.50, '2025-06': 4.25,
    '2025-09': 4.00, '2025-12': 3.75, '2026-01': 3.50, ...
}

# Fed 기조 키워드
HAWKISH_KEYWORDS = ['inflation', 'restrictive', 'vigilant', 'tighten', ...]
DOVISH_KEYWORDS = ['support', 'accommodate', 'easing', 'downside risk', ...]
```

### 6.2 sector_sensitivity_map.py

```python
# 14개 한국 섹터별 US 통화정책 민감도
SECTOR_SENSITIVITY = {
    'semiconductor': 1.3,
    'secondary_battery': 1.3,
    'bio': 1.2,
    'it': 1.2,
    'auto': 1.1,
    'shipbuilding': 1.0,
    'steel': 0.9,
    'chemical': 0.9,
    'construction': 0.8,
    'finance': 0.7,
    'insurance': 0.6,
    'retail': 0.5,
    'defense': 0.4,
    'food': 0.3,
}

# 민감도 근거
SENSITIVITY_RATIONALE = {
    'semiconductor': '수출 비중 높음 + 글로벌 수요 민감 + 성장주 특성',
    'food': '내수 방어주, 통화정책 영향 극히 제한적',
    ...
}
```

---

## 7. File Summary

### 7.1 New Files (12)

| # | Path | Type | Description |
|---|------|------|-------------|
| 1 | `skills/us-monetary-regime/SKILL.md` | Doc | 스킬 사용법 |
| 2 | `skills/us-monetary-regime/references/fed_policy_database.py` | Ref | FOMC/금리/키워드 DB |
| 3 | `skills/us-monetary-regime/references/sector_sensitivity_map.py` | Ref | 14섹터 민감도 |
| 4 | `skills/us-monetary-regime/scripts/fed_stance_analyzer.py` | Script | Fed 기조 분석 |
| 5 | `skills/us-monetary-regime/scripts/rate_trend_classifier.py` | Script | 금리 트렌드 분류 |
| 6 | `skills/us-monetary-regime/scripts/liquidity_tracker.py` | Script | 유동성 추적 |
| 7 | `skills/us-monetary-regime/scripts/kr_transmission_scorer.py` | Script | 한국 전이 스코어 |
| 8 | `skills/us-monetary-regime/scripts/regime_synthesizer.py` | Script | 종합 레짐 판정 |
| 9 | `skills/us-monetary-regime/scripts/tests/test_us_monetary_regime.py` | Test | 전체 테스트 |
| 10 | `skills/us-monetary-regime/scripts/tests/__init__.py` | Init | 테스트 패키지 |
| 11 | `skills/us-monetary-regime/scripts/__init__.py` | Init | 스크립트 패키지 |
| 12 | `skills/us-monetary-regime/references/__init__.py` | Init | 참조 패키지 |

### 7.2 Modified Files (3)

| # | Path | Change | Description |
|---|------|--------|-------------|
| 1 | `skills/kr-stock-analysis/scripts/comprehensive_scorer.py` | Patch | 오버레이 적용 함수 추가 (기존 로직 불변) |
| 2 | `skills/kr-strategy-synthesizer/scripts/conviction_scorer.py` | Patch | global_monetary_context optional 파라미터 추가 |
| 3 | `skills/kr-market-environment/scripts/(해당)` | Patch | 외국인 수급 예측에 US 유동성 optional 반영 |

### 7.3 Totals

| Metric | Count |
|--------|-------|
| New files | 12 |
| Modified files | 3 |
| Total files | 15 |
| New functions | ~15 |
| New constants | ~60 |
| Expected tests | ~100 |

---

## 8. Integration Strategy (B방식 Overlay)

### 8.1 Why Overlay (Not Direct Weight)

| Criteria | A: Direct Weight | B: Overlay (Selected) |
|----------|:----------------:|:---------------------:|
| 기존 점수 체계 보존 | X (5요소→6요소) | O (5요소 불변) |
| 섹터별 차등 반영 | X (모든 종목 동일%) | O (14섹터 민감도) |
| 기존 테스트 영향 | 전체 수정 필요 | 무영향 |
| 수출주/내수주 구분 | 불가 | 자동 차등 |
| 구현 복잡도 | 낮음 | 중간 |

### 8.2 Overlay 적용 규칙

```python
# 1. 기존 base_score는 절대 변경하지 않음
base_score = calc_comprehensive_score(F, T, S, V, G)  # 그대로

# 2. overlay는 Optional 파라미터로 추가
def apply_monetary_overlay(base_score, overlay, sector='default'):
    sensitivity = SECTOR_SENSITIVITY.get(sector, 0.7)
    adjusted = base_score + (overlay * sensitivity)
    return max(0, min(100, adjusted))

# 3. overlay 없이도 기존과 동일하게 동작
# apply_monetary_overlay(36.4, overlay=None) → 36.4
```

### 8.3 기존 스킬 호출 흐름 변경

```
[Before]
kr-stock-analysis → comprehensive_score → final

[After]
us-monetary-regime → regime_score + overlay
        ↓
kr-stock-analysis → comprehensive_score (불변) → + overlay → final
```

---

## 9. Data Sources

| Data | Source | Method | Freshness |
|------|--------|--------|-----------|
| FFR (Federal Funds Rate) | FRED / WebSearch | 정적 DB + 최신 WebSearch | 월간 |
| FOMC 성명서 톤 | Fed 홈페이지 / 뉴스 | WebSearch | 회의 후 즉시 |
| Fed 위원 발언 | 뉴스 | WebSearch | 주간 |
| 점도표 (Dot Plot) | Fed SEP | WebSearch (분기별) | 분기 |
| Fed 대차대조표 | FRED | WebSearch | 주간 |
| M2 통화량 | FRED | WebSearch | 월간 |
| DXY (달러인덱스) | 시장데이터 | WebSearch | 일간 |
| 한미 금리차 | BOK + Fed | 정적 DB + WebSearch | 월간 |
| USD/KRW | 시장데이터 | WebSearch | 일간 |
| 외국인 순매수 | PyKRX | kr-institutional-flow 연동 | 일간 |

---

## 10. Success Criteria

### 10.1 Definition of Done

- [ ] 5개 핵심 스크립트 구현 (fed_stance, rate_trend, liquidity, kr_transmission, regime_synthesizer)
- [ ] 2개 참조 데이터 파일 구현
- [ ] 기존 3개 스킬 오버레이 패치 (기존 테스트 전체 통과)
- [ ] 단위 테스트 100개+ 작성 및 통과
- [ ] SKILL.md 작성

### 10.2 Quality Criteria

- [ ] 가중치 합계 검증: 4개 합계 전부 1.00 (stance/rate_not_applicable/liquidity/transmission)
- [ ] 오버레이 범위: +-15 이내
- [ ] 기존 1,814 테스트 전체 통과 (무파괴)
- [ ] Match Rate >= 90% (PDCA Check)

---

## 11. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| WebSearch 데이터 불완전 | High | Medium | 정적 DB(FFR_HISTORY) 폴백, 최악 시 수동 입력 |
| 기존 스킬 테스트 파괴 | High | Low | overlay=Optional, 기본값 None → 기존 동작 불변 |
| Fed 정책 급변 (긴급 회의) | Medium | Low | 분석 시점 기준 최신 WebSearch 반영 |
| 섹터 민감도 부정확 | Medium | Medium | 역사적 상관관계 기반 + 향후 백테스트 검증 |
| 한국 전이 시차 | Medium | High | short_term(1-3m)/medium_term(6-12m) 분리 분석 |

---

## 12. Implementation Order

| Step | Task | Dependencies | Files |
|------|------|-------------|-------|
| 1 | Reference 데이터 작성 | None | fed_policy_database.py, sector_sensitivity_map.py |
| 2 | fed_stance_analyzer 구현 | Step 1 | fed_stance_analyzer.py |
| 3 | rate_trend_classifier 구현 | Step 1 | rate_trend_classifier.py |
| 4 | liquidity_tracker 구현 | Step 1 | liquidity_tracker.py |
| 5 | kr_transmission_scorer 구현 | Step 2,3,4 | kr_transmission_scorer.py |
| 6 | regime_synthesizer 구현 | Step 2,3,4,5 | regime_synthesizer.py |
| 7 | 기존 스킬 오버레이 패치 | Step 6 | comprehensive_scorer.py, conviction_scorer.py |
| 8 | 테스트 작성 및 실행 | Step 1-7 | test_us_monetary_regime.py |

---

## 13. Next Steps

1. [ ] Design 문서 작성 (`us-monetary-regime.design.md`)
2. [ ] 함수 시그니처, 상수 정의, 테스트 케이스 상세화
3. [ ] 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-05 | Initial draft - B방식 오버레이 확정, 5모듈+2참조+3패치 구조 | Claude |
