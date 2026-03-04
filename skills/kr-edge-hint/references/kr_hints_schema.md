# 한국 시장 엣지 힌트 스키마

## 힌트 구조

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| symbol | str | Y | 종목 코드 (6자리) |
| direction | str | Y | bullish / bearish / neutral |
| entry_family | str | N | pivot_breakout / gap_up_continuation |
| hypothesis | str | Y | 8가지 가설 유형 중 하나 |
| source | str | Y | rule:{source_name} 또는 llm:{model} |
| confidence | float | Y | 0.0 ~ 1.0 |
| memo | str | Y | 한국어 설명 |

## 한국 힌트 소스

| 소스 | 키 | 설명 |
|------|------|------|
| 외국인 수급 | foreign_flow | 외국인 순매수 전환/연속 |
| 기관 수급 | institutional_flow | 기관 순매수 전환/연속 |
| 프로그램 매매 | program_trading | 프로그램 순매수 방향 |
| 공매도 잔고 | short_interest | 공매도 잔고 변동 |
| 신용잔고 | credit_balance | 신용잔고 과열/냉각 |

## regime 판정

- market_summary의 risk_on / risk_off 카운트 비교
- risk_on - risk_off >= RISK_ON_OFF_THRESHOLD → "RiskOn"
- risk_off - risk_on >= RISK_ON_OFF_THRESHOLD → "RiskOff"
- 그 외 → "Neutral"

## 8가지 가설 유형 (Hypothesis)

1. **breakout** — 참여 확대 기반 추세 돌파
2. **earnings_drift** — 이벤트 기반 지속 드리프트
3. **news_reaction** — 뉴스 과반응 드리프트
4. **futures_trigger** — 교차 자산 전파
5. **calendar_anomaly** — 계절성 수요 불균형
6. **panic_reversal** — 충격 과도 반전
7. **regime_shift** — 레짐 전환 기회
8. **sector_x_stock** — 리더-래거드 섹터 릴레이
