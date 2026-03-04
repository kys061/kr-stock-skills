---
name: kr-earnings-trade
description: 한국 상장기업의 실적 발표 후 주가 반응을 5팩터 스코어링 시스템으로 분석한다. Gap Size(25%), Pre-Earnings Trend(30%), Volume Trend(20%), MA200 Position(15%), MA50 Position(10%) 가중치로 0-100점 산출 후 A/B/C/D 등급 부여. 외국인 연속 순매수 보너스(+5) 한국 특화.
---

# 한국 실적 트레이드 분석기 (kr-earnings-trade)

## 개요

실적 발표 후 주가 반응을 5팩터 가중 스코어링으로 평가하여 포스트-어닝 모멘텀 후보를 선별한다.
US `earnings-trade-analyzer` (FMP API)를 DART + PyKRX 기반으로 포팅.

## 5-Factor 스코어링

| # | 팩터 | 가중치 | 설명 |
|:-:|------|:------:|------|
| 1 | Gap Size | 25% | 실적 갭 크기 (절대값) |
| 2 | Pre-Earnings Trend | 30% | 실적 전 20일 수익률 |
| 3 | Volume Trend | 20% | 20d/60d 평균 거래량 비율 |
| 4 | MA200 Position | 15% | 200SMA 대비 현재가 |
| 5 | MA50 Position | 10% | 50SMA 대비 현재가 |

## 등급

| 등급 | 점수 | 해석 |
|:----:|:----:|------|
| A | 85-100 | 강한 실적 반응 + 기관 축적 — 진입 고려 |
| B | 70-84 | 양호한 실적 반응 — 모니터링 |
| C | 55-69 | 혼합 시그널 — 추가 분석 필요 |
| D | 0-54 | 약한 셋업 — 회피 |

## 한국 특화

- **±30% 가격제한폭**: 갭 크기 자연 캡핑
- **공시시간 기반 갭 계산**: 장전/장중/장후 별도 로직
- **외국인 순매수 보너스**: 실적 후 5일 연속 순매수 ≥10억 → +5점

## 워크플로우

```bash
python3 skills/kr-earnings-trade/scripts/kr_earnings_trade_analyzer.py \
  --lookback-days 14 --output-dir ./output
```

## 참고 자료
- `references/scoring_methodology_kr.md` — 5팩터 스코어링 한국 적용
- `references/kr_earnings_patterns.md` — 한국 실적 반응 패턴
