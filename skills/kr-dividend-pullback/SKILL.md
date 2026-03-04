---
name: kr-dividend-pullback
description: 배당 성장률 12%+ & 수익률 1.5%+ 종목 중 RSI≤40 눌림목 타이밍을 탐지하는 고성장 배당주 풀백 스크리너.
---

# kr-dividend-pullback: 한국 배당 성장 풀백 스크리닝

> 고성장 배당주 (3Y CAGR ≥ 8%) + RSI ≤ 40 타이밍 기반 진입 전략.
> US dividend-growth-pullback-screener의 한국 적용 버전.

## 사용 시점

- 성장하는 배당주가 일시적으로 눌림을 받을 때 매수 타이밍을 잡고 싶을 때
- 배당 성장 기록이 검증된 종목의 기술적 과매도 구간 진입
- 장기 배당 성장 + 단기 역발상 타이밍 조합

## 방법론

### 2-Phase 스크리닝

**Phase 1: 배당 성장 필터**
- 배당수익률 ≥ 2.0%
- 3년 배당 CAGR ≥ 8%
- 4년 연속 무삭감
- 시가총액 ≥ 3,000억원
- 매출/EPS 3년 양의 추세
- 부채비율 < 150%, 유동비율 > 1.0
- 배당성향 < 80%

**Phase 2: RSI 타이밍 필터**
- RSI(14) ≤ 40 → 진입 대상
- RSI < 30 → 극단적 과매도 (최고 점수)

### 4-컴포넌트 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Dividend Growth | 40% | 3Y CAGR + 연속성 |
| Financial Quality | 30% | ROE + 영업이익률 + 부채비율 |
| Technical Setup | 20% | RSI 수준 (낮을수록 높은 점수) |
| Valuation | 10% | PER + PBR 맥락 |

## 한국 시장 적응

- 배당 CAGR 기준: US 12% → KR **8%** (한국 배당 성장률 낮음)
- 최소 배당수익률: US 1.5% → KR **2.0%**
- 시가총액 기준: $2B → **3,000억원**
- RSI 임계값: 동일 (≤ 40)

## 실행 방법

```bash
cd ~/stock/skills/kr-dividend-pullback/scripts
python kr_dividend_pullback_screener.py --market ALL --output-dir ./output
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-value-dividend | 배당 가치주 (RSI 무관) |
| kr-stock-screener | 다조건 필터 도구 |
