# kr-growth-outlook-patch Planning Document

> **Summary**: 기존 kr-stock-analysis, kr-sector-analyst 스킬에 미래 성장성 분석(단기/중기/장기) 추가 + kr-growth-outlook 신규 스킬 생성
>
> **Project**: Korean Stock Skills (kr-stock-skills)
> **Version**: Phase 9 Complete → Patch
> **Author**: saisei
> **Date**: 2026-03-05
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 kr-stock-analysis(종합 스코어링)와 kr-sector-analyst(섹터 분석) 스킬은 **과거/현재 데이터 기반 스냅샷 분석**에 특화되어 있으나, **미래 성장성 예측**이 체계적으로 빠져있다.

```
현재 시간축 커버리지:
과거 ◄──────── 현재 ────────► 미래
[잘됨]          [잘됨]         [부족]
재무3년 추세     기술적 분석     TAM/SAM 없음
배당이력         수급현황       경쟁우위 없음
실적성장률       밸류에이션     파이프라인 없음
백테스트         섹터위치       정책 트렌드 없음
```

이 패치는 **3단계 시간축(단기 1-3년 / 중기 4-7년 / 장기 10년)**으로 성장 가능성을 정량+정성 분석하는 프레임워크를 추가한다.

### 1.2 Background

- **문제**: SK하이닉스(78점 BUY)와 두산에너빌리티(47점 SELL) 모두 동일하게 "과거 재무 + 현재 수급"으로만 평가
- SK하이닉스는 HBM 메가사이클로 장기 성장성이 높지만, 현재 스코어에 이 요소가 미반영
- 두산에너빌리티는 원전 테마로 주가가 올랐지만, 실제 장기 실적 경로는 불확실 → 이것도 미반영
- **결론**: "이 주식이 앞으로 얼마나 성장할 수 있는가"를 체계적으로 답하지 못함

### 1.3 Related Documents

- Phase 8 Design: `docs/02-design/features/kr-stock-skills-phase8.design.md` (kr-stock-analysis 원본 설계)
- Phase 2 Design: `docs/02-design/features/kr-stock-skills-phase2.design.md` (kr-sector-analyst 원본 설계)

---

## 2. Scope

### 2.1 In Scope

- [x] **kr-stock-analysis 패치**: Growth Quick Score 컴포넌트 추가 (5번째 컴포넌트)
- [x] **kr-sector-analyst 패치**: 섹터별 성장 전망 분석 추가
- [x] **kr-growth-outlook 신규 스킬**: 심층 성장성 분석 (6-컴포넌트, 3시간축)
- [x] **데이터 소스 통합**: WebSearch 기반 + 정적 데이터 + FnGuide/DART 활용
- [x] **kr-strategy-synthesizer 패치**: Growth Outlook 결과 통합

### 2.2 Out of Scope

- 실시간 뉴스 피드 스킬 (별도 프로젝트)
- 유료 API 구독 (Bloomberg, Refinitiv 등)
- 해외 주식 성장성 분석 (us-stock-analysis는 별도)
- 자동 매매 시스템 연동

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | kr-stock-analysis에 Growth Quick Score (0-100) 추가 | High | Pending |
| FR-02 | Growth Quick Score는 단기/중기/장기 3줄 요약 포함 | High | Pending |
| FR-03 | kr-growth-outlook 신규 스킬: 6-컴포넌트 심층 분석 | High | Pending |
| FR-04 | 3시간축(1-3년/4-7년/10년) 독립 스코어링 | High | Pending |
| FR-05 | kr-sector-analyst에 섹터별 Growth Outlook 추가 | Medium | Pending |
| FR-06 | kr-strategy-synthesizer에서 Growth Score 통합 | Medium | Pending |
| FR-07 | 한국 시장 특화 성장 동인/리스크 팩터 반영 | High | Pending |
| FR-08 | 데이터 소스 4-Tier 우선순위 체계 | Medium | Pending |
| FR-09 | 종합 점수의 가중치 재조정 (4→5 컴포넌트) | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 정확성 | 산업 전망 컨센서스와 70%+ 일치 | 증권사 리서치 대비 검증 |
| 재현성 | 동일 종목 분석 시 스코어 ±10점 이내 편차 | 3회 반복 테스트 |
| 속도 | 분석 1건당 60초 이내 (WebSearch 포함) | 실행 시간 측정 |

---

## 4. Data Sources (브레인스토밍 결과)

### 4.1 4-Tier 데이터 소스 체계

```
Tier 1: 정적 레퍼런스 (가장 빠름, 가장 안정적)
├─ references/korea_growth_drivers.md    → 한국 메가트렌드 (반도체/방산/바이오/원전...)
├─ references/sector_tam_database.md     → 14개 섹터별 글로벌 TAM 데이터
├─ references/moat_framework.md          → 경쟁 우위 분석 프레임워크
└─ references/korea_policy_roadmap.md    → 정부 정책 로드맵 (밸류업/탄소중립/...)

Tier 2: 자동 수집 가능 데이터
├─ DART API       → 재무제표, R&D 투자, 특허 수, 신사업 공시
├─ FnGuide        → 컨센서스 EPS/매출 전망, 목표가
├─ PyKRX          → 업종별 시가총액 변화, 수급 추이
├─ ECOS (한국은행)  → 산업별 성장률, 경기선행지수
└─ KIND (한국거래소) → IPO/상장 동향, 신규 사업보고서

Tier 3: WebSearch 기반 (AI 판단 필요)
├─ 증권사 리서치 (TAM 추정치, 산업 전망)
├─ 산업 뉴스 (신제품/기술/규제 동향)
├─ 글로벌 리서치 (Gartner/IDC/IHS 등 인용)
└─ IR 자료/실적발표 컨퍼런스콜 요약

Tier 4: 공공 데이터 포털 (보조)
├─ KIET 산업연구원 → 주요 산업 동향 지표
├─ KISTEP         → 기술 트렌드/R&D 투자 통계
├─ 통계청 KOSIS    → 산업별 생산/출하 지수
└─ 수출입은행      → 한국 수출 품목별 전망
```

### 4.2 데이터 소스별 장단점 분석

| 소스 | 장점 | 단점 | Growth 기여도 |
|------|------|------|:------------:|
| **정적 레퍼런스** | 즉시 사용, 일관성 | 업데이트 필요, 시의성 | ★★★☆ |
| **DART** | 공식 재무, 무료 API | 과거 데이터만, 전망 없음 | ★★☆☆ |
| **FnGuide** | 컨센서스 전망 데이터 | 스크래핑 필요, 불안정 | ★★★★ |
| **WebSearch** | 최신 정보, 전문가 의견 | 비결정적, 재현성 낮음 | ★★★★★ |
| **ECOS** | 거시경제 공식 통계 | API 응답 느림 | ★★☆☆ |
| **KIET/KISTEP** | 산업별 심층 보고서 | PDF 형태, 파싱 어려움 | ★★★☆ |

### 4.3 실행 전략: Hybrid Layered Approach

```
분석 실행 시 데이터 조합:

1단계: 정적 레퍼런스 로드 (즉시)
   → 섹터 TAM, 메가트렌드, Moat 프레임워크 기본값

2단계: DART/FnGuide 자동 수집 (10초)
   → R&D 투자 추이, 컨센서스 EPS, 목표가 괴리율

3단계: WebSearch 보완 (30초)
   → 최신 산업 전망, 경쟁 구도, 정책 변화

4단계: AI 종합 판단 (즉시)
   → 수집된 데이터 기반 6-컴포넌트 스코어링
```

### 4.4 WebSearch 의존도 관리

| 컴포넌트 | WebSearch 의존도 | 대안 |
|---------|:--------------:|------|
| TAM/SAM | 70% → **50%** | 정적 TAM DB + KIET 보고서 |
| 경쟁 우위 | 60% → **40%** | DART 시장점유율 + 특허 수 |
| 파이프라인 | 80% → **60%** | DART 신사업 공시 + IR 자료 |
| 실적 경로 | 30% → **20%** | FnGuide 컨센서스 (핵심!) |
| 정책 순풍 | 90% → **70%** | 정적 정책 로드맵 + WebSearch |
| 경영진 | 50% → **30%** | DART 임원현황 + 보수 공시 |

**핵심**: FnGuide 컨센서스가 실적 경로 분석의 anchor 역할. WebSearch는 보완.

---

## 5. Hybrid Architecture (Option 3)

### 5.1 kr-stock-analysis 패치 (경량 Growth Quick Score)

```
현재: Fundamental(35%) + Technical(25%) + Supply(25%) + Valuation(15%) = 100

변경: Fundamental(30%) + Technical(22%) + Supply(22%) + Valuation(13%) + Growth(13%) = 100

Growth Quick Score (0-100):
├─ FnGuide 컨센서스 EPS 성장률     (40%)
├─ R&D 투자 비율 + 추이            (20%)
├─ 섹터 TAM CAGR (정적 DB 참조)    (20%)
└─ 정책 순풍 (정적 DB 참조)         (20%)
→ WebSearch 미사용! 즉시 계산 가능한 경량 버전
```

**출력 예시:**
```
Growth Quick Score: 82/100 (A등급)
  단기(1-3년): HBM4 독점, 컨센서스 EPS +45% YoY
  중기(4-7년): TAM CAGR 18%, R&D 투자 매출 대비 15%
  장기(10년): AI 메모리 메가트렌드 지속, 정책 지원(K-반도체 전략)
→ 심층 분석: /kr-growth-outlook SK하이닉스
```

### 5.2 kr-growth-outlook 신규 스킬 (심층)

```
6-컴포넌트 Growth Score (0-100):

┌─────────────────────────────────────────────────────────────┐
│                    Growth Outlook Framework                   │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│   컴포넌트    │  단기 1-3년   │  중기 4-7년   │   장기 10년+    │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ TAM/SAM     │ SAM 점유율    │ TAM CAGR     │ TAM 2035 전망   │
│ (0.25)      │ 시장 성장 속도 │ SAM 확장 경로  │ 신시장 창출     │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ 경쟁우위     │ 현재 M/S      │ 진입장벽 강도  │ 와해 리스크     │
│ (0.20)      │ 경쟁자 수     │ 기술 해자     │ 대체재 출현     │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ 파이프라인   │ 신제품 출시   │ R&D 역량      │ 패러다임 전환   │
│ (0.15)      │ DART 공시    │ 특허 포트폴리오│ 기술 트렌드     │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ 실적 경로    │ 컨센서스 EPS  │ 이익률 레버리지│ 복리 성장 잠재력│
│ (0.20)      │ 가이던스      │ 규모의 경제   │ 재투자 효율     │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ 정책 순풍    │ 정부 지원     │ 규제 변화     │ 글로벌 규범     │
│ (0.10)      │ 보조금/세제   │ 산업 정책     │ ESG/탄소중립   │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ 경영진       │ 실행력       │ 비전/전략     │ 승계 계획      │
│ (0.10)      │ 트랙레코드   │ 자본 배분     │ 기업 문화      │
└─────────────┴──────────────┴──────────────┴─────────────────┘

가중치 합계: 0.25 + 0.20 + 0.15 + 0.20 + 0.10 + 0.10 = 1.00 ✓
```

**시간축별 가중치 조정:**

```python
TIME_HORIZON_MULTIPLIER = {
    "short_1_3y": {
        "tam_sam": 0.8, "competitive": 0.9, "pipeline": 1.3,
        "earnings_path": 1.3, "policy": 0.9, "management": 0.8
    },
    "mid_4_7y": {
        "tam_sam": 1.0, "competitive": 1.2, "pipeline": 1.1,
        "earnings_path": 1.0, "policy": 1.0, "management": 0.7
    },
    "long_10y": {
        "tam_sam": 1.3, "competitive": 1.3, "pipeline": 0.7,
        "earnings_path": 0.7, "policy": 1.5, "management": 1.5
    },
}
```

**등급 체계:**

| 등급 | 점수 | 의미 | 주가 함의 |
|:----:|:----:|------|----------|
| S | 85-100 | Hyper Growth | 10년 10배+ 잠재력 |
| A | 70-84 | Strong Growth | 10년 5배+ 잠재력 |
| B | 55-69 | Moderate Growth | 10년 2-3배 잠재력 |
| C | 40-54 | Slow Growth | 시장 수익률 수준 |
| D | 0-39 | No Growth / Decline | 구조적 하락 리스크 |

### 5.3 kr-sector-analyst 패치 (섹터 성장 전망)

기존 경기순환 위치 분석에 **섹터별 Growth Outlook** 추가:

```
현재 출력:
| 섹터 | 경기순환 위치 | 현재 모멘텀 |

패치 후:
| 섹터 | 경기순환 위치 | 현재 모멘텀 | 3년 성장전망 | 10년 성장전망 |
```

정적 레퍼런스 `sector_tam_database.md`에서 14개 섹터별 TAM CAGR, 정책 순풍, 구조적 트렌드를 로드.

### 5.4 kr-strategy-synthesizer 패치

기존 7-컴포넌트 → 8-컴포넌트로 확장:

```
현재: Breadth + Uptrend + MarketTop + Macro + FTD + VCP + CANSLIM
추가: + GrowthOutlook (가중치 0.12 할당, 기존 7개 가중치 비례 축소)
```

---

## 6. Korean Market Specific Factors

### 6.1 한국 고유 성장 동인 (Growth Drivers)

```
구조적 메가트렌드:
├─ K-반도체 전략: HBM/AI메모리 글로벌 1위, 정부 세제 지원
├─ K-방산 수출: 폴란드/사우디/UAE 파이프라인 $30B+
├─ K-원전 르네상스: SMR + APR1400 수출 (체코/폴란드)
├─ K-바이오: 글로벌 CDMO + ADC 라이선싱 딜 급증
├─ K-조선 슈퍼사이클: LNG/암모니아선 수주잔고 3-4년치
├─ K-컨텐츠: 게임/엔터/뷰티/식품 글로벌화
├─ AI 데이터센터: 전력장비/변압기 글로벌 수요 폭발
└─ 밸류업 프로그램: 주주환원 확대, 저PBR 해소
```

### 6.2 한국 고유 리스크 팩터 (Growth Headwinds)

```
구조적 리스크:
├─ 재벌 지배구조 디스카운트 (Korea Discount)
├─ 북한 지정학 리스크 (전쟁 프리미엄)
├─ 인구 감소: 2025년부터 총인구 감소, 내수 시장 축소
├─ 중국 기술 추격: 반도체/배터리/디스플레이
├─ 원화 변동성: 수출 기업 실적 번역 리스크
├─ 규제 리스크: 대주주 양도세, 공매도, 금투세 논란
├─ 산업 집중 리스크: 삼성전자+SK하이닉스 = KOSPI 30%
└─ 에너지 의존: 수입 에너지 100%, 유가/가스 민감
```

### 6.3 14개 섹터별 기본 TAM 데이터 (정적 DB)

| 섹터 | 2026 글로벌 TAM | CAGR '26-'30 | 한국 기업 글로벌 M/S | 성장 등급 |
|------|:--------------:|:------------:|:------------------:|:--------:|
| 반도체 | $680B | 12% | ~20% (메모리 60%) | S |
| 자동차 | $3.5T | 4% | ~8% (현대+기아) | B |
| 조선 | $150B | 8% | ~40% (3사 합산) | A |
| 방산 | $2.2T | 7% | ~3% (급성장) | A |
| 바이오/헬스 | $1.8T | 9% | ~2% (CDMO 성장) | A |
| 2차전지 | $180B | 15% | ~25% (3사 합산) | A→B (경쟁) |
| 전력장비 | $250B | 10% | ~5% (변압기) | A |
| 화학/소재 | $500B | 3% | ~5% | C |
| 철강 | $1.4T | 2% | ~3% | C |
| 건설 | 국내 중심 | 1% | 내수 90% | D |
| 금융 | 국내 중심 | 3% | 내수 95% | C |
| 통신 | 국내 중심 | 2% | 내수 99% | D |
| 유틸리티 | 국내 중심 | 1% | 내수 99% | D |
| 엔터/콘텐츠 | $350B | 8% | ~5% (K-콘텐츠) | B |

---

## 7. Implementation Scope (패치 목록)

### 7.1 수정 대상 파일

| # | 스킬 | 파일 | 변경 유형 | 내용 |
|:-:|------|------|:--------:|------|
| 1 | kr-stock-analysis | SKILL.md | 수정 | Growth Quick Score 섹션 추가 |
| 2 | kr-stock-analysis | scripts/growth_quick_scorer.py | 신규 | 경량 Growth Score 스크립트 |
| 3 | kr-stock-analysis | scripts/comprehensive_scorer.py | 수정 | 5번째 컴포넌트 추가, 가중치 재조정 |
| 4 | kr-stock-analysis | references/kr_stock_analysis_guide.md | 수정 | Growth 분석 가이드 추가 |
| 5 | kr-stock-analysis | tests/ | 수정 | Growth 관련 테스트 추가 |
| 6 | kr-growth-outlook | SKILL.md | **신규** | 심층 성장성 분석 스킬 정의 |
| 7 | kr-growth-outlook | scripts/tam_analyzer.py | **신규** | TAM/SAM 분석 |
| 8 | kr-growth-outlook | scripts/moat_scorer.py | **신규** | 경쟁 우위 평가 |
| 9 | kr-growth-outlook | scripts/pipeline_evaluator.py | **신규** | 기술/제품 파이프라인 |
| 10 | kr-growth-outlook | scripts/earnings_projector.py | **신규** | 실적 경로 추정 |
| 11 | kr-growth-outlook | scripts/policy_analyzer.py | **신규** | 정책/규제 분석 |
| 12 | kr-growth-outlook | scripts/management_scorer.py | **신규** | 경영진 평가 |
| 13 | kr-growth-outlook | scripts/growth_synthesizer.py | **신규** | 6-컴포넌트 종합 |
| 14 | kr-growth-outlook | references/korea_growth_drivers.md | **신규** | 한국 성장 동인 DB |
| 15 | kr-growth-outlook | references/sector_tam_database.md | **신규** | 14개 섹터 TAM DB |
| 16 | kr-growth-outlook | references/moat_framework.md | **신규** | Moat 분석 프레임워크 |
| 17 | kr-growth-outlook | references/korea_policy_roadmap.md | **신규** | 정부 정책 로드맵 |
| 18 | kr-growth-outlook | tests/test_growth_outlook.py | **신규** | 테스트 |
| 19 | kr-sector-analyst | SKILL.md | 수정 | 섹터 Growth Outlook 추가 |
| 20 | kr-sector-analyst | references/kr_sector_rotation.md | 수정 | 섹터별 TAM/성장등급 추가 |
| 21 | kr-sector-analyst | scripts/sector_growth_scorer.py | **신규** | 섹터 성장성 스코어링 |
| 22 | kr-strategy-synthesizer | SKILL.md | 수정 | 8번째 컴포넌트 추가 |
| 23 | kr-strategy-synthesizer | scripts/conviction_scorer.py | 수정 | Growth 가중치 추가 |

**합계**: 23개 파일 (신규 13개 + 수정 10개)

### 7.2 구현 순서

```
Step 1: 정적 레퍼런스 생성 (references/)
  → sector_tam_database.md, korea_growth_drivers.md,
    moat_framework.md, korea_policy_roadmap.md

Step 2: kr-growth-outlook 핵심 스크립트 구현
  → tam_analyzer.py → moat_scorer.py → pipeline_evaluator.py
  → earnings_projector.py → policy_analyzer.py → management_scorer.py
  → growth_synthesizer.py

Step 3: kr-stock-analysis 패치
  → growth_quick_scorer.py (신규)
  → comprehensive_scorer.py (가중치 수정)
  → SKILL.md 업데이트

Step 4: kr-sector-analyst 패치
  → sector_growth_scorer.py (신규)
  → kr_sector_rotation.md 업데이트
  → SKILL.md 업데이트

Step 5: kr-strategy-synthesizer 패치
  → conviction_scorer.py 가중치 추가

Step 6: 테스트 작성 및 검증
  → test_growth_outlook.py
  → 기존 테스트 수정 (가중치 변경 반영)
```

---

## 8. Success Criteria

### 8.1 Definition of Done

- [ ] kr-growth-outlook 스킬 6-컴포넌트 × 3시간축 스코어링 동작
- [ ] kr-stock-analysis Growth Quick Score 출력 확인
- [ ] kr-sector-analyst 14개 섹터 성장 전망 출력 확인
- [ ] kr-strategy-synthesizer 8-컴포넌트 종합 스코어 동작
- [ ] 모든 기존 테스트 통과 (가중치 변경 반영)
- [ ] 신규 테스트 90%+ 통과

### 8.2 Quality Criteria

- [ ] Match Rate >= 90% (PDCA Check)
- [ ] 기존 종목 분석 결과와 큰 괴리 없음 (±5점 이내)
- [ ] 3개 종목 실전 테스트 (SK하이닉스, 두산에너빌리티, 삼성바이오)

---

## 9. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| WebSearch 재현성 낮음 | Medium | High | 정적 DB를 anchor로 사용, WebSearch는 보완 |
| TAM 추정치 부정확 | Medium | Medium | 3개+ 소스 크로스체크, 보수적 추정 |
| 기존 테스트 깨짐 (가중치 변경) | High | High | 기존 테스트 먼저 수정 후 코드 변경 |
| AI 판단의 주관성 | Medium | High | 스코어링 기준 정량화, 프레임워크 강제 |
| FnGuide 스크래핑 불안정 | Low | Medium | 컨센서스 없으면 Tier 1 정적 DB fallback |

---

## 10. Next Steps

1. [ ] Design document 작성 (`/pdca design kr-growth-outlook-patch`)
2. [ ] 상수/가중치 확정
3. [ ] 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-05 | Initial draft | saisei |
