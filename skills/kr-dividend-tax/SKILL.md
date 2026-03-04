---
name: kr-dividend-tax
description: 한국 배당세(15.4%), ISA 비과세(200만원), 연금저축/IRP, 금융소득종합과세(2,000만원) 계산과 계좌 배치 최적화.
---

# kr-dividend-tax: 한국 배당 투자 세제 최적화

> 한국 투자 세제(배당세/금융소득종합과세/ISA/연금저축/IRP)를 계산하고,
> 계좌 배치 최적화로 절세 전략을 제시합니다.
> US kanchi-dividend-us-tax-accounting의 **한국 세제 완전 재작성** 버전.

## 사용 시점

- 배당 포트폴리오의 세후 수익률을 정확히 계산하고 싶을 때
- ISA/연금저축/IRP 중 어디에 배당주를 넣어야 유리한지 판단할 때
- 금융소득종합과세 2,000만원 기준을 관리해야 할 때
- 연간 세금 부담을 추정하고 절세 전략을 세울 때

## 핵심 세제 상수 (2026년 기준)

| 항목 | 세율/기준 | 비고 |
|------|:---------:|------|
| 배당소득세 | **15.4%** | 소득세 14% + 지방세 1.4% |
| 금융소득종합과세 | **2,000만원** | 초과 시 종합소득세율 (6-45%) |
| ISA 비과세 | **200만원** | 초과분 9.9% 분리과세 |
| 연금저축 세액공제 | **16.5%/13.2%** | 총급여 5,500만원 기준 |
| IRP 추가공제 | **300만원** | 안전자산 30% 의무 |
| 증권거래세 | **0.23%** | KOSPI/KOSDAQ 동일 |

## 계좌 배치 우선순위

```
1순위: ISA       → 고배당주 (비과세 200만원 + 초과 9.9%)
2순위: 연금저축   → 장기 성장주 (세액공제 + 과세이연)
3순위: IRP       → 채권 ETF (추가공제 + 안전자산 충족)
4순위: 일반계좌   → 매매 빈도 높은 종목
```

## 주요 기능

### 1. 세금 계산 (tax_calculator.py)
- `calc_dividend_tax()` - 배당소득세 계산 (계좌 유형별)
- `calc_financial_income_tax()` - 금융소득종합과세 판정
- `calc_capital_gains_tax()` - 양도소득세 계산
- `calc_transaction_tax()` - 증권거래세 계산
- `calc_isa_tax()` - ISA 계좌 세금 계산
- `calc_pension_deduction()` - 연금저축/IRP 세액공제
- `calc_total_tax_burden()` - 포트폴리오 전체 세금 부담

### 2. 계좌 최적화 (account_optimizer.py)
- `recommend_account_allocation()` - 계좌 배치 추천
- `calc_account_benefit()` - 계좌별 세금 혜택 비교
- `optimize_threshold_management()` - 금융소득 2,000만원 관리
- `generate_tax_optimization_tips()` - 맞춤형 절세 팁

## 실행 방법

```bash
cd ~/stock/skills/kr-dividend-tax/scripts
python tax_calculator.py --dividend 5000000 --account ISA
python account_optimizer.py --portfolio portfolio.json
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-dividend-sop | 배당 투자 SOP (세금은 Step 4: 수령에서 참조) |
| kr-dividend-monitor | 배당 안전성 모니터링 |
| kr-portfolio-manager | 포트폴리오 리밸런싱 (KR_TAX_MODEL 공유) |
