---
name: daily-market-check
description: 매일 아침 글로벌 매크로 6개 지표(VIX/CNN F&G/KOSPI/USD-KRW/S&P500/EWY) 수치 확인 및 종합 시장 상태 판정.
---

# daily-market-check: 매일 아침 시장 체크

> 글로벌 매크로 핵심 지표 6개를 조회하여 오늘의 시장 상태를 빠르게 판단합니다.
> 매일 아침 루틴으로 사용하며, 1분 안에 시장 온도를 파악할 수 있습니다.

## 데이터 소스 우선순위

```
1순위: yfinance (VIX/KOSPI/S&P500/EWY/USD-KRW 프로그래밍 조회)
2순위: WebFetch (지정 URL에서 직접 수집)
3순위: WebSearch 폴백 (검색 기반 수집)
```

### 스크립트 실행 (1순위)

```bash
cd ~/stock/skills/daily-market-check/scripts
python3 market_check.py
```

yfinance로 5개 지표(VIX, KOSPI, S&P500, EWY, USD/KRW)를 자동 수집한다.
CNN Fear & Greed Index는 yfinance 미제공 → WebSearch로 보완.

### WebFetch 폴백 (2순위)

스크립트 실패 시 아래 URL에서 직접 데이터를 수집한다:

| 지표 | 1순위 URL | 2순위 URL |
|------|-----------|-----------|
| VIX | https://finance.yahoo.com/quote/%5EVIX/ | https://www.investing.com/indices/volatility-s-p-500 |
| CNN F&G | https://www.cnn.com/markets/fear-and-greed | https://en.macromicro.me/charts/50108/cnn-fear-and-greed |
| KOSPI | https://finance.yahoo.com/quote/%5EKS11/ | https://finance.naver.com/sise/sise_index.naver?code=KOSPI |
| USD/KRW | https://www.investing.com/currencies/usd-krw | https://finance.yahoo.com/quote/KRW=X/ |
| S&P 500 | https://finance.yahoo.com/quote/%5EGSPC/ | https://www.investing.com/indices/us-spx-500 |
| EWY | https://finance.yahoo.com/quote/EWY/ | https://www.investing.com/etfs/ishares-msci-south-korea |

## 6개 체크 지표

### 1. VIX (CBOE 공포지수)
- **티커**: `^VIX`
- **의미**: S&P500 옵션 내재 변동성. 시장 공포 수준 측정.
- **상태 기준**:

| 범위 | 상태 | 의미 |
|------|------|------|
| < 20 | 정상 | 시장 안정 |
| 20 ~ 35 | 주의 | 변동성 확대 |
| 35 ~ 45 | 경고 | 공포 확산 |
| > 45 | 극공포 | 패닉 상태 |

### 2. CNN Fear & Greed Index
- **소스**: CNN Markets
- **범위**: 0 ~ 100
- **상태 기준**:

| 범위 | 상태 | 의미 |
|------|------|------|
| > 60 | 탐욕 | 과열 주의 |
| 40 ~ 60 | 중립 | 균형 |
| 20 ~ 40 | 공포 | 매수 기회 탐색 |
| < 20 | 극공포 | 역발상 매수 구간 |

### 3. KOSPI
- **티커**: `^KS11`
- **의미**: 한국 대표 지수. 전일 대비 등락률 확인.

### 4. USD/KRW 환율
- **티커**: `KRW=X`
- **의미**: 원화 가치. 외국인 자금 흐름과 직결.
- **상태 기준**:

| 범위 | 상태 | 의미 |
|------|------|------|
| < 1,350 | 정상 | 원화 안정 |
| 1,350 ~ 1,400 | 주의 | 원화 약세 |
| > 1,400 | 경고 | 외국인 이탈 우려 |

### 5. S&P 500
- **티커**: `^GSPC`
- **의미**: 미국 대표 지수. 글로벌 리스크 온/오프 기준.

### 6. EWY (iShares MSCI South Korea ETF)
- **티커**: `EWY`
- **의미**: 미국 시장에서 본 한국 시장 프록시. 야간 한국 시장 방향 선행지표.

## 출력 형식

```markdown
# Daily Market Check - {YYYY-MM-DD}

| 지표 | 현재 수치 | 변화 | 상태 | 출처 |
|------|----------|------|------|------|
| VIX | XX.XX | +X.XX% | 정상/주의/경고/극공포 | yfinance |
| CNN F&G | XX | - | 탐욕/중립/공포/극공포 | WebSearch |
| KOSPI | X,XXX.XX | +X.XX% | - | yfinance |
| USD/KRW | X,XXX.XX | +X.XX% | 정상/주의/경고 | yfinance |
| S&P 500 | X,XXX.XX | +X.XX% | - | yfinance |
| EWY | $XX.XX | +X.XX% | - | yfinance |

> **종합 판단**: {정상 / 주의 / 경고 / 위험}
> **판단 근거**: {한줄 설명}
```

## 종합 판단 로직

6개 지표의 상태를 종합하여 4단계로 판정:

| 종합 상태 | 조건 |
|----------|------|
| **정상** | VIX < 20 AND CNN F&G > 40 AND USD/KRW < 1,350 |
| **주의** | VIX 20~35 OR CNN F&G 20~40 OR USD/KRW 1,350~1,400 |
| **경고** | VIX > 35 OR CNN F&G < 20 OR USD/KRW > 1,400 |
| **위험** | VIX > 45 AND CNN F&G < 20 (복수 극단 동시 발생) |

## 사용 시점

- 매일 장 시작 전 시장 온도 파악
- 한국 장 마감 후 미국 시장 마감 결과 확인
- 글로벌 이벤트(FOMC, CPI) 전후 리스크 레벨 점검

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-market-environment | 종합 시장 환경 심층 분석 |
| kr-macro-regime | 매크로 레짐 판정 (RiskOn/Off) |
| kr-market-breadth | 시장폭 상세 분석 |
| kr-bubble-detector | 버블 위험도 정밀 스코어링 |

> daily-market-check는 1분 체크, 이상 발견 시 위 스킬로 심층 분석.

---

## Output Rule (마크다운 리포트 저장)

- **템플릿**: `_kr_common/templates/report_macro.md` 의 구조를 참조
- **공통 규칙**: `_kr_common/templates/report_rules.md` 참조
- 저장 경로: `reports/daily-market-check_market_{YYYYMMDD}.md`
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)
