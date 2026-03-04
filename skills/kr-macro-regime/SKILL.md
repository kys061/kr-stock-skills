# kr-macro-regime

한국 매크로 레짐 탐지기 — 6-컴포넌트 크로스에셋 비율 분석.

## 개요

월간 크로스에셋 비율의 6M/12M SMA 크로스오버로 구조적 레짐 전환을 탐지.
1-2년 투자 지평의 전략적 자산 배분 가이드.

## 6-컴포넌트 크로스에셋 비율 분석

| # | 컴포넌트 | 가중치 | 비율/데이터 | 탐지 대상 |
|---|---------|:------:|-----------|----------|
| 1 | 시장 집중도 | 25% | 대형주/전체 비중 | 대형주 쏠림 vs 시장 확산 |
| 2 | 금리 곡선 | 20% | 국고채 10Y - 3Y | 금리 사이클 전환 |
| 3 | 신용 환경 | 15% | BBB- vs AA- 스프레드 | 신용 리스크 선호도 |
| 4 | 사이즈 팩터 | 15% | KOSDAQ / KOSPI | 소형 vs 대형 로테이션 |
| 5 | 주식-채권 관계 | 15% | KOSPI / 국고채 + 상관관계 | 자산 간 관계 레짐 |
| 6 | 섹터 로테이션 | 10% | 경기민감 / 방어 | 경기 사이클 |

## 5개 레짐 분류

| 레짐 | 정의 | 전략적 함의 |
|------|------|-----------|
| **Concentration** | 대형주 쏠림, 좁은 시장 | 대형 성장주 유지 |
| **Broadening** | 참여 확대, 소형/가치 로테이션 | 소형/가치주 비중 확대 |
| **Contraction** | 신용 악화, 방어적 로테이션 | 현금 확대, 방어 섹터 |
| **Inflationary** | 주식-채권 양(+) 상관 | 실물자산, 에너지 |
| **Transitional** | 복합 시그널, 불확실 | 포지션 축소, 관망 |

## Component 1: 시장 집중도 (25%)

KOSPI 시총 상위 10종목 비중 추세.
- 비중 상승 (6M > 12M) → Concentration
- 비중 하락 (6M < 12M) → Broadening
- 안정 → Transitional

## Component 2: 금리 곡선 (20%)

국고채 10년 - 3년 스프레드.
| 스프레드 | 해석 | 레짐 |
|---------|------|------|
| < 0bp (역전) | 긴축/침체 선행 | Contraction |
| 0-30bp | 경계 | Transitional |
| 30-100bp | 정상 | 중립 |
| > 100bp | 완화적 | Broadening |

## Component 3: 신용 환경 (15%)

회사채 BBB- vs AA- 스프레드.
- 확대 (6M > 12M) → Contraction
- 축소 (6M < 12M) → Broadening
- 안정 → 중립

## Component 4: 사이즈 팩터 (15%)

KOSDAQ / KOSPI 비율 추세.
- 상승 → 소형주 선호 → Broadening
- 하락 → 대형주 선호 → Concentration
- 안정 → Transitional

## Component 5: 주식-채권 관계 (15%)

KOSPI / 국고채 비율 + 60일 롤링 상관계수.
| 상관 | 해석 | 레짐 |
|------|------|------|
| > 0.3 | 유동성/인플레 주도 | Inflationary |
| < -0.3 | 정상 역상관 | 중립 |
| -0.3~0.3 | 관계 붕괴 | Transitional |

## Component 6: 섹터 로테이션 (10%)

경기민감(운수장비, 철강금속, 건설) vs 방어(통신, 음식료, 의약품).
- 경기민감 강세 → Broadening
- 방어 강세 → Contraction
- 혼재 → Transitional

## 레짐 판정 로직

가중 투표 방식:
- 6개 컴포넌트가 각자 레짐 시그널 투표 (가중치 반영)
- 최고 득표 레짐 = 현재 레짐
- 최고 득표가 40% 미만 → Transitional

## 스크립트

| 파일 | 역할 |
|------|------|
| `calculators/concentration_calculator.py` | 시장 집중도 |
| `calculators/yield_curve_calculator.py` | 금리 곡선 |
| `calculators/credit_calculator.py` | 신용 환경 |
| `calculators/size_factor_calculator.py` | 사이즈 팩터 |
| `calculators/equity_bond_calculator.py` | 주식-채권 관계 |
| `calculators/sector_rotation_calculator.py` | 섹터 로테이션 |
| `scorer.py` | 레짐 분류 스코어러 |
| `report_generator.py` | JSON/Markdown 리포트 |
| `kr_macro_regime_detector.py` | 메인 오케스트레이터 |

## 참조 문서

| 파일 | 내용 |
|------|------|
| `references/regime_methodology_kr.md` | 크로스에셋 비율 분석 한국 적용 |
| `references/historical_kr_regimes.md` | 한국 역사적 레짐 전환 사례 |
