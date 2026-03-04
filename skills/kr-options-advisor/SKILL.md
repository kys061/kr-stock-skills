---
name: kr-options-advisor
description: KOSPI200 옵션 Black-Scholes 가격결정, 그릭스 계산, 18개 전략 시뮬레이션. 승수 250,000원, VKOSPI, BOK 금리 적용.
---

# kr-options-advisor

> KOSPI200 옵션 기반 Black-Scholes 가격결정, 그릭스 계산, 18개 전략 시뮬레이션.

## KOSPI200 옵션 기본 정보

| 항목 | 값 |
|------|---|
| 승수 | 250,000원/포인트 |
| 틱 사이즈 | 0.01pt (프리미엄<3) / 0.05pt (프리미엄≥3) |
| 틱 가치 | 2,500원 |
| 거래시간 | 09:00-15:45 (KST) |
| 결제 | T+1 현금결제 |
| 만기일 | 매월 2번째 목요일 |

## 18개 전략

| 카테고리 | 전략 | 레그 수 |
|----------|------|:-------:|
| 인컴 | Covered Call, Cash Secured Put, PMCC | 2, 1, 2 |
| 보호 | Protective Put, Collar | 2, 3 |
| 방향성 | Bull/Bear Call/Put Spread, Long Straddle/Strangle | 2 each |
| 변동성 | Short Straddle/Strangle, Iron Condor/Butterfly | 2, 2, 4, 4 |
| 고급 | Calendar Spread, Diagonal Spread, Ratio Spread | 2, 2, 3 |

## 주요 기능

- **Black-Scholes 가격결정**: 콜/풋 이론가 및 그릭스 (δ, γ, θ, ν, ρ)
- **전략 시뮬레이션**: 18개 전략 P/L 분석 및 만기 손익 곡선
- **VKOSPI 연동**: 한국 변동성 지수 기반 IV 분석
- **IV Crush 모델**: 실적 전후 변동성 변화 시뮬레이션

## 사용법

```bash
python black_scholes.py --spot 350 --strike 355 --dte 30 --vol 0.20 --type call
python strategy_simulator.py --strategy bull_call_spread --spot 350 --dte 30
```
