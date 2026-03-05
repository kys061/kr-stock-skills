---
name: kr-strategy-synthesizer
description: 7개 업스트림 스킬(Market Breadth/Uptrend/Market Top/Macro/FTD/VCP/CANSLIM) 결과를 통합하여 0-100 확신도 점수 산출.
---

# kr-strategy-synthesizer: 전략 통합 합성기

> 8개 업스트림 KR 스킬의 JSON 결과를 통합하여
> 7-컴포넌트 확신도 (0-100) 및 자산 배분 추천을 제공합니다.
> US stanley-druckenmiller-investment의 한국 적용.

## 사용 시점

- 시장 전체의 투자 확신도를 종합적으로 판단할 때
- 여러 스킬 분석 결과를 하나로 합성하고 싶을 때
- 자산 배분 비율과 포지션 사이즈를 결정할 때

## 8-컴포넌트 확신도 스코어링

| 컴포넌트 | 가중치 | 입력 소스 |
|----------|:------:|-----------|
| 시장 구조 (market_structure) | 16% | kr-market-breadth, kr-uptrend-analyzer |
| 분배 리스크 (distribution_risk) | 16% | kr-market-top-detector |
| 바닥 확인 (bottom_confirmation) | 10% | kr-ftd-detector |
| 거시 정합 (macro_alignment) | 16% | kr-macro-regime |
| 테마 품질 (theme_quality) | 10% | kr-theme-detector |
| 셋업 가용 (setup_availability) | 9% | kr-vcp-screener, kr-canslim-screener |
| 시그널 수렴 (signal_convergence) | 11% | 전체 스킬 |
| 성장 전망 (growth_outlook) | 12% | kr-growth-outlook |

## 확신도 존 (Conviction Zones)

| 존 | 점수 | 주식 비중 | 최대 단일 종목 |
|----|:----:|:---------:|:-------------:|
| MAXIMUM | 80+ | 90-100% | 25% |
| HIGH | 60-79 | 70-90% | 15% |
| MODERATE | 40-59 | 50-70% | 10% |
| LOW | 20-39 | 20-50% | 5% |
| PRESERVATION | 0-19 | 0-20% | 3% |

## 4 시장 패턴

| 패턴 | 트리거 |
|------|--------|
| POLICY_PIVOT | 정책 전환 + 높은 전환 확률 |
| UNSUSTAINABLE_DISTORTION | 고위험 + 수축/인플레이션 |
| EXTREME_CONTRARIAN | FTD 확인 + 약세 → 역발상 매수 |
| WAIT_OBSERVE | 낮은 확신 + 혼합 시그널 |

## 실행 방법

```bash
cd ~/stock/skills/kr-strategy-synthesizer/scripts
python conviction_scorer.py --report-dir ./reports/
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-market-breadth | 시장 구조 입력 |
| kr-uptrend-analyzer | 시장 구조 입력 |
| kr-market-top-detector | 분배 리스크 입력 |
| kr-ftd-detector | 바닥 확인 입력 |
| kr-macro-regime | 거시 정합 입력 |
| kr-theme-detector | 테마 품질 입력 |
| kr-vcp-screener | 셋업 가용 입력 |
| kr-canslim-screener | 셋업 가용 입력 |
| kr-growth-outlook | 성장 전망 입력 |
