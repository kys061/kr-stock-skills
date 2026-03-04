---
name: kr-dividend-sop
description: 5단계 SOP(스크리닝→진입→보유→수령→EXIT)로 배당주 투자 전 과정을 관리하는 표준 운영 절차 스킬.
---

# kr-dividend-sop: 한국 배당주 투자 표준 운용 절차

> 5단계 SOP(Standard Operating Procedure)로 배당주 투자의 전 과정을 관리합니다.
> US kanchi-dividend-sop의 한국 적용 버전.

## 사용 시점

- 배당주 투자를 체계적으로 운용하고 싶을 때
- 스크리닝 → 진입 → 보유 → 배당 수령 → 매도까지 전 과정 가이드 필요 시
- 배당 투자 포트폴리오를 정기적으로 점검할 때

## 방법론

### 5-Step SOP

| Step | 단계 | 설명 |
|:----:|------|------|
| 1 | SCREEN | 배당주 스크리닝 (품질+재무 필터) |
| 2 | ENTRY | 진입 판단 (밸류에이션+배당품질+타이밍) |
| 3 | HOLD | 보유 모니터링 (6개 체크리스트) |
| 4 | COLLECT | 배당 수령 관리 (배당락일+지급일) |
| 5 | EXIT | 매도 판단 (6개 EXIT 트리거) |

### 진입 스코어링 (0-100)

| 컴포넌트 | 가중치 | 만점 기준 |
|---------|:------:|----------|
| Valuation | 40% | PER 5~12, PBR 0.3~1.0 |
| Dividend Quality | 30% | 배당수익률 ≥4.0% |
| Financial Health | 20% | ROE ≥15% |
| Timing | 10% | RSI ≤ 40 |

## 한국 시장 적응

- 배당 주기: 분기 → **연 1회** (12월 결산 집중)
- 배당락일: 기준일 **2영업일 전** (US는 1영업일 전)
- 배당 지급: 기준일 후 **30~60일** (주총 후)
- 중간배당 기업: 소수 (삼성전자, SK텔레콤 등)

## 실행 방법

```
/kr-dividend-sop
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-value-dividend | Phase 4 스크리닝 기준 호환 |
| kr-dividend-pullback | RSI 타이밍 기준 공유 |
| kr-dividend-monitor | Step 3 보유 중 모니터링 연동 |
| kr-dividend-tax | 배당 수령 시 세제 최적화 |
