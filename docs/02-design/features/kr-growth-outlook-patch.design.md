# kr-growth-outlook-patch Design Document

> **Summary**: 미래 성장성 분석 (단기/중기/장기) 기존 스킬 패치 + kr-growth-outlook 신규 스킬
>
> **Plan**: `docs/01-plan/features/kr-growth-outlook-patch.plan.md`
> **Date**: 2026-03-05
> **Status**: Design

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                  Growth Outlook Patch Architecture              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  kr-stock-analysis (PATCH)          kr-growth-outlook (NEW)    │
│  ┌─────────────────────┐           ┌──────────────────────┐   │
│  │ Fundamental  30%    │           │ tam_analyzer.py      │   │
│  │ Technical    22%    │           │ moat_scorer.py       │   │
│  │ Supply       22%    │           │ pipeline_evaluator.py│   │
│  │ Valuation    13%    │           │ earnings_projector.py│   │
│  │ Growth       13% ◄─┼───Quick───┤ policy_analyzer.py   │   │
│  │  (NEW)              │           │ management_scorer.py │   │
│  └─────────────────────┘           │ growth_synthesizer.py│   │
│                                    └──────────────────────┘   │
│  kr-sector-analyst (PATCH)                                     │
│  ┌─────────────────────┐    Shared References                  │
│  │ + sector growth     │    ┌──────────────────────┐          │
│  │   outlook           │◄───┤ sector_tam_database   │          │
│  └─────────────────────┘    │ korea_growth_drivers  │          │
│                              │ moat_framework        │          │
│  kr-strategy-synthesizer     │ korea_policy_roadmap  │          │
│  (PATCH)                     └──────────────────────┘          │
│  ┌─────────────────────┐                                       │
│  │ + growth_outlook    │                                       │
│  │   (8th component)   │                                       │
│  └─────────────────────┘                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Constants & Configuration

### 2.1 kr-growth-outlook: Growth Score

```python
# ─── 6-컴포넌트 가중치 ───

GROWTH_COMPONENTS = {
    'tam_sam': {
        'weight': 0.25,
        'label': 'TAM/SAM 시장규모',
        'data_sources': ['sector_tam_database', 'WebSearch'],
    },
    'competitive_moat': {
        'weight': 0.20,
        'label': '경쟁우위/해자',
        'data_sources': ['moat_framework', 'DART', 'WebSearch'],
    },
    'pipeline': {
        'weight': 0.15,
        'label': '기술/제품 파이프라인',
        'data_sources': ['DART_disclosure', 'WebSearch'],
    },
    'earnings_path': {
        'weight': 0.20,
        'label': '실적 성장 경로',
        'data_sources': ['FnGuide_consensus', 'DART_financials'],
    },
    'policy_tailwind': {
        'weight': 0.10,
        'label': '정책/규제 순풍',
        'data_sources': ['korea_policy_roadmap', 'WebSearch'],
    },
    'management': {
        'weight': 0.10,
        'label': '경영진/거버넌스',
        'data_sources': ['DART_executive', 'WebSearch'],
    },
}
# 합계: 0.25 + 0.20 + 0.15 + 0.20 + 0.10 + 0.10 = 1.00 ✓
```

### 2.2 시간축별 가중치 배율 (Multiplier)

```python
# 각 시간축에서 컴포넌트 중요도 조정
TIME_HORIZON_MULTIPLIER = {
    'short_1_3y': {
        'tam_sam': 0.8,
        'competitive_moat': 0.9,
        'pipeline': 1.3,
        'earnings_path': 1.3,
        'policy_tailwind': 0.9,
        'management': 0.8,
    },
    'mid_4_7y': {
        'tam_sam': 1.0,
        'competitive_moat': 1.2,
        'pipeline': 1.1,
        'earnings_path': 1.0,
        'policy_tailwind': 1.0,
        'management': 0.7,
    },
    'long_10y': {
        'tam_sam': 1.3,
        'competitive_moat': 1.3,
        'pipeline': 0.7,
        'earnings_path': 0.7,
        'policy_tailwind': 1.5,
        'management': 1.5,
    },
}
```

### 2.3 Growth 등급

```python
GROWTH_GRADES = {
    'S': {'min': 85, 'label': 'Hyper Growth', 'implication': '10년 10배+ 잠재력'},
    'A': {'min': 70, 'label': 'Strong Growth', 'implication': '10년 5배+ 잠재력'},
    'B': {'min': 55, 'label': 'Moderate Growth', 'implication': '10년 2-3배 잠재력'},
    'C': {'min': 40, 'label': 'Slow Growth', 'implication': '시장 수익률 수준'},
    'D': {'min': 0, 'label': 'No Growth / Decline', 'implication': '구조적 하락 리스크'},
}
```

### 2.4 kr-stock-analysis: 가중치 변경

```python
# 기존 (Phase 8)
COMPREHENSIVE_SCORING_V1 = {
    'fundamental': {'weight': 0.35},
    'technical': {'weight': 0.25},
    'supply_demand': {'weight': 0.25},
    'valuation': {'weight': 0.15},
}
# 합계: 1.00

# 패치 후
COMPREHENSIVE_SCORING_V2 = {
    'fundamental': {'weight': 0.30, 'label': '펀더멘털'},
    'technical': {'weight': 0.22, 'label': '기술적'},
    'supply_demand': {'weight': 0.22, 'label': '수급'},
    'valuation': {'weight': 0.13, 'label': '밸류에이션'},
    'growth': {'weight': 0.13, 'label': '성장성'},
}
# 합계: 0.30 + 0.22 + 0.22 + 0.13 + 0.13 = 1.00 ✓
```

### 2.5 Growth Quick Score (경량)

```python
# kr-stock-analysis 내장 경량 Growth Score
# WebSearch 미사용, 즉시 계산 가능

GROWTH_QUICK_COMPONENTS = {
    'consensus_eps_growth': {
        'weight': 0.40,
        'source': 'FnGuide',
        'description': '컨센서스 EPS 성장률 (YoY)',
    },
    'rd_investment': {
        'weight': 0.20,
        'source': 'DART',
        'description': 'R&D 투자 매출 대비 비율 + 추이',
    },
    'sector_tam_cagr': {
        'weight': 0.20,
        'source': 'sector_tam_database (static)',
        'description': '해당 섹터 TAM CAGR',
    },
    'policy_score': {
        'weight': 0.20,
        'source': 'korea_policy_roadmap (static)',
        'description': '정책 순풍 강도',
    },
}
# 합계: 0.40 + 0.20 + 0.20 + 0.20 = 1.00 ✓
```

### 2.6 Growth Quick Score 벤치마크

```python
# 컨센서스 EPS 성장률 스코어링
CONSENSUS_EPS_BENCHMARKS = {
    'hyper': 50,     # 50%+ YoY → 95점
    'strong': 25,    # 25%+ → 80점
    'moderate': 10,  # 10%+ → 65점
    'low': 5,        # 5%+ → 50점
    'flat': 0,       # 0-5% → 40점
    'decline': -10,  # -10%+ → 25점
    'severe': -20,   # -20%+ → 10점
}

# R&D 투자 비율 벤치마크
RD_INVESTMENT_BENCHMARKS = {
    'leader': 15,    # 매출 15%+ → 90점
    'high': 10,      # 10%+ → 75점
    'moderate': 5,   # 5%+ → 60점
    'low': 2,        # 2%+ → 45점
    'minimal': 0,    # 0-2% → 30점
}

# 섹터 TAM CAGR 벤치마크
SECTOR_TAM_BENCHMARKS = {
    'explosive': 15, # 15%+ → 90점
    'high': 10,      # 10%+ → 75점
    'moderate': 7,   # 7%+ → 60점
    'low': 3,        # 3%+ → 45점
    'stagnant': 0,   # 0-3% → 30점
}

# 정책 순풍 레벨
POLICY_SCORE_MAP = {
    'strong_tailwind': 90,    # 국가전략산업, 대규모 보조금
    'moderate_tailwind': 70,  # 세제 혜택, 규제 완화
    'neutral': 50,            # 특별한 정책 없음
    'moderate_headwind': 30,  # 규제 강화, 세금 증가
    'strong_headwind': 10,    # 산업 규제, 퇴출 위험
}
```

### 2.7 kr-sector-analyst: 섹터 성장 등급

```python
# 14개 섹터 정적 TAM DB (references에서 로드)
SECTOR_GROWTH_RATINGS = {
    'semiconductor': {'tam_2026': 680e9, 'cagr_26_30': 0.12, 'kr_ms': 0.20, 'grade': 'S'},
    'automotive': {'tam_2026': 3.5e12, 'cagr_26_30': 0.04, 'kr_ms': 0.08, 'grade': 'B'},
    'shipbuilding': {'tam_2026': 150e9, 'cagr_26_30': 0.08, 'kr_ms': 0.40, 'grade': 'A'},
    'defense': {'tam_2026': 2.2e12, 'cagr_26_30': 0.07, 'kr_ms': 0.03, 'grade': 'A'},
    'bio_health': {'tam_2026': 1.8e12, 'cagr_26_30': 0.09, 'kr_ms': 0.02, 'grade': 'A'},
    'battery': {'tam_2026': 180e9, 'cagr_26_30': 0.15, 'kr_ms': 0.25, 'grade': 'A'},
    'power_equipment': {'tam_2026': 250e9, 'cagr_26_30': 0.10, 'kr_ms': 0.05, 'grade': 'A'},
    'chemical': {'tam_2026': 500e9, 'cagr_26_30': 0.03, 'kr_ms': 0.05, 'grade': 'C'},
    'steel': {'tam_2026': 1.4e12, 'cagr_26_30': 0.02, 'kr_ms': 0.03, 'grade': 'C'},
    'construction': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.90, 'grade': 'D'},
    'financial': {'tam_2026': None, 'cagr_26_30': 0.03, 'kr_ms': 0.95, 'grade': 'C'},
    'telecom': {'tam_2026': None, 'cagr_26_30': 0.02, 'kr_ms': 0.99, 'grade': 'D'},
    'utility': {'tam_2026': None, 'cagr_26_30': 0.01, 'kr_ms': 0.99, 'grade': 'D'},
    'entertainment': {'tam_2026': 350e9, 'cagr_26_30': 0.08, 'kr_ms': 0.05, 'grade': 'B'},
}
```

### 2.8 kr-strategy-synthesizer: 8번째 컴포넌트

```python
# 기존 7-컴포넌트 + growth_outlook
CONVICTION_COMPONENTS_V2 = {
    'market_structure': {'weight': 0.16},    # 0.18 → 0.16
    'distribution_risk': {'weight': 0.16},   # 0.18 → 0.16
    'bottom_confirmation': {'weight': 0.10}, # 0.12 → 0.10
    'macro_alignment': {'weight': 0.16},     # 0.18 → 0.16
    'theme_quality': {'weight': 0.10},       # 0.12 → 0.10
    'setup_availability': {'weight': 0.09},  # 0.10 → 0.09
    'signal_convergence': {'weight': 0.11},  # 0.12 → 0.11
    'growth_outlook': {'weight': 0.12,       # NEW
        'sources': ['kr-growth-outlook'],
        'description': '종목/섹터 성장성 전망',
    },
}
# 합계: 0.16+0.16+0.10+0.16+0.10+0.09+0.11+0.12 = 1.00 ✓
```

### 2.9 TAM Analyzer 상수

```python
# TAM/SAM 스코어링 기준
TAM_SCORING = {
    'tam_cagr': {  # 글로벌 TAM 성장률
        'explosive': {'min': 15, 'score': 90},
        'high': {'min': 10, 'score': 75},
        'moderate': {'min': 7, 'score': 60},
        'low': {'min': 3, 'score': 45},
        'stagnant': {'min': 0, 'score': 30},
        'decline': {'min': -999, 'score': 15},
    },
    'market_share_trend': {  # 시장점유율 추이
        'gaining_fast': {'delta': 2.0, 'score': 90},   # 연 +2%p 이상
        'gaining': {'delta': 0.5, 'score': 75},         # 연 +0.5%p
        'stable': {'delta': -0.5, 'score': 50},         # ±0.5%p
        'losing': {'delta': -2.0, 'score': 30},         # 연 -0.5~-2%p
        'losing_fast': {'delta': -999, 'score': 10},    # 연 -2%p 이상
    },
    'sam_penetration': {  # SAM 내 침투율
        'dominant': {'min': 30, 'score': 70},  # 30%+ (성장 제한)
        'strong': {'min': 15, 'score': 85},    # 15-30% (최적)
        'growing': {'min': 5, 'score': 90},    # 5-15% (고성장)
        'emerging': {'min': 1, 'score': 80},   # 1-5%
        'nascent': {'min': 0, 'score': 60},    # <1%
    },
}
```

### 2.10 Moat Scorer 상수

```python
# 경쟁 우위 (Moat) 유형별 스코어링
MOAT_TYPES = {
    'cost_advantage': {
        'description': '원가 우위',
        'weight': 0.20,
        'indicators': ['operating_margin_vs_peers', 'scale_efficiency'],
    },
    'switching_cost': {
        'description': '전환 비용',
        'weight': 0.20,
        'indicators': ['customer_retention', 'contract_duration'],
    },
    'network_effect': {
        'description': '네트워크 효과',
        'weight': 0.15,
        'indicators': ['user_base_growth', 'platform_stickiness'],
    },
    'intangible_assets': {
        'description': '무형자산 (브랜드/특허)',
        'weight': 0.25,
        'indicators': ['patent_count', 'brand_value', 'rd_ratio'],
    },
    'efficient_scale': {
        'description': '효율적 규모',
        'weight': 0.20,
        'indicators': ['market_share', 'competitor_count'],
    },
}
# 합계: 0.20+0.20+0.15+0.25+0.20 = 1.00 ✓

# Moat 강도 등급
MOAT_STRENGTH = {
    'wide': {'min': 75, 'description': '넓은 해자 (10년+ 방어 가능)'},
    'narrow': {'min': 50, 'description': '좁은 해자 (5-10년 방어)'},
    'none': {'min': 0, 'description': '해자 없음 (경쟁 심화 위험)'},
}
```

### 2.11 Pipeline Evaluator 상수

```python
PIPELINE_SCORING = {
    'new_products': {
        'weight': 0.35,
        'benchmarks': {
            'breakthrough': 90,  # 업계 최초, 신시장 개척
            'major': 75,         # 주요 제품 라인 확장
            'incremental': 55,   # 기존 제품 개선
            'maintenance': 35,   # 유지보수 수준
            'none': 15,          # 신제품 부재
        },
    },
    'rd_capability': {
        'weight': 0.30,
        'metrics': {
            'rd_to_revenue': RD_INVESTMENT_BENCHMARKS,  # 공유
            'patent_growth_yoy': {'high': 20, 'moderate': 10, 'low': 0},
            'rd_personnel_ratio': {'high': 15, 'moderate': 8, 'low': 3},
        },
    },
    'tech_position': {
        'weight': 0.35,
        'levels': {
            'leader': 90,        # 기술 선도자
            'fast_follower': 70, # 빠른 추격자
            'follower': 50,      # 일반 추격자
            'laggard': 25,       # 후발주자
        },
    },
}
# 합계: 0.35+0.30+0.35 = 1.00 ✓
```

### 2.12 Earnings Projector 상수

```python
EARNINGS_SCORING = {
    'consensus_growth': {
        'weight': 0.40,
        'benchmarks': CONSENSUS_EPS_BENCHMARKS,  # 공유
    },
    'margin_trajectory': {
        'weight': 0.25,
        'levels': {
            'expanding_fast': 90,   # OPM +3%p+ YoY
            'expanding': 75,        # OPM +1~3%p
            'stable': 55,           # OPM ±1%p
            'contracting': 35,      # OPM -1~3%p
            'contracting_fast': 15, # OPM -3%p+
        },
    },
    'reinvestment_efficiency': {
        'weight': 0.20,
        'metrics': {
            'roic': {'excellent': 20, 'good': 12, 'average': 8, 'poor': 3},
            'capex_to_depreciation': {'growth': 1.5, 'maintenance': 1.0, 'underinvest': 0.7},
        },
    },
    'revenue_quality': {
        'weight': 0.15,
        'factors': {
            'recurring_ratio': {'high': 70, 'medium': 40, 'low': 10},
            'customer_concentration': {'low_risk': 30, 'moderate': 50, 'high_risk': 70},
            'geographic_diversification': {'global': 80, 'regional': 50, 'domestic': 20},
        },
    },
}
# 합계: 0.40+0.25+0.20+0.15 = 1.00 ✓
```

### 2.13 Policy Analyzer 상수

```python
POLICY_SCORING = {
    'government_support': {
        'weight': 0.40,
        'levels': POLICY_SCORE_MAP,  # 공유
    },
    'regulatory_environment': {
        'weight': 0.30,
        'levels': {
            'deregulating': 85,     # 규제 완화 추세
            'stable_favorable': 70, # 안정적/우호적
            'neutral': 50,
            'tightening': 30,       # 규제 강화 추세
            'hostile': 10,          # 산업 퇴출 위험
        },
    },
    'global_alignment': {
        'weight': 0.30,
        'factors': {
            'esg_compliance': {'aligned': 80, 'transitioning': 55, 'lagging': 25},
            'trade_policy': {'beneficiary': 80, 'neutral': 50, 'tariff_risk': 20},
            'technology_standards': {'setter': 90, 'adopter': 60, 'excluded': 20},
        },
    },
}
# 합계: 0.40+0.30+0.30 = 1.00 ✓
```

### 2.14 Management Scorer 상수

```python
MANAGEMENT_SCORING = {
    'execution_track_record': {
        'weight': 0.40,
        'metrics': {
            'guidance_accuracy': {'high': 80, 'moderate': 55, 'low': 30},
            'strategy_delivery': {'strong': 85, 'moderate': 55, 'weak': 25},
            'crisis_management': {'proven': 80, 'untested': 50, 'failed': 15},
        },
    },
    'capital_allocation': {
        'weight': 0.35,
        'metrics': {
            'dividend_growth_consistency': {'strong': 80, 'moderate': 55, 'weak': 30},
            'buyback_discipline': {'active': 75, 'occasional': 50, 'none': 30},
            'ma_track_record': {'value_creating': 85, 'neutral': 50, 'value_destroying': 15},
        },
    },
    'governance_quality': {
        'weight': 0.25,
        'kr_specific': {
            'chaebol_discount': {'independent': 80, 'partial': 50, 'controlled': 25},
            'board_independence': {'high': 80, 'moderate': 55, 'low': 25},
            'succession_plan': {'clear': 80, 'developing': 50, 'none': 20},
        },
    },
}
# 합계: 0.40+0.35+0.25 = 1.00 ✓
```

### 2.15 한국 시장 성장 동인 (정적 DB)

```python
KR_GROWTH_DRIVERS = {
    'k_semiconductor': {
        'label': 'K-반도체 전략',
        'megatrend': 'HBM/AI메모리 글로벌 1위',
        'policy': '세제지원, 용인 클러스터',
        'tam_impact': 'S',
        'beneficiary_sectors': ['semiconductor'],
    },
    'k_defense': {
        'label': 'K-방산 수출',
        'megatrend': '글로벌 군비 증강, 폴란드/사우디/UAE',
        'policy': '방산 수출 지원',
        'tam_impact': 'A',
        'beneficiary_sectors': ['defense'],
    },
    'k_nuclear': {
        'label': 'K-원전 르네상스',
        'megatrend': 'SMR + APR1400 수출',
        'policy': '신한울 3,4호기, 체코 수출',
        'tam_impact': 'A',
        'beneficiary_sectors': ['power_equipment', 'utility'],
    },
    'k_bio': {
        'label': 'K-바이오',
        'megatrend': 'CDMO + ADC 라이선싱',
        'policy': '바이오 육성 정책',
        'tam_impact': 'A',
        'beneficiary_sectors': ['bio_health'],
    },
    'k_shipbuilding': {
        'label': 'K-조선 슈퍼사이클',
        'megatrend': 'LNG/암모니아선, 3-4년 백로그',
        'policy': '친환경 선박 전환',
        'tam_impact': 'A',
        'beneficiary_sectors': ['shipbuilding'],
    },
    'k_content': {
        'label': 'K-콘텐츠',
        'megatrend': '게임/엔터/뷰티/식품 글로벌화',
        'policy': '문화산업 수출 지원',
        'tam_impact': 'B',
        'beneficiary_sectors': ['entertainment'],
    },
    'ai_datacenter': {
        'label': 'AI 데이터센터',
        'megatrend': '전력장비/변압기 글로벌 수요',
        'policy': 'AI 인프라 투자',
        'tam_impact': 'A',
        'beneficiary_sectors': ['power_equipment', 'semiconductor'],
    },
    'valueup': {
        'label': '밸류업 프로그램',
        'megatrend': '주주환원 확대, 저PBR 해소',
        'policy': '코리아 밸류업 지수',
        'tam_impact': 'B',
        'beneficiary_sectors': ['financial'],
    },
}

KR_RISK_FACTORS = {
    'chaebol_discount': {'impact': -10, 'sectors': ['all']},
    'geopolitical': {'impact': -8, 'sectors': ['all']},
    'population_decline': {'impact': -5, 'sectors': ['construction', 'telecom', 'utility']},
    'china_competition': {'impact': -7, 'sectors': ['semiconductor', 'battery', 'steel']},
    'fx_volatility': {'impact': -3, 'sectors': ['automotive', 'semiconductor']},
    'regulation_risk': {'impact': -4, 'sectors': ['financial', 'telecom']},
    'energy_dependence': {'impact': -5, 'sectors': ['chemical', 'steel']},
}
```

---

## 3. File Structure & Functions

### 3.1 kr-growth-outlook (NEW — 13 files)

```
skills/kr-growth-outlook/
├── SKILL.md
├── references/
│   ├── sector_tam_database.md      # 14 섹터 TAM DB
│   ├── korea_growth_drivers.md     # 8 메가트렌드 + 7 리스크
│   ├── moat_framework.md           # 5-유형 Moat 분석 가이드
│   └── korea_policy_roadmap.md     # 정부 정책 로드맵
├── scripts/
│   ├── tam_analyzer.py             # TAM/SAM 분석
│   ├── moat_scorer.py              # 경쟁 우위 평가
│   ├── pipeline_evaluator.py       # 기술/제품 파이프라인
│   ├── earnings_projector.py       # 실적 경로 추정
│   ├── policy_analyzer.py          # 정책/규제 분석
│   ├── management_scorer.py        # 경영진 평가
│   ├── growth_synthesizer.py       # 6-컴포넌트 종합
│   └── tests/
│       └── test_growth_outlook.py  # 테스트
└── (13 files total)
```

### 3.2 함수 명세

#### tam_analyzer.py (5 functions)

```python
# Constants: TAM_SCORING, SECTOR_GROWTH_RATINGS

def score_tam_cagr(cagr_percent):
    """TAM CAGR → 0-100 점수. TAM_SCORING['tam_cagr'] 기준."""

def score_market_share_trend(current_ms, prev_ms):
    """시장점유율 변화율 → 0-100 점수."""

def score_sam_penetration(sam_share_percent):
    """SAM 내 침투율 → 0-100 점수 (비선형: 5-15%가 최적)."""

def get_sector_tam_data(sector_name):
    """정적 DB에서 섹터 TAM 데이터 조회.
    Returns: {'tam_2026', 'cagr_26_30', 'kr_ms', 'grade'}"""

def analyze_tam(sector, market_share=None, prev_market_share=None):
    """TAM/SAM 종합 분석. 3개 서브스코어 가중평균.
    Returns: {'cagr_score', 'ms_trend_score', 'penetration_score', 'score'}"""
```

#### moat_scorer.py (3 functions)

```python
# Constants: MOAT_TYPES, MOAT_STRENGTH

def score_moat_type(moat_data):
    """5-유형 Moat 개별 점수. moat_data: dict of type→score mappings.
    Returns: {'type_scores': {...}, 'weighted_score': float}"""

def classify_moat_strength(score):
    """Moat 강도 등급. MOAT_STRENGTH 기준.
    Returns: 'wide' | 'narrow' | 'none'"""

def analyze_competitive_moat(moat_indicators):
    """경쟁 우위 종합 분석.
    Args: moat_indicators: {cost_advantage: 0-100, switching_cost: 0-100, ...}
    Returns: {'score', 'strength', 'type_scores', 'top_moats'}"""
```

#### pipeline_evaluator.py (3 functions)

```python
# Constants: PIPELINE_SCORING

def score_new_products(product_level):
    """신제품 수준 → 0-100 점수. 'breakthrough'|'major'|'incremental'|..."""

def score_rd_capability(rd_to_revenue, patent_growth=None, rd_personnel=None):
    """R&D 역량 종합 점수."""

def analyze_pipeline(product_data):
    """파이프라인 종합 분석.
    Args: {new_products: str, rd_to_revenue: float, tech_position: str, ...}
    Returns: {'new_product_score', 'rd_score', 'tech_score', 'score'}"""
```

#### earnings_projector.py (3 functions)

```python
# Constants: EARNINGS_SCORING, CONSENSUS_EPS_BENCHMARKS

def score_consensus_growth(eps_growth_yoy):
    """컨센서스 EPS 성장률 → 0-100 점수."""

def score_margin_trajectory(opm_change_yoy):
    """영업이익률 변화 → 0-100 점수."""

def analyze_earnings_path(earnings_data):
    """실적 경로 종합 분석.
    Args: {eps_growth_yoy, opm_change, roic, recurring_ratio, ...}
    Returns: {'consensus_score', 'margin_score', 'reinvestment_score',
              'quality_score', 'score'}"""
```

#### policy_analyzer.py (2 functions)

```python
# Constants: POLICY_SCORING, POLICY_SCORE_MAP

def score_government_support(support_level):
    """정부 지원 수준 → 0-100 점수."""

def analyze_policy(policy_data):
    """정책/규제 종합 분석.
    Args: {support_level: str, regulatory: str, esg: str, trade: str, ...}
    Returns: {'support_score', 'regulatory_score', 'global_score', 'score'}"""
```

#### management_scorer.py (2 functions)

```python
# Constants: MANAGEMENT_SCORING

def score_execution(execution_data):
    """경영진 실행력 → 0-100 점수."""

def analyze_management(mgmt_data):
    """경영진 종합 분석.
    Args: {guidance_accuracy: str, capital_allocation: str, governance: str, ...}
    Returns: {'execution_score', 'capital_score', 'governance_score', 'score'}"""
```

#### growth_synthesizer.py (4 functions)

```python
# Constants: GROWTH_COMPONENTS, TIME_HORIZON_MULTIPLIER, GROWTH_GRADES

def _apply_horizon_multiplier(base_scores, horizon):
    """시간축별 가중치 배율 적용.
    Args: base_scores: {component: score}, horizon: 'short_1_3y'|'mid_4_7y'|'long_10y'
    Returns: dict with adjusted weights"""

def _get_growth_grade(score):
    """점수 → 성장 등급 (S/A/B/C/D)."""

def calc_growth_score(component_scores, horizon='short_1_3y'):
    """단일 시간축 성장 점수 계산.
    Returns: {'score', 'grade', 'components', 'horizon'}"""

def analyze_growth_outlook(analysis_data):
    """3시간축 종합 성장성 분석. 최종 엔트리포인트.
    Args: analysis_data: {tam, moat, pipeline, earnings, policy, management 결과}
    Returns: {
        'short': {'score', 'grade'},
        'mid': {'score', 'grade'},
        'long': {'score', 'grade'},
        'composite': 가중평균(short 40%, mid 35%, long 25%),
        'grade': 종합등급,
        'components': 6개 컴포넌트 상세
    }"""
```

### 3.3 kr-stock-analysis (PATCH — 3 files modified, 1 new)

#### growth_quick_scorer.py (NEW — 3 functions)

```python
# Constants: GROWTH_QUICK_COMPONENTS, CONSENSUS_EPS_BENCHMARKS,
#            RD_INVESTMENT_BENCHMARKS, SECTOR_TAM_BENCHMARKS, POLICY_SCORE_MAP

def score_quick_consensus(eps_growth):
    """컨센서스 EPS 성장률 → Quick Score."""

def score_quick_rd(rd_ratio, rd_trend=None):
    """R&D 투자비율 → Quick Score."""

def calc_growth_quick_score(consensus_eps=None, rd_ratio=None,
                            sector=None, policy_level=None):
    """경량 Growth Quick Score 계산. WebSearch 미사용.
    Returns: {'score', 'grade', 'components', 'summary_lines': [단기, 중기, 장기]}"""
```

#### comprehensive_scorer.py (PATCH)

변경사항:
```python
# COMPREHENSIVE_SCORING 가중치 변경: V1 → V2
# calc_comprehensive_score()에 growth_quick=None 파라미터 추가
# _generate_recommendation()에서 growth 컴포넌트도 강점/약점 식별
```

#### SKILL.md (PATCH)

추가 섹션:
- "Growth Quick Score" 설명
- 가중치 변경 안내 (4→5 컴포넌트)
- `/kr-growth-outlook` 연계 안내

#### tests/test_stock_analysis.py (PATCH)

추가:
- `TestGrowthQuickScorer` 클래스
- 기존 `TestComprehensiveScorer` 가중치 업데이트

### 3.4 kr-sector-analyst (PATCH — 2 files modified, 1 new)

#### sector_growth_scorer.py (NEW — 2 functions)

```python
# Constants: SECTOR_GROWTH_RATINGS (공유)

def get_sector_growth_outlook(sector_name):
    """섹터별 성장 전망 데이터.
    Returns: {'grade', 'cagr', 'tam', 'drivers', 'risks'}"""

def generate_sector_growth_table(sectors=None):
    """14개 섹터 성장 전망 테이블 생성.
    Returns: list of {sector, grade_3y, grade_10y, cagr, drivers}"""
```

### 3.5 kr-strategy-synthesizer (PATCH — 2 files modified)

#### conviction_scorer.py (PATCH)

변경사항:
```python
# CONVICTION_COMPONENTS에 'growth_outlook' 추가 (weight: 0.12)
# 기존 7개 가중치 비례 축소
# calc_component_scores()에 growth_outlook 계산 추가
# normalize_signal()에 'kr-growth-outlook' 케이스 추가
```

---

## 4. Implementation Order

```
Step 1: 정적 레퍼런스 생성 (4 files)
  ├─ references/sector_tam_database.md
  ├─ references/korea_growth_drivers.md
  ├─ references/moat_framework.md
  └─ references/korea_policy_roadmap.md

Step 2: kr-growth-outlook 핵심 스크립트 (7 files)
  ├─ tam_analyzer.py         (5 functions, ~80 lines)
  ├─ moat_scorer.py          (3 functions, ~70 lines)
  ├─ pipeline_evaluator.py   (3 functions, ~70 lines)
  ├─ earnings_projector.py   (3 functions, ~80 lines)
  ├─ policy_analyzer.py      (2 functions, ~50 lines)
  ├─ management_scorer.py    (2 functions, ~60 lines)
  └─ growth_synthesizer.py   (4 functions, ~100 lines)

Step 3: kr-stock-analysis 패치 (4 files)
  ├─ growth_quick_scorer.py  (NEW: 3 functions, ~80 lines)
  ├─ comprehensive_scorer.py (PATCH: 가중치 + 파라미터)
  ├─ SKILL.md                (PATCH: 섹션 추가)
  └─ report_generator.py     (PATCH: growth 출력)

Step 4: kr-sector-analyst 패치 (3 files)
  ├─ sector_growth_scorer.py (NEW: 2 functions, ~50 lines)
  ├─ kr_sector_rotation.md   (PATCH: TAM 테이블)
  └─ SKILL.md                (PATCH: 섹션 추가)

Step 5: kr-strategy-synthesizer 패치 (2 files)
  ├─ conviction_scorer.py    (PATCH: 8th component)
  └─ SKILL.md                (PATCH: 섹션 추가)

Step 6: 테스트 (2 files)
  ├─ test_growth_outlook.py  (NEW: ~150 lines)
  └─ test_stock_analysis.py  (PATCH: 가중치 변경)
```

**예상 규모**: 23 files, ~22 functions, ~900 lines, ~100 tests

---

## 5. Design Constants Summary

| Category | Count | Verification |
|----------|:-----:|:------------:|
| 가중치 합계 검증 | 10개 | 모두 1.00 ✓ |
| 벤치마크 상수 | 42개 | |
| 등급 체계 | 3세트 (Growth/Moat/Policy) | |
| 섹터 DB | 14개 | |
| 메가트렌드 | 8개 | |
| 리스크 팩터 | 7개 | |
| **총 설계 상수** | **~85개** | |

---

## 6. Test Design

### test_growth_outlook.py (~100 tests)

```python
class TestTamAnalyzer:  # ~15 tests
    def test_score_tam_cagr_explosive()
    def test_score_tam_cagr_stagnant()
    def test_score_market_share_gaining()
    def test_score_sam_penetration_optimal()  # 5-15% = 최적
    def test_get_sector_tam_data_semiconductor()
    def test_get_sector_tam_data_unknown()
    def test_analyze_tam_full()
    ...

class TestMoatScorer:  # ~10 tests
    def test_score_moat_type_wide()
    def test_classify_moat_strength_thresholds()
    def test_analyze_competitive_moat_full()
    ...

class TestPipelineEvaluator:  # ~10 tests
    def test_score_new_products_breakthrough()
    def test_score_rd_capability_leader()
    def test_analyze_pipeline_full()
    ...

class TestEarningsProjector:  # ~12 tests
    def test_score_consensus_hyper()
    def test_score_consensus_decline()
    def test_score_margin_expanding()
    def test_analyze_earnings_path_full()
    ...

class TestPolicyAnalyzer:  # ~8 tests
    def test_score_government_support_levels()
    def test_analyze_policy_full()
    ...

class TestManagementScorer:  # ~8 tests
    def test_score_execution_strong()
    def test_analyze_management_full()
    ...

class TestGrowthSynthesizer:  # ~20 tests
    def test_apply_horizon_multiplier_short()
    def test_apply_horizon_multiplier_long()
    def test_get_growth_grade_all_grades()
    def test_calc_growth_score_short()
    def test_calc_growth_score_long()
    def test_analyze_growth_outlook_full()
    def test_composite_weighting()  # short 40% + mid 35% + long 25%
    ...

class TestGrowthQuickScorer:  # ~15 tests
    def test_score_quick_consensus_hyper()
    def test_score_quick_rd_leader()
    def test_calc_growth_quick_score_full()
    def test_calc_growth_quick_score_missing_data()
    def test_summary_lines_format()
    ...

class TestComprehensiveScorerV2:  # ~5 tests (패치 검증)
    def test_v2_weights_sum_to_one()
    def test_v2_with_growth_component()
    def test_v2_backward_compat_without_growth()
    ...
```

**예상 테스트 수**: ~100 tests

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-05 | Initial design | saisei |
