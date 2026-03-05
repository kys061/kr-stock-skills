---
name: kr-stock-analysis
description: 펀더멘털(재무/밸류에이션) + 기술적(추세/패턴) + 수급(투자자별) 종합 주식 분석 리포트 생성.
---

# kr-stock-analysis: 한국 종목 종합 분석

> 펀더멘털, 기술적 분석, 수급 분석, 밸류에이션을 통합하여
> 한국 주식의 종합 투자 판단을 제공합니다.
> US us-stock-analysis의 한국 적용 + 수급 분석 추가.

## 사용 시점

- 특정 한국 종목의 투자 매력도를 종합 분석할 때
- 펀더멘털/기술적/수급을 한 번에 확인하고 싶을 때
- 매수/매도 판단을 위한 종합 점수가 필요할 때

## 5가지 분석 유형

| 유형 | 설명 |
|------|------|
| BASIC | 기본 정보 (시가총액, PER, PBR, 배당, 52주 고저) |
| FUNDAMENTAL | 펀더멘털 (매출, 영업이익, ROE, 부채비율) |
| TECHNICAL | 기술적 (MA, RSI, MACD, Bollinger Bands) |
| SUPPLY_DEMAND | 수급 (외국인, 기관, 개인) - KR 고유 |
| COMPREHENSIVE | 종합 리포트 (위 4개 통합) |

## 종합 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Fundamental | 30% | 수익성 + 성장성 + 재무건전성 |
| Technical | 22% | 추세 + 모멘텀 + 거래량 |
| Supply/Demand | 22% | 외국인/기관 수급 (KR 고유) |
| Valuation | 13% | PER + PBR 복합 |
| Growth Quick | 13% | 성장성 경량 평가 (EPS/R&D/TAM/정책) |

## Growth Quick Score

WebSearch 없이 즉시 계산 가능한 경량 성장성 점수:
- 컨센서스 EPS 성장률 (40%)
- R&D 투자비율 (20%)
- 섹터 TAM CAGR (20%, 정적 DB)
- 정책 순풍 (20%, 정적 DB)

딥 분석이 필요하면 `/kr-growth-outlook` 스킬 사용.

## 투자 등급

| 등급 | 점수 | 판단 |
|------|:----:|------|
| STRONG_BUY | 80+ | 적극 매수 |
| BUY | 65-79 | 매수 |
| HOLD | 50-64 | 보유 |
| SELL | 35-49 | 매도 |
| STRONG_SELL | 0-34 | 적극 매도 |

## 실행 방법

```bash
cd ~/stock/skills/kr-stock-analysis/scripts
python comprehensive_scorer.py --ticker 005930
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-value-dividend | 배당 가치주 스크리닝 |
| kr-canslim-screener | CANSLIM 성장주 스크리닝 |
| kr-institutional-flow | 수급 상세 분석 |
| kr-strategy-synthesizer | 전략 통합 (종합 판단 입력) |
| kr-growth-outlook | 6-컴포넌트 딥 성장 분석 |
