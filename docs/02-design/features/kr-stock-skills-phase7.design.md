# Phase 7: 배당 & 세제 최적화 스킬 설계

> **Feature**: kr-stock-skills-phase7
> **Phase**: Design
> **Created**: 2026-03-03
> **Based on**: kr-stock-skills.plan.md (Section 3.7)
> **Depends on**: Phase 1 (KRClient), Phase 4 (kr-value-dividend, kr-dividend-pullback), Phase 6 (kr-portfolio-manager KR_TAX_MODEL)

---

## 1. 범위 요약

Phase 7은 **배당 투자 운용 절차, 배당 안전성 모니터링, 한국 세제 최적화**를 다루는 3개 스킬을 구현한다.

| # | US 원본 | KR 스킬명 | 복잡도 | 핵심 변경 |
|:-:|---------|-----------|:------:|-----------|
| 33 | kanchi-dividend-sop | **kr-dividend-sop** | Medium | 한국 배당 패턴(연 1회), DART 배당 이력, 한국 배당락일/기준일 체계 |
| 34 | kanchi-dividend-review-monitor | **kr-dividend-monitor** | Medium | DART 공시 기반 감배/무배 감지, 한국 기업 지배구조 트리거 |
| 35 | kanchi-dividend-us-tax-accounting | **kr-dividend-tax** | High | **한국 세제로 완전 재작성**: ISA/연금저축/IRP/금융소득종합과세/배당세/양도세 |

**총계**: High 1 + Medium 2 = 3개 스킬

---

## 2. 스킬 간 관계 아키텍처

```
Phase 4 (스크리닝)                    Phase 7 (운용/모니터링/세제)
─────────────────                    ─────────────────────────────
kr-value-dividend ───────┐
kr-dividend-pullback ────┤
                         │
                         ▼
                  kr-dividend-sop  (SOP: 5단계 배당 투자 절차)
                         │
                         ├──→ kr-dividend-monitor (감배/무배/지배구조 모니터링)
                         │         │
                         │         ▼
                         │    DART 공시 분석
                         │         │
                         │    OK / WARN / REVIEW
                         │
                         └──→ kr-dividend-tax (세제 최적화 엔진)
                                   │
                                   ▼
                              계좌 배치 전략
                              ISA > 연금저축 > IRP > 일반계좌
                                   │
                                   ▼
                         Phase 6: kr-portfolio-manager (리밸런싱)
```

### 데이터 흐름

```
[DART API] ─→ 배당 공시/재무제표/배당 이력
     │
     ├─→ kr-dividend-sop: 스크리닝 → 진입 → 보유 → 수령 → 매도 판단
     │
     ├─→ kr-dividend-monitor: 공시 모니터링 → 트리거 감지 → 상태 판정
     │
     └─→ kr-dividend-tax: 배당금 세금 계산 → 계좌 배치 → 절세 전략

[PyKRX] ─→ OHLCV/배당수익률/PER/PBR
[KR_TAX_MODEL] ─→ Phase 6에서 정의한 세율 상수 재활용
```

---

## 3. 스킬별 상세 설계

---

### 3.1 Skill 33: kr-dividend-sop (Medium)

**US 원본**: kanchi-dividend-sop (かんち式 배당투자 SOP)
**핵심**: 배당주 투자의 5단계 표준 운용 절차

#### 3.1.1 5-Step SOP 프레임워크

```python
# ─── SOP 단계 정의 ───

SOP_STEPS = [
    'SCREEN',      # Step 1: 스크리닝 (종목 발굴)
    'ENTRY',       # Step 2: 진입 (매수 판단)
    'HOLD',        # Step 3: 보유 (모니터링)
    'COLLECT',     # Step 4: 수령 (배당금 수령)
    'EXIT',        # Step 5: 매도 (EXIT 판단)
]
```

#### 3.1.2 Step 1: 스크리닝 기준

```python
# ─── 배당주 스크리닝 필수 조건 ───

SCREENING_CRITERIA = {
    # 배당 품질
    'min_yield': 2.5,                # 최소 배당수익률 2.5%
    'min_consecutive_years': 3,      # 최소 3년 연속 배당
    'no_cut_years': 3,               # 최근 3년 감배 없음
    'max_payout_ratio': 0.80,        # 배당성향 80% 이하

    # 재무 건전성
    'min_market_cap': 500_000_000_000,   # 시가총액 5,000억원 이상
    'max_debt_ratio': 1.50,              # 부채비율 150% 이하
    'min_current_ratio': 1.0,            # 유동비율 1.0 이상
    'min_roe': 0.05,                     # ROE 5% 이상

    # 성장성
    'revenue_trend_years': 3,        # 매출 3년 양의 추세
    'eps_trend_years': 3,            # EPS 3년 양의 추세
}
```

#### 3.1.3 Step 2: 진입 판단 매트릭스

```python
# ─── 진입 점수 (0-100) ───

ENTRY_SCORING = {
    'valuation': {                   # 밸류에이션 (40점)
        'weight': 0.40,
        'per_sweet_spot': (5, 12),   # PER 5~12배 = 만점
        'pbr_sweet_spot': (0.3, 1.0),# PBR 0.3~1.0배 = 만점
    },
    'dividend_quality': {            # 배당 품질 (30점)
        'weight': 0.30,
        'yield_excellent': 4.0,      # ≥4.0%: 만점
        'yield_good': 3.0,           # ≥3.0%: 80%
        'growth_bonus': 0.10,        # 배당 성장 기업 가산 10%
    },
    'financial_health': {            # 재무 건전성 (20점)
        'weight': 0.20,
        'roe_excellent': 0.15,       # ≥15%: 만점
        'roe_good': 0.10,            # ≥10%: 80%
    },
    'timing': {                      # 타이밍 (10점)
        'weight': 0.10,
        'rsi_oversold': 40,          # RSI ≤ 40: 만점
        'near_ex_date_penalty': True, # 배당락일 30일 이내: 감점
    },
}

# 진입 등급
ENTRY_GRADES = {
    'STRONG_BUY': 85,    # ≥85점
    'BUY': 70,           # 70-84점
    'HOLD': 55,          # 55-69점
    'PASS': 0,           # <55점
}
```

#### 3.1.4 Step 3: 보유 모니터링 체크리스트

```python
# ─── 보유 기간 모니터링 항목 ───

HOLD_CHECKLIST = [
    'dividend_maintained',      # 배당 유지 여부 (감배 없음)
    'payout_ratio_safe',        # 배당성향 80% 이하 유지
    'debt_ratio_safe',          # 부채비율 150% 이하 유지
    'earnings_positive',        # 영업이익 흑자 유지
    'no_governance_issue',      # 지배구조 이슈 없음
    'market_cap_maintained',    # 시가총액 급락 없음 (-30% 이하)
]

# 보유 상태
HOLD_STATUS = ['HEALTHY', 'CAUTION', 'WARNING', 'EXIT_SIGNAL']
```

#### 3.1.5 Step 4: 배당 수령 관리

```python
# ─── 한국 배당 캘린더 ───

KR_DIVIDEND_CALENDAR = {
    'record_date_major': '12-31',        # 12월 결산 (대부분)
    'record_date_mid': '06-30',          # 6월 중간배당
    'ex_date_offset': -2,                # 기준일 2영업일 전 = 배당락일
    'payment_lag_days': (30, 60),        # 배당 지급: 기준일 후 30~60일
    'interim_dividend_months': [3, 6, 9],# 분기배당 기업 (소수)
}

# 배당락일 전략
EX_DATE_STRATEGY = {
    'hold_through': True,              # 기본: 배당락일 보유 유지
    'min_holding_days_before_ex': 2,   # 배당락일 최소 2영업일 전 보유
    'reinvest_after_payment': True,    # 배당금 재투자 권장
}
```

#### 3.1.6 Step 5: EXIT 판단 기준

```python
# ─── 매도 트리거 ───

EXIT_TRIGGERS = {
    'dividend_cut': {              # 감배 발생
        'severity': 'HIGH',
        'action': 'REVIEW',        # 즉시 검토 (자동 매도 아님)
    },
    'dividend_suspension': {       # 무배당 전환
        'severity': 'CRITICAL',
        'action': 'EXIT',          # 매도 권고
    },
    'payout_exceed': {             # 배당성향 초과
        'severity': 'MEDIUM',
        'threshold': 1.00,         # 100% 초과 = 위험
        'action': 'WARN',
    },
    'earnings_loss': {             # 영업적자 전환
        'severity': 'HIGH',
        'consecutive_quarters': 2, # 2분기 연속
        'action': 'REVIEW',
    },
    'debt_spike': {                # 부채비율 급등
        'severity': 'MEDIUM',
        'threshold': 2.00,         # 200% 초과
        'action': 'WARN',
    },
    'price_crash': {               # 주가 급락
        'severity': 'HIGH',
        'threshold': -0.30,        # -30% 하락 (가격제한폭 도달)
        'action': 'REVIEW',
    },
}
```

#### 3.1.7 파일 구조

```
skills/kr-dividend-sop/
├── SKILL.md                              # 스킬 매뉴얼
├── references/
│   └── kr_dividend_sop_guide.md          # 5-Step SOP 가이드
├── scripts/
│   ├── dividend_screener.py              # Step 1: 스크리닝 + Step 2: 진입 점수
│   ├── hold_monitor.py                   # Step 3: 보유 + Step 4: 수령 + Step 5: EXIT
│   ├── report_generator.py               # SOP 리포트 생성
│   └── tests/
│       └── test_dividend_sop.py          # 테스트
```

#### 3.1.8 함수 시그니처

```python
# dividend_screener.py
def screen_dividend_stocks(market, min_yield, min_years) -> list
def calc_entry_score(stock_data) -> dict      # {score, grade, components}
def check_screening_criteria(stock_data) -> dict  # {passed, failed_reasons}

# hold_monitor.py
def check_hold_status(holdings) -> list       # [{ticker, status, issues}]
def calc_ex_date(record_date) -> str          # 배당락일 계산
def check_exit_triggers(stock_data) -> dict   # {triggered, trigger_id, action}
def generate_dividend_calendar(holdings) -> list  # 배당 일정 캘린더
```

**예상 테스트**: ~35개

---

### 3.2 Skill 34: kr-dividend-monitor (Medium)

**US 원본**: kanchi-dividend-review-monitor
**핵심**: DART 공시 기반 배당 안전성 모니터링, 5가지 강제 리뷰 트리거

#### 3.2.1 5대 강제 리뷰 트리거 (T1-T5)

```python
# ─── 트리거 정의 ───

REVIEW_TRIGGERS = {
    'T1_DIVIDEND_CUT': {
        'name': '감배 감지',
        'source': 'DART',
        'severity': 'CRITICAL',
        'description': '전년 대비 주당배당금 감소',
        'detection': 'DART 배당 공시 or 사업보고서 배당 항목 비교',
        'action': 'REVIEW',
    },
    'T2_DIVIDEND_SUSPENSION': {
        'name': '무배당 전환',
        'source': 'DART',
        'severity': 'CRITICAL',
        'description': '배당 결의 없음 or 무배당 공시',
        'detection': 'DART 주주총회 결의 공시 모니터링',
        'action': 'EXIT_REVIEW',
    },
    'T3_EARNINGS_DETERIORATION': {
        'name': '실적 악화',
        'source': 'DART',
        'severity': 'HIGH',
        'description': '영업이익 적자 전환 or 50% 이상 급감',
        'detection': 'DART 분기보고서 손익계산서 비교',
        'thresholds': {
            'earnings_decline_pct': -0.50,    # 영업이익 50% 감소
            'operating_loss': True,            # 영업적자 전환
            'consecutive_decline': 2,          # 2분기 연속 감소
        },
    },
    'T4_PAYOUT_DANGER': {
        'name': '배당성향 위험',
        'source': 'calculated',
        'severity': 'HIGH',
        'description': '배당성향 100% 초과 (이익보다 많이 배당)',
        'threshold': 1.00,
        'action': 'WARN',
    },
    'T5_GOVERNANCE_ISSUE': {
        'name': '지배구조 이슈',
        'source': 'DART',
        'severity': 'MEDIUM',
        'description': '대주주 지분 대량 매각, 경영권 분쟁, 감사의견 비적정',
        'detection': 'DART 5% 대량보유 공시 + 감사보고서',
        'subtypes': [
            'major_shareholder_sale',    # 대주주 지분 5% 이상 매각
            'management_dispute',        # 경영권 분쟁 관련 공시
            'audit_qualified',           # 감사의견 한정/부적정/거절
            'delisting_risk',            # 관리종목/상장폐지 사유
        ],
    },
}
```

#### 3.2.2 모니터링 상태 머신

```python
# ─── 상태 정의 ───

MONITOR_STATES = ['OK', 'WARN', 'REVIEW', 'EXIT_REVIEW']

# ─── 상태 전이 규칙 ───
STATE_TRANSITIONS = {
    'OK': {
        'T3_minor': 'WARN',        # 실적 소폭 악화 → 주의
        'T4': 'WARN',             # 배당성향 위험 → 주의
        'T5': 'WARN',             # 지배구조 이슈 → 주의
        'T1': 'REVIEW',           # 감배 감지 → 리뷰
        'T3_major': 'REVIEW',     # 실적 대폭 악화 → 리뷰
        'T2': 'EXIT_REVIEW',      # 무배당 전환 → 매도 검토
    },
    'WARN': {
        'resolved': 'OK',         # 이슈 해소 → 정상
        'T1': 'REVIEW',           # 감배 추가 감지 → 리뷰
        'T3_major': 'REVIEW',     # 실적 급락 → 리뷰
        'T2': 'EXIT_REVIEW',      # 무배당 → 매도 검토
    },
    'REVIEW': {
        'resolved': 'OK',         # 감배 후 회복 → 정상
        'maintained': 'WARN',     # 현상 유지 → 주의
        'T2': 'EXIT_REVIEW',      # 무배당 전환 → 매도 검토
    },
    'EXIT_REVIEW': {
        'recovered': 'REVIEW',    # 배당 재개 공시 → 리뷰
        'confirmed': 'EXIT',      # 사용자 매도 확정
    },
}
```

#### 3.2.3 DART 공시 모니터링 대상

```python
# ─── DART 공시 유형별 모니터링 ───

DART_MONITORING = {
    'dividend_disclosure': {
        'kind': 'B',                    # 주요사항보고서
        'keywords': ['배당', '주당배당금', '현금배당'],
        'check_frequency': 'quarterly',
    },
    'earnings_report': {
        'kind': 'A',                    # 정기보고서
        'report_types': [
            '11013',  # 1분기보고서
            '11012',  # 반기보고서
            '11014',  # 3분기보고서
            '11011',  # 사업보고서
        ],
        'check_frequency': 'quarterly',
    },
    'major_shareholder': {
        'kind': 'D',                    # 지분공시
        'keywords': ['대량보유', '임원', '주요주주'],
        'check_frequency': 'weekly',
    },
    'audit_report': {
        'kind': 'A',                    # 사업보고서 내 감사보고서
        'keywords': ['감사의견', '적정', '한정', '부적정'],
        'check_frequency': 'annually',
    },
}
```

#### 3.2.4 배당 안전성 스코어 (0-100)

```python
# ─── 배당 안전성 점수 체계 ───

SAFETY_SCORING = {
    'payout_ratio': {               # 배당성향 (30점)
        'weight': 0.30,
        'safe': 0.50,               # ≤50%: 만점
        'caution': 0.70,            # 51-70%: 70%
        'warning': 0.90,            # 71-90%: 40%
        'danger': 1.00,             # >90%: 0점
    },
    'earnings_stability': {         # 실적 안정성 (25점)
        'weight': 0.25,
        'positive_years': 5,        # 5년 연속 흑자: 만점
        'min_years': 3,             # 3년 미만: 0점
    },
    'dividend_history': {           # 배당 이력 (25점)
        'weight': 0.25,
        'excellent_years': 10,      # 10년 연속: 만점
        'good_years': 5,            # 5년 연속: 70%
        'min_years': 3,             # 3년 미만: 0점
    },
    'debt_health': {                # 부채 건전성 (20점)
        'weight': 0.20,
        'safe_ratio': 0.80,         # 부채비율 ≤80%: 만점
        'caution_ratio': 1.20,      # 81-120%: 60%
        'warning_ratio': 1.50,      # 121-150%: 30%
        'danger_ratio': 2.00,       # >150%: 0점
    },
}

# 안전성 등급
SAFETY_GRADES = {
    'SAFE': 80,           # ≥80점: 안전
    'MODERATE': 60,       # 60-79점: 보통
    'AT_RISK': 40,        # 40-59점: 주의
    'DANGEROUS': 0,       # <40점: 위험
}
```

#### 3.2.5 파일 구조

```
skills/kr-dividend-monitor/
├── SKILL.md                                # 스킬 매뉴얼
├── references/
│   ├── kr_dividend_monitor_guide.md        # 모니터링 가이드
│   └── dart_disclosure_types.md            # DART 공시 유형 레퍼런스
├── scripts/
│   ├── trigger_detector.py                 # T1-T5 트리거 감지 엔진
│   ├── safety_scorer.py                    # 배당 안전성 스코어링
│   ├── report_generator.py                 # 모니터링 리포트 생성
│   └── tests/
│       └── test_dividend_monitor.py        # 테스트
```

#### 3.2.6 함수 시그니처

```python
# trigger_detector.py
def detect_dividend_cut(corp, current_dps, prev_dps) -> dict       # T1
def detect_dividend_suspension(corp, dart_disclosures) -> dict      # T2
def detect_earnings_deterioration(corp, financials) -> dict         # T3
def detect_payout_danger(earnings, dividend) -> dict                # T4
def detect_governance_issue(corp, dart_disclosures) -> dict         # T5
def run_all_triggers(corp, data) -> list                            # 전체 트리거 실행
def determine_state(current_state, triggers) -> str                 # 상태 전이

# safety_scorer.py
def calc_payout_score(payout_ratio) -> float
def calc_earnings_stability_score(earnings_history) -> float
def calc_dividend_history_score(dividend_years) -> float
def calc_debt_health_score(debt_ratio) -> float
def calc_safety_score(stock_data) -> dict          # {score, grade, components}
```

**예상 테스트**: ~40개

---

### 3.3 Skill 35: kr-dividend-tax (High)

**US 원본**: kanchi-dividend-us-tax-accounting
**핵심**: **한국 세제로 완전 재작성** - ISA/연금저축/IRP/금융소득종합과세/배당세/양도세

#### 3.3.1 한국 세제 상수 (Complete)

```python
# ═══════════════════════════════════════════════════════
# 한국 투자 세제 상수 (2026년 기준)
# ═══════════════════════════════════════════════════════

# ─── 1. 배당소득세 ───
DIVIDEND_TAX = {
    'rate': 0.154,                      # 15.4% (소득세 14% + 지방세 1.4%)
    'income_tax': 0.14,                 # 소득세 14%
    'local_tax': 0.014,                 # 지방소득세 1.4% (소득세의 10%)
    'withholding': True,                # 원천징수 여부
}

# ─── 2. 금융소득종합과세 ───
FINANCIAL_INCOME_TAX = {
    'threshold': 20_000_000,            # 2,000만원 (연간 금융소득 합계)
    'includes': [                        # 금융소득 포함 항목
        'interest',                      # 이자소득
        'dividend',                      # 배당소득
    ],
    'excludes': [                        # 제외 항목
        'isa_tax_free',                  # ISA 비과세 분
        'pension_deferred',              # 연금저축 과세이연 분
    ],
    # 2,000만원 초과 시 종합소득세율 적용
    'progressive_rates': [
        (12_000_000, 0.06),              # ~1,200만원: 6%
        (46_000_000, 0.15),              # ~4,600만원: 15%
        (88_000_000, 0.24),              # ~8,800만원: 24%
        (150_000_000, 0.35),             # ~1.5억원: 35%
        (300_000_000, 0.38),             # ~3억원: 38%
        (500_000_000, 0.40),             # ~5억원: 40%
        (1_000_000_000, 0.42),           # ~10억원: 42%
        (float('inf'), 0.45),            # 10억원 초과: 45%
    ],
    'local_tax_surcharge': 0.10,         # 지방소득세 = 소득세의 10%
}

# ─── 3. 양도소득세 (주식) ───
CAPITAL_GAINS_TAX = {
    # 대주주 기준
    'major_shareholder_threshold': 1_000_000_000,  # 10억원
    'major_shareholder_rate_long': 0.22,   # 1년 이상 보유: 22% (지방세 포함)
    'major_shareholder_rate_short': 0.33,  # 1년 미만 보유: 33% (지방세 포함)
    'sme_rate': 0.11,                      # 중소기업 대주주: 11%

    # 소액주주 (비상장 or 금투세 시행 시)
    'small_investor_rate': 0.22,           # 22% (금투세)
    'small_investor_exempt': 50_000_000,   # 5,000만원 기본공제

    # 해외주식
    'foreign_stock_rate': 0.22,            # 22%
    'foreign_stock_exempt': 2_500_000,     # 250만원 기본공제
}

# ─── 4. 증권거래세 ───
TRANSACTION_TAX = {
    'kospi': 0.0023,                     # 0.23%
    'kosdaq': 0.0023,                    # 0.23%
    'konex': 0.0010,                     # 0.10%
    'k_otc': 0.0023,                     # 0.23%
    'seller_only': True,                 # 매도 시에만 부과
}

# ─── 5. ISA (개인종합자산관리계좌) ───
ISA_ACCOUNT = {
    'tax_free_limit': 2_000_000,         # 비과세 200만원
    'tax_free_limit_low_income': 4_000_000,  # 서민형 400만원
    'excess_tax_rate': 0.099,            # 초과분 9.9% 분리과세
    'annual_contribution_limit': 20_000_000,  # 연간 납입한도 2,000만원
    'mandatory_period_years': 3,          # 의무가입기간 3년
    'eligible_products': [
        'stocks',                         # 국내 상장주식
        'domestic_funds',                 # 국내 펀드
        'etf',                           # ETF
        'elw',                           # ELW
        'rp',                            # RP
    ],
}

# ─── 6. 연금저축 ───
PENSION_SAVINGS = {
    'annual_contribution_limit': 18_000_000,  # 연간 납입한도 1,800만원
    'tax_deduction_limit': 6_000_000,    # 세액공제 한도 600만원
    'deduction_rate_under_5500': 0.165,  # 총급여 5,500만원 이하: 16.5%
    'deduction_rate_over_5500': 0.132,   # 총급여 5,500만원 초과: 13.2%
    'withdrawal_tax_before_55': 0.165,   # 55세 미만 중도인출: 16.5% 기타소득세
    'withdrawal_tax_after_55': {         # 55세 이후 연금 수령
        'under_1200': 0.055,             # 연 1,200만원 이하: 5.5%
        'over_1200_70': 0.055,           # 70세 이하: 5.5%
        'over_1200_80': 0.044,           # 80세 이하: 4.4%
        'over_1200_90': 0.033,           # 80세 초과: 3.3%
    },
    'eligible_products': [
        'pension_fund',                   # 연금펀드
        'pension_etf',                    # 연금 ETF
        'pension_trust',                  # 연금신탁
    ],
}

# ─── 7. IRP (개인형 퇴직연금) ───
IRP_ACCOUNT = {
    'annual_contribution_limit': 18_000_000,   # 연간 납입한도 1,800만원
    'combined_limit_with_pension': 18_000_000,  # 연금저축 + IRP 합산 1,800만원
    'tax_deduction_limit': 9_000_000,          # 세액공제 한도 900만원 (연금저축 600 + IRP 300)
    'deduction_rate_under_5500': 0.165,
    'deduction_rate_over_5500': 0.132,
    'mandatory_products': ['safe_assets_30'],   # 위험자산 70% 한도
    'safe_asset_ratio': 0.30,                  # 안전자산 30% 의무
}
```

#### 3.3.2 계좌 배치 최적화 (Account Location Strategy)

```python
# ─── 계좌 우선순위 ───

ACCOUNT_PRIORITY = [
    {
        'account': 'ISA',
        'priority': 1,
        'reason': '비과세 200만원 + 초과분 9.9%',
        'best_for': ['high_yield_stocks', 'etf'],
        'tax_benefit': 'tax_free_first',
    },
    {
        'account': 'PENSION_SAVINGS',
        'priority': 2,
        'reason': '세액공제 16.5%/13.2% + 과세이연',
        'best_for': ['long_term_growth', 'pension_etf'],
        'tax_benefit': 'tax_deduction',
    },
    {
        'account': 'IRP',
        'priority': 3,
        'reason': '추가 세액공제 300만원 + 과세이연',
        'best_for': ['safe_assets', 'bond_etf'],
        'tax_benefit': 'tax_deduction',
        'constraint': 'safe_asset_30pct',
    },
    {
        'account': 'GENERAL',
        'priority': 4,
        'reason': '제한 없음, 15.4% 원천징수',
        'best_for': ['trading', 'all_products'],
        'tax_benefit': 'none',
    },
]

# ─── 계좌 배치 규칙 ───

ALLOCATION_RULES = {
    'high_yield_first_to_isa': True,             # 고배당주 → ISA 우선
    'growth_stocks_to_pension': True,             # 성장주 → 연금저축 (과세이연)
    'bond_etf_to_irp': True,                     # 채권 ETF → IRP (안전자산 의무)
    'trading_to_general': True,                   # 매매 빈도 높은 → 일반계좌
    'threshold_management': True,                  # 금융소득 2,000만원 관리
}
```

#### 3.3.3 세금 계산 엔진

```python
# ─── 세금 계산 함수 시그니처 ───

# tax_calculator.py
def calc_dividend_tax(gross_dividend, account_type='GENERAL') -> dict
    # Returns: {gross, tax, net, effective_rate, account_type}

def calc_financial_income_tax(total_interest, total_dividend, other_income=0) -> dict
    # Returns: {total_financial, threshold_exceeded, additional_tax, effective_rate}

def calc_capital_gains_tax(gains, holding_period, is_major_shareholder, is_sme=False) -> dict
    # Returns: {gross_gain, exempt, taxable, tax, effective_rate}

def calc_transaction_tax(sell_amount, market='kospi') -> dict
    # Returns: {amount, tax, market}

def calc_isa_tax(total_income, is_low_income=False) -> dict
    # Returns: {tax_free, taxable, tax, effective_rate}

def calc_pension_deduction(contribution, salary) -> dict
    # Returns: {contribution, deduction_limit, deduction_rate, tax_saved}

def calc_total_tax_burden(portfolio) -> dict
    # Returns: {dividend_tax, transaction_tax, gains_tax, total_tax, optimization_tips}
```

#### 3.3.4 절세 전략 엔진

```python
# ─── 절세 전략 ───

TAX_OPTIMIZATION_STRATEGIES = [
    {
        'id': 'ISA_FIRST',
        'name': 'ISA 우선 활용',
        'description': '고배당주를 ISA에 우선 배치하여 200만원 비과세 혜택 극대화',
        'max_benefit': 308_000,           # 200만 × 15.4% = 30.8만원 절세
    },
    {
        'id': 'PENSION_DEDUCTION',
        'name': '연금저축 세액공제',
        'description': '연금저축 600만원 납입으로 최대 99만원 세액공제',
        'max_benefit': 990_000,           # 600만 × 16.5% = 99만원
    },
    {
        'id': 'IRP_EXTRA_DEDUCTION',
        'name': 'IRP 추가 공제',
        'description': 'IRP에 추가 300만원 납입으로 49.5만원 추가 공제',
        'max_benefit': 495_000,           # 300만 × 16.5% = 49.5만원
    },
    {
        'id': 'INCOME_THRESHOLD_MGMT',
        'name': '금융소득 2,000만원 관리',
        'description': '금융소득종합과세 회피를 위해 배당/이자 수입 2,000만원 이하 유지',
        'action': 'split_across_family',  # 가족 명의 분산 고려
    },
    {
        'id': 'LOSS_HARVESTING',
        'name': '손실 매도 (Tax-Loss Harvesting)',
        'description': '손실 종목 매도로 양도소득과 상계',
        'applicable': 'major_shareholder_or_financial_tax',  # 양도세 과세 대상만
    },
    {
        'id': 'HOLDING_PERIOD',
        'name': '보유기간 관리',
        'description': '대주주 양도세 1년 이상 보유 시 22% (미만 33%) → 장기보유 유리',
        'benefit': '11%p 세율 차이',
    },
]

# 세제 비교표 (계좌별)
ACCOUNT_TAX_COMPARISON = {
    'GENERAL': {
        'dividend_tax': 0.154,
        'capital_gains': 'major_shareholder_only',
        'transaction_tax': 0.0023,
        'deduction': 0,
    },
    'ISA': {
        'dividend_tax': 0,              # 200만원까지 비과세
        'excess_tax': 0.099,            # 초과분 9.9%
        'capital_gains': 'exempt',      # 비과세
        'transaction_tax': 0.0023,      # 거래세는 부과
        'deduction': 0,
    },
    'PENSION_SAVINGS': {
        'dividend_tax': 'deferred',     # 과세이연
        'capital_gains': 'deferred',    # 과세이연
        'transaction_tax': 0,           # 면제
        'deduction': 0.165,             # 16.5% 세액공제
        'withdrawal_tax': 0.055,        # 55세 이후 연금수령 시
    },
    'IRP': {
        'dividend_tax': 'deferred',     # 과세이연
        'capital_gains': 'deferred',    # 과세이연
        'transaction_tax': 0,           # 면제
        'deduction': 0.165,             # 16.5% 세액공제
        'withdrawal_tax': 0.055,        # 55세 이후 연금수령 시
        'constraint': 'safe_30pct',     # 안전자산 30%
    },
}
```

#### 3.3.5 파일 구조

```
skills/kr-dividend-tax/
├── SKILL.md                               # 스킬 매뉴얼
├── references/
│   ├── kr_tax_code_2026.md                # 2026년 한국 세제 코드
│   └── account_comparison_guide.md        # 계좌 유형별 비교 가이드
├── scripts/
│   ├── tax_calculator.py                  # 세금 계산 엔진
│   ├── account_optimizer.py               # 계좌 배치 최적화
│   ├── report_generator.py                # 세금 리포트 생성
│   └── tests/
│       └── test_dividend_tax.py           # 테스트
```

#### 3.3.6 함수 시그니처

```python
# tax_calculator.py (위 3.3.3에서 정의)
def calc_dividend_tax(gross_dividend, account_type) -> dict
def calc_financial_income_tax(total_interest, total_dividend, other_income) -> dict
def calc_capital_gains_tax(gains, holding_period, is_major_shareholder, is_sme) -> dict
def calc_transaction_tax(sell_amount, market) -> dict
def calc_isa_tax(total_income, is_low_income) -> dict
def calc_pension_deduction(contribution, salary) -> dict
def calc_total_tax_burden(portfolio) -> dict

# account_optimizer.py
def recommend_account_allocation(holdings) -> dict
def calc_account_benefit(holding, account_type) -> dict
def optimize_threshold_management(total_financial_income) -> dict
def generate_tax_optimization_tips(portfolio) -> list
```

**예상 테스트**: ~50개

---

## 4. 상수 총정리

### 4.1 전체 상수 카운트

| 스킬 | 상수 그룹 | 개수 |
|------|-----------|:----:|
| kr-dividend-sop | SOP_STEPS(5) + SCREENING(10) + ENTRY(4+4) + HOLD(6+4) + CALENDAR(5) + EXIT(6) | 44 |
| kr-dividend-monitor | TRIGGERS(5) + STATES(4) + TRANSITIONS(8) + DART(4) + SAFETY(4+4) | 29 |
| kr-dividend-tax | DIVIDEND(4) + FINANCIAL(3+8) + GAINS(7) + TRANSACTION(5) + ISA(6) + PENSION(8) + IRP(6) + ACCOUNTS(4) + STRATEGIES(6) + COMPARISON(4) | 61 |
| **합계** | | **134** |

### 4.2 Phase 6 KR_TAX_MODEL 재활용

Phase 6 `kr-portfolio-manager`의 `KR_TAX_MODEL`과의 일관성:

| Phase 6 상수 | Phase 7 상수 | 관계 |
|------|------|------|
| `dividend_tax: 0.154` | `DIVIDEND_TAX['rate']: 0.154` | 동일 |
| `financial_income_threshold: 20_000_000` | `FINANCIAL_INCOME_TAX['threshold']: 20_000_000` | 동일 |
| `capital_gains_tax: 0.22` | `CAPITAL_GAINS_TAX['major_shareholder_rate_long']: 0.22` | 동일 |
| `capital_gains_threshold: 1_000_000_000` | `CAPITAL_GAINS_TAX['major_shareholder_threshold']: 1_000_000_000` | 동일 |
| `transaction_tax: 0.0023` | `TRANSACTION_TAX['kospi']: 0.0023` | 동일 |
| `isa_tax_free: 2_000_000` | `ISA_ACCOUNT['tax_free_limit']: 2_000_000` | 동일 |

**Phase 7은 Phase 6의 요약 모델을 상세 확장한 것** (기본값은 100% 일치)

---

## 5. 파일 인벤토리

### 5.1 전체 파일 목록

| # | 경로 | 유형 |
|:-:|------|:----:|
| 1 | kr-dividend-sop/SKILL.md | doc |
| 2 | kr-dividend-sop/references/kr_dividend_sop_guide.md | ref |
| 3 | kr-dividend-sop/scripts/dividend_screener.py | code |
| 4 | kr-dividend-sop/scripts/hold_monitor.py | code |
| 5 | kr-dividend-sop/scripts/report_generator.py | code |
| 6 | kr-dividend-sop/scripts/tests/test_dividend_sop.py | test |
| 7 | kr-dividend-monitor/SKILL.md | doc |
| 8 | kr-dividend-monitor/references/kr_dividend_monitor_guide.md | ref |
| 9 | kr-dividend-monitor/references/dart_disclosure_types.md | ref |
| 10 | kr-dividend-monitor/scripts/trigger_detector.py | code |
| 11 | kr-dividend-monitor/scripts/safety_scorer.py | code |
| 12 | kr-dividend-monitor/scripts/report_generator.py | code |
| 13 | kr-dividend-monitor/scripts/tests/test_dividend_monitor.py | test |
| 14 | kr-dividend-tax/SKILL.md | doc |
| 15 | kr-dividend-tax/references/kr_tax_code_2026.md | ref |
| 16 | kr-dividend-tax/references/account_comparison_guide.md | ref |
| 17 | kr-dividend-tax/scripts/tax_calculator.py | code |
| 18 | kr-dividend-tax/scripts/account_optimizer.py | code |
| 19 | kr-dividend-tax/scripts/report_generator.py | code |
| 20 | kr-dividend-tax/scripts/tests/test_dividend_tax.py | test |

**총계**: 3 SKILL.md + 5 references + 9 scripts + 3 test files = **20 파일**

---

## 6. 구현 순서

```
Step 1 (Low→Medium): kr-dividend-sop
├── dividend_screener.py (Step 1-2: 스크리닝 + 진입)
├── hold_monitor.py (Step 3-5: 보유 + 수령 + EXIT)
├── report_generator.py
└── ~35 tests

Step 2 (Medium): kr-dividend-monitor
├── trigger_detector.py (T1-T5 + 상태 머신)
├── safety_scorer.py (안전성 스코어)
├── report_generator.py
└── ~40 tests

Step 3 (High): kr-dividend-tax
├── tax_calculator.py (7개 세금 계산 함수)
├── account_optimizer.py (계좌 배치 + 절세 전략)
├── report_generator.py
└── ~50 tests

Step 4: 통합 테스트
└── 전체 스킬 테스트 실행 (Phase 1-7 누적)
```

**예상 테스트 합계**: ~125개
**Phase 3-6 경험치 기반 실제 예상**: ~250개 (×2.0 보정)

---

## 7. Phase 4/6 연동 포인트

### 7.1 Phase 4 스크리닝 스킬 연동

| Phase 4 스킬 | Phase 7 연동 | 역할 |
|---|---|---|
| kr-value-dividend | kr-dividend-sop Step 1 | 스크리닝 기준 호환 (min_yield, PER, PBR) |
| kr-dividend-pullback | kr-dividend-sop Step 2 | RSI 타이밍 기준 공유 |

### 7.2 Phase 6 포트폴리오 연동

| Phase 6 스킬 | Phase 7 연동 | 역할 |
|---|---|---|
| kr-portfolio-manager | kr-dividend-tax | KR_TAX_MODEL 상수 일관성 |
| kr-portfolio-manager | kr-dividend-sop | 리밸런싱 시 배당 포지션 보호 |

### 7.3 DART API 연동

Phase 7은 **DART API를 가장 많이 활용하는 Phase**:

| 기능 | DART API | 스킬 |
|------|----------|------|
| 배당 이력 조회 | `dart.report(corp, '배당')` | kr-dividend-sop, kr-dividend-monitor |
| 재무제표 비교 | `dart.finstate(corp, year)` | kr-dividend-monitor (T3 실적 악화) |
| 공시 목록 | `dart.list(corp, kind)` | kr-dividend-monitor (T1/T2/T5) |
| 대량보유 공시 | `dart.major_shareholders(corp)` | kr-dividend-monitor (T5 지배구조) |
| 기업 정보 | `dart.company(corp)` | kr-dividend-sop (기업 기본 정보) |

---

## 8. 한국 시장 특화 요소

### 8.1 한국 배당 문화 (US 대비)

| 항목 | 한국 | US |
|------|------|------|
| 배당 주기 | **연 1회** (12월 결산 집중) | 분기 배당 (3개월) |
| 평균 배당수익률 | 2~3% | 1.5~2% |
| 배당성향 | 20~30% (낮음) | 35~50% (높음) |
| 배당 성장 기업 | 소수 (삼성전자, KB금융 등) | 배당귀족 다수 |
| 중간배당 | 일부만 (삼성전자, SK텔레콤) | 대부분 분기 배당 |
| 배당락일 | 기준일 2영업일 전 | 기준일 1영업일 전 (T+1) |

### 8.2 한국 절세 계좌 (US IRA/401k 대비)

| 한국 | US | 유사점 | 차이점 |
|------|------|------|------|
| ISA | Roth IRA | 비과세 혜택 | 한도 200만원 vs $6,500 |
| 연금저축 | Traditional IRA | 세액공제 | 인출 시 과세 |
| IRP | 401(k) | 퇴직연금 | 안전자산 30% 의무 |
| 일반계좌 | Taxable Account | 동일 개념 | 세율 다름 |

---

## 9. 테스트 전략

### 9.1 주요 테스트 시나리오

**kr-dividend-sop (35 tests)**:
- 스크리닝 기준 필터 (pass/fail 각 조건)
- 진입 점수 계산 (경계값 테스트)
- 보유 상태 체크리스트 (HEALTHY→WARNING 전이)
- EXIT 트리거 감지 (6개 트리거별)
- 배당락일 계산 (영업일 계산)

**kr-dividend-monitor (40 tests)**:
- T1-T5 트리거 각각 (감지/미감지)
- 상태 전이 (OK→WARN→REVIEW→EXIT)
- 안전성 스코어 (경계값 4개 컴포넌트)
- DART 공시 유형 분류
- 복합 트리거 (다중 이슈 동시 감지)

**kr-dividend-tax (50 tests)**:
- 배당세 계산 (계좌별 4가지)
- 금융소득종합과세 (2,000만원 경계)
- 양도세 계산 (대주주/소액/해외)
- ISA 비과세 한도 (200만원/400만원)
- 연금저축 세액공제 (급여 구간별)
- IRP 안전자산 제약
- 계좌 배치 최적화 (최적 계좌 추천)
- 절세 전략 생성 (시나리오별)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-03 | Phase 7 배당 & 세제 최적화 스킬 초기 설계 |
