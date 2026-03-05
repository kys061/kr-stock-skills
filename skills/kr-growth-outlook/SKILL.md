---
name: kr-growth-outlook
description: 6개 컴포넌트(TAM/SAM, 경쟁우위, 파이프라인, 실적경로, 정책순풍, 경영진)로 한국 종목/섹터의 단기(1-3년)/중기(4-7년)/장기(10년) 성장 전망을 분석하고 S/A/B/C/D 등급 부여.
---

# kr-growth-outlook: 한국 종목 성장 전망 분석

> 6개 컴포넌트 x 3개 시간 지평으로 종합 성장 등급(S/A/B/C/D)을 산출합니다.
> kr-stock-analysis의 Growth Quick Score와 연계됩니다.

## 사용 시점

- 종목의 미래 성장 잠재력을 체계적으로 평가할 때
- 단기/중기/장기 시간 지평별 성장 차이를 확인할 때
- 섹터 간 성장성을 비교할 때

## 6개 분석 컴포넌트

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| TAM/SAM | 25% | 시장 규모, CAGR, 점유율 추이 |
| 경쟁우위/해자 | 20% | 5-Type 모트 (비용/전환/네트워크/무형/효율) |
| 파이프라인 | 15% | 신제품, R&D 역량, 기술 포지션 |
| 실적 경로 | 20% | 컨센서스 EPS, 마진 궤적, ROIC |
| 정책 순풍 | 10% | 정부 지원, 규제, 글로벌 정렬 |
| 경영진 | 10% | 실행력, 자본배분, 거버넌스 |

## 3개 시간 지평

| 지평 | 복합 가중치 | 강조 컴포넌트 |
|-----|:----------:|-------------|
| 단기 (1-3년) | 40% | 파이프라인, 실적 |
| 중기 (4-7년) | 35% | 경쟁우위, TAM |
| 장기 (10년) | 25% | 정책, 경영진, TAM |

## 성장 등급

| 등급 | 점수 | 의미 |
|------|:----:|------|
| S | 85+ | Hyper Growth (10년 10배+ 잠재력) |
| A | 70+ | Strong Growth (10년 5배+ 잠재력) |
| B | 55+ | Moderate Growth (10년 2-3배) |
| C | 40+ | Slow Growth (시장 수익률 수준) |
| D | 0-39 | No Growth / Decline |

## 데이터 소스 (4-Tier)

| Tier | 소스 | 의존도 |
|------|------|:------:|
| 1 (Static) | sector_tam_database, moat_framework, policy_roadmap | 25% |
| 2 (API) | DART 재무/공시, FnGuide 컨센서스, ECOS | 30% |
| 3 (Search) | WebSearch (산업리포트, 뉴스) | 35% |
| 4 (Gov) | KIET, KISTEP, KOSIS | 10% |

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-stock-analysis | Growth Quick Score (경량 버전) 내장 |
| kr-sector-analyst | 섹터 성장 전망 테이블 활용 |
| kr-strategy-synthesizer | 8번째 확신도 컴포넌트 |
| kr-canslim-screener | 성장주 스크리닝 후 딥 분석 |
