# kr-market-top-detector

한국 시장 천장 탐지기 — 7-컴포넌트 리스크 스코어링.

## 개요

O'Neil 분배일 + Minervini 선도주 악화 + 방어 섹터 로테이션 + 외국인 이탈 지표.
KOSPI/KOSDAQ 이중 추적, 한국 선도주 8종목 바스켓, KRX 업종 기반 방어/성장 분류.

## 7-컴포넌트 스코어링 (0-100)

| # | 컴포넌트 | 가중치 | 핵심 시그널 |
|---|---------|:------:|-----------|
| 1 | Distribution Day Count | 20% | 25 거래일 내 분배일 누적 |
| 2 | Leading Stock Health | 15% | 선도주 8종목 건전성 악화 |
| 3 | Defensive Sector Rotation | 12% | 방어→성장 상대 성과 역전 |
| 4 | Market Breadth Divergence | 13% | 지수 고점 vs 시장폭 하락 |
| 5 | Index Technical Condition | 13% | MA 구조 악화, 실패 랠리 |
| 6 | Sentiment & Speculation | 12% | VKOSPI + 신용잔고 변화 |
| 7 | Foreign Investor Flow | 15% | 외국인 연속 순매도, 이탈 강도 |

## 리스크 존

| 점수 | 존 | 리스크 예산 | 행동 |
|:----:|-----|:---------:|------|
| 0-20 | Green | 100% | 정상 운영 |
| 21-40 | Yellow | 80-90% | 손절 강화, 진입 축소 |
| 41-60 | Orange | 60-75% | 약한 포지션 이익실현 |
| 61-80 | Red | 40-55% | 적극적 이익실현 |
| 81-100 | Critical | 20-35% | 최대 방어, 헤지 |

## Component 1: Distribution Day Count (20%)

### 분배일 정의 (O'Neil)
- 지수 종가 전일 대비 **-0.2% 이상** 하락
- 거래량이 **전일 거래량 이상**
- 25 거래일 이내 발생

### KOSPI + KOSDAQ 이중 추적
- 두 지수의 분배일 독립 계산
- 최종 = max(KOSPI, KOSDAQ) × 0.7 + min × 0.3
- 두 지수 동시 분배일 → 신호 강화

| 분배일 수 | 점수 | 해석 |
|:---------:|:----:|------|
| 0-2 | 0-20 | 정상 |
| 3 | 30 | 초기 경고 |
| 4 | 50 | 주의 |
| 5 | 70 | 위험 상승 |
| 6+ | 80-100 | 높은 천장 확률 |

## Component 2: Leading Stock Health (15%)

### 한국 선도주 바스켓 (8종목)
| 종목 | Ticker | 테마 |
|------|--------|------|
| 삼성전자 | 005930 | AI/반도체 |
| SK하이닉스 | 000660 | 반도체 |
| LG에너지솔루션 | 373220 | 2차전지 |
| 삼성바이오로직스 | 207940 | 바이오 |
| 현대차 | 005380 | 자동차 |
| 셀트리온 | 068270 | 바이오시밀러 |
| NAVER | 035420 | 플랫폼 |
| 한화에어로스페이스 | 012450 | 방산 |

### 건전성 지표
- `pct_below_50ma`: 50MA 아래 종목 비율 (높을수록 위험)
- `avg_drawdown`: 52주 고점 대비 평균 하락률 (깊을수록 위험)
- `declining_count`: 주간 수익률 음수 종목 수

## Component 3: Defensive Sector Rotation (12%)

### KRX 업종 분류
| 방어 | 성장 |
|------|------|
| 전기가스업(1013) | 전기전자(1009) |
| 음식료(1001) | 서비스업(1021) |
| 의약품(1005) | 유통업(1012) |

- 상대 성과 = 방어 수익률 - 성장 수익률
- 양(+) = 방어 outperform → 위험 시그널

## Component 4: Market Breadth Divergence (13%)

지수가 고점을 만들지만 시장폭(200MA 위 종목 비율)이 축소되는 다이버전스.
kr-market-breadth JSON 출력 참조 또는 자체 계산.

## Component 5: Index Technical Condition (13%)

| 신호 | 점수 기여 |
|------|:--------:|
| 10MA < 21MA | +15 |
| 21MA < 50MA | +15 |
| 50MA < 200MA (데드크로스) | +25 |
| 실패 랠리 | +20 |
| 저점 하향 (Lower Low) | +15 |
| 거래량 감소 속 상승 | +10 |

## Component 6: Sentiment & Speculation (12%)

### VKOSPI 스코어링
| VKOSPI | 점수 | 해석 |
|:------:|:----:|------|
| < 13 | +40 | 극단적 안일 → 위험 |
| 13-18 | +20 | 정상적 낙관 |
| 18-25 | 0 | 건전한 경계 |
| > 25 | -10 | 공포 → 바닥 근접 |

### 신용잔고 스코어링
| YoY 변화 | 점수 | 해석 |
|:--------:|:----:|------|
| +15% 이상 | +30 | 레버리지 과열 |
| +5~15% | +15 | 보통 |
| -5~+5% | 0 | 정상 |
| -5% 이하 | -10 | 디레버리징 |

## Component 7: Foreign Investor Flow (15%) — 한국 특화

| 조건 | 점수 |
|------|:----:|
| 연속 순매수 5일+ | 0-10 |
| 중립 | 10-30 |
| 연속 순매도 3-5일 | 30-50 |
| 연속 순매도 5-10일 + 강도 1.5x+ | 50-75 |
| 연속 순매도 10일+ + 강도 2x+ | 75-100 |

## 스크립트

| 파일 | 역할 |
|------|------|
| `distribution_calculator.py` | 분배일 카운터 |
| `leading_stock_calculator.py` | 선도주 건전성 |
| `defensive_rotation_calculator.py` | 방어 섹터 로테이션 |
| `foreign_flow_calculator.py` | 외국인 이탈 (한국 특화) |
| `scorer.py` | 7-컴포넌트 스코어링 |
| `report_generator.py` | JSON/Markdown 리포트 |
| `kr_market_top_detector.py` | 메인 오케스트레이터 |

## 참조 문서

| 파일 | 내용 |
|------|------|
| `references/distribution_day_kr.md` | 분배일 방법론 한국 적용 |
| `references/historical_kr_tops.md` | 한국 역사적 천장 사례 |
