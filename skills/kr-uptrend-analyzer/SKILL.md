# kr-uptrend-analyzer

## 개요

한국 시장의 업트렌드 종목 비율을 업종별로 분석하여 시장 건강도를 진단하는 스킬.
US `uptrend-analyzer` (Monty's Uptrend Dashboard)를 한국 시장에 맞게 포팅.

## 핵심 차이점 (US → KR)

| US 원본 | KR 버전 |
|---------|---------|
| Monty's CSV (~2,800 종목) | **KRX 업종별 구성종목** (PyKRX 자체 계산) |
| 11 GICS Sectors | **KRX 업종 분류** (~17개 그룹) |
| S&P 500 기준 | **KOSPI + KOSDAQ** 기준 |

## 실행 방법

```bash
# 업트렌드 분석 실행
python3 skills/kr-uptrend-analyzer/scripts/kr_uptrend_analyzer.py \
  --output-dir reports/

# 예상 소요시간: 3-5분 (업종별 종목 OHLCV 조회)
```

## 5-컴포넌트 스코어링

| 컴포넌트 | 가중치 | 설명 |
|----------|:------:|------|
| Market Breadth (Overall) | 30% | 전체 업트렌드 비율 + 추세 방향 |
| Sector Participation | 25% | 업트렌드 업종 수 + 비율 편차 |
| Sector Rotation | 15% | 경기민감 vs 방어 균형 |
| Momentum | 20% | 기울기 방향 + 가속도 |
| Historical Context | 10% | 히스토리 내 백분위 |

## 한국 업종 그룹핑

```
Cyclical: 반도체, 자동차, 철강, 화학, 건설, 조선, 기계
Defensive: 통신, 유틸리티, 필수소비재, 제약/바이오
Growth: 2차전지, 인터넷, IT서비스
Financial: 은행, 보험, 증권
```

## 출력

### Uptrend Zone 매핑

| 점수 | 진단 | 권장 노출도 |
|:----:|------|:---------:|
| 80-100 | Strong Bull | 90-100% |
| 60-79 | Bull-Lower | 80-100% |
| 40-59 | Neutral | 60-80% |
| 20-39 | Bear-Lower | 40-60% |
| 0-19 | Strong Bear | 25-40% |

### 경고 시스템

- **Late Cycle**: 원자재 업종 업트렌드 > 경기민감 AND 방어
- **High Spread**: 업종간 최대-최소 스프레드 > 40pp
- **Divergence**: 그룹 내 표준편차 높음 (>20pp)

## 스크립트 구조

```
kr-uptrend-analyzer/
├── SKILL.md
├── references/
│   └── uptrend_methodology.md
└── scripts/
    ├── kr_uptrend_analyzer.py   # 메인 오케스트레이터
    ├── uptrend_calculator.py    # 업종별 업트렌드 비율 계산
    ├── scorer.py                # 5-컴포넌트 스코어링
    ├── report_generator.py      # JSON + Markdown 리포트
    ├── history_tracker.py       # 점수 히스토리 관리
    └── tests/
        └── test_uptrend.py      # 단위 테스트
```

## 데이터 소스

KRClient (PyKRX) 사용:
- `get_index_constituents()` — 지수/업종 구성종목
- `get_ohlcv()` — 종목별 OHLCV
- `get_market_cap()` — 시가총액 (가중 평균용)

## 업트렌드 판정 기준

```
종목이 업트렌드:
1. 종가 > 200일 SMA (필수)
2. 200일 SMA 기울기 > 0 (상승 추세, 필수)
3. 종가 > 50일 SMA (보조 확인)

판정: 조건 1 AND 조건 2 충족 시 업트렌드
```
