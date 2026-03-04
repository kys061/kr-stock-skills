# 한국 주식 스킬 - Phase 2 시장 분석 스킬 상세 설계

> **Feature**: kr-stock-skills (Phase 2)
> **Created**: 2026-02-27
> **Status**: Design Phase
> **Plan Reference**: `docs/01-plan/features/kr-stock-skills.plan.md` (섹션 3.2)
> **Phase 1 Reference**: `docs/02-design/features/kr-stock-skills.design.md`

---

## 1. 설계 개요

### 1.1 Phase 2 목표
**7개 시장 분석 스킬**을 한국 시장에 맞게 포팅한다.
US 스킬의 분석 방법론(스코어링, 시나리오 확률, 라이프사이클)은 보존하되,
데이터 소스를 Phase 1에서 구현한 `KRClient`로 교체한다.

### 1.2 설계 원칙
- **방법론 보존**: US 스킬의 스코어링 공식/가중치/임계값을 최대한 유지
- **KRClient 활용**: Phase 1 공통 모듈을 데이터 계층으로 일관 사용
- **자체 계산**: TraderMonty CSV, FINVIZ 등 US 전용 소스는 PyKRX 데이터로 자체 계산
- **한국 특화**: 기관/외국인 수급, KRX 업종 분류, 한국 테마주 반영
- **점진적 구현**: Low → Medium → High 복잡도 순서로 구현

### 1.3 Phase 2 스킬 목록

| # | KR 스킬명 | US 원본 | 복잡도 | 스크립트 | 데이터 소스 |
|---|-----------|---------|:------:|:--------:|-------------|
| 1 | kr-market-environment | market-environment-analysis | Low | 1개 | WebSearch + KRClient |
| 2 | kr-market-news-analyst | market-news-analyst | Medium | 0 | WebSearch |
| 3 | kr-sector-analyst | sector-analyst | Low | 0 | 차트 이미지 |
| 4 | kr-technical-analyst | technical-analyst | Low | 0 | 차트 이미지 |
| 5 | kr-market-breadth | market-breadth-analyzer | **High** | 6개 | KRClient (PyKRX) |
| 6 | kr-uptrend-analyzer | uptrend-analyzer | **High** | 6개 | KRClient (PyKRX) |
| 7 | kr-theme-detector | theme-detector | **High** | 8개 | KRClient (PyKRX) + WebSearch |

### 1.4 디렉토리 구조 (전체)

```
~/stock/skills/
├── _kr-common/                    # Phase 1 (구현 완료)
│   ├── kr_client.py
│   ├── providers/
│   ├── models/
│   ├── utils/
│   └── tests/
├── kr-market-environment/         # Skill 1
│   ├── SKILL.md
│   ├── references/
│   │   ├── indicators.md
│   │   └── analysis_patterns.md
│   └── scripts/
│       └── market_utils.py
├── kr-market-news-analyst/        # Skill 2
│   ├── SKILL.md
│   └── references/
│       ├── market_event_patterns.md
│       ├── trusted_kr_news_sources.md
│       └── kr_market_correlations.md
├── kr-sector-analyst/             # Skill 3
│   ├── SKILL.md
│   └── references/
│       └── kr_sector_rotation.md
├── kr-technical-analyst/          # Skill 4
│   ├── SKILL.md
│   └── references/
│       └── technical_analysis_framework.md
├── kr-market-breadth/             # Skill 5
│   ├── SKILL.md
│   ├── references/
│   │   └── breadth_methodology.md
│   └── scripts/
│       ├── kr_breadth_analyzer.py      # 메인 오케스트레이터
│       ├── breadth_calculator.py       # KOSPI/KOSDAQ 시장폭 계산
│       ├── scorer.py                   # 6-컴포넌트 스코어링
│       ├── report_generator.py         # JSON/Markdown 리포트
│       ├── history_tracker.py          # 점수 히스토리 관리
│       └── tests/
│           └── test_breadth.py
├── kr-uptrend-analyzer/           # Skill 6
│   ├── SKILL.md
│   ├── references/
│   │   └── uptrend_methodology.md
│   └── scripts/
│       ├── kr_uptrend_analyzer.py      # 메인 오케스트레이터
│       ├── uptrend_calculator.py       # 업종별 업트렌드 비율 계산
│       ├── scorer.py                   # 5-컴포넌트 스코어링
│       ├── report_generator.py         # JSON/Markdown 리포트
│       ├── history_tracker.py          # 점수 히스토리 관리
│       └── tests/
│           └── test_uptrend.py
└── kr-theme-detector/             # Skill 7
    ├── SKILL.md
    ├── references/
    │   ├── kr_themes.md                # 한국 테마 정의
    │   ├── kr_industry_codes.md        # KRX 업종 분류
    │   └── theme_methodology.md
    ├── scripts/
    │   ├── kr_theme_detector.py        # 메인 오케스트레이터
    │   ├── industry_data_collector.py  # KRX 업종/종목 데이터 수집
    │   ├── theme_classifier.py         # 종목 → 테마 분류
    │   ├── scorer.py                   # 3D 스코어링 (Heat/Lifecycle/Confidence)
    │   ├── report_generator.py         # JSON/Markdown 리포트
    │   ├── kr_themes.yaml              # 테마 정의 파일
    │   └── tests/
    │       └── test_theme.py
    └── config/
        └── default_theme_config.py
```

---

## 2. 공통 의존성

### 2.1 KRClient 메서드 매핑 (Phase 2 스킬별 사용)

| KRClient 메서드 | Skill 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|-----------------|:-------:|:-:|:-:|:-:|:-:|:-:|:-:|
| `get_ohlcv()` | | | | | ● | ● | ● |
| `get_ohlcv_multi()` | | | | | | | ● |
| `get_fundamentals_market()` | | | | | | | ● |
| `get_market_cap()` | | | | | | | ● |
| `get_index()` | ● | | | | ● | ● | ● |
| `get_index_fundamentals()` | ● | | | | | | |
| `get_index_constituents()` | | | | | ● | ● | |
| `get_sector_performance()` | ● | | ● | | | ● | ● |
| `get_investor_trading_market()` | ● | | | | | | |
| `get_global_index()` | ● | | | | | | |
| `get_fred()` | ● | | | | | | |
| `get_bond_yields()` | ● | | | | | | |
| `get_us_treasury()` | ● | | | | | | |
| `get_ticker_list()` | | | | | ● | ● | ● |

### 2.2 ta_utils 메서드 매핑

| ta_utils 메서드 | Skill 5 | 6 | 7 |
|----------------|:-------:|:-:|:-:|
| `sma()` | ● | ● | ● |
| `ema()` | | ● | |
| `rsi()` | | | ● |
| `macd()` | | | ● |
| `volume_ratio()` | ● | | ● |
| `rate_of_change()` | | ● | |
| `disparity()` | | | ● |

### 2.3 추가 의존성

```
# Phase 2 추가 (requirements.txt에 추가)
scipy>=1.10               # 통계 계산 (percentile, z-score)
pyyaml>=6.0               # 테마 정의 파일 (kr_themes.yaml)
```

---

## 3. Skill 1: kr-market-environment (시장 환경 분석)

### 3.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | market-environment-analysis |
| 복잡도 | Low |
| 주요 변경 | 한국 시장 지표 추가 (KOSPI/KOSDAQ/원달러/국고채) |
| 데이터 소스 | WebSearch (글로벌) + KRClient (한국) |

### 3.2 US 원본 → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| S&P 500, NASDAQ, Dow | KOSPI, KOSDAQ + 미국지수 유지 | KRClient `get_index()` |
| VIX | VKOSPI + VIX 병행 | KRClient `get_index('0060')` |
| USD/JPY, EUR/USD | **USD/KRW, EUR/KRW** 추가 | KRClient `get_global_index()` |
| US Treasury 2Y/10Y/30Y | **국고채 3Y/5Y/10Y** + US 유지 | KRClient `get_bond_yields()` |
| Sector rotation (GICS) | KRX 업종별 수익률 | KRClient `get_sector_performance()` |
| - (없음) | **기관/외국인 순매수 동향** | KRClient `get_investor_trading_market()` |
| - (없음) | **KOSPI PER 밴드 위치** | KRClient `get_index_fundamentals()` |

### 3.3 SKILL.md 핵심 구조

```markdown
# kr-market-environment

## 분석 프레임워크 (4차원 + 한국 특화 2차원)

### 기본 4차원 (US 원본 유지)
1. Trend Direction: 상승/하락/박스권
2. Risk Sentiment: Risk-on / Risk-off
3. Volatility: VKOSPI + VIX 기반 시장 불안도
4. Sector Rotation: 자금 흐름 방향

### 한국 특화 2차원 (신규)
5. 수급 동향: 기관/외국인 순매수 추세 (연속일수, 금액 규모)
6. 밸류에이션 위치: KOSPI PER 밴드 내 현재 위치 (저평가/적정/고평가)
```

### 3.4 scripts/market_utils.py

```python
"""한국 시장 환경 분석 유틸리티."""

import sys
sys.path.insert(0, '/path/to/stock/skills')
from _kr_common.kr_client import KRClient
from _kr_common.models.market import INDEX_CODES

def get_kr_market_snapshot() -> dict:
    """한국 시장 핵심 지표 스냅샷.

    Returns:
        {
            'kospi': {'close': float, 'change_pct': float, 'per': float, 'pbr': float},
            'kosdaq': {'close': float, 'change_pct': float, 'per': float, 'pbr': float},
            'usdkrw': float,
            'bond_yields': {'3Y': float, '5Y': float, '10Y': float},
            'investor_flow': {'institutional': float, 'foreign': float},
            'vkospi': float,
        }
    """

def get_per_band_position(index_code: str = '0001', years: int = 10) -> dict:
    """KOSPI PER 밴드 내 현재 위치 계산.

    Returns:
        {
            'current_per': float,
            'percentile': float,      # 0~100 (역사적 백분위)
            'zone': str,              # '저평가' / '적정' / '고평가' / '과열'
            'min_per': float,
            'max_per': float,
            'avg_per': float,
        }
    """

def categorize_vkospi(value: float) -> str:
    """VKOSPI 레벨 분류.

    10 미만: 극도 안정 → '매우 낮음'
    10~15:   안정      → '낮음'
    15~20:   보통      → '보통'
    20~25:   불안      → '높음'
    25~30:   경계      → '매우 높음'
    30 이상:  공포      → '극단적'
    """

def format_investor_flow(institutional: float, foreign: float) -> str:
    """수급 동향 포맷팅 (억원 단위, 연속일수 포함)."""
```

### 3.5 출력 포맷

```markdown
# 한국 시장 환경 분석 리포트

## Executive Summary
- [3-5줄 핵심 요약]

## 1. 한국 시장 현황
### KOSPI / KOSDAQ
### 수급 동향 (기관/외국인)
### 밸류에이션 (PER 밴드 위치)
### VKOSPI (변동성)

## 2. 글로벌 시장
### 미국 (S&P 500 / NASDAQ)
### 아시아 (니케이 / 항셍 / 상해)
### 유럽

## 3. 환율 & 원자재
### USD/KRW, EUR/KRW
### WTI, 금

## 4. 채권 시장
### 한국 국고채 (3Y/5Y/10Y)
### 미국 국채 (2Y/10Y)
### 한미 금리차

## 5. 리스크 팩터 분석
## 6. 투자 전략 시사점
```

---

## 4. Skill 2: kr-market-news-analyst (시장 뉴스 분석)

### 4.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | market-news-analyst |
| 복잡도 | Medium |
| 주요 변경 | 한국 뉴스 소스 추가, 한국 시장 이벤트 패턴 |
| 데이터 소스 | WebSearch (한국+글로벌 뉴스) |

### 4.2 US 원본 → KR 변경점

| US 원본 | KR 변경 | 비고 |
|---------|---------|------|
| FOMC/Fed 정책 | **한은 금통위** + FOMC 병행 | 기준금리 결정 |
| CPI, NFP, GDP (미국) | **한국 CPI, 고용, GDP** + 미국 유지 | 양국 지표 모니터링 |
| Mega-Cap (AAPL, MSFT...) | **삼성전자, SK하이닉스, NAVER, 카카오** | 시총 상위 |
| Bloomberg, Reuters, WSJ | **한경, 매경, 연합인포맥스, 조선비즈** | 한국 Tier 1 소스 |
| SEC filings | **DART 공시** | 5% 보고, 실적 공시 등 |
| - (없음) | **외국인 대규모 매매 이벤트** | 한국 특화 |
| - (없음) | **정책/규제 변경** (공매도 재개 등) | 한국 특화 |

### 4.3 뉴스 소스 우선순위 (한국)

```markdown
## 한국 뉴스 소스

### Tier 1: 공식 소스
- 한국은행 (bok.or.kr) - 금통위, 기준금리
- 금융위원회 (fsc.go.kr) - 금융 규제/정책
- 통계청 (kostat.go.kr) - 경제지표 (CPI, GDP)
- DART (dart.fss.or.kr) - 기업 공시

### Tier 2: 경제 전문지
- 한국경제 (hankyung.com)
- 매일경제 (mk.co.kr)
- 연합인포맥스 (einfomax.co.kr)
- 조선비즈 (biz.chosun.com)
- 이데일리 (edaily.co.kr)

### Tier 3: 증권사 리서치
- 키움증권 리서치
- 삼성증권 리서치
- NH투자증권 리서치
```

### 4.4 임팩트 스코어 계산 (한국 시장 적용)

```
Impact Score = (Price Impact × Breadth Multiplier) × Forward Modifier

Price Impact Score (한국 시장 기준):
- Severe: 10점 (KOSPI ±2%+, 원달러 ±2%+)
- Major:   7점 (KOSPI ±1~2%, 원달러 ±1~2%)
- Moderate: 4점 (KOSPI ±0.5~1%)
- Minor:   2점 (KOSPI ±0.2~0.5%)
- Negligible: 1점 (<0.2%)

Breadth Multiplier:
- Systemic: 3x (복수 자산/글로벌 영향)
- Cross-Asset: 2x (주식 + 환율/채권)
- Sector-Wide: 1.5x (업종 전체)
- Stock-Specific: 1x (개별 종목)

Forward Modifier (한국 특화 추가):
- 정책 레짐 전환: +50% (금리 인하/인상 전환, 공매도 정책 변경)
- 외국인 수급 전환: +30% (연속 순매수 → 순매도 전환 등)
- 추세 확인: +25%
- 단발 이벤트: 0%
```

### 4.5 한국 시장 이벤트 카테고리

```markdown
1. 한은 금통위 (연 8회) - 기준금리 결정
2. 경제지표 (CPI, GDP, 수출입, 고용)
3. 대형주 실적 (삼성전자, SK하이닉스, 현대차, LG에너지솔루션)
4. 외국인 수급 이벤트 (MSCI 리밸런싱, 대규모 순매수/순매도)
5. 정책/규제 (공매도, 밸류업 프로그램, 세제 변경)
6. 지정학 리스크 (남북관계, 미중 갈등의 반도체 영향)
7. 원달러 환율 이벤트 (급등/급락, 정부 개입 시사)
```

### 4.6 출력 포맷

```markdown
# 한국 시장 뉴스 분석 리포트 [날짜]

## Executive Summary
## Market Impact Rankings (표)
## 상세 이벤트 분석
  - 한국 시장 이벤트 (한은, 공시, 정책)
  - 글로벌 이벤트 (FOMC, 미국 지표)
## 테마별 종합 (Thematic Synthesis)
## 수급 동향 심층 분석
## Forward-Looking Implications
```

---

## 5. Skill 3: kr-sector-analyst (업종 분석)

### 5.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | sector-analyst |
| 복잡도 | Low |
| 주요 변경 | 한국 업종 분류 체계, KRX 업종 지수 기준 |
| 데이터 소스 | 차트 이미지 (사용자 제공) |

### 5.2 US 원본 → KR 변경점

| US 원본 | KR 변경 |
|---------|---------|
| GICS 11 Sectors | **KRX 업종 분류** (약 30개) |
| S&P 500 sector ETFs | **KOSPI 업종 지수** |
| US 경기 순환 모델 | **한국 경기 순환 모델** (수출 주도, 반도체 사이클) |
| Cyclical/Defensive 분류 | 한국 시장 경기 민감/방어 분류 |

### 5.3 한국 업종 분류 (경기 순환 기준)

```markdown
## 경기 민감주 (Cyclical)
- 반도체 (삼성전자, SK하이닉스)
- 자동차 (현대차, 기아)
- 철강 (POSCO)
- 화학 (LG화학, 롯데케미칼)
- 건설 (현대건설, 대우건설)
- 조선 (HD한국조선, 삼성중공업)
- 은행 (KB금융, 신한지주)

## 방어주 (Defensive)
- 통신 (SK텔레콤, KT, LG유플러스)
- 유틸리티 (한국전력, 한국가스공사)
- 필수소비재 (CJ제일제당, 오뚜기)
- 제약/바이오 (삼성바이오, 셀트리온)

## 성장주 (Growth)
- 2차전지 (LG에너지솔루션, 삼성SDI)
- 인터넷/플랫폼 (NAVER, 카카오)
- 엔터/콘텐츠 (하이브, SM엔터)
- AI/소프트웨어

## 원자재/에너지
- 정유 (SK이노베이션, S-Oil)
- 해운 (HMM, 팬오션)
```

### 5.4 references/kr_sector_rotation.md 핵심 내용

```markdown
# 한국 시장 경기 순환과 업종 로테이션

## 1. 한국 경기 순환 특징
- **수출 주도**: GDP의 40%+ 수출, 반도체/자동차/조선이 핵심
- **반도체 슈퍼사이클**: 삼성전자+SK하이닉스 = KOSPI 시총 30%+
- **원달러 환율 민감도**: 환율 하락(원 강세) = KOSPI 상승 높은 상관관계
- **외국인 지분율**: KOSPI 외국인 지분 30%+ → 외국인 수급이 시장 방향 결정

## 2. 경기 국면별 선도 업종
| 국면 | 선도 업종 | 후행 업종 |
|------|-----------|-----------|
| 초기 회복 | 반도체, 자동차, 건설 | 방어주, 유틸리티 |
| 중기 확장 | IT, 2차전지, 금융 | - (전반적 상승) |
| 후기 과열 | 조선, 원자재, 은행 | 성장주, IT |
| 침체 | 통신, 유틸리티, 필수소비재 | 경기민감주 전반 |

## 3. 한국 특유의 로테이션 패턴
- 반도체 업사이클 → IT부품/장비 → PCB → 소재 (순서적 파급)
- 외국인 순매수 시작 → 대형주 → 중형주 → 소형주 (사이즈 로테이션)
- 환율 하락(원 강세) → 내수주 상승, 환율 상승(원 약세) → 수출주 상승
```

---

## 6. Skill 4: kr-technical-analyst (기술적 분석)

### 6.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | technical-analyst |
| 복잡도 | Low |
| 주요 변경 | 가격제한폭 ±30% 반영, 한국 특화 지표 참조 추가 |
| 데이터 소스 | 차트 이미지 (사용자 제공) |

### 6.2 US 원본 → KR 변경점

| US 원본 | KR 변경 |
|---------|---------|
| 동일한 6-단계 분석 프레임워크 | **그대로 유지** |
| 무제한 가격 변동 | **가격제한폭 ±30%** 감안 |
| After-hours trading 고려 | **없음** (한국은 장중만) |
| - (없음) | **외국인/기관 수급 참조** (보조 지표로) |
| Weekly chart | Weekly + **Daily** 지원 |

### 6.3 한국 시장 특화 분석 보조 항목

```markdown
## 추가 참조 지표 (차트 외 보조 정보)
SKILL.md에서 선택적으로 KRClient 데이터 참조 가능:

1. **외국인 순매수/순매도 동향**: 최근 20일 추세
   - KRClient.get_investor_trading(ticker, start)

2. **기관 순매수/순매도 동향**: 최근 20일 추세
   - KRClient.get_investor_trading(ticker, start)

3. **공매도 잔고 추세**: 공매도 비율 변화
   - KRClient.get_short_selling(ticker, start)

※ 이 보조 지표는 차트 분석의 시나리오 확률 보정에만 사용.
   순수 차트 분석이 주(Primary), 수급은 보조(Secondary).
```

### 6.4 가격제한폭 관련 분석 규칙

```markdown
## 한국 시장 가격제한폭 주의사항

1. **상한가/하한가 캔들 해석**
   - 상한가(+30%): 극도의 매수세. 다음 날 갭업 가능성 높음
   - 하한가(-30%): 극도의 매도세. VI(Volatility Interruption) 발동 가능

2. **가격 변동폭 감안**
   - US 대비 일일 변동폭 제한 → 캔들 길이 해석 시 주의
   - ±30%는 이론상 상한. 실제 대형주는 ±3~5%가 일반적

3. **VI (Volatility Interruption)**
   - 정적 VI: 전일 종가 대비 ±10% (KOSPI) / ±15% (KOSDAQ)
   - 동적 VI: 직전 체결가 대비 ±3% (KOSPI) / ±6% (KOSDAQ)
   - VI 발동 = 급변동 신호 → 차트에서 갭/긴 캔들로 표현
```

---

## 7. Skill 5: kr-market-breadth (시장폭 분석) — **핵심 스킬**

### 7.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | market-breadth-analyzer |
| 복잡도 | **High** |
| 핵심 차이 | TraderMonty CSV 없음 → PyKRX 데이터로 자체 계산 |
| 데이터 소스 | KRClient (PyKRX) |
| 스크립트 | 6개 파일 |
| 분석 대상 | KOSPI 200 + KOSDAQ 150 구성종목 |

### 7.2 데이터 소스 전환

```
US 원본 (TraderMonty CSV):
  - market_breadth_data.csv (사전 계산된 ~2,500행)
  - Breadth_Index_Raw, Breadth_Index_200MA, Breadth_Index_8MA, etc.
  → 이미 계산된 데이터를 다운로드하여 사용

KR 대체 (자체 계산):
  - KRClient.get_index_constituents('0028')  # KOSPI 200 구성종목
  - KRClient.get_index_constituents('0177')  # KOSDAQ 150 구성종목
  - KRClient.get_ohlcv(ticker, start)         # 각 종목 OHLCV
  → 원시 데이터에서 시장폭 지표를 직접 계산
```

### 7.3 시장폭 지표 자체 계산 방법

```python
"""시장폭 계산 로직 (breadth_calculator.py 핵심)"""

def calculate_breadth_index(market: str = 'KOSPI200') -> dict:
    """시장폭 지수 계산.

    1. 구성종목 리스트 가져오기
       - KOSPI200: get_index_constituents('0028') → ~200종목
       - KOSDAQ150: get_index_constituents('0177') → ~150종목

    2. 각 종목의 200일 이동평균 위치 계산
       - get_ohlcv(ticker, 1년전~오늘)
       - sma(close, 200) 계산
       - close > sma200 이면 'above' (업트렌드)

    3. Breadth Index 계산
       - Raw = (200MA 위 종목 수 / 전체 종목 수) × 100
       - 8MA = sma(Raw, 8)   # 8일 이동평균 (단기 추세)
       - 200MA = sma(Raw, 200) # 200일 이동평균 (장기 추세)

    4. 추가 신호 계산
       - Trend = 200MA 방향 (상승/하락/횡보)
       - Peak/Trough 감지 (8MA 기준 고점/저점)
       - Bearish Signal = 8MA < 40 AND 하락 추세

    Returns:
        {
            'date': str,
            'market': str,            # 'KOSPI200' or 'KOSDAQ150'
            'breadth_raw': float,     # 0~100
            'breadth_8ma': float,     # 8일 이동평균
            'breadth_200ma': float,   # 200일 이동평균
            'trend': str,             # 'up' / 'down' / 'flat'
            'is_peak': bool,
            'is_trough': bool,
            'bearish_signal': bool,
            'total_stocks': int,
            'above_200ma': int,
            'sp500_price': float,     # → kospi_price로 대체
        }
    """
```

### 7.4 6-컴포넌트 스코어링 (US 방법론 보존)

| 컴포넌트 | 가중치 | 핵심 신호 | KR 적용 |
|----------|:------:|-----------|---------|
| Breadth Level & Trend | 25% | 8MA 레벨 + 200MA 추세 + 8MA 방향 | KOSPI200 기준 |
| 8MA vs 200MA Crossover | 20% | MA 갭 방향과 크기 | 동일 |
| Peak/Trough Cycle | 20% | 시장폭 사이클 위치 | 동일 |
| Bearish Signal | 15% | 백테스트 기반 약세 신호 | 한국 데이터로 재보정 |
| Historical Percentile | 10% | 전체 히스토리 내 백분위 | 한국 히스토리 |
| 지수 Divergence | 10% | 20일+60일 지수 vs 시장폭 괴리 | **KOSPI** vs Breadth |

### 7.5 Health Zone 매핑 (동일)

| 점수 | 건강 등급 | 주식 비중 권고 |
|:----:|-----------|:-------------:|
| 80-100 | Strong (강세) | 90-100% |
| 60-79 | Healthy (건강) | 75-90% |
| 40-59 | Neutral (중립) | 60-75% |
| 20-39 | Weakening (약화) | 40-60% |
| 0-19 | Critical (위험) | 25-40% |

### 7.6 스크립트 상세 설계

#### kr_breadth_analyzer.py (메인 오케스트레이터)

```python
"""한국 시장폭 분석기 메인.

Usage:
    python3 kr_breadth_analyzer.py --market KOSPI200 --output-dir reports/
    python3 kr_breadth_analyzer.py --market KOSDAQ150 --output-dir reports/
    python3 kr_breadth_analyzer.py --market ALL --output-dir reports/

Arguments:
    --market: KOSPI200, KOSDAQ150, ALL (둘 다)
    --output-dir: 리포트 출력 디렉토리
    --history-file: 히스토리 파일 경로 (기본: ~/.cache/kr-stock-skills/breadth_history.json)
    --lookback-days: 시장폭 계산 기간 (기본: 250, 약 1년)
"""

import sys
sys.path.insert(0, '/path/to/stock/skills')
from _kr_common.kr_client import KRClient
from _kr_common.models.market import INDEX_CODES

class KRBreadthAnalyzer:
    def __init__(self, market='KOSPI200', output_dir='reports/'):
        self.client = KRClient()
        self.market = market
        self.output_dir = output_dir

    def run(self) -> dict:
        """전체 분석 실행.

        Steps:
        1. get_index_constituents()로 구성종목 가져오기
        2. breadth_calculator로 시장폭 계산
        3. scorer로 6-컴포넌트 스코어 계산
        4. history_tracker로 히스토리 업데이트
        5. report_generator로 JSON/MD 리포트 생성
        """
```

#### breadth_calculator.py

```python
"""시장폭 지표 계산기.

KOSPI 200 / KOSDAQ 150 구성종목의 시장폭을 계산.
US의 TraderMonty CSV 데이터를 PyKRX 원시 데이터로 대체.

성능 최적화:
- 종목별 OHLCV를 병렬이 아닌 순차 호출 (PyKRX 크롤링 제약)
- request_delay 준수 (기본 0.1초)
- 캐시 활용으로 재실행 시 속도 향상
- KOSPI 200 기준 예상 소요시간: 약 2-3분 (첫 실행)
"""

class BreadthCalculator:
    def __init__(self, client: KRClient, market: str = 'KOSPI200'):
        self.client = client
        self.market = market
        self.index_code = {'KOSPI200': '0028', 'KOSDAQ150': '0177'}[market]

    def calculate(self, lookback_days: int = 250) -> dict:
        """시장폭 지표 계산.

        Returns:
            {
                'date': str,
                'market': str,
                'breadth_raw': float,
                'breadth_8ma': float,
                'breadth_200ma': float,
                'trend': str,
                'is_peak': bool,
                'is_trough': bool,
                'bearish_signal': bool,
                'index_price': float,
                'total_stocks': int,
                'above_200ma': int,
                'history': list,  # 일별 breadth_raw 시계열 (lookback 기간)
            }
        """

    def _get_constituents(self) -> list:
        """지수 구성종목 코드 리스트."""
        return self.client.get_index_constituents(self.index_code)

    def _calculate_daily_breadth(self, tickers: list, date: str) -> float:
        """특정일의 시장폭 (200MA 위 종목 비율) 계산.

        각 종목에 대해:
        1. 최근 250일 OHLCV 조회
        2. 200일 SMA 계산
        3. 당일 종가 > 200SMA 이면 카운트
        4. 비율 = count / total × 100
        """

    def _detect_peaks_troughs(self, breadth_8ma_series: list) -> dict:
        """8MA 기준 고점/저점 탐지."""

    def _detect_bearish_signal(self, breadth_8ma: float, trend: str) -> bool:
        """약세 신호 탐지: 8MA < 40 AND 하락 추세."""
```

#### scorer.py

```python
"""6-컴포넌트 스코어 계산기.

US market-breadth-analyzer의 스코어링 로직을 그대로 보존.
가중치: Breadth(25%) + Crossover(20%) + Cycle(20%) + Bearish(15%) + Percentile(10%) + Divergence(10%)
"""

class BreadthScorer:
    WEIGHTS = {
        'breadth_level': 0.25,
        'crossover': 0.20,
        'cycle': 0.20,
        'bearish': 0.15,
        'percentile': 0.10,
        'divergence': 0.10,
    }

    def score(self, breadth_data: dict) -> dict:
        """종합 점수 계산.

        Returns:
            {
                'composite_score': float,       # 0~100
                'health_zone': str,             # 'Strong'~'Critical'
                'equity_exposure': str,          # '90-100%' 등
                'components': {
                    'breadth_level': {'score': float, 'weight': float, 'detail': str},
                    'crossover': {...},
                    'cycle': {...},
                    'bearish': {...},
                    'percentile': {...},
                    'divergence': {...},
                },
                'strongest_component': str,
                'weakest_component': str,
            }
        """

    def _score_breadth_level(self, raw: float, ma8: float, ma200: float, trend: str) -> float:
        """Breadth Level & Trend (25%).

        8MA 레벨 기준:
        - 8MA >= 70: 기본 80점
        - 8MA >= 50: 기본 60점
        - 8MA >= 30: 기본 40점
        - 8MA < 30:  기본 20점

        보정:
        - 200MA 상승추세: +10
        - 8MA 상승 방향: +10
        """

    def _score_crossover(self, ma8: float, ma200: float, prev_gap: float) -> float:
        """8MA vs 200MA Crossover (20%).

        갭 = 8MA - 200MA
        갭 > 0 AND 확대중: 90점
        갭 > 0 AND 축소중: 60점
        갭 < 0 AND 축소중: 40점
        갭 < 0 AND 확대중: 10점
        """

    def _score_cycle(self, is_peak: bool, is_trough: bool, ma8_direction: str) -> float:
        """Peak/Trough Cycle (20%)."""

    def _score_bearish(self, bearish_signal: bool) -> float:
        """Bearish Signal (15%). True=0점, False=100점."""

    def _score_percentile(self, raw: float, history: list) -> float:
        """Historical Percentile (10%). scipy.stats.percentileofscore 사용."""

    def _score_divergence(self, index_prices: list, breadth_history: list) -> float:
        """지수 Divergence (10%). 20일+60일 윈도우."""
```

#### report_generator.py / history_tracker.py

```python
# report_generator.py
"""JSON + Markdown 리포트 생성.

출력 파일:
- kr_breadth_KOSPI200_YYYY-MM-DD_HHMMSS.json
- kr_breadth_KOSPI200_YYYY-MM-DD_HHMMSS.md
"""

# history_tracker.py
"""점수 히스토리 관리. 최대 30개 엔트리 유지.

파일: ~/.cache/kr-stock-skills/breadth_history.json
용도: 점수 추세 (개선중/악화중/안정) 판단
"""
```

### 7.7 실행 및 출력 예시

```bash
# KOSPI 200 시장폭 분석
python3 skills/kr-market-breadth/scripts/kr_breadth_analyzer.py \
  --market KOSPI200 --output-dir reports/

# 예상 소요시간: 2-3분 (200종목 × OHLCV 조회)
```

```markdown
# 한국 시장폭 분석 리포트 - KOSPI 200

## 종합 점수: 72/100 (Healthy)
## 권장 주식 비중: 75-90%

## 컴포넌트 상세
| 컴포넌트 | 점수 | 가중치 | 판정 |
|----------|:----:|:-----:|------|
| Breadth Level & Trend | 78 | 25% | 8MA=62.5, 200MA 상승 |
| 8MA vs 200MA Crossover | 70 | 20% | 갭 +8.3, 확대중 |
| Peak/Trough Cycle | 65 | 20% | 중간 구간 |
| Bearish Signal | 100 | 15% | 신호 없음 |
| Historical Percentile | 55 | 10% | 상위 55% |
| KOSPI Divergence | 60 | 10% | 경미한 괴리 |

## 시장폭 현황
- KOSPI 200 중 200MA 위: 128개 (64.0%)
- 8일 평균: 62.5%
- 200일 평균: 54.2%
- 추세: 상승

## 히스토리
[최근 10회 점수 추이 + 추세 방향]
```

---

## 8. Skill 6: kr-uptrend-analyzer (업트렌드 분석)

### 8.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | uptrend-analyzer |
| 복잡도 | **High** |
| 핵심 차이 | Monty's CSV 없음 → KRX 업종별 자체 계산 |
| 데이터 소스 | KRClient (PyKRX) |
| 스크립트 | 6개 파일 |
| 분석 대상 | KRX 업종 지수별 구성종목 |

### 8.2 데이터 소스 전환

```
US 원본 (Monty's Uptrend Dashboard):
  - ~2,800 US 주식 × 11 GICS 섹터
  - 사전 계산된 CSV (각 섹터별 uptrend ratio)

KR 대체 (자체 계산):
  - KRX 업종 지수별 구성종목 (PyKRX)
  - 각 종목의 업트렌드 여부를 직접 판정
  - 업종별 업트렌드 비율 계산
```

### 8.3 한국 업종 분류 (US 11 GICS → KRX 업종)

```python
# US: 11 GICS Sectors
US_SECTORS = [
    'Technology', 'Healthcare', 'Financials', 'Consumer Discretionary',
    'Communication', 'Industrials', 'Consumer Staples', 'Energy',
    'Utilities', 'Real Estate', 'Materials'
]

# KR: KRX 주요 업종 (약 20개로 그룹핑)
KR_SECTORS = {
    'cyclical': {  # 경기민감
        '반도체': ['삼성전자', 'SK하이닉스', ...],        # KOSPI 업종지수에서 매핑
        '자동차': ['현대차', '기아', ...],
        '철강': ['POSCO홀딩스', ...],
        '화학': ['LG화학', '롯데케미칼', ...],
        '건설': ['현대건설', 'GS건설', ...],
        '조선': ['HD한국조선해양', ...],
        '기계': ['두산에너빌리티', ...],
    },
    'defensive': {  # 방어
        '통신': ['SK텔레콤', 'KT', ...],
        '유틸리티': ['한국전력', ...],
        '필수소비재': ['CJ제일제당', ...],
        '제약/바이오': ['삼성바이오로직스', '셀트리온', ...],
    },
    'growth': {  # 성장
        '2차전지': ['LG에너지솔루션', '삼성SDI', ...],
        '인터넷': ['NAVER', '카카오', ...],
        'IT서비스': ['삼성SDS', ...],
    },
    'financial': {  # 금융
        '은행': ['KB금융', '신한지주', ...],
        '보험': ['삼성화재', '현대해상', ...],
        '증권': ['키움증권', '미래에셋', ...],
    },
}

# Cyclical/Defensive/Commodity 그룹핑 (US 원본과 동일한 분류 체계)
KR_SECTOR_GROUPS = {
    'Cyclical': ['반도체', '자동차', '철강', '화학', '건설', '조선', '기계'],
    'Defensive': ['통신', '유틸리티', '필수소비재', '제약/바이오'],
    'Growth': ['2차전지', '인터넷', 'IT서비스'],
    'Financial': ['은행', '보험', '증권'],
}
```

### 8.4 업트렌드 판정 기준

```python
def is_uptrend(ohlcv_df: pd.DataFrame) -> bool:
    """종목이 업트렌드인지 판정.

    US 원본과 동일한 기준:
    1. 종가 > 200일 SMA
    2. 200일 SMA 기울기 > 0 (상승 추세)
    3. 종가 > 50일 SMA (보조 확인)

    판정: 조건 1 AND 조건 2 충족 시 업트렌드
    """
```

### 8.5 5-컴포넌트 스코어링 (US 방법론 보존)

| 컴포넌트 | 가중치 | 핵심 신호 | KR 적용 |
|----------|:------:|-----------|---------|
| Market Breadth (Overall) | 30% | 전체 업트렌드 비율 + 추세 방향 | KRX 전체 |
| Sector Participation | 25% | 업트렌드 업종 수 + 비율 편차 | KRX 업종별 |
| Sector Rotation | 15% | 경기민감 vs 방어 균형 | KR 업종 분류 |
| Momentum | 20% | 기울기 방향 + 가속도 | EMA(3) 스무딩 |
| Historical Context | 10% | 히스토리 내 백분위 | KR 히스토리 |

### 8.6 Warning System (US 동일)

```python
WARNINGS = {
    'late_cycle': {
        'condition': '원자재 평균 > 경기민감 AND 방어',
        'penalty': -5,
        'description': '후기 사이클 경고'
    },
    'high_spread': {
        'condition': '업종간 최대-최소 스프레드 > 40pp',
        'penalty': -3,
        'description': '높은 편차 경고'
    },
    'divergence': {
        'condition': '그룹 내 표준편차 높음, 스프레드 > 20pp',
        'penalty': -3,
        'description': '다이버전스 경고'
    },
}
# 최대 감점: -10, 복수 경고 시 +1 할인
```

### 8.7 스크립트 상세 설계

#### kr_uptrend_analyzer.py (메인)

```python
"""한국 업트렌드 분석기.

Usage:
    python3 kr_uptrend_analyzer.py --output-dir reports/

예상 소요시간: 3-5분 (업종별 종목 OHLCV 조회)
"""

class KRUptrendAnalyzer:
    def run(self) -> dict:
        """
        1. KRX 업종별 구성종목 가져오기
        2. 각 종목 업트렌드 여부 판정
        3. 업종별 업트렌드 비율 계산
        4. 5-컴포넌트 스코어 계산
        5. 경고 시스템 적용
        6. 리포트 생성
        """
```

#### uptrend_calculator.py

```python
"""업종별 업트렌드 비율 계산기.

KRX 업종 지수에서 구성종목을 가져와
각 종목의 업트렌드 여부를 판정하고 업종별 비율을 산출.
"""

class UptrendCalculator:
    def calculate_all_sectors(self) -> dict:
        """전체 업종 업트렌드 비율 계산.

        Returns:
            {
                '반도체': {'ratio': 72.5, 'total': 40, 'uptrend': 29, 'group': 'Cyclical'},
                '자동차': {'ratio': 65.0, 'total': 20, 'uptrend': 13, 'group': 'Cyclical'},
                ...
            }
        """

    def calculate_overall_ratio(self, sector_data: dict) -> float:
        """전체 시장 업트렌드 비율 (시총 가중 또는 단순 평균)."""
```

### 8.8 출력 포맷

```markdown
# 한국 업트렌드 분석 리포트

## 종합 점수: 65/100 (Bull-Lower)
## 권장 노출도: 80-100%

## 업종 히트맵
| 업종 | 그룹 | 업트렌드 비율 | 종목수 | 상태 |
|------|------|:------------:|:-----:|------|
| 반도체 | Cyclical | 72.5% | 29/40 | 🟢 |
| 2차전지 | Growth | 68.0% | 17/25 | 🟢 |
| 자동차 | Cyclical | 55.0% | 11/20 | 🟡 |
| 통신 | Defensive | 40.0% | 4/10 | 🟡 |
| 건설 | Cyclical | 25.0% | 5/20 | 🔴 |
...

## 컴포넌트 상세
## 경고 시스템
## 모멘텀 & 로테이션 신호
```

---

## 9. Skill 7: kr-theme-detector (테마 탐지) — **최고 복잡도**

### 9.1 개요

| 항목 | 값 |
|------|-----|
| US 원본 | theme-detector |
| 복잡도 | **High** (Phase 2 최고) |
| 핵심 차이 | FINVIZ 없음 → KRX 업종/종목 데이터로 자체 구성 |
| 데이터 소스 | KRClient (PyKRX) + WebSearch (뉴스 확인) |
| 스크립트 | 8개 파일 |

### 9.2 데이터 소스 전환

```
US 원본:
  - FINVIZ: ~145 industries, 주가/거래량/시총 데이터
  - Uptrend Dashboard: 섹터별 업트렌드 비율
  - FMP API: P/E 밸류에이션
  - WebSearch: 뉴스 내러티브 확인

KR 대체:
  - KRClient.get_ticker_list(): 전체 상장 종목 (시총/업종 포함)
  - KRClient.get_ohlcv(): 종목별 OHLCV (모멘텀/거래량 계산)
  - KRClient.get_fundamentals_market(): PER/PBR (밸류에이션)
  - KRClient.get_sector_performance(): 업종별 수익률
  - KRClient.get_market_cap(): 시총 (가중 평균용)
  - WebSearch: 한국 뉴스 내러티브 확인
```

### 9.3 한국 테마 정의 (kr_themes.yaml)

```yaml
# 한국 시장 테마 정의 (14개 + 확장 가능)
themes:
  ai_semiconductor:
    name: "AI/반도체"
    description: "AI 인프라 및 반도체 밸류체인"
    industries:  # KRX 업종 매핑
      - "반도체"
      - "전자부품"
      - "IT하드웨어"
    representative_stocks:
      - {ticker: "005930", name: "삼성전자", role: "core"}
      - {ticker: "000660", name: "SK하이닉스", role: "core"}
      - {ticker: "042700", name: "한미반도체", role: "sub"}
      - {ticker: "403870", name: "HPSP", role: "sub"}
    related_etfs:
      - {ticker: "091160", name: "KODEX 반도체"}
      - {ticker: "091170", name: "KODEX 은행"}

  secondary_battery:
    name: "2차전지"
    description: "배터리 소재-셀-모듈 밸류체인"
    industries:
      - "전기장비"
      - "화학"
    representative_stocks:
      - {ticker: "373220", name: "LG에너지솔루션", role: "core"}
      - {ticker: "006400", name: "삼성SDI", role: "core"}
      - {ticker: "051910", name: "LG화학", role: "sub"}
      - {ticker: "247540", name: "에코프로비엠", role: "sub"}
    related_etfs:
      - {ticker: "305720", name: "KODEX 2차전지산업"}

  bio_pharma:
    name: "바이오/제약"
    description: "바이오시밀러, 신약개발, CDMO"
    industries:
      - "제약"
      - "바이오"
    representative_stocks:
      - {ticker: "207940", name: "삼성바이오로직스", role: "core"}
      - {ticker: "068270", name: "셀트리온", role: "core"}
      - {ticker: "091990", name: "셀트리온헬스케어", role: "sub"}

  auto_mobility:
    name: "자동차/모빌리티"
    description: "완성차, 자율주행, 전기차, 부품"
    industries:
      - "자동차"
      - "자동차부품"
    representative_stocks:
      - {ticker: "005380", name: "현대차", role: "core"}
      - {ticker: "000270", name: "기아", role: "core"}
      - {ticker: "012330", name: "현대모비스", role: "sub"}

  defense:
    name: "방산"
    description: "방위산업, 우주항공"
    industries:
      - "기계"
      - "전기장비"
    representative_stocks:
      - {ticker: "012450", name: "한화에어로스페이스", role: "core"}
      - {ticker: "047810", name: "한국항공우주", role: "core"}
      - {ticker: "082740", name: "HSD엔진", role: "sub"}

  k_content:
    name: "K-컨텐츠"
    description: "엔터테인먼트, 게임, 미디어"
    industries:
      - "미디어"
      - "오락"
    representative_stocks:
      - {ticker: "352820", name: "하이브", role: "core"}
      - {ticker: "041510", name: "SM엔터", role: "sub"}
      - {ticker: "263750", name: "펄어비스", role: "sub"}

  shipbuilding:
    name: "조선/해운"
    description: "조선, LNG, 해운"
    industries:
      - "조선"
      - "해운"
    representative_stocks:
      - {ticker: "329180", name: "HD현대중공업", role: "core"}
      - {ticker: "042660", name: "한화오션", role: "core"}
      - {ticker: "011200", name: "HMM", role: "sub"}

  financial_valueup:
    name: "금융/밸류업"
    description: "은행, 보험, 증권 (밸류업 프로그램 수혜)"
    industries:
      - "은행"
      - "보험"
      - "증권"
    representative_stocks:
      - {ticker: "105560", name: "KB금융", role: "core"}
      - {ticker: "055550", name: "신한지주", role: "core"}
      - {ticker: "316140", name: "우리금융지주", role: "sub"}

  internet_platform:
    name: "인터넷/플랫폼"
    description: "포털, 이커머스, 핀테크"
    industries:
      - "인터넷"
      - "소프트웨어"
    representative_stocks:
      - {ticker: "035420", name: "NAVER", role: "core"}
      - {ticker: "035720", name: "카카오", role: "core"}

  steel_materials:
    name: "철강/소재"
    description: "철강, 비철금속, 화학소재"
    industries:
      - "철강"
      - "비철금속"
      - "화학"
    representative_stocks:
      - {ticker: "005490", name: "POSCO홀딩스", role: "core"}

  construction_infra:
    name: "건설/인프라"
    description: "건설, 시멘트, SOC"
    industries:
      - "건설"
      - "건축자재"
    representative_stocks:
      - {ticker: "000720", name: "현대건설", role: "core"}

  energy_refinery:
    name: "에너지/정유"
    description: "정유, 가스, 신재생에너지"
    industries:
      - "에너지"
      - "유틸리티"
    representative_stocks:
      - {ticker: "096770", name: "SK이노베이션", role: "core"}
      - {ticker: "010950", name: "S-Oil", role: "sub"}

  telecom_utility:
    name: "통신/유틸리티"
    description: "통신서비스, 전력, 가스 (방어주)"
    industries:
      - "통신"
      - "유틸리티"
    representative_stocks:
      - {ticker: "017670", name: "SK텔레콤", role: "core"}
      - {ticker: "015760", name: "한국전력", role: "core"}

  consumer_retail:
    name: "소비재/유통"
    description: "식품, 의류, 유통, 화장품"
    industries:
      - "유통"
      - "식품"
      - "화장품"
    representative_stocks:
      - {ticker: "051900", name: "LG생활건강", role: "core"}
      - {ticker: "090430", name: "아모레퍼시픽", role: "core"}
```

### 9.4 3D 스코어링 모델 (US 방법론 보존)

#### Dimension 1: Theme Heat (0-100)

```python
def calculate_theme_heat(theme_stocks: list, ohlcv_data: dict) -> float:
    """테마 열기 점수 계산.

    Components (가중 합산):
    1. Momentum (40%): 대표 종목의 1주/1개월 수익률 (시총 가중 평균)
    2. Volume (20%): 최근 5일 거래량 / 20일 평균 거래량
    3. Uptrend Ratio (25%): 200MA 위 종목 비율
    4. Breadth (15%): 양봉 종목 비율 (최근 5일)

    Returns: 0~100 (높을수록 강한 모멘텀)
    """
```

#### Dimension 2: Lifecycle Maturity

```python
def classify_lifecycle(theme_data: dict) -> str:
    """테마 라이프사이클 분류.

    Early:      모멘텀 시작, 거래량 증가 초기, ETF 없거나 1개
    Mid:        모멘텀 지속, 거래량 안정적 높음, ETF 2-3개
    Late:       모멘텀 극단, 거래량 급증, ETF 4개+, 밸류에이션 과열
    Exhaustion: 모멘텀 둔화, 거래량 감소, 가격 정체

    한국 특화 기준:
    - 개인투자자 순매수 급증 = Late/Exhaustion 징후
    - 관련 ETF 신규 상장 = Mid~Late 전환 징후
    - 뉴스 빈도 급증 = Late 징후
    """
```

#### Dimension 3: Confidence (Low / Medium / High)

```python
def assess_confidence(quant_score: float, narrative_confirmed: bool) -> str:
    """신뢰도 평가.

    Quantitative (정량):
    - breadth_high: 업트렌드 비율 > 60% AND 거래량 확인
    - breadth_low: 업트렌드 비율 < 40% OR 거래량 미확인

    Narrative (정성, WebSearch):
    - strong: 최근 1주 내 주요 뉴스 3건+
    - weak: 뉴스 없거나 부정적

    조합:
    - Quant High + Narrative Strong = High
    - Quant High + Narrative Weak = Medium (모멘텀 다이버전스)
    - Quant Low + Narrative Strong = Medium (내러티브 선행 가능)
    - Quant Low + Narrative Weak = Low
    """
```

### 9.5 스크립트 상세 설계

#### kr_theme_detector.py (메인)

```python
"""한국 테마 탐지기.

Usage:
    python3 kr_theme_detector.py --output-dir reports/
    python3 kr_theme_detector.py --max-themes 5 --output-dir reports/

Arguments:
    --output-dir: 리포트 출력 디렉토리
    --max-themes: 상위 N개 테마만 상세 분석 (기본: 전체)
    --skip-narrative: WebSearch 내러티브 확인 건너뛰기 (속도 우선)
    --themes-file: 커스텀 테마 정의 파일 (기본: kr_themes.yaml)

예상 소요시간: 3-5분 (종목 데이터 조회 + 선택적 WebSearch)
"""

class KRThemeDetector:
    def run(self) -> dict:
        """
        1. kr_themes.yaml에서 테마 정의 로드
        2. industry_data_collector로 종목/업종 데이터 수집
        3. theme_classifier로 종목 → 테마 분류
        4. scorer로 3D 스코어 계산 (Heat/Lifecycle/Confidence)
        5. (선택) WebSearch로 내러티브 확인
        6. report_generator로 JSON/MD 리포트 생성
        """
```

#### industry_data_collector.py

```python
"""KRX 업종/종목 데이터 수집기.

FINVIZ의 업종별 데이터를 KRX 데이터로 대체.
각 테마 대표종목의 OHLCV, 시총, 거래량 데이터를 수집.
"""

class IndustryDataCollector:
    def collect(self, themes: dict) -> dict:
        """테마별 종목 데이터 수집.

        각 테마의 representative_stocks에서:
        1. get_ohlcv() - 최근 60일 OHLCV
        2. get_market_cap() - 시가총액
        3. get_fundamentals() - PER/PBR (밸류에이션)

        Returns:
            {
                'ai_semiconductor': {
                    'stocks': [
                        {
                            'ticker': '005930',
                            'name': '삼성전자',
                            'close': 72000,
                            'change_1w': 2.5,
                            'change_1m': -3.2,
                            'volume_ratio': 1.35,
                            'above_200ma': True,
                            'market_cap': 430_000_000_000_000,
                            'per': 12.5,
                        },
                        ...
                    ],
                    'sector_performance': {...},
                },
                ...
            }
        """
```

#### theme_classifier.py

```python
"""종목 → 테마 분류기.

kr_themes.yaml의 정의를 기반으로 종목을 테마에 매핑.
업종(industry) 기반 자동 분류 + 수동 정의된 대표 종목.
"""

class ThemeClassifier:
    def classify(self, ticker_list: pd.DataFrame, themes: dict) -> dict:
        """전체 종목을 테마별로 분류.

        1. 수동 정의: kr_themes.yaml의 representative_stocks
        2. 자동 확장: 같은 업종의 시총 상위 종목 추가
        3. 중복 허용: 하나의 종목이 여러 테마에 속할 수 있음
           (예: LG화학 → 2차전지 + 화학소재)
        """
```

### 9.6 Direction Detection (Bullish/Bearish)

```python
def detect_direction(theme_data: dict) -> str:
    """테마 방향 판정.

    US 원본 로직 동일:
    1. 시총 가중 평균 수익률 (1주+1개월)
    2. 업트렌드 비율 (200MA 위 종목 %)
    3. 거래량 확인 (축적 vs 분산)

    Bullish: 가중 수익률 > 0 AND (업트렌드 > 50% OR 거래량 축적)
    Bearish: 가중 수익률 < 0 AND (업트렌드 < 50% OR 거래량 분산)
    Neutral: 혼재된 신호
    """
```

### 9.7 출력 포맷

```markdown
# 한국 테마 탐지 리포트

## 테마 대시보드
| 테마 | Heat | 방향 | 라이프사이클 | 신뢰도 |
|------|:----:|:----:|:----------:|:------:|
| AI/반도체 | 82 | 🟢 Bullish | Mid | High |
| 방산 | 75 | 🟢 Bullish | Mid | High |
| 2차전지 | 45 | 🔴 Bearish | Late | Medium |
| 조선/해운 | 70 | 🟢 Bullish | Early | Medium |
| K-컨텐츠 | 35 | ⚪ Neutral | Exhaustion | Low |
...

## Bullish 테마 상세
### AI/반도체 (Heat: 82, Bullish, Mid-Cycle)
- 대표종목 동향: 삼성전자 +2.5%, SK하이닉스 +4.1%
- 업트렌드 비율: 75% (12/16종목)
- 거래량: 평균 대비 135%
- 뉴스 확인: HBM4 양산 시작 보도 (한경, 2/25)
- ETF: KODEX 반도체 +3.2%

## Bearish 테마 상세
### 2차전지 (Heat: 45, Bearish, Late-Cycle)
- 대표종목 동향: LG에솔 -5.2%, 에코프로비엠 -8.1%
- 업트렌드 비율: 30% (6/20종목)
- 거래량: 매도 물량 증가
- 뉴스 확인: EU 전기차 보조금 축소 보도

## 업종 순위
## 방법론 설명
```

---

## 10. 구현 순서 및 일정

### 10.1 구현 순서 (의존성 기반)

```
Phase 2 구현 순서:
─────────────────────────────────────────────────
Step 1: Low 복잡도 (SKILL.md + references만)     ← 1일
  ├── Skill 3: kr-sector-analyst
  ├── Skill 4: kr-technical-analyst
  └── Skill 1: kr-market-environment (+ market_utils.py)

Step 2: Medium 복잡도 (SKILL.md + references)     ← 0.5일
  └── Skill 2: kr-market-news-analyst

Step 3: High 복잡도 - 시장폭 (스크립트 6개)        ← 2일
  └── Skill 5: kr-market-breadth

Step 4: High 복잡도 - 업트렌드 (스크립트 6개)      ← 2일
  └── Skill 6: kr-uptrend-analyzer
  (Skill 5의 breadth_calculator 패턴 재활용)

Step 5: High 복잡도 - 테마 (스크립트 8개)          ← 2.5일
  └── Skill 7: kr-theme-detector
  (Skill 5/6의 계산 패턴 + 테마 정의 추가)
─────────────────────────────────────────────────
합계: ~8일 (High 스킬 3개가 전체의 80%)
```

### 10.2 의존성 그래프

```
_kr-common (Phase 1) ─────────────────────────────────────┐
  │                                                        │
  ├── kr-market-environment (Step 1) ←─ market_utils.py    │
  ├── kr-sector-analyst (Step 1) ←─ kr_sector_rotation.md  │
  ├── kr-technical-analyst (Step 1)                        │
  ├── kr-market-news-analyst (Step 2)                      │
  │                                                        │
  ├── kr-market-breadth (Step 3)                           │
  │   ├── breadth_calculator.py  ← KRClient                │
  │   ├── scorer.py              ← ta_utils (sma)          │
  │   ├── report_generator.py                              │
  │   └── history_tracker.py                               │
  │                                                        │
  ├── kr-uptrend-analyzer (Step 4)                         │
  │   ├── uptrend_calculator.py  ← KRClient + breadth 패턴 │
  │   ├── scorer.py                                        │
  │   └── report_generator.py                              │
  │                                                        │
  └── kr-theme-detector (Step 5)                           │
      ├── industry_data_collector.py ← KRClient            │
      ├── theme_classifier.py    ← kr_themes.yaml          │
      ├── scorer.py              ← Heat/Lifecycle/Confidence│
      └── report_generator.py                              │
```

### 10.3 Phase 1 Gap 해결 (Phase 2 시작 전)

| Gap | 내용 | 소요 | Phase 2 영향 |
|-----|------|:----:|-------------|
| G-4 | `shorting_trade_top50` → `shorting_balance_top50` | 5분 | Skill 5 (breadth) |
| G-5 | `get_short_top50` by 파라미터 미사용 | 5분 | 경미 |
| G-6 | 캐시 데코레이터 미통합 | 30분 | **Skill 5/6/7 성능에 중요** |

> G-6 (캐시 통합)은 Phase 2 High 스킬들이 대량의 OHLCV 데이터를 조회하므로
> **반드시 Phase 2 구현 전에 해결**해야 한다.

---

## 11. 테스트 전략

### 11.1 스킬별 테스트

| 스킬 | 테스트 방법 | 검증 항목 |
|------|------------|-----------|
| Skill 1-4 (Low/Med) | SKILL.md 수동 실행 후 출력 확인 | 리포트 포맷, 한국 데이터 정확성 |
| Skill 5 (Breadth) | `test_breadth.py` 단위 테스트 | 스코어 계산 정확성, 구성종목 조회 |
| Skill 6 (Uptrend) | `test_uptrend.py` 단위 테스트 | 업트렌드 판정, 업종 분류 |
| Skill 7 (Theme) | `test_theme.py` 단위 테스트 | 테마 분류, 3D 스코어 |

### 11.2 통합 테스트

```python
# 각 High 스킬의 end-to-end 테스트
def test_breadth_e2e():
    """kr-market-breadth 전체 파이프라인.

    1. KRClient로 KOSPI200 구성종목 조회 (mock 가능)
    2. 시장폭 계산
    3. 스코어링
    4. 리포트 생성
    5. JSON/MD 파일 검증
    """

def test_uptrend_e2e():
    """kr-uptrend-analyzer 전체 파이프라인."""

def test_theme_e2e():
    """kr-theme-detector 전체 파이프라인."""
```

### 11.3 성능 목표

| 스킬 | 실행 시간 목표 | 비고 |
|------|:------------:|------|
| kr-market-environment | <30초 | WebSearch + KRClient 1-2회 |
| kr-market-breadth | <3분 | 200종목 OHLCV (캐시 미적중) |
| kr-uptrend-analyzer | <5분 | 업종별 종목 OHLCV |
| kr-theme-detector | <5분 | 테마별 대표종목 + 선택적 WebSearch |

---

## 12. 리스크 & 완화 방안

| 리스크 | 영향 | 완화 방안 |
|--------|------|-----------|
| PyKRX 크롤링 제한 | Skill 5/6/7 실행 실패 | request_delay 준수 + 캐시 적극 활용 |
| KOSPI200 구성종목 변경 | 시장폭 연속성 깨짐 | 분기별 리밸런싱 대응 로직 |
| KRX 업종 분류와 테마 불일치 | 테마 분류 부정확 | kr_themes.yaml 수동 보정 + 정기 업데이트 |
| 한국 뉴스 WebSearch 한계 | 영어 결과 혼입 | 검색어에 "한국" "KOSPI" 명시 |
| 대량 종목 조회 시간 | 사용자 대기 시간 | 캐시 + 진행률 표시 + 부분 결과 반환 |

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2026-02-27 | 1.0 | Phase 2 초기 설계 - 7개 시장 분석 스킬 |
