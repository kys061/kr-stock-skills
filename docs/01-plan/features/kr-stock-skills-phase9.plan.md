# Phase 9: 한국 시장 전용 신규 스킬 개발 계획

> **Summary**: US 스킬에 대응하지 않는 한국 시장 고유 스킬 5개 신규 개발
>
> **Project**: Korean Stock Skills
> **Version**: 9.0
> **Author**: Claude Code + User
> **Date**: 2026-03-04
> **Status**: Draft

---

## 1. Overview

### 1.1 목적

Phase 1-8에서 US 스킬 39개를 한국 시장으로 포팅 완료(40개 모듈, 1,402 테스트).
Phase 9는 **미국에는 없지만 한국 시장에서 필수적인 신규 스킬 5개**를 개발한다.

한국 시장은 투자자별 매매동향 실시간 공개, 신용거래 잔고 공개, 프로그램매매 구분,
공매도 잔고 공개 등 **미국보다 더 상세한 시장 미시구조 데이터**를 제공한다.
이 고유 데이터를 활용하는 전용 분석 스킬이 Phase 9의 핵심이다.

### 1.2 배경

| 항목 | 설명 |
|------|------|
| Phase 1-8 완료 | 39 스킬 + 1 공통 모듈 = 40 모듈, 1,402 테스트 |
| 연속 97% Match Rate | Phase 3-8 연속 6회 97%, Major Gap 0 |
| Phase 9 범위 | 마스터 플랜 섹션 3.9 "한국 시장 전용 신규 스킬" 5개 |
| 데이터 인프라 | Tier 1 (PyKRX+FDR+DART) 100% 활용 가능 |

### 1.3 관련 문서

- 마스터 플랜: `docs/01-plan/features/kr-stock-skills.plan.md` (섹션 3.9)
- Phase 8 완료 보고서: `docs/04-report/features/kr-stock-skills-phase8.report.md`
- 공통 모듈: `skills/_kr-common/`

---

## 2. Scope

### 2.1 In Scope

- [x] **kr-supply-demand-analyzer**: 시장 전체 수급 종합 분석 (시장 레벨 + 섹터 레벨)
- [x] **kr-short-sale-tracker**: 공매도 잔고/거래량 추적 및 숏커버 시그널 감지
- [x] **kr-credit-monitor**: 신용잔고 과열 모니터링 + 반대매매 리스크 평가
- [x] **kr-program-trade-analyzer**: 차익/비차익 프로그램 매매 분석 + 만기일 영향
- [x] **kr-dart-disclosure-monitor**: DART 공시 종합 모니터링 (M&A, 증자, 감배, 지분변동)
- [x] 통합 테스트: Phase 1-9 전체 44개 모듈 호환성 검증

### 2.2 Out of Scope

- Tier 2 (한투 API 실시간) 연동 - Tier 1 (PyKRX/DART) 기반으로 구현
- 실시간 알림/모니터링 데몬 - 분석 엔진만 구현
- GUI/웹 대시보드 - CLI 스킬으로 구현
- 자동 주문/체결 연동

---

## 3. 스킬 상세 설계

### 3.1 kr-supply-demand-analyzer (시장 수급 종합 분석)

> **기존과의 차별화**: kr-institutional-flow는 개별 종목의 4팩터 수급 분석.
> kr-supply-demand-analyzer는 **시장 전체** 수급 동학 + 섹터별 자금 흐름 + 유동성 지표.

| 항목 | 설명 |
|------|------|
| 복잡도 | High |
| 스크립트 수 | 4개 |
| 테스트 목표 | ~50개 |
| 데이터 소스 | PyKRX (투자자별 매매동향, 지수별 수급) |
| 핵심 차별점 | 시장 레벨 수급 + 섹터 레벨 자금 흐름 + 유동성 지표 |

**핵심 분석 컴포넌트**:

```
1. 시장 레벨 수급 (Market-Level Flow)
   - KOSPI/KOSDAQ 전체 순매수 추이 (외국인/기관/개인)
   - 순매수 연속일 추적 (3, 5, 10, 20일 연속)
   - 투자자별 매매 강도 (금액 대비 시총 비율)
   - 투자자 심리 지수 (3-투자자 합성)

2. 섹터별 자금 흐름 (Sector Flow Mapping)
   - 14개 한국 섹터별 순매수/순매도 히트맵
   - 섹터 로테이션 속도 (이전 주 대비 변화율)
   - 섹터 집중도 (HHI: 허핀달-허쉬만 지수)
   - 외국인 선호 섹터 vs 기관 선호 섹터 괴리

3. 유동성 지표 (Liquidity Metrics)
   - 거래대금 (5일/20일 평균 대비 비율)
   - 회전율 (turnover ratio)
   - 예탁금 추이 (투자자 대기 자금)
   - 거래대금 편중도 (상위 10 종목 비중)

4. 수급 종합 스코어 (Supply-Demand Composite)
   - market_flow: 30% (시장 순매수 강도)
   - sector_rotation: 25% (섹터 로테이션 건전성)
   - liquidity: 25% (유동성 충분도)
   - investor_sentiment: 20% (투자자 심리)
   - 5단계: STRONG_INFLOW / INFLOW / BALANCED / OUTFLOW / STRONG_OUTFLOW
```

**파일 구조**:
```
kr-supply-demand-analyzer/
├── SKILL.md
├── references/
│   └── kr_supply_demand_guide.md
└── scripts/
    ├── market_flow_analyzer.py    # 시장 레벨 수급
    ├── sector_flow_mapper.py      # 섹터별 자금 흐름
    ├── liquidity_tracker.py       # 유동성 지표
    ├── report_generator.py        # 리포트 생성
    └── tests/
        ├── __init__.py
        └── test_supply_demand.py
```

### 3.2 kr-short-sale-tracker (공매도 추적)

> **기존과의 차별화**: KRClient에 공매도 기본 조회 메서드 존재하나, 분석 스킬은 없음.
> 공매도 비율 추이, 숏커버 시그널, 섹터 집중도, 공매도 잔고 리스크 분석 신규.

| 항목 | 설명 |
|------|------|
| 복잡도 | Medium |
| 스크립트 수 | 3개 |
| 테스트 목표 | ~40개 |
| 데이터 소스 | PyKRX (공매도 잔고/거래량/투자자별) |
| 핵심 차별점 | 숏커버 시그널 + 공매도 집중도 + 리스크 스코어링 |

**핵심 분석 컴포넌트**:

```
1. 공매도 비율 분석 (Short Ratio Analysis)
   - 공매도 잔고비율: 공매도 잔고 / 상장주식수
   - 공매도 거래비율: 공매도 거래량 / 총 거래량
   - 공매도 비율 추이 (5일/20일/60일 이동평균)
   - 공매도 비율 퍼센타일 (역사적 위치)

2. 숏커버 시그널 (Short Cover Signal)
   - 공매도 잔고 감소 연속일 (3, 5, 7일)
   - 공매도 잔고 급감 탐지 (전일 대비 -10% 이상)
   - 숏스퀴즈 확률 (높은 잔고비율 + 감소 추세 + 상승)
   - Days to Cover (공매도 잔고 / 일평균 거래량)

3. 공매도 집중도 (Sector Concentration)
   - 섹터별 공매도 비율 분포
   - 공매도 Top 50 종목 모니터링
   - 섹터 공매도 이상 탐지 (평균 대비 2σ 이상)

4. 공매도 리스크 스코어 (Short Risk Score)
   - short_ratio: 30% (잔고비율 수준)
   - trend: 30% (증가/감소 추세)
   - concentration: 20% (집중도)
   - days_to_cover: 20% (커버 소요일)
   - 4단계: LOW / MODERATE / HIGH / EXTREME
```

**파일 구조**:
```
kr-short-sale-tracker/
├── SKILL.md
├── references/
│   └── kr_short_sale_guide.md
└── scripts/
    ├── short_ratio_analyzer.py    # 공매도 비율 분석
    ├── short_cover_detector.py    # 숏커버 시그널 탐지
    ├── report_generator.py        # 리포트 생성
    └── tests/
        ├── __init__.py
        └── test_short_sale.py
```

### 3.3 kr-credit-monitor (신용잔고 모니터링)

> **기존과의 차별화**: kr-bubble-detector는 신용잔고 YoY만 6개 지표 중 1개로 사용.
> kr-credit-monitor는 **신용잔고 전문 분석** - 과열 구간, 반대매매 리스크, 종목별 신용비율.

| 항목 | 설명 |
|------|------|
| 복잡도 | Medium |
| 스크립트 수 | 3개 |
| 테스트 목표 | ~40개 |
| 데이터 소스 | PyKRX (신용잔고), 금융투자협회 |
| 핵심 차별점 | 반대매매 리스크 + 신용과열 조기 경보 + 레버리지 사이클 |

**핵심 분석 컴포넌트**:

```
1. 신용잔고 분석 (Credit Balance Analysis)
   - 시장 전체 신용잔고 (절대금액 + 시총 비율)
   - 신용잔고 YoY / MoM 변화율
   - 신용융자 잔고 + 신용대주 잔고
   - 신용잔고 역사적 퍼센타일 (3년 기준)

2. 반대매매 리스크 (Forced Liquidation Risk)
   - 담보유지비율 추정 (시장 하락 시나리오별)
   - 반대매매 트리거 가격 대역 (현재가 대비 -10%, -20%, -30%)
   - 반대매매 물량 추정 (신용잔고 × 하락폭)
   - 연쇄 하락 위험도 (신용비율 상위 종목 집중)

3. 레버리지 사이클 (Leverage Cycle)
   - 신용잔고 증감 사이클 (확장기 / 수축기)
   - 개인투자자 레버리지 추이
   - 신용잔고 vs 시장 수익률 상관관계
   - 투자자예탁금 대비 신용잔고 비율

4. 신용 리스크 스코어 (Credit Risk Score)
   - credit_level: 30% (시총 대비 신용잔고 수준)
   - growth_rate: 25% (신용잔고 증가 속도)
   - forced_liquidation: 25% (반대매매 근접도)
   - leverage_cycle: 20% (사이클 위치)
   - 5단계: SAFE / NORMAL / ELEVATED / HIGH / CRITICAL
```

**파일 구조**:
```
kr-credit-monitor/
├── SKILL.md
├── references/
│   └── kr_credit_guide.md
└── scripts/
    ├── credit_balance_analyzer.py    # 신용잔고 분석
    ├── forced_liquidation_risk.py    # 반대매매 리스크
    ├── report_generator.py           # 리포트 생성
    └── tests/
        ├── __init__.py
        └── test_credit_monitor.py
```

### 3.4 kr-program-trade-analyzer (프로그램 매매 분석)

> **100% 신규**: 프로그램 매매는 미국에 없는 한국 고유 시장 메커니즘.
> 차익/비차익 구분, 선물/옵션 만기일 영향, 사이드카/서킷브레이커 근접도.

| 항목 | 설명 |
|------|------|
| 복잡도 | High |
| 스크립트 수 | 4개 |
| 테스트 목표 | ~50개 |
| 데이터 소스 | PyKRX (프로그램매매), KRX 파생상품 |
| 핵심 차별점 | 차익/비차익 구분 + 만기일 효과 + 베이시스 분석 |

**핵심 분석 컴포넌트**:

```
1. 프로그램 매매 분석 (Program Trade Analysis)
   - 차익거래 (Arbitrage): 선물-현물 차익 매수/매도
   - 비차익거래 (Non-Arbitrage): 외국인/기관 바스켓 매매
   - 프로그램 순매수/순매도 추이 (일별/시간별)
   - 차익/비차익 비율 및 방향성

2. 선물 베이시스 분석 (Futures Basis)
   - KOSPI200 선물 vs 현물 베이시스 (콘탱고/백워데이션)
   - 선물 미결제약정 (Open Interest) 추이
   - 선물 롤오버 기간 패턴
   - 베이시스 이상 탐지 (과대 콘탱고/백워데이션)

3. 만기일 효과 (Expiry Effect)
   - 옵션 만기일 (매월 둘째 목요일) 임팩트
   - 쿼드러플 위칭 (분기 만기) 영향
   - 만기일 전 5일/3일/1일 패턴
   - 만기 주간 변동성 프리미엄
   - 최대 고통 가격 (Max Pain) 추정

4. 프로그램 영향 스코어 (Program Impact Score)
   - arbitrage_flow: 25% (차익거래 방향 및 규모)
   - non_arb_flow: 30% (비차익 방향 및 규모)
   - basis_signal: 25% (베이시스 이상 신호)
   - expiry_effect: 20% (만기일 근접도)
   - 4단계: POSITIVE / NEUTRAL / NEGATIVE / WARNING
```

**파일 구조**:
```
kr-program-trade-analyzer/
├── SKILL.md
├── references/
│   ├── kr_program_trade_guide.md
│   └── kr_expiry_calendar.md
└── scripts/
    ├── program_trade_analyzer.py    # 프로그램 매매 분석
    ├── basis_analyzer.py            # 선물 베이시스
    ├── expiry_effect_analyzer.py    # 만기일 효과
    ├── report_generator.py          # 리포트 생성
    └── tests/
        ├── __init__.py
        └── test_program_trade.py
```

### 3.5 kr-dart-disclosure-monitor (DART 공시 종합 모니터)

> **기존과의 차별화**: kr-earnings-calendar는 실적 공시 5유형만 추적.
> kr-dart-disclosure-monitor는 **전체 공시 유형** 모니터링 + 이벤트 영향도 스코어링.

| 항목 | 설명 |
|------|------|
| 복잡도 | High |
| 스크립트 수 | 4개 |
| 테스트 목표 | ~50개 |
| 데이터 소스 | DART OpenAPI (공시, 대량보유, 임원지분) |
| 핵심 차별점 | 전체 공시 유형 분류 + 이벤트 영향도 스코어 + 알림 우선순위 |

**핵심 분석 컴포넌트**:

```
1. 공시 유형 분류 (Disclosure Classification)
   10개 주요 공시 유형:
   - EARNINGS: 실적 공시 (잠정/확정)
   - DIVIDEND: 배당 관련 (증배/감배/무배/기준일)
   - CAPITAL: 자본 변동 (유상증자/무상증자/감자/전환사채)
   - MA: M&A (합병/인수/분할/영업양수도)
   - GOVERNANCE: 지배구조 (대표이사 변경/이사 선임/정관 변경)
   - STAKE: 지분 변동 (5% 대량보유/임원 매수매도/자사주)
   - LEGAL: 법적 이벤트 (소송/제재/과징금)
   - IPO: 상장/상장폐지/스팩 합병
   - REGULATION: 규제 (관리종목/투자주의/매매정지)
   - OTHER: 기타 (공장 설립/특허/수주)

2. 이벤트 영향도 스코어 (Event Impact Score)
   영향도 레벨 (1-5):
   - 5 (Critical): 상장폐지, 감자, 관리종목 지정
   - 4 (High): M&A, 유상증자, 대표이사 변경, 감배
   - 3 (Medium): 실적 서프라이즈, 5% 보유 변동, 증배
   - 2 (Low): 자사주, 정관 변경, 일반 수주
   - 1 (Info): 사업보고서, 이사회 구성

3. 대량보유/지분변동 추적 (Stake Change Tracker)
   - 5% 대량보유 보고서 파싱
   - 임원/주요주주 매수/매도 추적
   - 자사주 취득/처분 모니터링
   - 지분 변동 패턴 (축적 vs 매각)

4. 공시 리스크 스코어 (Disclosure Risk Score)
   - event_severity: 35% (이벤트 심각도)
   - frequency: 20% (공시 빈도 이상 탐지)
   - stake_change: 25% (지분 변동 방향)
   - governance: 20% (지배구조 안정성)
   - 4단계: NORMAL / ATTENTION / WARNING / CRITICAL
```

**파일 구조**:
```
kr-dart-disclosure-monitor/
├── SKILL.md
├── references/
│   ├── kr_disclosure_types.md
│   └── kr_dart_api_guide.md
└── scripts/
    ├── disclosure_classifier.py     # 공시 유형 분류
    ├── event_impact_scorer.py       # 이벤트 영향도
    ├── stake_change_tracker.py      # 지분 변동 추적
    ├── report_generator.py          # 리포트 생성
    └── tests/
        ├── __init__.py
        └── test_dart_disclosure.py
```

---

## 4. 기존 스킬과의 관계

### 4.1 차별화 매트릭스

| Phase 9 스킬 | 기존 관련 스킬 | 차별화 포인트 |
|-------------|--------------|-------------|
| kr-supply-demand-analyzer | kr-institutional-flow | 종목→**시장/섹터** 레벨, 유동성 지표 추가 |
| kr-short-sale-tracker | KRClient 메서드만 | 분석 없음→**숏커버 시그널+리스크 스코어** |
| kr-credit-monitor | kr-bubble-detector (1/6) | YoY 1개→**전문 신용분석+반대매매 리스크** |
| kr-program-trade-analyzer | (없음) | **100% 신규** - 한국 고유 |
| kr-dart-disclosure-monitor | kr-earnings-calendar (실적만) | 실적 5유형→**전체 10유형+영향도 스코어** |

### 4.2 상위 스킬 통합

Phase 9 스킬은 Phase 8 메타 스킬에 데이터를 제공:

```
Phase 9 (Input)          →  Phase 8 (Consumer)
─────────────────────────────────────────────────
kr-supply-demand-analyzer →  kr-weekly-strategy (시장 환경)
kr-short-sale-tracker     →  kr-stock-analysis (수급 분석)
kr-credit-monitor         →  kr-bubble-detector (위험 보조지표)
kr-program-trade-analyzer →  kr-weekly-strategy (주간 이벤트)
kr-dart-disclosure-monitor→  kr-earnings-trade (이벤트 트리거)
```

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | 요구사항 | 우선순위 | 스킬 |
|----|----------|---------|------|
| FR-01 | 시장 전체 투자자별 순매수 추이 분석 | High | supply-demand |
| FR-02 | 섹터별 자금 흐름 히트맵 생성 | High | supply-demand |
| FR-03 | 거래대금/회전율 유동성 지표 산출 | Medium | supply-demand |
| FR-04 | 수급 종합 스코어 (4 컴포넌트) | High | supply-demand |
| FR-05 | 공매도 잔고비율/거래비율 추이 분석 | High | short-sale |
| FR-06 | 숏커버 시그널 탐지 (잔고 감소+상승) | High | short-sale |
| FR-07 | 공매도 섹터 집중도 분석 | Medium | short-sale |
| FR-08 | 공매도 리스크 스코어 (4 컴포넌트) | High | short-sale |
| FR-09 | 시장 전체 신용잔고 모니터링 | High | credit |
| FR-10 | 반대매매 리스크 시나리오 분석 | High | credit |
| FR-11 | 레버리지 사이클 위치 판단 | Medium | credit |
| FR-12 | 신용 리스크 스코어 (4 컴포넌트) | High | credit |
| FR-13 | 차익/비차익 프로그램 매매 분석 | High | program-trade |
| FR-14 | 선물 베이시스 이상 탐지 | High | program-trade |
| FR-15 | 만기일 효과 분석 (월간/분기) | Medium | program-trade |
| FR-16 | 프로그램 영향 스코어 (4 컴포넌트) | High | program-trade |
| FR-17 | DART 10개 공시 유형 분류 | High | dart-disclosure |
| FR-18 | 이벤트 영향도 5단계 스코어링 | High | dart-disclosure |
| FR-19 | 대량보유/지분변동 추적 | High | dart-disclosure |
| FR-20 | 공시 리스크 스코어 (4 컴포넌트) | High | dart-disclosure |

### 5.2 Non-Functional Requirements

| 카테고리 | 기준 | 측정 방법 |
|---------|------|----------|
| 테스트 | 스킬당 30+ 테스트, 총 ~230개 | pytest -v |
| 일관성 | Phase 1-8 코딩 패턴 100% 준수 | Gap Analysis 97%+ |
| 데이터 | Tier 1만으로 100% 동작 | 계좌 불필요 검증 |
| 성능 | 모든 함수 순수 Python, 외부 I/O 없음 | 단위 테스트 |

---

## 6. 구현 계획

### 6.1 파일 수량 예상

| 스킬 | SKILL.md | References | Scripts | Tests | 합계 |
|------|:--------:|:----------:|:-------:|:-----:|:----:|
| kr-supply-demand-analyzer | 1 | 1 | 4 | 1 | 7 |
| kr-short-sale-tracker | 1 | 1 | 3 | 1 | 6 |
| kr-credit-monitor | 1 | 1 | 3 | 1 | 6 |
| kr-program-trade-analyzer | 1 | 2 | 4 | 1 | 8 |
| kr-dart-disclosure-monitor | 1 | 2 | 4 | 1 | 8 |
| **합계** | 5 | 7 | 18 | 5 | **35** |

### 6.2 상수 수량 예상

| 스킬 | 상수 | 주요 상수 |
|------|:----:|----------|
| supply-demand | ~25 | 14 섹터, 수급 스코어 가중치 4개, 5단계, 유동성 기준 |
| short-sale | ~20 | 공매도 기준 4단계, 비율 퍼센타일, 숏커버 기준 |
| credit | ~25 | 담보유지비율 기준, 반대매매 시나리오, 사이클 5단계 |
| program-trade | ~30 | 차익/비차익 기준, 베이시스 임계값, 만기일 캘린더 |
| dart-disclosure | ~30 | 10 공시유형, 5 영향도, 이벤트 매핑 |
| **합계** | **~130** | |

### 6.3 구현 순서 (5-Step)

```
Step 1: kr-supply-demand-analyzer (High, 기존 패턴 확장)
  └─ 기존 kr-institutional-flow 패턴 활용, 시장/섹터 레벨 확장
  └─ 의존: _kr-common, kr-institutional-flow 상수 참조

Step 2: kr-short-sale-tracker (Medium, PyKRX 공매도 API 활용)
  └─ KRClient 공매도 메서드 기반, 분석 로직 신규
  └─ 의존: _kr-common

Step 3: kr-credit-monitor (Medium, 신용잔고 데이터)
  └─ kr-bubble-detector의 credit_balance_yoy 확장
  └─ 의존: _kr-common

Step 4: kr-program-trade-analyzer (High, 100% 신규)
  └─ 프로그램 매매 + 선물 베이시스 + 만기일 - 완전 신규 설계
  └─ 의존: _kr-common, kr-options-advisor 상수 참조

Step 5: kr-dart-disclosure-monitor (High, DART API 확장)
  └─ kr-earnings-calendar의 DART 패턴 활용, 전체 공시로 확장
  └─ 의존: _kr-common, DART 공시 유형 코드

Step 6: 통합 테스트 (Phase 1-9 전체 44개 모듈)
```

---

## 7. Success Criteria

### 7.1 Definition of Done

- [ ] 5개 스킬 전체 구현 완료
- [ ] 스킬당 30+ 단위 테스트 통과
- [ ] 총 ~230개 테스트 전체 통과
- [ ] Phase 1-9 전체 44개 모듈 통합 테스트 통과 (누적 ~1,632 테스트)
- [ ] Gap Analysis Match Rate >= 97%

### 7.2 Quality Criteria

- [ ] Major Gap 0개
- [ ] 모든 스코어링 가중치 합계 1.0 (±0.001)
- [ ] 14 한국 섹터 일관성 유지 (Phase 6, 8과 동일)
- [ ] Phase 3-9 연속 97% Match Rate 유지 (7연속 목표)

---

## 8. Risks and Mitigation

| 리스크 | 영향 | 가능성 | 대응 |
|--------|------|-------|------|
| PyKRX 프로그램매매 API 미제공 | High | Medium | 정적 데이터 + 패턴 분석으로 대체 |
| 신용잔고 일별 데이터 수집 제한 | Medium | Low | 월별/주별 집계로 대체 |
| DART 공시 유형 코드 변경 | Low | Low | 공시유형 매핑 테이블 분리 |
| 기존 스킬과 중복 로직 | Medium | Medium | 공통 유틸리티 분리, import 활용 |
| 프로그램 매매 상세 데이터 부재 (Tier 1) | Medium | High | 지수 선물 데이터로 베이시스 추정 |

---

## 9. 한국 시장 고유 데이터 활용

### 9.1 PyKRX API 활용 매핑

| Phase 9 기능 | PyKRX API | 설명 |
|-------------|-----------|------|
| 시장 수급 | `get_market_trading_value_by_date()` | 12분류 투자자별 매매 |
| 섹터 수급 | `get_index_trading_value_by_date()` | 업종지수별 매매 |
| 공매도 잔고 | `get_shorting_status_by_date()` | 종목별 잔고/거래 |
| 공매도 Top | `get_shorting_balance_top50()` | 잔고비율 상위 |
| 프로그램 | `get_market_trading_value_by_date()` | 프로그램 순매수 |
| 외국인 한도 | `get_exhaustion_rates_of_foreign_investment()` | 지분 한도소진율 |

### 9.2 DART API 활용 매핑

| Phase 9 기능 | DART API | 설명 |
|-------------|----------|------|
| 전체 공시 | `dart.list()` | corp/kind/sort 파라미터 |
| 대량보유 | `dart.major_shareholders()` | 5% 보유 보고서 |
| 임원지분 | `dart.elestock()` | 임원 주식 변동 |
| 배당 상세 | `dart.report(배당)` | 배당금/배당률 |
| 자본변동 | `dart.list(kind='B')` | 증자/감자/전환 |

---

## 10. Next Steps

1. [ ] Design 문서 작성 (`/pdca design kr-stock-skills-phase9`)
2. [ ] 구현 (`/pdca do kr-stock-skills-phase9`)
3. [ ] Gap Analysis (`/pdca analyze kr-stock-skills-phase9`)
4. [ ] 완료 보고서 (`/pdca report kr-stock-skills-phase9`)
5. [ ] README.md 업데이트 (44개 스킬 전체 목록)

---

## Version History

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2026-03-04 | Phase 9 초기 계획 작성 | Claude Code + User |
