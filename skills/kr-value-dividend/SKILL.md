# kr-value-dividend: 한국 배당 가치주 스크리닝

> 3-Phase 펀더멘털 필터 + 4-컴포넌트 스코어링으로 배당 가치주를 발굴합니다.
> US value-dividend-screener의 한국 적용 버전.

## 사용 시점

- 배당수익률과 밸류에이션을 함께 고려하여 종목을 발굴할 때
- 안정적 배당 + 저평가 종목을 찾을 때
- 배당 지속가능성과 재무 건전성을 함께 평가할 때

## 방법론

### 3-Phase 스크리닝 필터

**Phase 1: 정량 필터**
- 배당수익률 ≥ 2.5%
- PER ≤ 15
- PBR ≤ 1.5
- 시가총액 ≥ 5,000억원

**Phase 2: 성장 품질 필터**
- 3년 배당 연속 유지 (무삭감)
- 매출 3년 양의 추세
- EPS 3년 양의 추세

**Phase 3: 지속가능성 필터**
- 배당성향 < 80%
- 부채비율 < 150%
- 유동비율 > 1.0

### 4-컴포넌트 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Value Score | 40% | PER + PBR 복합 |
| Growth Score | 35% | 3년 배당/매출/EPS 성장률 |
| Sustainability Score | 20% | 배당성향 + 부채비율 |
| Quality Score | 5% | ROE + 영업이익률 |

### 등급 체계

| 등급 | 점수 | 권고 |
|------|:----:|------|
| Excellent | 85-100 | 즉시 매수 고려 |
| Good | 70-84 | 매수 후보 |
| Average | 55-69 | 관찰 |
| Below Average | < 55 | 패스 |

## 한국 시장 적응

- 배당수익률 기준: US 3.5% → KR **2.5%** (한국 배당 평균 낮음)
- PER 기준: US 20 → KR **15** (한국 시장 PER 평균 낮음)
- 배당 패턴: 분기 → **연 1회** (12월 결산 집중)
- 배당세: 적격/비적격 → **15.4%** 균일

## 실행 방법

```bash
cd ~/stock/skills/kr-value-dividend/scripts
python kr_value_dividend_screener.py --market ALL --output-dir ./output
python kr_value_dividend_screener.py --market KOSPI --min-yield 3.0 --output-dir ./output
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-dividend-pullback | 배당 성장주 + RSI 타이밍 |
| kr-stock-screener | 다조건 필터 도구 |
| kr-canslim-screener | 성장주 관점 대조 |
