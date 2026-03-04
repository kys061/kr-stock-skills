---
name: kr-portfolio-manager
description: 한국 세제(배당세 15.4%, ISA, 금종과세) 반영 포트폴리오 분석, 자산배분, 리스크 메트릭스, 리밸런싱 추천.
---

# kr-portfolio-manager

> 한국 시장 포트폴리오 분석: 자산배분, 리스크 메트릭스, 리밸런싱 추천, 한국 세제 반영.

## 분석 차원

| 차원 | 설명 |
|------|------|
| asset_class | 주식/채권/현금/대안 |
| sector | KRX 업종 분류 |
| market_cap | 대형/중형/소형 |
| market | KOSPI/KOSDAQ/ETF |

## 분산투자 지표

| 지표 | 기준 |
|------|------|
| 최적 종목 수 | 15-30개 |
| 과집중 | <10개 |
| 과분산 | >50개 |
| 단일 종목 최대 | 15% |
| 단일 섹터 최대 | 35% |
| 상관계수 중복 | >0.8 |

## 한국 세제

| 항목 | 세율/기준 |
|------|----------|
| 배당소득세 | 15.4% (소득세 14% + 지방세 1.4%) |
| 금융소득종합과세 | 연 2,000만원 초과 시 |
| 양도소득세 | 22% (대주주 10억+ 기준) |
| 증권거래세 | 0.23% |
| ISA 비과세 | 200만원 한도 |

## 사용법

```bash
python portfolio_analyzer.py --holdings portfolio.json
python risk_calculator.py --holdings portfolio.json
python rebalancing_engine.py --holdings portfolio.json --target balanced
```
