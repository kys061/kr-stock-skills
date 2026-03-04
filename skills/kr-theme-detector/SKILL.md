# kr-theme-detector

## 개요

한국 시장의 테마(섹터/산업) 트렌드를 탐지하고 분석하는 스킬.
US `theme-detector` (FINVIZ 기반)를 한국 시장에 맞게 포팅.

## 핵심 차이점 (US → KR)

| US 원본 | KR 버전 |
|---------|---------|
| FINVIZ ~145 industries | **KRX 업종 + 커스텀 테마 14개** (kr_themes.yaml) |
| FINVIZ price/volume | **KRClient (PyKRX)** OHLCV/시총/거래량 |
| FMP API P/E | **KRClient** PER/PBR |
| Uptrend Dashboard | **자체 업트렌드 비율 계산** |
| WebSearch (US 뉴스) | **WebSearch (한국 뉴스)** |

## 실행 방법

```bash
# 전체 테마 분석
python3 skills/kr-theme-detector/scripts/kr_theme_detector.py \
  --output-dir reports/

# 상위 5개만 상세 분석 (속도 우선)
python3 skills/kr-theme-detector/scripts/kr_theme_detector.py \
  --max-themes 5 --skip-narrative --output-dir reports/

# 예상 소요시간: 3-5분
```

## 3D 스코어링 모델

### Dimension 1: Theme Heat (0-100)
| 컴포넌트 | 가중치 | 설명 |
|----------|:------:|------|
| Momentum | 40% | 시총가중 1주/1개월 수익률 |
| Volume | 20% | 5일 거래량 / 20일 평균 |
| Uptrend Ratio | 25% | 200MA 위 종목 비율 |
| Breadth | 15% | 최근 5일 양봉 비율 |

### Dimension 2: Lifecycle
- **Early**: 모멘텀 시작, 거래량 증가 초기
- **Mid**: 모멘텀 지속, 거래량 안정적
- **Late**: 모멘텀 극단, 거래량 급증, 밸류에이션 과열
- **Exhaustion**: 모멘텀 둔화, 거래량 감소

### Dimension 3: Confidence
- **High**: 정량 + 정성 모두 강한 신호
- **Medium**: 혼재된 신호
- **Low**: 약한 신호

## 한국 테마 14개

AI/반도체, 2차전지, 바이오/제약, 자동차/모빌리티, 방산, K-컨텐츠,
조선/해운, 금융/밸류업, 인터넷/플랫폼, 철강/소재, 건설/인프라,
에너지/정유, 통신/유틸리티, 소비재/유통

## 스크립트 구조

```
kr-theme-detector/
├── SKILL.md
├── config/
│   └── kr_themes.yaml          # 테마 정의 (14개)
├── references/
│   └── theme_methodology.md    # 방법론 문서
└── scripts/
    ├── kr_theme_detector.py    # 메인 오케스트레이터
    ├── industry_data_collector.py  # KRX 데이터 수집
    ├── theme_classifier.py     # 종목 → 테마 분류
    ├── scorer.py               # 3D 스코어링
    ├── report_generator.py     # JSON + Markdown 리포트
    └── tests/
        └── test_theme.py       # 단위 테스트
```

## 출력 포맷

### 테마 대시보드
| 테마 | Heat | 방향 | 라이프사이클 | 신뢰도 |
|------|:----:|:----:|:----------:|:------:|
| AI/반도체 | 82 | Bullish | Mid | High |
| 방산 | 75 | Bullish | Mid | High |
| 2차전지 | 45 | Bearish | Late | Medium |

### 방향 판정
- **Bullish**: 가중 수익률 > 0 AND (업트렌드 > 50% OR 거래량 축적)
- **Bearish**: 가중 수익률 < 0 AND (업트렌드 < 50% OR 거래량 분산)
- **Neutral**: 혼재된 신호
