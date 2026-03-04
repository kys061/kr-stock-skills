# 한국 CANSLIM 적용 가이드

## CANSLIM 개요
William O'Neil이 개발한 성장주 선별 시스템.
7가지 핵심 요소로 종목을 종합 평가.

## 한국 적용 핵심 변경점

### C (Current Earnings)
- US: FMP quarterly income-statement
- KR: DART 분기보고서 (`get_financial_statements()`)
- 한국은 분기별 DART 보고서 제출 일정이 상이 (45일 지연)
- Q1→'11013', Q2→'11012'(반기), Q3→'11014', Q4→'11011'(사업보고서)

### I (Institutional)
- US: 13F 분기별 (지연)
- KR: **일별 12분류 실시간** (`get_investor_trading(detail=True)`)
- 외국인 지분율: `get_foreign_exhaustion()`
- 연기금 순매수 한국 특화 보너스

### M (Market Direction)
- US: S&P 500 + 50 EMA + VIX
- KR: KOSPI + 50 EMA + VKOSPI + **Phase 3 크로스레퍼런스**
  - kr-market-breadth → breadth_score
  - kr-macro-regime → regime
  - kr-market-top-detector → risk_zone

## 스크리닝 유니버스
- KOSPI 200 + KOSDAQ 150 = **350종목**
- API 제한 없으므로 전종목 스크리닝 가능
