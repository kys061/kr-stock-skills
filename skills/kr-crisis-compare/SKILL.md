# kr-crisis-compare — 역사적 위기 비교 패턴

> 현재 시장 상황을 5개 역사적 위기 사례와 비교 분석하여
> 유사도 순위, 회복 패턴, 예상 시나리오를 제시한다.

## 사용법

```
/kr-crisis-compare                    # 기본 분석 (자동 위기 유형 감지)
/kr-crisis-compare --type geopolitical  # 위기 유형 수동 지정
/kr-crisis-compare 현재 KOSPI 상황 분석  # 자연어 요청
```

## 비교 대상 사례 (5개)

| # | 사례 | 시기 | 트리거 | KOSPI 하락 | VIX 최고 |
|---|------|------|--------|-----------|---------|
| 1 | 글로벌 금융위기 | 2008.10 | 리먼 파산 | -54.5% | 89.53 |
| 2 | 코로나 팬데믹 | 2020.03 | 글로벌 락다운 | -33.9% | 82.69 |
| 3 | 금리인상 충격 | 2022.01~09 | Fed 425bp 인상 | -24.9% | ~36 |
| 4 | 트럼프 관세 쇼크 | 2025.04 | "해방의 날" 관세 | -14.0% | 52.33 |
| 5 | 이란 위기 | 2026.03 | 미-이스라엘 이란 공습 | -18.0% | ~45 |

## 데이터 소스 우선순위

### 현재 시장 데이터 (자동 수집)
| 순위 | 소스 | 데이터 | 비고 |
|:----:|------|--------|------|
| 1 | yfinance | KOSPI(^KS11), VIX(^VIX), S&P500(^GSPC), USD/KRW(KRW=X) | 6개월 히스토리 |
| 2 | WebFetch | VKOSPI, CNN Fear & Greed | yfinance 미제공 시 |
| 3 | WebSearch | 뉴스 센티먼트, 정책 변화 | 보조 데이터 |

### 현재 시장 데이터 수집 URL
- KOSPI: https://finance.yahoo.com/quote/%5EKS11/
- VIX: https://finance.yahoo.com/quote/%5EVIX/
- VKOSPI: https://kr.investing.com/indices/kospi-volatility
- S&P 500: https://finance.yahoo.com/quote/%5EGSPC/
- 뉴스: https://www.cnbc.com/asia-markets/

### 역사적 데이터 (스크립트 내장)
- 5개 사례의 정량 데이터(하락폭, VIX, 회복률)는 `crisis_compare.py`에 내장
- 참고 소스: https://tradingeconomics.com/south-korea/stock-market
- VIX 히스토리: https://www.macroption.com/vix-all-time-high/

## 분석 절차

### Step 1: 현재 시장 데이터 수집
```bash
cd skills/kr-crisis-compare/scripts && python crisis_compare.py --format json
```
- yfinance로 KOSPI, VIX, S&P500, USD/KRW 자동 수집
- 6개월 고점 대비 하락폭(drawdown) 자동 계산

### Step 2: 유사도 분석 (5차원 가중 비교)
| 차원 | 가중치 | 비교 기준 |
|------|--------|----------|
| VIX 수준 | 20% | 현재 VIX vs 과거 VIX 피크 |
| KOSPI 하락폭 | 25% | 현재 drawdown vs 과거 하락폭 |
| S&P500 하락폭 | 15% | 현재 drawdown vs 과거 하락폭 |
| 하락 속도 | 15% | 일당 하락률 비교 |
| 위기 유형 | 25% | financial/pandemic/monetary/trade/geopolitical |

### Step 3: 회복 패턴 조회
- 가장 유사한 사례의 바닥 대비 회복률 표시:
  - 1주 후, 1개월 후, 3개월 후, 6개월 후

### Step 4: 시나리오 생성
과거 회복 패턴 기반 3단계 시나리오:
- **낙관** (회복계수 1.3x): 조기 해결, 대규모 부양책
- **기본** (회복계수 1.0x): 과거 패턴 반복
- **보수** (회복계수 0.5x): 위기 장기화, 추가 악재

### Step 5: 위기 유형 판단
자동 감지가 어려울 경우 `--crisis-type` 옵션으로 수동 지정:
- `financial`: 금융 시스템 리스크 (은행 파산, 신용경색)
- `pandemic`: 감염병/외부 충격 (경제활동 중단)
- `monetary`: 통화정책 충격 (금리, 긴축)
- `trade`: 무역/관세 정책 (무역전쟁)
- `geopolitical`: 지정학적 충격 (군사 충돌, 전쟁)

## Output Rule

`_kr_common/templates/report_rules.md` 공통 규칙을 따른다.

### 리포트 저장 경로
```
~/stock_reports/crisis-compare/crisis_compare_YYYYMMDD_HHMM.md
```

### 출력 형식

```markdown
# 역사적 위기 비교 분석 — YYYY-MM-DD HH:MM

## 현재 시장 상황
| 지표 | 현재값 | 6개월 고점 | 고점대비 하락 |
|------|--------|-----------|-------------|

## 유사도 순위
| 순위 | 위기 사례 | 유사도 | VIX | KOSPI 하락 | 속도 |
|------|----------|--------|-----|-----------|------|

## 가장 유사한 사례: {사례명}
| 항목 | 가장 유사한 과거 사례 | 현재 상황 |
|------|---------------------|----------|

## 유사 사례 회복 패턴
- 바닥까지 소요: **N일** (속도분류)
- 바닥 대비 1주/1개월/3개월/6개월 후 회복률

## 과거 패턴 기반 예상 시나리오
- 낙관: (조건) → KOSPI 예상 범위
- 기본: (조건) → KOSPI 예상 범위
- 보수: (조건) → KOSPI 예상 범위

> 주의: 과거 패턴은 미래를 보장하지 않습니다. 참고용으로만 활용하세요.
```

## 관련 스킬

| 스킬 | 연관성 |
|------|--------|
| kr-rebound-signal | 14개 반등 시그널 체크 → 본 스킬의 회복 시나리오 보완 |
| kr-market-top-detector | 천장 감지 → 위기 진입 시점 판단 |
| kr-bubble-detector | 버블 위험도 → 위기 규모 예측 |
| kr-macro-regime | 매크로 레짐 → 위기 유형 자동 분류 보조 |
| daily-market-check | 일일 매크로 지표 → 현재 상황 데이터 보완 |
| kr-market-environment | 글로벌 시장 진단 → 위기 컨텍스트 |
