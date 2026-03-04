# 한국 주식 스킬 - Phase 5 캘린더 & 실적 분석 스킬 상세 설계

> **Feature**: kr-stock-skills (Phase 5)
> **Created**: 2026-03-03
> **Status**: Design Phase
> **Plan Reference**: `docs/01-plan/features/kr-stock-skills.plan.md` (섹션 3.5)
> **Phase 1 Reference**: `docs/02-design/features/kr-stock-skills-phase1.design.md`
> **Phase 2 Reference**: `docs/02-design/features/kr-stock-skills-phase2.design.md`
> **Phase 3 Reference**: `docs/02-design/features/kr-stock-skills-phase3.design.md`
> **Phase 4 Reference**: `docs/02-design/features/kr-stock-skills-phase4.design.md`

---

## 1. 설계 개요

### 1.1 Phase 5 목표
**4개 캘린더 & 실적 분석 스킬**을 한국 시장에 맞게 포팅한다.
US 스킬의 분석 방법론(실적 캘린더, 경제 캘린더, 실적 트레이드 5팩터 스코어링, 기관 투자자 추적)은 보존하되,
데이터 소스를 한국 특화 API(DART, ECOS, PyKRX)로 교체하고 한국 시장 고유 패턴을 반영한다.

Phase 5 스킬은 **이벤트 기반 분석**에 집중한다:
- 실적 캘린더 (Earnings Calendar): DART 공시일 기반 실적 발표 일정
- 경제 캘린더 (Economic Calendar): 한국은행 ECOS + 주요 한국 경제지표 일정
- 실적 트레이드 (Earnings Trade): 실적 발표 후 5팩터 스코어링 분석
- 기관 투자자 수급 (Institutional Flow): PyKRX 일별 투자자별 매매동향 추적

### 1.2 설계 원칙
- **방법론 보존**: US 스킬의 5팩터 스코어링 / 시그널 강도 프레임워크 유지
- **KRClient 활용**: Phase 1 공통 모듈(48개 메서드)을 데이터 계층으로 일관 사용
- **FMP API → DART/ECOS/PyKRX**: US 스킬이 FMP API로 수집하던 데이터를 한국 API로 대체
- **한국 실적 시즌 반영**: 잠정실적/확정실적, 분기별 공시 패턴, ±30% 가격제한폭
- **일별 수급 데이터 활용**: US 13F(분기 지연 45일) vs 한국 PyKRX(일별 즉시) 장점 극대화
- **Phase 2/3/4 크로스레퍼런스**: 시장 건강도, 레짐 분류, 종목 스크리닝 결과 연동

### 1.3 Phase 5 스킬 목록

| # | KR 스킬명 | US 원본 | 복잡도 | 스크립트 | 데이터 소스 | 용도 |
|---|-----------|---------|:------:|:--------:|-------------|------|
| 20 | kr-earnings-calendar | earnings-calendar | **Medium** | 4개 | DART API | 실적 발표 일정 조회 |
| 21 | kr-economic-calendar | economic-calendar-fetcher | **Low** | 3개 | ECOS API (한국은행) | 한국 경제지표 발표 일정 |
| 22 | kr-earnings-trade | earnings-trade-analyzer | **High** | 8개 | DART + PyKRX | 실적 후 5팩터 분석 |
| 23 | kr-institutional-flow | institutional-flow-tracker | **High** | 7개 | PyKRX (투자자별 매매동향) | 기관/외국인 수급 추적 |

### 1.4 스킬 간 관계

```
┌─────────────────────────────────────────────────────────┐
│             이벤트 기반 분석 파이프라인                     │
│                                                         │
│  캘린더 (사전 준비)          분석 (이벤트 후 대응)         │
│  ┌──────────────────┐      ┌──────────────────┐         │
│  │kr-earnings-       │──→  │kr-earnings-trade  │         │
│  │calendar           │      │(5팩터 스코어링)    │         │
│  │(실적 일정 조회)    │      └────────┬─────────┘         │
│  └──────────────────┘               │                    │
│                                     ▼                    │
│  ┌──────────────────┐      ┌──────────────────┐         │
│  │kr-economic-       │──→  │Phase 3 레짐 분류   │         │
│  │calendar           │      │(경제지표 컨텍스트)  │         │
│  │(경제지표 일정)     │      └──────────────────┘         │
│  └──────────────────┘                                    │
│                                                         │
│  수급 분석 (독립)                                        │
│  ┌──────────────────────────────────────────┐           │
│  │kr-institutional-flow                      │           │
│  │(일별 투자자별 매매동향 → 수급 시그널)       │           │
│  │  ※ Phase 4 스크리닝 결과 확인용으로 활용    │           │
│  │  ※ Phase 8 전략 통합에 수급 컨텍스트 제공   │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 1.5 디렉토리 구조 (전체)

```
~/stock/skills/
├── _kr-common/                        # Phase 1 (구현 완료)
├── kr-market-environment/ ~ ...       # Phase 2 (구현 완료, 7개)
├── kr-market-top-detector/ ~ ...      # Phase 3 (구현 완료, 5개)
├── kr-stock-screener/ ~ ...           # Phase 4 (구현 완료, 7개)
│
├── kr-earnings-calendar/              # Skill 20 (Medium)
│   ├── SKILL.md
│   ├── references/
│   │   ├── kr_earnings_season.md          # 한국 실적 시즌 가이드
│   │   └── dart_disclosure_guide.md       # DART 공시 유형 가이드
│   └── scripts/
│       ├── kr_earnings_calendar.py        # 메인 오케스트레이터
│       ├── dart_earnings_fetcher.py       # DART 실적 공시 조회
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_earnings_calendar.py
│
├── kr-economic-calendar/              # Skill 21 (Low)
│   ├── SKILL.md
│   ├── references/
│   │   └── kr_economic_indicators.md      # 한국 주요 경제지표 가이드
│   └── scripts/
│       ├── kr_economic_calendar.py        # 메인 오케스트레이터
│       ├── ecos_fetcher.py                # ECOS API 조회
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_economic_calendar.py
│
├── kr-earnings-trade/                 # Skill 22 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── scoring_methodology_kr.md      # 5팩터 스코어링 한국 적용
│   │   └── kr_earnings_patterns.md        # 한국 실적 반응 패턴
│   └── scripts/
│       ├── kr_earnings_trade_analyzer.py   # 메인 오케스트레이터
│       ├── gap_analyzer.py                # 갭 크기 분석 (Factor 1)
│       ├── trend_analyzer.py              # 사전 추세 분석 (Factor 2)
│       ├── volume_analyzer.py             # 거래량 추세 분석 (Factor 3)
│       ├── ma_position_analyzer.py        # MA200/MA50 포지션 (Factor 4,5)
│       ├── scorer.py                      # 5팩터 종합 스코어링
│       ├── report_generator.py            # JSON/Markdown 리포트
│       └── tests/
│           └── test_earnings_trade.py
│
├── kr-institutional-flow/             # Skill 23 (High)
│   ├── SKILL.md
│   ├── references/
│   │   ├── kr_investor_categories.md      # 한국 투자자 12분류 가이드
│   │   └── flow_interpretation_kr.md      # 수급 시그널 해석 프레임워크
│   └── scripts/
│       ├── kr_institutional_flow_tracker.py  # 메인 오케스트레이터
│       ├── investor_flow_analyzer.py         # 투자자별 매매동향 분석
│       ├── foreign_flow_tracker.py           # 외국인 수급 심화 분석
│       ├── accumulation_detector.py          # 수급 축적/이탈 감지
│       ├── scorer.py                         # 수급 강도 스코어링
│       ├── report_generator.py               # JSON/Markdown 리포트
│       └── tests/
│           └── test_institutional_flow.py
│
```

**파일 인벤토리 요약**:
| 항목 | 수량 |
|------|:----:|
| SKILL.md | 4 |
| References | 7 |
| Scripts | 22 |
| Test Files | 4 |
| **총 파일** | **37** |

---

## 2. 한국 vs US 데이터 소스 매핑

### 2.1 데이터 소스 교체표

| US 데이터 소스 | KR 대체 | 차이점 |
|---------------|---------|--------|
| FMP Earnings Calendar API | **DART 공시 API** (정기보고서/잠정실적) | DART는 공시일 기준, FMP는 BMO/AMC 구분 |
| FMP Economic Calendar API | **한국은행 ECOS API** | 한국 경제지표 전용, 글로벌 이벤트는 미포함 |
| FMP Stock Historical Price | **PyKRX OHLCV** (KRClient.get_ohlcv) | 동일 기능 |
| FMP Company Profile | **KRClient.get_stock_info** | 시가총액, 업종 등 |
| SEC 13F Filings (분기, 45일 지연) | **PyKRX 투자자별 매매동향** (일별, 즉시) | 한국이 훨씬 우수 — 일별 실시간 |
| FMP Institutional Holders | **PyKRX 외국인 지분율** + **DART 5% 공시** | 외국인 일별 추적 가능 |

### 2.2 한국 실적 시즌 캘린더

```
═══════════════════════════════════════════════════════════
  한국 실적 발표 패턴 (연간)
═══════════════════════════════════════════════════════════
┌─────────┬───────────────────────────────────────────────┐
│  1월    │ 4Q 잠정실적 공시 시작 (대형주 순)              │
│  2월    │ 4Q 잠정실적 집중 (중소형주)                   │
│  3월    │ 4Q 확정실적 (사업보고서 제출 마감 3/31)        │
├─────────┼───────────────────────────────────────────────┤
│  4월    │ 1Q 잠정실적 공시 시작                         │
│  5월    │ 1Q 확정실적 (분기보고서 제출 마감 5/15)        │
├─────────┼───────────────────────────────────────────────┤
│  7월    │ 2Q 잠정실적 공시 시작                         │
│  8월    │ 2Q 확정실적 (반기보고서 제출 마감 8/14)        │
├─────────┼───────────────────────────────────────────────┤
│  10월   │ 3Q 잠정실적 공시 시작                         │
│  11월   │ 3Q 확정실적 (분기보고서 제출 마감 11/14)       │
└─────────┴───────────────────────────────────────────────┘

잠정실적: 매출액 + 영업이익 + 순이익 (속보치, 수정 가능)
확정실적: 감사 완료 재무제표 (DART 정기보고서)
```

### 2.3 한국 투자자 12분류 (PyKRX)

```
═══════════════════════════════════════════════════════════
  PyKRX 투자자별 매매동향 12분류
═══════════════════════════════════════════════════════════
┌── 기관 (Institutional) ──────────────────────────────────┐
│  1. 금융투자 (증권사)     7. 기타법인                     │
│  2. 보험                  8. 기타외국인                   │
│  3. 투신 (자산운용)       9. 기타금융                     │
│  4. 사모                                                 │
│  5. 은행                                                 │
│  6. 연기금/기금                                          │
├── 외국인 ────────────────────────────────────────────────┤
│  10. 외국인 (등록 외국인)                                 │
├── 개인 ──────────────────────────────────────────────────┤
│  11. 개인                                                │
├── 기타 ──────────────────────────────────────────────────┤
│  12. 국가/지자체                                         │
└──────────────────────────────────────────────────────────┘

핵심 3분류: 외국인(10) + 기관합계(1-6) + 개인(11)
```

---

## 3. Skill 20: kr-earnings-calendar (Medium)

### 3.1 US → KR 변경 매핑

| 항목 | US (earnings-calendar) | KR (kr-earnings-calendar) |
|------|----------------------|--------------------------|
| 데이터 소스 | FMP Earnings Calendar API | DART 공시 API (정기보고서) |
| 대상 종목 | 시총 $2B+ US 상장주 | KOSPI200 + KOSDAQ150 + 시총 1조+ |
| 발표 시간 | BMO/AMC/TAS 구분 | 장중/장후 공시 구분 (DART 공시시간) |
| 실적 추정치 | EPS/Revenue Estimate (FMP) | 컨센서스 (증권사 추정 — 수집 불가시 이전 분기 실적 참조) |
| 분기 구분 | Q1-Q4 (회계연도) | 잠정실적/확정실적 구분 추가 |
| 시총 필터 | $2B (약 2.8조원) | 시총 1조원 이상 |
| 마켓캡 단위 | USD | KRW (억원 단위 표시) |

### 3.2 DART 공시 유형 매핑

| DART 공시 유형 | 코드 | 구분 | 상세 |
|---------------|------|------|------|
| 사업보고서 | `A001` | 4Q 확정 | 매년 3월 말 제출 마감 |
| 반기보고서 | `A002` | 2Q 확정 | 매년 8월 중순 제출 마감 |
| 분기보고서 | `A003` | 1Q/3Q 확정 | 5월/11월 중순 제출 마감 |
| 매출액/손익구조변경 | `D001` | 잠정실적 | 전 분기 대비 변동 시 공시 |
| 영업(잠정)실적 | `D002` | 잠정실적 | 속보치 (1-2월, 4-5월, 7-8월, 10-11월) |

### 3.3 디렉토리 구조

```
kr-earnings-calendar/
├── SKILL.md
├── references/
│   ├── kr_earnings_season.md           # 한국 실적 시즌 가이드
│   └── dart_disclosure_guide.md        # DART 공시 유형/코드 가이드
└── scripts/
    ├── kr_earnings_calendar.py         # 메인 오케스트레이터
    ├── dart_earnings_fetcher.py        # DART API 공시 조회
    ├── report_generator.py             # JSON/Markdown 리포트
    └── tests/
        └── test_earnings_calendar.py
```

### 3.4 주요 모듈 설계

#### 3.4.1 dart_earnings_fetcher.py

```python
# ─── 상수 ───
DART_REPORT_CODES = {
    'annual': 'A001',       # 사업보고서 (4Q 확정)
    'semi_annual': 'A002',  # 반기보고서 (2Q 확정)
    'quarterly': 'A003',    # 분기보고서 (1Q/3Q 확정)
    'preliminary': 'D002',  # 영업(잠정)실적
    'revenue_change': 'D001',  # 매출액/손익구조 변경
}

MARKET_CAP_MIN = 1_000_000_000_000   # 1조원 (시총 필터)
LOOKBACK_DAYS = 7                     # 기본 조회 기간
LOOKAHEAD_DAYS = 14                   # 향후 조회 기간

EARNINGS_SEASON_MAP = {
    1: {'quarter': '4Q', 'type': 'preliminary'},
    2: {'quarter': '4Q', 'type': 'preliminary'},
    3: {'quarter': '4Q', 'type': 'confirmed'},
    4: {'quarter': '1Q', 'type': 'preliminary'},
    5: {'quarter': '1Q', 'type': 'confirmed'},
    7: {'quarter': '2Q', 'type': 'preliminary'},
    8: {'quarter': '2Q', 'type': 'confirmed'},
    10: {'quarter': '3Q', 'type': 'preliminary'},
    11: {'quarter': '3Q', 'type': 'confirmed'},
}

# ─── 함수 ───
def fetch_recent_disclosures(days_back, days_ahead, report_codes)
    """DART 공시 목록 조회 (기간/유형 필터링)."""

def filter_earnings_disclosures(disclosures, min_market_cap)
    """시총 필터 + 실적 관련 공시만 추출."""

def classify_disclosure_timing(disclosure)
    """공시 시간 → 장전/장중/장후 분류.
    Returns: 'before_open' | 'during_market' | 'after_close'
    - 08:00 이전: before_open
    - 08:00-15:30: during_market
    - 15:30 이후: after_close
    """

def get_current_earnings_season(month)
    """현재 월 → 실적 시즌 (분기/유형) 매핑."""
```

#### 3.4.2 report_generator.py

```python
class EarningsCalendarReportGenerator:
    def generate_json(results, metadata) -> str
    def generate_markdown(results, metadata) -> str
    # 일자별 그룹핑 + 시총 순 정렬
    # 잠정/확정 구분 표시
    # 컨센서스 대비 서프라이즈율 표시 (가능시)
```

### 3.5 테스트 설계 (~20 tests)

| 테스트 클래스 | 테스트 수 | 검증 항목 |
|-------------|:--------:|----------|
| TestDartEarningsFetcher | 5 | 공시 조회 + 필터링 + 시간 분류 |
| TestEarningsSeason | 4 | 월별 실적 시즌 매핑 |
| TestReportGenerator | 3 | JSON/Markdown 리포트 생성 |
| TestConstants | 3 | DART 코드 + 시총 필터 + 시즌맵 검증 |
| TestCalendarOrchestrator | 5 | 메인 플로우 + 에러 처리 |
| **합계** | **~20** | |

---

## 4. Skill 21: kr-economic-calendar (Low)

### 4.1 US → KR 변경 매핑

| 항목 | US (economic-calendar-fetcher) | KR (kr-economic-calendar) |
|------|-------------------------------|--------------------------|
| 데이터 소스 | FMP Economic Calendar API | 한국은행 ECOS API + 정적 캘린더 |
| 대상 국가 | US, EU, UK, JP, CN, CA, AU | **한국 전용** (글로벌 이벤트는 미포함) |
| 이벤트 유형 | 중앙은행 결정, 고용, 물가, GDP 등 | 금통위, 고용률, CPI, GDP, 무역수지 등 |
| 임팩트 레벨 | High/Medium/Low | 동일 (H/M/L 3단계) |
| 조회 기간 | 최대 90일 | 동일 |
| 출력 형식 | Markdown 리포트 | 동일 |

### 4.2 한국 주요 경제지표 목록

| 지표명 | 발표 주기 | 임팩트 | 발표 기관 | ECOS 통계코드 |
|--------|:--------:|:------:|----------|:------------:|
| 기준금리 (금통위) | 연 8회 | **H** | 한국은행 | `722Y001` |
| 소비자물가지수 (CPI) | 매월 | **H** | 통계청 | `901Y009` |
| GDP 성장률 | 분기 | **H** | 한국은행 | `200Y002` |
| 고용률/실업률 | 매월 | **H** | 통계청 | `901Y055` |
| 무역수지 (수출입) | 매월 | **H** | 관세청 | `403Y003` |
| 산업생산지수 | 매월 | **M** | 통계청 | `901Y033` |
| 소매판매지수 | 매월 | **M** | 통계청 | `901Y061` |
| 경상수지 | 매월 | **M** | 한국은행 | `301Y013` |
| PMI (제조업) | 매월 | **M** | S&P Global | N/A (외부) |
| BSI (기업경기전망) | 매월 | **L** | 한국은행 | `512Y014` |
| CSI (소비자심리) | 매월 | **L** | 한국은행 | `511Y002` |
| 생산자물가지수 (PPI) | 매월 | **L** | 한국은행 | `404Y014` |

### 4.3 디렉토리 구조

```
kr-economic-calendar/
├── SKILL.md
├── references/
│   └── kr_economic_indicators.md      # 한국 주요 경제지표 가이드
└── scripts/
    ├── kr_economic_calendar.py         # 메인 오케스트레이터
    ├── ecos_fetcher.py                 # ECOS API 조회 + 정적 캘린더
    ├── report_generator.py             # JSON/Markdown 리포트
    └── tests/
        └── test_economic_calendar.py
```

### 4.4 주요 모듈 설계

#### 4.4.1 ecos_fetcher.py

```python
# ─── 상수 ───
IMPACT_HIGH = 'H'
IMPACT_MEDIUM = 'M'
IMPACT_LOW = 'L'

KR_INDICATORS = [
    {'name': '기준금리', 'code': '722Y001', 'frequency': 'irregular',
     'impact': IMPACT_HIGH, 'source': '한국은행'},
    {'name': 'CPI', 'code': '901Y009', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '통계청'},
    {'name': 'GDP 성장률', 'code': '200Y002', 'frequency': 'quarterly',
     'impact': IMPACT_HIGH, 'source': '한국은행'},
    {'name': '고용률', 'code': '901Y055', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '통계청'},
    {'name': '무역수지', 'code': '403Y003', 'frequency': 'monthly',
     'impact': IMPACT_HIGH, 'source': '관세청'},
    {'name': '산업생산지수', 'code': '901Y033', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '통계청'},
    {'name': '소매판매지수', 'code': '901Y061', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '통계청'},
    {'name': '경상수지', 'code': '301Y013', 'frequency': 'monthly',
     'impact': IMPACT_MEDIUM, 'source': '한국은행'},
    {'name': 'BSI', 'code': '512Y014', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
    {'name': 'CSI', 'code': '511Y002', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
    {'name': 'PPI', 'code': '404Y014', 'frequency': 'monthly',
     'impact': IMPACT_LOW, 'source': '한국은행'},
]

# 금통위 일정 (연 8회 — 정적 등록)
BOK_RATE_DECISION_MONTHS = [1, 2, 4, 5, 7, 8, 10, 11]
# 보통 매월 둘째주 목요일 (고정 일정은 한국은행 공지 참조)

DEFAULT_LOOKAHEAD_DAYS = 7
MAX_LOOKAHEAD_DAYS = 90

# ─── 함수 ───
def fetch_indicator_value(indicator_code, period)
    """ECOS API로 경제지표 최근값 조회."""

def build_static_calendar(year, month)
    """정적 경제 캘린더 생성 (금통위 + 정기 발표일).
    대부분의 경제지표 발표일은 정형화되어 있어 정적 매핑 사용.
    - CPI: 매월 초 (보통 1-5일)
    - 고용: 매월 중순
    - 무역수지: 매월 1일 (속보치)
    - GDP: 분기 종료 후 약 25일
    """

def get_upcoming_events(days_ahead, impact_filter)
    """향후 N일 경제 이벤트 목록 반환."""

def classify_impact(indicator_name)
    """경제지표 → 임팩트 레벨 분류."""
```

### 4.5 테스트 설계 (~15 tests)

| 테스트 클래스 | 테스트 수 | 검증 항목 |
|-------------|:--------:|----------|
| TestEcosFetcher | 4 | ECOS 코드 매핑 + 값 조회 |
| TestStaticCalendar | 4 | 정적 캘린더 생성 + 월별 이벤트 |
| TestImpactClassifier | 3 | H/M/L 분류 검증 |
| TestReportGenerator | 2 | JSON/Markdown 리포트 |
| TestConstants | 2 | 지표 목록 + 금통위 일정 검증 |
| **합계** | **~15** | |

---

## 5. Skill 22: kr-earnings-trade (High)

### 5.1 US → KR 변경 매핑

| 항목 | US (earnings-trade-analyzer) | KR (kr-earnings-trade) |
|------|----------------------------|----------------------|
| 데이터 소스 | FMP Earnings + Historical Price | DART 공시 + PyKRX OHLCV |
| 5팩터 가중치 | Gap(25%) + Trend(30%) + Vol(20%) + MA200(15%) + MA50(10%) | **동일 유지** |
| 갭 계산 | BMO: open/prev_close - 1, AMC: next_open/close - 1 | 공시일 기준 + ±30% 가격제한폭 감안 |
| 사전 추세 | 20일 수익률 | **동일** |
| 거래량 추세 | 20d/60d 평균 비율 | **동일** |
| MA200 포지션 | 200SMA 대비 현재가 | **동일** |
| MA50 포지션 | 50SMA 대비 현재가 | **동일** |
| 등급 | A(85+)/B(70-84)/C(55-69)/D(<55) | **동일 유지** |
| 시총 필터 | $2B+ | 시총 5,000억원+ |
| 추가 팩터 | - | 외국인 순매수 보너스 (한국 특화) |

### 5.2 5-Factor 스코어링 시스템

#### Factor 1: Gap Size (25% 가중치)

실적 발표 후 갭 크기를 측정한다. **한국 ±30% 가격제한폭** 내에서 갭 크기를 평가.

| 절대 갭 크기 | 점수 | 비고 |
|:----------:|:----:|------|
| ≥ 10% | 100 | US 동일 |
| ≥ 7% | 85 | US 동일 |
| ≥ 5% | 70 | US 동일 |
| ≥ 3% | 55 | US 동일 |
| ≥ 1% | 35 | US 동일 |
| < 1% | 15 | US 동일 |

**한국 특화 갭 계산**:
```python
GAP_SCORE_TABLE = [
    (10, 100), (7, 85), (5, 70), (3, 55), (1, 35), (0, 15),
]

# 공시 시간에 따른 갭 계산
# 장전 공시 (08:00 이전): gap = open[D] / close[D-1] - 1
# 장중 공시 (08:00-15:30): gap = close[D] / open[D] - 1 (장중 반응)
# 장후 공시 (15:30 이후): gap = open[D+1] / close[D] - 1

KR_PRICE_LIMIT = 0.30  # ±30% 가격제한폭
# 갭 > 30%일 수 없으므로 max(gap, 30%) 캡핑 불필요 (이미 제한됨)
```

#### Factor 2: Pre-Earnings Trend (30% 가중치)

실적 발표 전 20일 수익률. US와 동일한 스코어 테이블 사용.

| 20일 수익률 | 점수 |
|:----------:|:----:|
| ≥ 15% | 100 |
| ≥ 10% | 85 |
| ≥ 5% | 70 |
| ≥ 0% | 50 |
| ≥ -5% | 30 |
| < -5% | 15 |

```python
TREND_SCORE_TABLE = [
    (15, 100), (10, 85), (5, 70), (0, 50), (-5, 30), (-999, 15),
]
TREND_LOOKBACK = 20  # 20일 사전 추세
```

#### Factor 3: Volume Trend (20% 가중치)

실적 발표일 전후 20일 평균 거래량 / 60일 평균 거래량 비율.

| 거래량 비율 (20d/60d) | 점수 |
|:-------------------:|:----:|
| ≥ 2.0x | 100 |
| ≥ 1.5x | 80 |
| ≥ 1.2x | 60 |
| ≥ 1.0x | 40 |
| < 1.0x | 20 |

```python
VOLUME_SCORE_TABLE = [
    (2.0, 100), (1.5, 80), (1.2, 60), (1.0, 40), (0, 20),
]
VOLUME_SHORT_WINDOW = 20
VOLUME_LONG_WINDOW = 60
```

#### Factor 4: MA200 Position (15% 가중치)

현재가의 200일 이동평균 대비 위치.

| MA200 대비 거리 | 점수 |
|:--------------:|:----:|
| ≥ 20% | 100 |
| ≥ 10% | 85 |
| ≥ 5% | 70 |
| ≥ 0% | 55 |
| ≥ -5% | 35 |
| < -5% | 15 |

```python
MA200_SCORE_TABLE = [
    (20, 100), (10, 85), (5, 70), (0, 55), (-5, 35), (-999, 15),
]
MA200_PERIOD = 200
```

#### Factor 5: MA50 Position (10% 가중치)

현재가의 50일 이동평균 대비 위치.

| MA50 대비 거리 | 점수 |
|:-------------:|:----:|
| ≥ 10% | 100 |
| ≥ 5% | 80 |
| ≥ 0% | 60 |
| ≥ -5% | 35 |
| < -5% | 15 |

```python
MA50_SCORE_TABLE = [
    (10, 100), (5, 80), (0, 60), (-5, 35), (-999, 15),
]
MA50_PERIOD = 50
```

### 5.3 종합 스코어링

```python
# ─── 가중치 ───
WEIGHTS = {
    'gap_size': 0.25,
    'pre_earnings_trend': 0.30,
    'volume_trend': 0.20,
    'ma200_position': 0.15,
    'ma50_position': 0.10,
}
# sum(WEIGHTS.values()) == 1.0

# ─── 등급 ───
GRADE_THRESHOLDS = [
    {'min': 85, 'max': 100, 'grade': 'A', 'name': 'Strong Setup',
     'desc': '강한 실적 반응 + 기관 축적 — 진입 고려'},
    {'min': 70, 'max': 84, 'grade': 'B', 'name': 'Good Setup',
     'desc': '양호한 실적 반응 — 모니터링'},
    {'min': 55, 'max': 69, 'grade': 'C', 'name': 'Mixed Setup',
     'desc': '혼합 시그널 — 추가 분석 필요'},
    {'min': 0, 'max': 54, 'grade': 'D', 'name': 'Weak Setup',
     'desc': '약한 셋업 — 회피'},
]

# ─── 한국 특화: 외국인 순매수 보너스 ───
FOREIGN_BUY_BONUS_DAYS = 5          # 실적 발표 후 5일 연속 순매수
FOREIGN_BUY_BONUS_SCORE = 5         # 보너스 점수 (+5)
FOREIGN_BUY_MIN_AMOUNT = 1_000_000_000  # 10억원 이상 순매수 시

# ─── 시총 필터 ───
MARKET_CAP_MIN = 500_000_000_000    # 5,000억원

# ─── 실적 조회 ───
LOOKBACK_DAYS = 14                   # 최근 14일 실적 공시 조회
```

### 5.4 한국 특화: 외국인 순매수 보너스

US에는 없는 한국 전용 보너스 로직:
```
실적 발표 후 5거래일 연속 외국인 순매수 ≥ 10억원
→ composite_score += 5 (최대 100 캡핑)
```

이 보너스는 한국 시장에서 외국인 수급이 주가에 미치는 영향이 크기 때문에 추가.
US 13F는 분기 45일 지연이라 이런 실시간 추적이 불가능하지만,
한국 PyKRX는 일별 외국인 매매동향을 즉시 제공하므로 활용.

### 5.5 테스트 설계 (~40 tests)

| 테스트 클래스 | 테스트 수 | 검증 항목 |
|-------------|:--------:|----------|
| TestGapAnalyzer | 7 | 갭 크기 6구간 + 공시시간별 갭 계산 |
| TestTrendAnalyzer | 6 | 20일 수익률 6구간 스코어링 |
| TestVolumeAnalyzer | 5 | 거래량 비율 5구간 스코어링 |
| TestMAPositionAnalyzer | 6 | MA200 6구간 + MA50 5구간 |
| TestEarningsTradeScorer | 6 | 종합 스코어 + 등급 A/B/C/D + 외국인 보너스 |
| TestForeignBuyBonus | 4 | 연속 순매수 감지 + 보너스 적용 + 캡핑 |
| TestReportGenerator | 3 | JSON/Markdown 리포트 |
| TestConstants | 3 | 가중치 합 1.0 + 등급 범위 연속성 + 시총 필터 |
| **합계** | **~40** | |

---

## 6. Skill 23: kr-institutional-flow (High)

### 6.1 US → KR 변경 매핑

| 항목 | US (institutional-flow-tracker) | KR (kr-institutional-flow) |
|------|-------------------------------|--------------------------|
| 데이터 소스 | SEC 13F 파일링 (FMP API) | **PyKRX 투자자별 매매동향** (일별) |
| 데이터 지연 | 분기 45일 지연 | **당일 또는 D+1** (즉시) |
| 투자자 분류 | Hedge Fund / Mutual Fund / Pension 등 | **12분류** (금융투자/보험/투신/사모/은행/연기금/기타법인/외국인/개인 등) |
| 분석 단위 | 분기별 포지션 스냅샷 | **일별 매수/매도 금액** |
| 시그널 강도 | QoQ 변화율 (15%+ Strong) | 연속 순매수/순매도 일수 + 금액 |
| 데이터 품질 | A/B/C (13F 커버리지 기반) | A/B/C (데이터 가용성 기반) |
| 대상 종목 | 시총 $1B+ | KOSPI200 + KOSDAQ150 + 시총 5,000억+ |

### 6.2 한국 수급 분석의 핵심 차이

```
═══════════════════════════════════════════════════════════
  US (13F) vs KR (PyKRX) 비교
═══════════════════════════════════════════════════════════

  US 13F                          KR PyKRX
  ├─ 분기 1회 스냅샷              ├─ 매일 실시간
  ├─ 45일 보고 지연               ├─ D+0 ~ D+1
  ├─ 포지션 크기만 공개            ├─ 매수/매도 금액 분리
  ├─ 기관명 공개                  ├─ 카테고리별 합계만
  ├─ 매수/매도 구분 불가           ├─ 순매수 직접 계산 가능
  └─ 소형주 커버리지 제한          └─ 전 종목 커버

  한국 장점: 일별 수급 추적 → 추세 전환 조기 감지
  한국 단점: 개별 기관명 비공개 → 품질별 가중 불가
═══════════════════════════════════════════════════════════
```

### 6.3 수급 시그널 강도 프레임워크

US의 QoQ 변화율 기반 시그널을 **일별 연속 순매수/순매도** 기반으로 재설계:

#### 6.3.1 외국인 수급 시그널

| 시그널 | 조건 | 점수 | 설명 |
|--------|------|:----:|------|
| Strong Buy | 10일+ 연속 순매수 & 금액 ≥ 50억/일 | 100 | 강력 매수 축적 |
| Buy | 5-9일 연속 순매수 & 금액 ≥ 10억/일 | 80 | 매수 축적 |
| Mild Buy | 3-4일 연속 순매수 | 60 | 약한 매수 |
| Neutral | 방향 불명 (혼조) | 40 | 중립 |
| Mild Sell | 3-4일 연속 순매도 | 30 | 약한 매도 |
| Sell | 5-9일 연속 순매도 & 금액 ≥ 10억/일 | 15 | 매도 이탈 |
| Strong Sell | 10일+ 연속 순매도 & 금액 ≥ 50억/일 | 0 | 강력 이탈 |

```python
# ─── 외국인 수급 상수 ───
FOREIGN_CONSECUTIVE_STRONG = 10     # Strong 시그널 최소 연속일
FOREIGN_CONSECUTIVE_MODERATE = 5    # Moderate 시그널 최소 연속일
FOREIGN_CONSECUTIVE_MILD = 3        # Mild 시그널 최소 연속일
FOREIGN_STRONG_AMOUNT = 5_000_000_000    # 50억원/일
FOREIGN_MODERATE_AMOUNT = 1_000_000_000  # 10억원/일
```

#### 6.3.2 기관 수급 시그널

기관합계(금융투자+보험+투신+사모+은행+연기금) 기준:

| 시그널 | 조건 | 점수 |
|--------|------|:----:|
| Strong Buy | 10일+ 연속 순매수 & ≥ 100억/일 | 100 |
| Buy | 5-9일 연속 순매수 & ≥ 30억/일 | 80 |
| Mild Buy | 3-4일 연속 순매수 | 60 |
| Neutral | 혼조 | 40 |
| Mild Sell | 3-4일 연속 순매도 | 30 |
| Sell | 5-9일 연속 순매도 & ≥ 30억/일 | 15 |
| Strong Sell | 10일+ 연속 순매도 & ≥ 100억/일 | 0 |

```python
# ─── 기관 수급 상수 ───
INST_CONSECUTIVE_STRONG = 10
INST_CONSECUTIVE_MODERATE = 5
INST_CONSECUTIVE_MILD = 3
INST_STRONG_AMOUNT = 10_000_000_000   # 100억원/일
INST_MODERATE_AMOUNT = 3_000_000_000  # 30억원/일
```

#### 6.3.3 개인 vs 기관 역방향 감지

개인 매도 + 외국인/기관 매수 = 강한 bullish 시그널 (한국 시장 특화):

```python
# 개인-기관 역방향 보너스
RETAIL_COUNTER_BONUS = 10  # 개인 매도 & (외국인+기관) 매수 시 보너스
RETAIL_COUNTER_MIN_DAYS = 5  # 최소 5일 연속 역방향
```

### 6.4 종합 수급 스코어링

```python
# ─── 가중치 ───
WEIGHTS = {
    'foreign_flow': 0.40,       # 외국인 수급 (가장 중요)
    'institutional_flow': 0.30, # 기관 합계 수급
    'flow_consistency': 0.20,   # 수급 일관성 (20일 추세)
    'volume_confirmation': 0.10, # 거래량 확인 (수급 동반 거래량)
}
# sum(WEIGHTS.values()) == 1.0

# ─── 등급 ───
RATING_BANDS = [
    {'min': 85, 'max': 100, 'name': 'Strong Accumulation',
     'desc': '강력 축적 — 외국인+기관 동반 매수'},
    {'min': 70, 'max': 84, 'name': 'Accumulation',
     'desc': '축적 중 — 모니터링'},
    {'min': 55, 'max': 69, 'name': 'Mild Positive',
     'desc': '약한 긍정 — 추가 확인 필요'},
    {'min': 40, 'max': 54, 'name': 'Neutral',
     'desc': '중립 — 수급 방향 불명'},
    {'min': 0, 'max': 39, 'name': 'Distribution',
     'desc': '이탈 중 — 주의'},
]

# ─── 분석 기간 ───
ANALYSIS_WINDOW = 20      # 20거래일 수급 추적
TREND_WINDOW = 60         # 60거래일 장기 추세
MARKET_CAP_MIN = 500_000_000_000  # 5,000억원
```

### 6.5 수급 일관성 점수 (Flow Consistency)

20일 수급 추세의 일관성을 측정:

```python
def calc_flow_consistency(daily_net_buys: list) -> dict:
    """20일 수급 일관성 점수 계산.

    - 20일 중 순매수 일수 비율로 산출
    - ≥ 80% 순매수일 → 100
    - ≥ 60% → 80
    - ≥ 50% → 60
    - ≥ 40% → 40
    - < 40% → 20
    """

CONSISTENCY_SCORE_TABLE = [
    (80, 100),  # ≥ 80% 순매수일
    (60, 80),   # ≥ 60%
    (50, 60),   # ≥ 50%
    (40, 40),   # ≥ 40%
    (0, 20),    # < 40%
]
```

### 6.6 거래량 확인 점수 (Volume Confirmation)

수급 방향과 거래량 증가가 동반되는지 확인:

```python
def calc_volume_confirmation(net_buys: list, volumes: list) -> dict:
    """수급 동반 거래량 확인.

    - 순매수일 평균 거래량 / 순매도일 평균 거래량 비율
    - ≥ 1.5x → 100 (매수일 거래량이 1.5배 이상 = 강한 확인)
    - ≥ 1.2x → 75
    - ≥ 1.0x → 50
    - < 1.0x → 25 (매도일 거래량이 더 많음 = 약한 확인)
    """

VOLUME_CONFIRM_TABLE = [
    (1.5, 100), (1.2, 75), (1.0, 50), (0, 25),
]
```

### 6.7 디렉토리 구조

```
kr-institutional-flow/
├── SKILL.md
├── references/
│   ├── kr_investor_categories.md         # 한국 투자자 12분류 가이드
│   └── flow_interpretation_kr.md         # 수급 시그널 해석 프레임워크
└── scripts/
    ├── kr_institutional_flow_tracker.py   # 메인 오케스트레이터
    ├── investor_flow_analyzer.py          # 투자자별 매매동향 분석
    ├── foreign_flow_tracker.py            # 외국인 수급 심화 분석
    ├── accumulation_detector.py           # 수급 축적/이탈 감지
    ├── scorer.py                          # 수급 강도 스코어링
    ├── report_generator.py                # JSON/Markdown 리포트
    └── tests/
        └── test_institutional_flow.py
```

### 6.8 주요 모듈 설계

#### 6.8.1 investor_flow_analyzer.py

```python
# ─── 핵심 3분류 매핑 ───
INVESTOR_GROUPS = {
    'foreign': ['외국인'],
    'institutional': ['금융투자', '보험', '투신', '사모', '은행', '연기금'],
    'retail': ['개인'],
    'other': ['기타법인', '기타외국인', '기타금융', '국가'],
}

def get_daily_flow(ticker, period=20)
    """종목별 일별 투자자 매매동향 조회 (KRClient 활용)."""

def calc_net_buy(flow_data, investor_group)
    """특정 투자자 그룹의 일별 순매수 계산."""

def calc_consecutive_days(net_buys)
    """연속 순매수/순매도 일수 계산.
    Returns: {'direction': 'buy'|'sell'|'neutral', 'days': int, 'avg_amount': float}
    """

def score_foreign_flow(consecutive_data) -> dict
    """외국인 수급 시그널 점수 산출."""

def score_institutional_flow(consecutive_data) -> dict
    """기관 합계 수급 시그널 점수 산출."""
```

#### 6.8.2 foreign_flow_tracker.py

```python
def get_foreign_ownership(ticker)
    """외국인 지분율 + 한도소진율 조회 (KRClient)."""

def calc_ownership_trend(ticker, period=60)
    """외국인 지분율 60일 추세 분석."""

def detect_foreign_turning_point(daily_flow, window=5)
    """외국인 순매수→순매도 또는 역방향 전환점 감지.
    Returns: {'turning_point': bool, 'direction': str, 'date': str}
    """
```

#### 6.8.3 accumulation_detector.py

```python
def detect_accumulation(foreign_flow, inst_flow, retail_flow)
    """수급 축적 패턴 감지.

    Accumulation Pattern (강한 축적):
    - 외국인 순매수 + 기관 순매수 + 개인 순매도
    - 최소 5일 연속

    Distribution Pattern (이탈):
    - 외국인 순매도 + 기관 순매도 + 개인 순매수
    - 최소 5일 연속

    Returns: {'pattern': 'accumulation'|'distribution'|'neutral',
              'strength': float, 'days': int}
    """

def detect_retail_counter(retail_flow, smart_money_flow)
    """개인-스마트머니 역방향 감지."""
```

### 6.9 테스트 설계 (~45 tests)

| 테스트 클래스 | 테스트 수 | 검증 항목 |
|-------------|:--------:|----------|
| TestInvestorFlowAnalyzer | 7 | 3분류 매핑 + 순매수 계산 + 연속일 |
| TestForeignFlowSignal | 7 | 외국인 7등급 시그널 스코어링 |
| TestInstitutionalFlowSignal | 5 | 기관 시그널 스코어링 |
| TestForeignFlowTracker | 4 | 지분율 추세 + 전환점 감지 |
| TestAccumulationDetector | 5 | 축적/이탈/역방향 패턴 감지 |
| TestFlowConsistency | 5 | 수급 일관성 5구간 스코어링 |
| TestVolumeConfirmation | 4 | 거래량 확인 4구간 |
| TestFlowScorer | 4 | 종합 스코어 + 등급 5단계 |
| TestReportGenerator | 2 | JSON/Markdown 리포트 |
| TestConstants | 2 | 가중치 합 1.0 + 등급 범위 연속성 |
| **합계** | **~45** | |

---

## 7. 구현 순서

### 7.1 5-Step 구현 순서

```
Step 1: kr-economic-calendar (Low)     ← 가장 간단, ECOS API 학습
    ↓
Step 2: kr-earnings-calendar (Medium)  ← DART API 학습, 공시 조회
    ↓
Step 3: kr-earnings-trade (High)       ← 5팩터 스코어링 + 갭 분석
    ↓
Step 4: kr-institutional-flow (High)   ← 12분류 수급 + 축적 감지
    ↓
Step 5: 통합 테스트 + Phase 1 갭 수정
```

### 7.2 단계별 세부 계획

| Step | 스킬 | 작업 내용 | 파일 수 | 테스트 |
|:----:|------|----------|:-------:|:------:|
| 1 | kr-economic-calendar | SKILL.md + ref 1 + scripts 3 + test 1 | 6 | ~15 |
| 2 | kr-earnings-calendar | SKILL.md + ref 2 + scripts 3 + test 1 | 7 | ~20 |
| 3 | kr-earnings-trade | SKILL.md + ref 2 + scripts 6 + test 1 | 10 | ~40 |
| 4 | kr-institutional-flow | SKILL.md + ref 2 + scripts 6 + test 1 | 10 | ~45 |
| 5 | 통합 테스트 | 전체 테스트 실행 + 누락 수정 | 0 | 전체 |
| **합계** | | | **33+** | **~120** |

### 7.3 예상 구현 기간

| Step | 스킬 | 예상 기간 |
|:----:|------|:--------:|
| 1 | kr-economic-calendar | ~1일 |
| 2 | kr-earnings-calendar | ~2일 |
| 3 | kr-earnings-trade | ~3일 |
| 4 | kr-institutional-flow | ~3일 |
| 5 | 통합 테스트 | ~1일 |
| **합계** | | **~10일** |

---

## 8. Phase 간 의존성

### 8.1 Phase 5가 사용하는 Phase 1 공통 모듈

| KRClient 메서드 | 사용 스킬 | 용도 |
|----------------|----------|------|
| `get_ohlcv(ticker, period)` | kr-earnings-trade | 가격 데이터 (갭/추세/MA 계산) |
| `get_stock_info(ticker)` | 전체 | 시총, 업종 정보 |
| `get_investor_trading(ticker, period)` | kr-institutional-flow | 투자자별 매매동향 |
| `get_foreign_ownership(ticker)` | kr-institutional-flow, kr-earnings-trade | 외국인 지분율 |
| `get_dart_disclosures(ticker, period)` | kr-earnings-calendar, kr-earnings-trade | DART 공시 조회 |
| `search_stocks(query)` | kr-earnings-calendar | 종목 검색 |
| `get_market_cap(ticker)` | 전체 | 시총 필터 |

### 8.2 Phase 5 → Phase 8 연결

```
Phase 5 출력                     Phase 8 입력 (전략 통합)
───────────────                  ──────────────────────
kr-earnings-trade Grade A/B  →  kr-strategy-synthesizer (실적 모멘텀)
kr-institutional-flow 축적    →  kr-strategy-synthesizer (수급 확인)
kr-earnings-calendar 일정     →  kr-scenario-analyzer (이벤트 캘린더)
kr-economic-calendar 일정     →  kr-macro-regime (레짐 전환 트리거)
```

---

## 9. 위험 요소 & 대응

| 위험 | 영향도 | 대응 |
|------|:------:|------|
| DART API 키 없을 때 | Medium | 정적 목업 데이터로 테스트 실행 가능 |
| ECOS API 키 없을 때 | Low | 정적 캘린더만으로 기본 기능 제공 |
| PyKRX 투자자 매매동향 형식 변경 | Low | KRClient가 추상화하므로 영향 최소 |
| 한국 실적 공시 시간 파싱 이슈 | Medium | DART 공시시간 형식 표준화 로직 |
| 개별 기관명 비공개 (US 대비 단점) | Low | 카테고리별 합계로 충분한 시그널 생성 |

---

## 10. 검증 기준 (Gap Analysis 체크리스트)

- [ ] 4개 SKILL.md 파일 존재 + 내용 일치
- [ ] 7개 Reference 문서 존재
- [ ] 22개 스크립트 파일 존재 + 함수명 일치
- [ ] 4개 테스트 파일 존재 + 120+ 테스트 통과
- [ ] 모든 설계 상수 (가중치, 임계값, 등급) 코드와 100% 일치
- [ ] WEIGHTS.values() 합이 1.0 (kr-earnings-trade, kr-institutional-flow)
- [ ] 등급 범위 연속성 (max[i] + 1 == min[i-1])
- [ ] KRClient 메서드 호출 패턴 Phase 1-4와 일관
- [ ] 한국 특화 상수 반영 (시총 5,000억+, 외국인 보너스, 12분류 매핑)
