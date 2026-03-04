---
name: kr-scenario-analyzer
description: 뉴스/이벤트 기반 Base/Bull/Bear 3-시나리오 18개월 전개 분석. 1차/2차/3차 영향과 섹터별 추천 종목 도출.
---

# kr-scenario-analyzer

> 한국 뉴스/이벤트로부터 18개월 시나리오를 분석하는 스킬.

## 개요

뉴스 헤드라인이나 이벤트를 입력받아 3가지 시나리오(기본/강세/약세)를 구축하고,
1차/2차/3차 영향 분석과 수혜/피해 종목을 추천한다. 한국어로 출력한다.

## 시나리오 구조

- **기본 시나리오**: 가장 가능성 높은 전개
- **강세 시나리오**: 낙관적 전개
- **약세 시나리오**: 비관적 전개
- 3개 시나리오 확률 합계 = 100%

## 한국 특화 이벤트

| 이벤트 | 설명 |
|--------|------|
| bok_rate_decision | BOK 금통위 금리 결정 |
| north_korea_geopolitical | 북한 지정학 리스크 |
| china_trade_policy | 중국 통상 정책 |
| semiconductor_cycle | 반도체 사이클 |
| exchange_rate_shock | 환율 급변 |
| government_policy | 정부 정책 (부동산, 규제) |
| earnings_surprise | 대형주 실적 서프라이즈 |

## 14개 한국 섹터

반도체, 자동차, 조선/해운, 철강/화학, 바이오/제약, 금융/은행,
유통/소비재, 건설/부동산, IT/소프트웨어, 통신, 에너지/유틸리티,
엔터테인먼트, 방산, 2차전지

## 사용법

```bash
python kr_scenario_analyzer.py --headline "BOK 기준금리 0.25%p 인하"
```
