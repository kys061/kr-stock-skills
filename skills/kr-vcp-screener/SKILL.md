---
name: kr-vcp-screener
description: Mark Minervini Stage 2 트렌드 템플릿 + VCP(Volatility Contraction Pattern) 탐지. 변동성 수축 + 피봇 근접 종목 선별.
---

# kr-vcp-screener: 한국 VCP 패턴 스크리닝

> Mark Minervini Stage 2 트렌드 템플릿 + Volatility Contraction Pattern.
> ±30% 가격제한폭 반영, KOSPI 대비 RS Rank.
> US vcp-screener의 한국 적용 버전.

## 사용 시점

- Stage 2 상승 추세 종목의 VCP 패턴 브레이크아웃 대기
- Minervini 방법론 기반 한국 종목 발굴
- 변동성 축소 + 피봇 포인트 근접 종목 스크리닝

## 방법론

### Stage 2 트렌드 템플릿 (7점)

| # | 조건 | 통과 기준 |
|---|------|---------|
| 1 | 현재가 > 150일 SMA AND > 200일 SMA | 필수 |
| 2 | 150일 SMA > 200일 SMA | 필수 |
| 3 | 200일 SMA 22일+ 상승 | 필수 |
| 4 | 현재가 > 50일 SMA | 필수 |
| 5 | 현재가 ≥ 52주 저가 +25% | 필수 |
| 6 | 현재가 ≥ 52주 고가 -25% | 필수 |
| 7 | RS Rank > 70 (KOSPI 대비) | 필수 |

**통과**: 7점 중 6점 이상

### 5-컴포넌트 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Trend Template | 25% | 7점 Stage 2 |
| Contraction Quality | 25% | 수축 횟수+깊이 |
| Volume Pattern | 20% | Dry-Up Ratio |
| Pivot Proximity | 15% | 피봇 근접도 |
| Relative Strength | 15% | KOSPI 대비 RS |

### VCP 파라미터 (한국 적응)
- T1 깊이: 10-30% (US 8-35%, ±30% 가격제한폭 반영)
- 수축 비율: ≤ 0.75
- 최소 수축: 2회

## 실행 방법

```bash
cd ~/stock/skills/kr-vcp-screener/scripts
python kr_vcp_screener.py --market KOSPI200 --output-dir ./output
```
