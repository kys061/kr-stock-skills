# kr-weekly-strategy: 주간 전략 워크플로우

> 한국 시장 주간 전략을 6개 섹션으로 구성하여
> 시장 환경, 섹터 전략, 리스크 관리, 액션 플랜을 제공합니다.
> US weekly-trade-strategy의 한국 적용 (에이전트 → 함수 단순화).

## 사용 시점

- 매주 월요일 시장 개장 전 주간 전략을 수립할 때
- 시장 환경 변화에 따라 포트폴리오를 조정할 때
- 섹터 로테이션 및 비중 변경을 계획할 때

## 6개 섹션 구조

| 섹션 | 설명 |
|------|------|
| market_summary | 시장 환경 요약 (3줄) |
| this_week_action | 이번 주 액션 플랜 |
| scenario_plans | 시나리오별 계획 (Base/Bull/Bear) |
| sector_strategy | 섹터 전략 (14개 KR 섹터) |
| risk_management | 리스크 관리 |
| operation_guide | 운용 가이드 (겸업 투자자용) |

## 시장 상태 분류

| 상태 | 설명 | 주식 목표 |
|------|------|:---------:|
| RISK_ON | 위험 선호 (강세장) | 80-100% |
| BASE | 보통 (횡보장) | 60-80% |
| CAUTION | 주의 (약세 전환 가능) | 40-60% |
| STRESS | 스트레스 (약세장) | 10-40% |

## 한국 14개 섹터

반도체, 자동차, 조선/해운, 철강/화학, 바이오/제약, 금융/은행,
유통/소비, 건설/부동산, IT/소프트웨어, 통신, 에너지/유틸리티,
엔터테인먼트, 방산, 2차전지

## 주간 체크리스트 (8항목)

1. KOSPI/KOSDAQ 주간 추세
2. 외국인 순매수/매도
3. 기관 순매수/매도
4. BOK 금리 결정 (있을 경우)
5. 주요 실적 발표
6. DART 주요 공시
7. 지정학적 이벤트
8. USD/KRW 환율 추세

## 실행 방법

```bash
cd ~/stock/skills/kr-weekly-strategy/scripts
python weekly_planner.py --date 2026-03-03
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-strategy-synthesizer | 확신도/배분 입력 |
| kr-macro-regime | 거시 환경 입력 |
| kr-theme-detector | 섹터 모멘텀 입력 |
