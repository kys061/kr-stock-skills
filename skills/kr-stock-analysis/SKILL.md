---
name: kr-stock-analysis
description: 펀더멘털(재무/밸류에이션) + 기술적(추세/패턴) + 수급(투자자별) 종합 주식 분석 리포트 생성.
---

# kr-stock-analysis: 한국 종목 종합 분석

> 펀더멘털, 기술적 분석, 수급 분석, 밸류에이션을 통합하여
> 한국 주식의 종합 투자 판단을 제공합니다.
> US us-stock-analysis의 한국 적용 + 수급 분석 추가.
> **KRClient 불가 시 WebSearch 폴백으로 분석을 계속한다.**

## 데이터 소스 우선순위

```
1순위: KRX Open API / KIS API → 정밀 정량 데이터
2순위: KRClient (pykrx/FDR) → 프로그래밍 데이터 수집
3순위: WebSearch 폴백 → 종목명+지표 검색 기반 수집
```

### WebSearch 폴백 실행 절차

KRClient 실패 시 아래 WebSearch 쿼리 조합으로 5-컴포넌트 데이터를 수집한다:

| 컴포넌트 | 검색 쿼리 패턴 | 수집 대상 |
|---------|--------------|----------|
| Fundamental | `"{종목명} 매출 영업이익 순이익 ROE 부채비율 실적"` | 매출, OPM, 순이익, 부채비율 |
| Technical | `"{종목명} 주가 차트 이동평균 기술적분석"` | 현재가, 추세, 목표가 |
| Supply/Demand | `"{종목명} 외국인 기관 수급 동향"` | 투자자별 매매 |
| Valuation | `"{종목명} PER PBR 시가총액"` | PER, PBR, 시총, 업종 비교 |
| Growth Quick | `"{종목명} 수주 파이프라인 성장 전망"` | 수주잔고, 컨센서스 |

### WebSearch 폴백 시 리포트 표기
```markdown
> **데이터 소스**: WebSearch 폴백 (KRX API 미가용)
> **정밀도 한계**: 기술적 지표(RSI/MACD)는 정확값 미확인, 뉴스/리포트 기반 추정
```

## 사용 시점

- 특정 한국 종목의 투자 매력도를 종합 분석할 때
- 펀더멘털/기술적/수급을 한 번에 확인하고 싶을 때
- 매수/매도 판단을 위한 종합 점수가 필요할 때

## 5가지 분석 유형

| 유형 | 설명 |
|------|------|
| BASIC | 기본 정보 (시가총액, PER, PBR, 배당, 52주 고저) |
| FUNDAMENTAL | 펀더멘털 (매출, 영업이익, ROE, 부채비율) |
| TECHNICAL | 기술적 (MA, RSI, Stochastic, MACD, Bollinger Bands) |
| SUPPLY_DEMAND | 수급 (외국인, 기관, 개인) - KR 고유 |
| COMPREHENSIVE | 종합 리포트 (위 4개 통합) |

## 종합 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Fundamental | 30% | 수익성 + 성장성 + 재무건전성 |
| Technical | 22% | 추세 + 모멘텀(RSI/Stochastic 이중확인) + 거래량 |
| Supply/Demand | 22% | 외국인/기관 수급 (KR 고유) |
| Valuation | 13% | PER + PBR 복합 |
| Growth Quick | 13% | 성장성 경량 평가 (EPS/R&D/TAM/정책) |

## Growth Quick Score

WebSearch 없이 즉시 계산 가능한 경량 성장성 점수:
- 컨센서스 EPS 성장률 (40%)
- R&D 투자비율 (20%)
- 섹터 TAM CAGR (20%, 정적 DB)
- 정책 순풍 (20%, 정적 DB)

딥 분석이 필요하면 `/kr-growth-outlook` 스킬 사용.

## Technical 모멘텀 지표 상세

### Slow Stochastic (%K 14, %D 3)
- `ta_utils.stochastic(high, low, close, k_period=14, d_period=3)` 사용
- 과매수: %K > 80, 과매도: %K < 20
- %K가 %D 상향 돌파 → 골든크로스 (매수 시그널)
- %K가 %D 하향 돌파 → 데드크로스 (매도 시그널)

### RSI + Stochastic 이중확인 보너스
모멘텀 채점 시 두 지표가 동일 방향을 가리키면 보너스/페널티를 적용한다:

| 조건 | 보너스 | 해석 |
|------|:------:|------|
| RSI ≤ 30 AND Stochastic %K ≤ 20 | +5점 | 이중 과매도 → 반등 확률 높음 |
| RSI ≥ 70 AND Stochastic %K ≥ 80 | -5점 | 이중 과매수 → 조정 확률 높음 |
| Stochastic 골든크로스 AND RSI 상승 반전 | +3점 | 모멘텀 전환 확인 |
| Stochastic 데드크로스 AND RSI 하락 반전 | -3점 | 모멘텀 약화 확인 |

> 보너스는 Technical Score의 모멘텀 배점(30점) 내에서 가감한다.

## 투자 등급

| 등급 | 점수 | 판단 |
|------|:----:|------|
| STRONG_BUY | 80+ | 적극 매수 |
| BUY | 65-79 | 매수 |
| HOLD | 50-64 | 보유 |
| SELL | 35-49 | 매도 |
| STRONG_SELL | 0-34 | 적극 매도 |

## US 통화정책 오버레이 (필수)

종합 분석 시 **반드시** US 통화정책 영향을 포함한다.

### 적용 절차
1. WebSearch로 현재 Fed 기준금리, FOMC 기조, DXY, BOK 기준금리, 한미 금리차 조회
2. US Regime Score 산출 (stance×0.35 + rate×0.30 + liquidity×0.35)
3. B방식 오버레이 계산: `(regime_score - 50) × 0.30 × sector_sensitivity`
4. 종합 점수에 오버레이 가산: `final_score = base_score + overlay`

### 15 섹터 민감도

| 섹터 | 민감도 | 섹터 | 민감도 |
|------|:------:|------|:------:|
| semiconductor | 1.3 | finance | 0.7 |
| secondary_battery | 1.3 | nuclear | 0.6 |
| bio | 1.2 | insurance | 0.6 |
| it | 1.2 | retail | 0.5 |
| auto | 1.1 | defense | 0.4 |
| shipbuilding | 1.0 | food | 0.3 |
| steel | 0.9 | default | 0.7 |
| chemical | 0.9 | | |
| construction | 0.8 | | |

### 리포트 필수 포함 항목
- US Regime Score 및 Label (tightening/hold/easing)
- 한국 전이 5채널 점수 (금리차/환율/위험선호/섹터로테이션/BOK)
- 해당 종목의 섹터 민감도 및 오버레이 값
- 기본 점수 → 오버레이 → 최종 점수 과정

## 실행 방법

```bash
cd ~/stock/skills/kr-stock-analysis/scripts
python comprehensive_scorer.py --ticker 005930
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| us-monetary-regime | **US 통화정책 오버레이 (필수 연동)** |
| kr-value-dividend | 배당 가치주 스크리닝 |
| kr-canslim-screener | CANSLIM 성장주 스크리닝 |
| kr-institutional-flow | 수급 상세 분석 |
| kr-strategy-synthesizer | 전략 통합 (종합 판단 입력) |
| kr-growth-outlook | 6-컴포넌트 딥 성장 분석 |

---

## Output Rule (마크다운 리포트 저장)

- **템플릿**: `_kr_common/templates/report_stock.md` 의 구조를 그대로 따른다
- **공통 규칙**: `_kr_common/templates/report_rules.md` 참조
- 저장 경로: `reports/kr-stock-analysis_{종목코드}_{종목명}_{YYYYMMDD}.md`
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)
