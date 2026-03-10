# Design: 미국 경제지표 대시보드 스킬

> **Feature**: us-indicator-dashboard
> **Phase**: Design
> **Created**: 2026-03-10
> **Plan Reference**: `docs/01-plan/features/us-indicator-dashboard.plan.md`

---

## 1. 설계 개요

사용자가 수동으로 텍스트 파일에 관리하던 **미국 경제지표 21개 항목**(7개 카테고리)을
자동 수집 + 5-컴포넌트 레짐 판정 + 한국 시장 영향 분석까지 수행하는 스킬.

> 원본 이미지: `미국지표.jpg`(14개) + `미국지표02.jpg`(7개)

### 설계 원칙

1. **2분 이내 완료** — yfinance 2개 + WebSearch 9배치로 21개 지표 수집
2. **모듈 독립성** — 5개 모듈 각각 독립 실행, 개별 실패가 전체를 중단하지 않음
3. **기존 인프라 재활용** — `_kr_common/utils/`, `report_rules.md`, `email_sender.py`
4. **fail-safe** — WebSearch 파싱 실패 시 `N/A` 표시, 수집률 80%+ 보장

---

## 2. 디렉토리 구조

```
skills/us-indicator-dashboard/
├── SKILL.md                        # 스킬 명세서 (7-Step 실행 절차)
├── scripts/
│   ├── us_indicator_dashboard.py   # 메인 오케스트레이터
│   ├── indicator_collector.py      # 21개 지표 데이터 수집
│   ├── regime_classifier.py        # 5-컴포넌트 → 4-레짐 판정
│   ├── kr_impact_analyzer.py       # 한국 시장 영향 분석
│   ├── calendar_tracker.py         # 다음 발표 일정 추적
│   ├── report_generator.py         # 마크다운 4-Section 리포트 생성
│   └── tests/
│       ├── test_indicator_collector.py   # 15+ tests
│       ├── test_regime_classifier.py     # 10+ tests
│       ├── test_kr_impact_analyzer.py    # 8+ tests
│       ├── test_calendar_tracker.py      # 5+ tests
│       └── test_report_generator.py      # 6+ tests
└── references/
    ├── indicator_meta.json         # 21개 지표 메타데이터
    └── release_calendar.json       # 정기 발표 일정
```

---

## 3. 모듈 상세 설계

### 3.1 indicator_collector.py — 21개 지표 수집

#### 3.1.1 상수 정의

```python
"""미국 경제지표 데이터 수집 모듈."""

import os
import sys
import json
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# ── 21개 지표 ID + 카테고리 매핑 ──────────────────
INDICATOR_IDS = [
    # 성장 (1)
    'gdp',
    # 금리 (3)
    'fed_rate', 'treasury_2y', 'treasury_10y',
    # 물가 (4)
    'cpi', 'pce', 'ppi', 'inflation_exp',
    # 경기 (6)
    'unemployment', 'weekly_hours', 'hourly_earnings',
    'real_earnings', 'jobless_claims', 'retail_sales',
    # 선행 (3)
    'ism_pmi', 'consumer_sentiment', 'consumer_confidence',
    # 동행 (3)
    'business_inventories', 'housing_starts', 'auto_sales',
    # 대외 (1)
    'current_account',
]

CATEGORY_MAP = {
    'growth': ['gdp'],
    'rates': ['fed_rate', 'treasury_2y', 'treasury_10y'],
    'inflation': ['cpi', 'pce', 'ppi', 'inflation_exp'],
    'economy': ['unemployment', 'weekly_hours', 'hourly_earnings',
                'real_earnings', 'jobless_claims', 'retail_sales'],
    'leading': ['ism_pmi', 'consumer_sentiment', 'consumer_confidence'],
    'coincident': ['business_inventories', 'housing_starts', 'auto_sales'],
    'external': ['current_account'],
}

CATEGORY_NAMES_KR = {
    'growth': '성장',
    'rates': '금리',
    'inflation': '물가',
    'economy': '경기',
    'leading': '경기 선행',
    'coincident': '경기 동행',
    'external': '대외',
}

CATEGORY_ORDER = ['growth', 'rates', 'inflation', 'economy',
                  'leading', 'coincident', 'external']

# ── yfinance 티커 (국채 2개만) ────────────────────
YFINANCE_TICKERS = {
    'treasury_2y': '^IRX',   # 13-Week Treasury Bill (2Y 대용) or '2YY=F'
    'treasury_10y': '^TNX',  # 10-Year Treasury Note
}
```

#### 3.1.2 데이터 구조

```python
# 단일 지표 결과 타입
IndicatorResult = {
    'id': str,              # 'cpi'
    'name_kr': str,         # 'CPI (소비자물가지수)'
    'name_en': str,         # 'CPI YoY'
    'category': str,        # 'inflation'
    'value': float | None,  # 2.9
    'prev_value': float | None,  # 3.0
    'change': float | None,      # -0.1
    'direction': str,       # '↓' / '↑' / '→'
    'trend_label': str,     # '둔화' / '가속' / '안정'
    'unit': str,            # '%'
    'release_date': str | None,  # '2026-02-12'
    'source': str,          # 'BLS'
    'baseline': float | None,    # 50.0 (ISM PMI), 100.0 (심리지수)
    'error': str | None,    # 파싱 실패 시 에러 메시지
}
```

#### 3.1.3 함수 시그니처

```python
def load_indicator_meta() -> list[dict]:
    """references/indicator_meta.json 로드.

    Returns:
        21개 지표 메타데이터 리스트

    Logic:
        1. __file__ 기준으로 ../references/indicator_meta.json 경로 계산
        2. JSON 로드 후 indicators 키 반환
        3. 파일 없으면 하드코딩 기본값 반환
    """


def collect_treasury_yields() -> dict:
    """yfinance로 국채 2년/10년 수익률 수집.

    Returns:
        {
            'treasury_2y': {'value': 4.15, 'prev_value': 4.20, ...},
            'treasury_10y': {'value': 4.26, 'prev_value': 4.30, ...},
        }

    Logic:
        1. yf.download(['^IRX', '^TNX'], period='5d')
        2. 마지막 종가 → value, 전일 종가 → prev_value
        3. ^TNX는 10배로 나누어 % 단위 (yfinance 특성)
        4. 실패 시 error 필드에 메시지
    """


def parse_indicator_from_text(text: str, indicator_id: str,
                               meta: dict) -> IndicatorResult:
    """WebSearch 텍스트에서 특정 지표 값을 파싱.

    Args:
        text: WebSearch 결과 텍스트
        indicator_id: 지표 ID (예: 'cpi')
        meta: indicator_meta.json의 해당 지표 메타데이터

    Returns:
        IndicatorResult (value, prev_value, release_date 등)

    Logic:
        1. 지표별 정규식 패턴 매칭 (복수 패턴 시도)
        2. 숫자 추출 + 단위 정규화
        3. 발표일 파싱 (YYYY-MM-DD 또는 MM/DD 형식)
        4. 매칭 실패 시 value=None, error='파싱 실패'
    """


def calc_direction(value: float, prev_value: float,
                   indicator_id: str) -> tuple[str, str]:
    """변화 방향 화살표와 추세 라벨 계산.

    Args:
        value: 현재값
        prev_value: 이전값
        indicator_id: 지표 ID (역방향 지표 판별용)

    Returns:
        (direction, trend_label)
        예: ('↓', '둔화') — CPI 하락 시 '둔화'
        예: ('↑', '냉각') — 실업률 상승 시 '냉각'

    Logic:
        1. change = value - prev_value
        2. change > 0 → '↑', change < 0 → '↓', else '→'
        3. REVERSE_INDICATORS (실업률, 실업수당)는 의미 반전
           실업률 ↑ = '냉각', 실업률 ↓ = '과열'
        4. 물가 지표: ↓ = '둔화', ↑ = '가속'
        5. ISM PMI: < 50 시 '수축', ≥ 50 시 '확장'
    """

# 의미 역방향 지표 (값 상승이 부정적)
REVERSE_INDICATORS = {'unemployment', 'jobless_claims', 'current_account'}

# 물가 지표 (값 하락이 '둔화')
INFLATION_INDICATORS = {'cpi', 'pce', 'ppi', 'inflation_exp'}

# 기준선 지표 (ISM 50, 심리 100)
BASELINE_INDICATORS = {'ism_pmi': 50.0, 'consumer_sentiment': 100.0,
                       'consumer_confidence': 100.0}


def collect_all(websearch_context: dict = None) -> list[IndicatorResult]:
    """21개 지표 전체 수집 — yfinance + WebSearch 결합.

    Args:
        websearch_context: SKILL.md 실행 시 Claude가 주입하는 WebSearch 결과
            {
                'gdp': {'value': 2.3, 'prev_value': 3.1, 'release_date': '2026-01-30'},
                'cpi': {'value': 2.9, 'prev_value': 3.0, 'release_date': '2026-02-12'},
                ...
            }

    Returns:
        list[IndicatorResult] (21개, 수집 실패 항목은 error 포함)

    Logic:
        1. load_indicator_meta()로 메타데이터 로드
        2. collect_treasury_yields()로 국채 2개 수집
        3. websearch_context에서 나머지 19개 매핑
        4. 각 지표별 calc_direction() 호출
        5. 누락 항목은 value=None, error='미수집' 처리
    """


def get_collection_stats(results: list[IndicatorResult]) -> dict:
    """수집 통계 반환.

    Returns:
        {
            'total': 21,
            'collected': 18,
            'failed': 3,
            'rate': 85.7,
            'failed_ids': ['auto_sales', 'current_account', 'business_inventories']
        }
    """
```

---

### 3.2 regime_classifier.py — 5-컴포넌트 레짐 판정

#### 3.2.1 레짐 정의

```python
"""미국 경제 레짐 분류 모듈."""

from enum import Enum
from typing import Optional

class Regime(Enum):
    GOLDILOCKS = 'Goldilocks'      # 골디락스: 적당한 성장 + 안정 물가
    OVERHEATING = 'Overheating'    # 과열: 강한 성장 + 높은 물가
    STAGFLATION = 'Stagflation'    # 스태그: 약한 성장 + 높은 물가
    RECESSION = 'Recession'        # 침체: 약한 성장 + 낮은 물가

REGIME_DESCRIPTIONS = {
    Regime.GOLDILOCKS: {
        'kr': '골디락스 (적정 성장 + 물가 안정)',
        'kr_impact': '위험자산 강세, 한국 시장 유리',
        'color': 'green',
    },
    Regime.OVERHEATING: {
        'kr': '과열 (강한 성장 + 물가 상승)',
        'kr_impact': '금리 인상 우려, 한국 시장 부정적',
        'color': 'orange',
    },
    Regime.STAGFLATION: {
        'kr': '스태그플레이션 (성장 둔화 + 물가 상승)',
        'kr_impact': '최악 시나리오, 위험자산 급락',
        'color': 'red',
    },
    Regime.RECESSION: {
        'kr': '침체 (역성장 + 물가 안정)',
        'kr_impact': '긴급 인하 기대, 초기 부정→후반 긍정',
        'color': 'blue',
    },
}
```

#### 3.2.2 5-컴포넌트 스코어링

```python
# 컴포넌트별 가중치
COMPONENT_WEIGHTS = {
    'inflation': 0.30,    # 물가 (CPI, PCE, PPI, 기대심리)
    'growth': 0.25,       # 경기 (GDP, ISM PMI, 소매판매, 주택착공, 기업재고)
    'employment': 0.25,   # 고용 (실업률, 근무시간, 시간당소득, 실업수당)
    'sentiment': 0.10,    # 심리 (소비자심리, 소비자신뢰)
    'external': 0.10,     # 대외 (경상수지)
}
```

#### 3.2.3 함수 시그니처

```python
def calc_inflation_score(cpi: float = None, pce: float = None,
                          ppi: float = None, inflation_exp: float = None) -> dict:
    """물가 컴포넌트 스코어 (0~100).

    Returns:
        {
            'score': 65.0,
            'level': 'moderate',   # low / moderate / high / very_high
            'detail': {
                'cpi': {'value': 2.9, 'gap_from_target': 0.9, 'score': 62},
                'pce': {'value': 2.5, 'gap_from_target': 0.5, 'score': 70},
                ...
            }
        }

    Logic:
        - Fed 목표 2.0% 기준으로 갭 계산
        - 갭 < 0.5%p → score 80+ (Low)
        - 갭 0.5~1.0%p → score 50~80 (Moderate)
        - 갭 1.0~2.0%p → score 20~50 (High)
        - 갭 > 2.0%p → score 0~20 (Very High)
        - 점수 높을수록 물가 안정 (인하 여유)
        - None인 지표는 제외, 나머지로 평균
    """


def calc_growth_score(gdp: float = None, ism_pmi: float = None,
                       retail_sales: float = None,
                       housing_starts: float = None,
                       business_inventories: float = None) -> dict:
    """경기 컴포넌트 스코어 (0~100).

    Returns:
        {
            'score': 55.0,
            'level': 'moderate',   # recession / weak / moderate / strong / overheating
            'detail': {...}
        }

    Logic:
        - GDP: 0% → 0점, 2% → 50점, 3%+ → 75점, 4%+ → 90점
        - ISM PMI: 40 → 0점, 50 → 50점, 55 → 75점, 60+ → 100점
        - 소매판매 MoM: -1% → 10점, 0% → 50점, +0.5%+ → 80점
        - 주택착공/기업재고: 보조 지표 (가중치 낮음)
        - 가중: GDP(0.35) + ISM(0.30) + 소매(0.20) + 주택(0.10) + 재고(0.05)
    """


def calc_employment_score(unemployment: float = None,
                           weekly_hours: float = None,
                           hourly_earnings: float = None,
                           jobless_claims: float = None) -> dict:
    """고용 컴포넌트 스코어 (0~100).

    Returns:
        {
            'score': 45.0,
            'level': 'cooling',   # tight / balanced / cooling / weak
            'detail': {...}
        }

    Logic:
        - 실업률: 3.5% → 100점(과열), 4.0% → 75점, 5.0% → 25점, 6%+ → 0점
        - 주당근무시간: 34.5+ → 80점, 34.0 → 50점, 33.5 → 20점
        - 시간당소득 MoM: 0.5%+ → 30점(임금인플레), 0.3% → 60점, 0.2% → 80점
          (시간당소득은 높을수록 인플레 압력 → 한국에 부정적 → 점수 역방향)
        - 실업수당: 200K → 80점, 250K → 50점, 300K+ → 20점
    """


def calc_sentiment_score(consumer_sentiment: float = None,
                          consumer_confidence: float = None) -> dict:
    """심리 컴포넌트 스코어 (0~100).

    Returns:
        {
            'score': 60.0,
            'level': 'neutral',   # pessimistic / cautious / neutral / optimistic
            'detail': {...}
        }

    Logic:
        - 소비자심리(UMich): baseline 100 기준
          50 → 0점, 75 → 40점, 100 → 70점, 110+ → 90점
        - 소비자신뢰(CB): baseline 100 기준
          60 → 0점, 80 → 40점, 100 → 70점, 120+ → 90점
        - 두 지표 단순 평균
    """


def calc_external_score(current_account: float = None) -> dict:
    """대외 컴포넌트 스코어 (0~100).

    Returns:
        {
            'score': 40.0,
            'level': 'deficit_widening',
            'detail': {...}
        }

    Logic:
        - 경상수지 적자 규모 기준 (음수가 정상)
        - -100B → 80점 (소규모 적자, 양호)
        - -200B → 50점 (보통)
        - -300B+ → 20점 (대규모 적자, 달러 약세 압력)
    """


def classify_regime(inflation_score: float, growth_score: float,
                     employment_score: float, sentiment_score: float,
                     external_score: float) -> dict:
    """5-컴포넌트로 4-레짐 판정.

    Returns:
        {
            'regime': Regime.GOLDILOCKS,
            'regime_kr': '골디락스 (적정 성장 + 물가 안정)',
            'composite_score': 62.5,
            'kr_impact': '위험자산 강세, 한국 시장 유리',
            'components': {
                'inflation': {'score': 65, 'weight': 0.30, 'weighted': 19.5},
                'growth': {'score': 55, 'weight': 0.25, 'weighted': 13.75},
                'employment': {'score': 45, 'weight': 0.25, 'weighted': 11.25},
                'sentiment': {'score': 60, 'weight': 0.10, 'weighted': 6.0},
                'external': {'score': 40, 'weight': 0.10, 'weighted': 4.0},
            },
            'reasoning': '물가 둔화세 지속(CPI 2.9%)으로 인하 여유 유지...'
        }

    Logic:
        1. composite = Σ(score_i × weight_i)
        2. 물가 점수 기준 High/Low 분류:
           - inflation_score >= 50 → 물가 Low (안정)
           - inflation_score < 50 → 물가 High (압력)
        3. 경기 점수 기준 Strong/Weak 분류:
           - growth_score >= 50 → 경기 Strong
           - growth_score < 50 → 경기 Weak
        4. 레짐 매핑:
           - 물가Low + 경기Strong → Goldilocks
           - 물가High + 경기Strong → Overheating
           - 물가High + 경기Weak → Stagflation
           - 물가Low + 경기Weak → Recession
        5. 경계값(45~55) 구간은 sentiment_score로 tie-break
    """


def analyze_regime(indicators: list) -> dict:
    """지표 리스트에서 레짐 분석 전체 수행.

    Args:
        indicators: collect_all() 결과 (21개 IndicatorResult)

    Returns:
        classify_regime() 결과

    Logic:
        1. indicators에서 각 지표 value 추출
        2. 5개 calc_*_score() 호출
        3. classify_regime() 호출
    """
```

---

### 3.3 kr_impact_analyzer.py — 한국 시장 영향 분석

#### 3.3.1 영향 분류 체계

```python
"""한국 시장 영향 분석 모듈."""

from enum import Enum

class Impact(Enum):
    POSITIVE = 'positive'      # 한국 시장에 긍정적
    NEGATIVE = 'negative'      # 한국 시장에 부정적
    NEUTRAL = 'neutral'        # 중립

# 지표별 한국 영향 룰 테이블
# key: (indicator_id, direction)
# value: (Impact, reason_template)
IMPACT_RULES = {
    # 성장
    ('gdp', '↑'): (Impact.POSITIVE, 'GDP 상승 → 미국 소비 확대 → 한국 수출 증가'),
    ('gdp', '↓'): (Impact.NEGATIVE, 'GDP 하락 → 미국 수요 둔화 → 한국 수출 감소'),

    # 금리
    ('fed_rate', '↓'): (Impact.POSITIVE, '기준금리 인하 → 한미 금리차 축소 → 외국인 유입'),
    ('fed_rate', '↑'): (Impact.NEGATIVE, '기준금리 인상 → 한미 금리차 확대 → 외국인 이탈'),
    ('treasury_10y', '↓'): (Impact.POSITIVE, '장기금리 하락 → 성장주 밸류에이션 개선'),
    ('treasury_10y', '↑'): (Impact.NEGATIVE, '장기금리 상승 → 성장주 밸류에이션 압박'),
    ('treasury_2y', '↓'): (Impact.POSITIVE, '단기금리 하락 → 인하 기대 반영'),
    ('treasury_2y', '↑'): (Impact.NEGATIVE, '단기금리 상승 → 인하 지연 반영'),

    # 물가 (하락이 긍정)
    ('cpi', '↓'): (Impact.POSITIVE, 'CPI 둔화 → Fed 인하 기대 유지 → 위험자산 선호'),
    ('cpi', '↑'): (Impact.NEGATIVE, 'CPI 가속 → 인하 지연/인상 우려 → 위험자산 회피'),
    ('pce', '↓'): (Impact.POSITIVE, 'PCE 둔화 → Fed 선호 지표 개선 → 인하 기대'),
    ('pce', '↑'): (Impact.NEGATIVE, 'PCE 가속 → Fed 매파 전환 가능'),
    ('ppi', '↓'): (Impact.POSITIVE, 'PPI 하락 → 기업 비용 압력 완화 → CPI 둔화 선행'),
    ('ppi', '↑'): (Impact.NEGATIVE, 'PPI 상승 → 기업 비용 전가 → CPI 상승 우려'),
    ('inflation_exp', '↓'): (Impact.POSITIVE, '인플레 기대 하락 → 인플레 기대 앵커링 성공'),
    ('inflation_exp', '↑'): (Impact.NEGATIVE, '인플레 기대 상승 → 자기실현적 인플레 우려'),

    # 경기
    ('unemployment', '↑'): (Impact.POSITIVE, '실업률 상승 → 고용 냉각 → 인하 기대 ↑ → 신흥국 유리'),
    ('unemployment', '↓'): (Impact.NEUTRAL, '실업률 하락 → 고용 견조 → 인하 지연 가능'),
    ('weekly_hours', '↓'): (Impact.NEGATIVE, '근무시간 감소 → 경기 냉각 신호'),
    ('weekly_hours', '↑'): (Impact.POSITIVE, '근무시간 증가 → 생산 확대 → 수출 수요'),
    ('hourly_earnings', '↑'): (Impact.NEGATIVE, '임금 가속 → 임금-물가 스파이럴 위험 → 인하 제약'),
    ('hourly_earnings', '↓'): (Impact.POSITIVE, '임금 둔화 → 인플레 완화 → 인하 여유'),
    ('real_earnings', '↑'): (Impact.POSITIVE, '실질임금 상승 → 소비력 개선 → 수요 지지'),
    ('real_earnings', '↓'): (Impact.NEGATIVE, '실질임금 하락 → 소비력 약화'),
    ('jobless_claims', '↓'): (Impact.POSITIVE, '실업수당 감소 → 고용 안정 → 미국 경기 양호'),
    ('jobless_claims', '↑'): (Impact.NEGATIVE, '실업수당 증가 → 고용 악화 신호'),
    ('retail_sales', '↑'): (Impact.POSITIVE, '소매판매 증가 → 미국 소비 견조 → 수출 수요'),
    ('retail_sales', '↓'): (Impact.NEGATIVE, '소매판매 감소 → 미국 소비 둔화 → 수출 타격'),

    # 선행
    ('ism_pmi', '↑'): (Impact.POSITIVE, 'ISM PMI 상승 → 제조업 확장 → 한국 수출 선행 개선'),
    ('ism_pmi', '↓'): (Impact.NEGATIVE, 'ISM PMI 하락 → 제조업 위축 → 한국 수출 둔화 우려'),
    ('consumer_sentiment', '↑'): (Impact.POSITIVE, '소비심리 개선 → 소비 회복 기대'),
    ('consumer_sentiment', '↓'): (Impact.NEGATIVE, '소비심리 악화 → 소비 둔화 우려'),
    ('consumer_confidence', '↑'): (Impact.POSITIVE, '소비자신뢰 상승 → 소비 의향 확대'),
    ('consumer_confidence', '↓'): (Impact.NEGATIVE, '소비자신뢰 하락 → 소비 위축 우려'),

    # 동행
    ('business_inventories', '↑'): (Impact.NEUTRAL, '기업재고 증가 → 수요 대비 과잉 가능성'),
    ('business_inventories', '↓'): (Impact.POSITIVE, '기업재고 감소 → 보충 주문 기대 → 수출 긍정'),
    ('housing_starts', '↑'): (Impact.POSITIVE, '주택착공 증가 → 건설/원자재 수요 → 철강/구리'),
    ('housing_starts', '↓'): (Impact.NEGATIVE, '주택착공 감소 → 건설 경기 둔화'),
    ('auto_sales', '↑'): (Impact.POSITIVE, '자동차판매 증가 → 부품 수출 수혜'),
    ('auto_sales', '↓'): (Impact.NEGATIVE, '자동차판매 감소 → 부품 수출 둔화'),

    # 대외
    ('current_account', '↓'): (Impact.NEUTRAL, '경상적자 확대 → 달러 약세 압력 → 신흥국 상대 유리'),
    ('current_account', '↑'): (Impact.NEUTRAL, '경상적자 축소 → 달러 강세 → 신흥국 부담'),
}
```

#### 3.3.2 함수 시그니처

```python
def analyze_impact(indicators: list) -> dict:
    """21개 지표별 한국 시장 영향 분석.

    Args:
        indicators: collect_all() 결과

    Returns:
        {
            'positive': [
                {'id': 'cpi', 'name_kr': 'CPI', 'reason': 'CPI 둔화 → ...'},
                ...
            ],
            'negative': [
                {'id': 'hourly_earnings', 'name_kr': '시간당소득', 'reason': '...'},
                ...
            ],
            'neutral': [...],
            'summary': '물가 둔화와 고용 냉각이 동시 진행되어...',
            'net_impact': 'mildly_positive',  # strongly_positive/mildly_positive/neutral/mildly_negative/strongly_negative
        }

    Logic:
        1. 각 지표의 direction을 IMPACT_RULES에서 조회
        2. value=None (미수집) 항목은 제외
        3. direction='→' (변화 없음) 항목은 neutral 분류
        4. 긍정/부정 개수 비교로 net_impact 판정
        5. summary는 상위 2-3개 요인으로 1-2문장 생성
    """


def format_impact_section(impact_result: dict) -> str:
    """한국 영향 분석 결과를 마크다운으로 포맷팅.

    Returns:
        ```markdown
        ## 한국 시장 영향 분석

        **종합 판정**: 약간 긍정적 (Mildly Positive)

        ### 긍정 요인 (5개)
        - CPI 둔화 → Fed 인하 기대 유지 → 외국인 자금 유입 환경
        - ...

        ### 부정 요인 (2개)
        - 시간당소득 가속 → 임금발 인플레 우려 → 인하 지연 가능
        - ...

        ### 중립 요인 (3개)
        - ...
        ```
    """
```

---

### 3.4 calendar_tracker.py — 발표 일정 추적

#### 3.4.1 상수 정의

```python
"""미국 경제지표 발표 일정 추적 모듈."""

import json
import os
from datetime import datetime, timedelta

# 발표 일정 정기 패턴 (release_calendar.json에서 로드)
# 아래는 하드코딩 기본값
DEFAULT_RELEASE_PATTERNS = {
    'cpi': {'name_kr': 'CPI', 'day_of_month': 'mid', 'source': 'BLS', 'importance': 5},
    'ppi': {'name_kr': 'PPI', 'day_of_month': 'mid', 'source': 'BLS', 'importance': 3},
    'pce': {'name_kr': 'PCE', 'day_of_month': 'late', 'source': 'BEA', 'importance': 5},
    'unemployment': {'name_kr': '고용보고서', 'day_of_month': '1st_friday', 'source': 'BLS', 'importance': 5},
    'jobless_claims': {'name_kr': '실업수당', 'day_of_month': 'weekly_thu', 'source': 'DOL', 'importance': 2},
    'retail_sales': {'name_kr': '소매판매', 'day_of_month': 'mid', 'source': 'Census', 'importance': 4},
    'ism_pmi': {'name_kr': 'ISM PMI', 'day_of_month': '1st_biz', 'source': 'ISM', 'importance': 4},
    'consumer_sentiment': {'name_kr': '소비자심리', 'day_of_month': 'mid+late', 'source': 'UMich', 'importance': 3},
    'consumer_confidence': {'name_kr': '소비자신뢰', 'day_of_month': 'late', 'source': 'CB', 'importance': 3},
    'gdp': {'name_kr': 'GDP', 'day_of_month': 'late', 'source': 'BEA', 'importance': 5, 'frequency': 'quarterly'},
    'fed_rate': {'name_kr': 'FOMC 금리결정', 'source': 'Fed', 'importance': 5, 'frequency': 'fomc'},
    'housing_starts': {'name_kr': '주택착공', 'day_of_month': 'mid', 'source': 'Census', 'importance': 2},
    'business_inventories': {'name_kr': '기업재고', 'day_of_month': 'mid', 'source': 'Census', 'importance': 2},
    'inflation_exp': {'name_kr': '인플레 기대', 'day_of_month': 'mid', 'source': 'UMich', 'importance': 3},
    'current_account': {'name_kr': '경상수지', 'source': 'BEA', 'importance': 3, 'frequency': 'quarterly'},
}

# 중요도 → 별 매핑
IMPORTANCE_STARS = {1: '★', 2: '★★', 3: '★★★', 4: '★★★★', 5: '★★★★★'}
```

#### 3.4.2 함수 시그니처

```python
def load_release_calendar() -> dict:
    """references/release_calendar.json 로드.

    Returns:
        {
            '2026-03': {
                'events': [
                    {'date': '2026-03-07', 'indicator': 'unemployment', 'name': '고용보고서 (2월)', 'importance': 5},
                    {'date': '2026-03-12', 'indicator': 'cpi', 'name': 'CPI (2월)', 'importance': 5},
                    ...
                ]
            }
        }

    Logic:
        1. ../references/release_calendar.json 로드
        2. 파일 없으면 빈 dict 반환 (WebSearch 의존)
    """


def get_upcoming_releases(days: int = 14,
                           websearch_context: dict = None) -> list[dict]:
    """향후 N일간 발표 예정 일정 조회.

    Args:
        days: 조회 기간 (기본 14일)
        websearch_context: WebSearch로 수집한 일정 + 컨센서스
            {
                'events': [
                    {'date': '2026-03-12', 'indicator': 'CPI',
                     'forecast': '2.8%', 'previous': '2.9%'},
                    ...
                ]
            }

    Returns:
        [
            {
                'date': '2026-03-12',
                'indicator_id': 'cpi',
                'name_kr': 'CPI (2월)',
                'forecast': '2.8%',
                'previous': '2.9%',
                'importance': 5,
                'stars': '★★★★★',
                'source': 'BLS',
            },
            ...
        ]

    Logic:
        1. load_release_calendar()에서 정적 일정 로드
        2. websearch_context에서 동적 일정/컨센서스 병합
        3. today ~ today+days 범위 필터
        4. 날짜순 정렬, importance 내림차순
    """


def format_calendar_section(upcoming: list[dict]) -> str:
    """발표 일정을 마크다운 테이블로 포맷팅.

    Returns:
        ```markdown
        ## 향후 2주 발표 일정

        | 날짜 | 지표 | 예상 | 이전 | 중요도 |
        |------|------|------|------|:------:|
        | 3/12 | CPI (2월) | 2.8% | 2.9% | ★★★★★ |
        | 3/13 | PPI (2월) | 2.1% | 2.2% | ★★★ |
        ...
        ```
    """
```

---

### 3.5 report_generator.py — 4-Section 리포트 생성

#### 3.5.1 함수 시그니처

```python
"""리포트 생성 모듈."""

import os
from datetime import datetime


def build_header(collection_stats: dict, regime: dict) -> str:
    """리포트 헤더 생성.

    Returns:
        ```markdown
        # 미국 경제지표 대시보드
        > 생성일: 2026-03-10 08:30 | 지표 수: 21개 (수집 18/21) | 레짐: Goldilocks
        ```
    """


def build_dashboard_section(indicators: list) -> str:
    """Section 1: 대시보드 테이블 생성.

    Args:
        indicators: collect_all() 결과 (21개)

    Returns:
        7개 카테고리별 마크다운 테이블

    Logic:
        1. CATEGORY_ORDER 순서대로 카테고리 그룹화
        2. 각 카테고리별 ### 헤더 + 테이블 생성
        3. value=None 항목은 'N/A' 표시
        4. baseline 있는 지표 (ISM, 심리)는 '기준' 칼럼 추가
        5. 변화량 포맷: +0.2%p / -7K / -$5.5B 등 단위별 처리
    """


def build_regime_section(regime_result: dict) -> str:
    """Section 2: 종합 진단 생성.

    Args:
        regime_result: classify_regime() 결과

    Returns:
        레짐 판정 + 5-컴포넌트 스코어 테이블 + 판단 근거

    Format:
        ```markdown
        ## 종합 진단: Goldilocks (골디락스)

        **한국 시장 영향**: 위험자산 강세, 한국 시장 유리

        ### 5-컴포넌트 스코어
        | 컴포넌트 | 스코어 | 가중치 | 가중점수 | 수준 |
        |---------|:------:|:------:|:-------:|------|
        | 물가 | 65 | 30% | 19.5 | 안정(Moderate) |
        | 경기 | 55 | 25% | 13.75 | 적정(Moderate) |
        | 고용 | 45 | 25% | 11.25 | 냉각(Cooling) |
        | 심리 | 60 | 10% | 6.0 | 중립(Neutral) |
        | 대외 | 40 | 10% | 4.0 | 보통 |
        | **합계** | | | **54.5** | |

        ### 판단 근거
        물가 둔화세 지속(CPI 2.9%, PCE 2.5%)으로...
        ```
    """


def build_impact_section(impact_result: dict) -> str:
    """Section 3: 한국 시장 영향 분석 — kr_impact_analyzer 결과 포맷팅."""


def build_calendar_section(upcoming: list[dict]) -> str:
    """Section 4: 다음 발표 일정 — calendar_tracker 결과 포맷팅."""


def build_footer() -> str:
    """리포트 푸터.

    Returns:
        ```markdown
        ---
        *Generated by us-indicator-dashboard | {datetime}*
        ```
    """


def generate_report(indicators: list, regime: dict,
                     impact: dict, upcoming: list,
                     collection_stats: dict) -> str:
    """4-Section 리포트 전체 조합.

    Returns:
        Header + Section1 + Section2 + Section3 + Section4 + Footer

    Logic:
        1. build_header()
        2. build_dashboard_section()
        3. build_regime_section()
        4. build_impact_section()
        5. build_calendar_section()
        6. build_footer()
        7. 전체 조합 후 문자열 반환
    """


def save_report(content: str, date_str: str = None) -> str:
    """리포트를 reports/ 디렉토리에 저장.

    Args:
        content: 마크다운 리포트 전체
        date_str: YYYYMMDD (기본: 오늘)

    Returns:
        저장된 파일 경로

    Logic:
        1. 파일명: reports/us-indicator-dashboard_macro_미국경제지표_{YYYYMMDD}.md
        2. reports/ 디렉토리 없으면 생성
        3. 동일 파일 존재 시 덮어쓰기
    """
```

---

### 3.6 us_indicator_dashboard.py — 오케스트레이터

```python
"""미국 경제지표 대시보드 오케스트레이터."""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from indicator_collector import collect_all, get_collection_stats
from regime_classifier import analyze_regime
from kr_impact_analyzer import analyze_impact
from calendar_tracker import get_upcoming_releases
from report_generator import generate_report, save_report


def run(websearch_context: dict = None,
        calendar_context: dict = None) -> dict:
    """대시보드 전체 실행.

    Args:
        websearch_context: SKILL.md에서 Claude가 주입하는 지표 데이터
            {
                'gdp': {'value': 2.3, 'prev_value': 3.1, 'release_date': '2026-01-30'},
                ...
            }
        calendar_context: WebSearch로 수집한 발표 일정
            {
                'events': [{'date': '...', 'indicator': '...', 'forecast': '...'}]
            }

    Returns:
        {
            'success': True,
            'report_path': 'reports/us-indicator-dashboard_macro_미국경제지표_20260310.md',
            'collection_stats': {'total': 21, 'collected': 18, 'rate': 85.7},
            'regime': 'Goldilocks',
            'net_impact': 'mildly_positive',
            'errors': []
        }

    Logic:
        1. [Step 1] collect_all(websearch_context)
           - 실패해도 수집된 항목으로 계속 진행
        2. [Step 2] analyze_regime(indicators)
           - try-except: 실패 시 regime='Unknown'
        3. [Step 3] analyze_impact(indicators)
           - try-except: 실패 시 빈 결과
        4. [Step 4] get_upcoming_releases(calendar_context)
           - try-except: 실패 시 빈 리스트
        5. [Step 5] generate_report() + save_report()
        6. 결과 dict 반환
    """

    result = {
        'success': False,
        'report_path': None,
        'collection_stats': {},
        'regime': 'Unknown',
        'net_impact': 'unknown',
        'errors': [],
    }

    # Step 1: 지표 수집
    try:
        indicators = collect_all(websearch_context)
        stats = get_collection_stats(indicators)
        result['collection_stats'] = stats
    except Exception as e:
        result['errors'].append(f'[collect] {e}')
        return result

    # Step 2: 레짐 판정
    try:
        regime = analyze_regime(indicators)
        result['regime'] = regime['regime'].value
    except Exception as e:
        regime = {'regime_kr': 'Unknown', 'composite_score': 0, 'components': {}}
        result['errors'].append(f'[regime] {e}')

    # Step 3: 한국 영향 분석
    try:
        impact = analyze_impact(indicators)
        result['net_impact'] = impact.get('net_impact', 'unknown')
    except Exception as e:
        impact = {'positive': [], 'negative': [], 'neutral': [], 'summary': ''}
        result['errors'].append(f'[impact] {e}')

    # Step 4: 발표 일정
    try:
        upcoming = get_upcoming_releases(websearch_context=calendar_context)
    except Exception as e:
        upcoming = []
        result['errors'].append(f'[calendar] {e}')

    # Step 5: 리포트 생성 & 저장
    try:
        content = generate_report(indicators, regime, impact, upcoming, stats)
        path = save_report(content)
        result['report_path'] = path
        result['success'] = True
    except Exception as e:
        result['errors'].append(f'[report] {e}')

    return result


if __name__ == '__main__':
    result = run()
    print(f"Success: {result['success']}")
    print(f"Report: {result['report_path']}")
    print(f"Stats: {result['collection_stats']}")
    print(f"Regime: {result['regime']}")
```

---

## 4. 참조 데이터 설계

### 4.1 references/indicator_meta.json

Plan 문서 Section 7에 정의된 21개 지표 메타데이터를 그대로 사용한다.
(id, name_kr, name_en, category, unit, frequency, source, thresholds, baseline, note)

### 4.2 references/release_calendar.json

```json
{
  "2026-03": {
    "events": [
      {"date": "2026-03-01", "indicator": "ism_pmi", "name": "ISM 제조업 PMI (2월)"},
      {"date": "2026-03-07", "indicator": "unemployment", "name": "고용보고서 (2월)"},
      {"date": "2026-03-12", "indicator": "cpi", "name": "CPI (2월)"},
      {"date": "2026-03-13", "indicator": "ppi", "name": "PPI (2월)"},
      {"date": "2026-03-14", "indicator": "inflation_exp", "name": "UMich 인플레 기대 (3월 예비)"},
      {"date": "2026-03-14", "indicator": "consumer_sentiment", "name": "소비자심리 (3월 예비)"},
      {"date": "2026-03-17", "indicator": "retail_sales", "name": "소매판매 (2월)"},
      {"date": "2026-03-18", "indicator": "housing_starts", "name": "주택착공 (2월)"},
      {"date": "2026-03-19", "indicator": "fed_rate", "name": "FOMC 금리 결정"},
      {"date": "2026-03-20", "indicator": "current_account", "name": "경상수지 (Q4)"},
      {"date": "2026-03-25", "indicator": "consumer_confidence", "name": "소비자신뢰 (3월)"},
      {"date": "2026-03-28", "indicator": "pce", "name": "Core PCE (2월)"},
      {"date": "2026-03-28", "indicator": "gdp", "name": "GDP (Q4 확정)"}
    ]
  },
  "fomc_dates_2026": [
    "2026-01-29", "2026-03-19", "2026-05-07", "2026-06-18",
    "2026-07-30", "2026-09-17", "2026-11-05", "2026-12-17"
  ]
}
```

---

## 5. SKILL.md 실행 절차 (7-Step)

```
Step 1: WebSearch — 물가 지표 수집
  → "US CPI PPI PCE latest March 2026"
  → CPI, PPI, PCE 값 + 발표일 추출

Step 2: WebSearch — 고용/경기 지표 수집
  → "US jobs report unemployment March 2026"
  → 실업률, 근무시간, 시간당소득, 실질임금 추출
  → "initial jobless claims latest week"
  → 신규실업수당 추출

Step 3: WebSearch — 성장/소비/금리 지표 수집
  → "US GDP growth rate retail sales latest 2026"
  → GDP, 소매판매 추출
  → "fed funds rate FOMC decision 2026"
  → 기준금리 추출

Step 4: WebSearch — 선행/심리 지표 수집
  → "ISM manufacturing PMI UMich consumer sentiment confidence March 2026"
  → ISM PMI, 소비자심리, 소비자신뢰, 인플레 기대 추출

Step 5: WebSearch — 동행/대외 지표 + 일정 수집
  → "US housing starts business inventories auto sales current account 2026"
  → 주택착공, 기업재고, 자동차판매, 경상수지 추출
  → "economic calendar this week US"
  → 향후 발표 일정 + 컨센서스

Step 6: Python 스크립트 실행
  → us_indicator_dashboard.py에 websearch_context 주입
  → 21개 지표 수집 + 레짐 판정 + 한국 영향 분석 + 일정
  → reports/ 저장

Step 7: 이메일 발송
  → python3 skills/_kr_common/utils/email_sender.py "{path}" "us-indicator-dashboard"
```

---

## 6. 에러 핸들링

### 6.1 fail-safe 원칙

| 모듈 | 실패 시 동작 | 리포트 영향 |
|------|------------|-----------|
| indicator_collector | 개별 지표 `N/A` 표시, 나머지 정상 | Section 1 일부 N/A |
| regime_classifier | regime='Unknown' | Section 2 '판정 불가' 표시 |
| kr_impact_analyzer | 빈 결과 | Section 3 '분석 불가' 표시 |
| calendar_tracker | 빈 리스트 | Section 4 생략 |
| report_generator | 실패 시 전체 실패 | 리포트 미생성 |

### 6.2 WebSearch 파싱 실패 대응

```python
# parse_indicator_from_text 내부
PARSE_PATTERNS = {
    'cpi': [
        r'CPI[:\s]+(\d+\.?\d*)%',           # CPI: 2.9%
        r'consumer price.+?(\d+\.?\d*)%',    # consumer price index 2.9%
        r'CPI YoY.+?(\d+\.?\d*)',            # CPI YoY 2.9
    ],
    'unemployment': [
        r'unemployment.+?(\d+\.?\d*)%',
        r'실업률[:\s]+(\d+\.?\d*)%',
    ],
    # ... 각 지표별 3+ 패턴
}

# 패턴 매칭 순서: 첫 매칭 성공 시 반환
# 모든 패턴 실패 → value=None, error='파싱 실패'
```

---

## 7. 테스트 설계

### 7.1 test_indicator_collector.py (15+ tests)

| # | 테스트명 | 검증 항목 |
|:-:|---------|----------|
| 1 | test_indicator_ids_count | INDICATOR_IDS 길이 == 21 |
| 2 | test_category_map_covers_all | CATEGORY_MAP 합계 == 21 |
| 3 | test_category_order_complete | CATEGORY_ORDER 7개 카테고리 |
| 4 | test_yfinance_tickers_count | YFINANCE_TICKERS 2개 |
| 5 | test_load_indicator_meta | JSON 로드 + 21개 확인 |
| 6 | test_load_meta_fallback | 파일 없을 때 기본값 반환 |
| 7 | test_calc_direction_up | value > prev → '↑' |
| 8 | test_calc_direction_down | value < prev → '↓' |
| 9 | test_calc_direction_flat | value == prev → '→' |
| 10 | test_reverse_indicator_label | 실업률 ↑ → '냉각' |
| 11 | test_inflation_label | CPI ↓ → '둔화' |
| 12 | test_baseline_label | ISM < 50 → '수축' |
| 13 | test_collect_all_with_context | websearch_context 주입 시 21개 반환 |
| 14 | test_collect_all_partial | 일부 누락 시 error 포함 |
| 15 | test_collection_stats | 수집률 계산 정확성 |

### 7.2 test_regime_classifier.py (10+ tests)

| # | 테스트명 | 검증 항목 |
|:-:|---------|----------|
| 1 | test_inflation_score_low | CPI 1.8%, PCE 1.5% → 80+ |
| 2 | test_inflation_score_high | CPI 5.0%, PCE 4.0% → 20 미만 |
| 3 | test_growth_score_moderate | GDP 2.5%, ISM 52 → 50~70 |
| 4 | test_growth_score_recession | GDP -1.0%, ISM 42 → 20 미만 |
| 5 | test_employment_score_tight | 실업 3.4%, 실업수당 190K → 80+ |
| 6 | test_employment_score_weak | 실업 6.0%, 실업수당 350K → 20 미만 |
| 7 | test_sentiment_score | 심리 90, 신뢰 110 → 60~80 |
| 8 | test_classify_goldilocks | 물가Low + 경기Mod → Goldilocks |
| 9 | test_classify_stagflation | 물가High + 경기Low → Stagflation |
| 10 | test_classify_recession | 물가Low + 경기Low → Recession |
| 11 | test_classify_overheating | 물가High + 경기High → Overheating |
| 12 | test_analyze_regime_integration | indicators → regime 전체 파이프라인 |

### 7.3 test_kr_impact_analyzer.py (8+ tests)

| # | 테스트명 | 검증 항목 |
|:-:|---------|----------|
| 1 | test_impact_rules_coverage | 21개 지표 × 2방향 = 42개 룰 존재 |
| 2 | test_cpi_down_positive | CPI ↓ → positive |
| 3 | test_cpi_up_negative | CPI ↑ → negative |
| 4 | test_unemployment_up_positive | 실업률 ↑ → positive (역방향) |
| 5 | test_flat_neutral | 변화 없음 → neutral |
| 6 | test_missing_value_excluded | value=None → 분류에서 제외 |
| 7 | test_net_impact_positive | 긍정 > 부정 → mildly_positive |
| 8 | test_net_impact_negative | 부정 > 긍정 → mildly_negative |

### 7.4 test_calendar_tracker.py (5+ tests)

| # | 테스트명 | 검증 항목 |
|:-:|---------|----------|
| 1 | test_load_calendar | JSON 로드 성공 |
| 2 | test_upcoming_filter | 14일 범위 필터 |
| 3 | test_importance_stars | 중요도 5 → ★★★★★ |
| 4 | test_empty_calendar | 빈 JSON → 빈 리스트 |
| 5 | test_format_table | 마크다운 테이블 형식 확인 |

### 7.5 test_report_generator.py (6+ tests)

| # | 테스트명 | 검증 항목 |
|:-:|---------|----------|
| 1 | test_build_header | 헤더에 지표 수, 레짐 포함 |
| 2 | test_build_dashboard_7_categories | 7개 카테고리 헤더 존재 |
| 3 | test_build_regime_section | 5-컴포넌트 테이블 포함 |
| 4 | test_build_impact_section | 긍정/부정/중립 섹션 |
| 5 | test_generate_report_complete | 4-Section 전체 조합 |
| 6 | test_save_report_path | 파일명 패턴 확인 |

### 합계: 44+ tests (Plan 목표 47+ 달성 가능)

---

## 8. 검증 기준 (V-01 ~ V-14)

| ID | 검증 항목 | 가중치 | 판정 기준 |
|:--:|---------|:------:|----------|
| V-01 | INDICATOR_IDS == 21개 | 8% | 정확히 21개 |
| V-02 | CATEGORY_MAP 7개 카테고리 | 5% | growth/rates/inflation/economy/leading/coincident/external |
| V-03 | yfinance 국채 수집 | 7% | ^TNX, ^IRX 모두 수집 |
| V-04 | WebSearch context 주입 | 10% | 19개 지표 매핑 |
| V-05 | calc_direction 역방향 처리 | 7% | REVERSE_INDICATORS 올바른 라벨 |
| V-06 | 5-컴포넌트 가중치 합계 | 5% | == 1.0 |
| V-07 | 4-레짐 분류 매트릭스 | 10% | 물가H/L × 경기S/W = 4조합 |
| V-08 | IMPACT_RULES 커버리지 | 8% | 21 × 2 = 42개 룰 |
| V-09 | 발표 일정 JSON | 5% | release_calendar.json 로드 |
| V-10 | 리포트 4-Section | 10% | Header + S1 + S2 + S3 + S4 + Footer |
| V-11 | 리포트 파일 저장 | 5% | reports/ 경로 + 파일명 패턴 |
| V-12 | fail-safe 격리 | 8% | 개별 모듈 실패 시 나머지 정상 |
| V-13 | 테스트 44+ 통과 | 7% | 전체 PASS |
| V-14 | SKILL.md 7-Step | 5% | 실행 절차 완성 |
| | **합계** | **100%** | |

---

## 9. 구현 순서

| 순서 | 파일 | 의존성 | 예상 LOC |
|:----:|------|--------|:-------:|
| 1 | references/indicator_meta.json | 없음 | 120 |
| 2 | references/release_calendar.json | 없음 | 40 |
| 3 | indicator_collector.py | indicator_meta.json, yfinance | 250 |
| 4 | regime_classifier.py | 없음 | 200 |
| 5 | kr_impact_analyzer.py | 없음 | 180 |
| 6 | calendar_tracker.py | release_calendar.json | 120 |
| 7 | report_generator.py | 3~6 모듈 결과 | 200 |
| 8 | us_indicator_dashboard.py | 3~7 모듈 | 80 |
| 9 | tests/ (5개 파일) | 3~8 모듈 | 500 |
| 10 | SKILL.md | 전체 | 100 |
| | **합계** | | **~1,790** |

---

## 10. 기존 스킬 대비 차별점 요약

| 비교 항목 | us-monetary-regime | us-indicator-dashboard |
|----------|-------------------|----------------------|
| 목적 | 통화정책 기조 레짐 분류 | 21개 지표 대시보드 |
| 지표 수 | ~8개 (간접) | **21개 (직접)** |
| 출력 | 0-100 레짐 점수 | 개별 지표 테이블 + 레짐 + 영향 |
| 한국 영향 | 오버레이 점수 (+-15) | 지표별 긍정/부정 상세 분류 |
| 발표 일정 | 없음 | **향후 2주 캘린더** |
| 이전값 비교 | 없음 | **변화량 + 추세 화살표** |

---

| 날짜 | 버전 | 작업 내용 |
|------|:----:|----------|
| 2026-03-10 | 1.0 | Design 문서 작성 |
