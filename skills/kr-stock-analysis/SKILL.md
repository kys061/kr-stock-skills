---
name: kr-stock-analysis
description: 펀더멘털(재무/밸류에이션) + 기술적(추세/패턴) + 수급(투자자별) 종합 주식 분석 리포트 생성.
---

# kr-stock-analysis: 한국 종목 종합 분석

> 펀더멘털, 기술적 분석, 수급 분석, 밸류에이션을 통합하여
> 한국 주식의 종합 투자 판단을 제공합니다.
> US us-stock-analysis의 한국 적용 + 수급 분석 추가.
> **Tier 0-3 실패 시 WebSearch 폴백으로 분석을 계속한다.**

## 데이터 소스 우선순위

```
1순위: KRX Open API (승인 완료, OHLCV/시총/지수)
2순위: yfinance (PER/PBR/재무제표/밸류에이션)
3순위: KRClient (pykrx/FDR) → 프로그래밍 데이터 수집
4순위: WebSearch 폴백 → 종목명+지표 검색 기반 수집
```

### WebSearch 폴백 실행 절차

Tier 0-2 실패 시 아래 WebSearch 쿼리 조합으로 5-컴포넌트 데이터를 수집한다:

| 컴포넌트 | 검색 쿼리 패턴 | 수집 대상 |
|---------|--------------|----------|
| **Company Profile** | `"{종목명} 사업 개요 핵심기술 경쟁력"` | 사업 내용, 제품, 기술력 |
| **Company Pipeline** | `"{종목명} 제품 파이프라인 신사업 전망"` | 파이프라인, 글로벌 진출, 수주 |
| **Shareholders** | `"{종목명} 주주현황 지분율 최대주주"` | 최대주주, 기관/외국인 비율, 자사주 |
| Fundamental | `"{종목명} 매출 영업이익 순이익 ROE 부채비율 실적"` | 매출, OPM, 순이익, 부채비율 |
| Technical | `"{종목명} 주가 차트 이동평균 기술적분석"` | 현재가, 추세, 목표가 |
| Supply/Demand | `"{종목명} 외국인 기관 수급 동향"` | 투자자별 매매 |
| Valuation | `"{종목명} PER PBR 시가총액"` | PER, PBR, 시총, 업종 비교 |
| Growth Quick | `"{종목명} 수주 파이프라인 성장 전망"` | 수주잔고, 컨센서스 |

### WebSearch 폴백 시 리포트 표기
```markdown
> **데이터 소스**: WebSearch 폴백 (Tier 0-2 실패)
> **정밀도 한계**: 기술적 지표(RSI/MACD)는 정확값 미확인, 뉴스/리포트 기반 추정
```

## 사용 시점

- 특정 한국 종목의 투자 매력도를 종합 분석할 때
- 펀더멘털/기술적/수급을 한 번에 확인하고 싶을 때
- 매수/매도 판단을 위한 종합 점수가 필요할 때

## 회사 소개 및 기술력 분석 (필수)

종합 분석 시 **반드시** 해당 기업의 사업 내용과 기술력을 상세 조사하여 리포트에 포함한다.

### 수집 항목

| 항목 | 설명 | 필수 |
|------|------|:----:|
| 사업 개요 | 회사가 무엇을 하는 기업인지, 핵심 비즈니스 모델 | ✅ |
| 핵심 제품/서비스 | 주요 제품명, 설명, 상용화 여부 (테이블 형태) | ✅ |
| 핵심 기술력 | 보유 원천기술, 특허, 경쟁우위 (기술 단위별 상세 설명) | ✅ |
| 파이프라인/사업 확장 | 신규 적응증, 신사업, 확장 계획 (테이블 형태) | ✅ |
| 글로벌 진출 현황 | 해외 매출비중, 진출국, 주요 고객사 | 해당 시 |
| 최근 주요 이벤트 | 대규모 수주, 투자유치, M&A, 인허가 등 | 해당 시 |
| **주주현황** | 최대주주 및 특수관계인, 기관/외국인 비율, 자사주 (테이블 형태) | ✅ |
| 성장 모멘텀 요약 | 핵심 성장 동력 정리 (테이블: 모멘텀/상세/영향도) | ✅ |

### 주주현황 수집 절차

**데이터 소스 우선순위**:

| 순위 | 소스 | 수집 방법 | 제공 데이터 |
|:----:|------|----------|-----------|
| 1순위 | DART API | `hyslrSttus` (최대주주현황) | 최대주주+특수관계인 이름, 관계, 보유주수, 지분율 |
| 2순위 | yfinance | `major_holders`, `institutional_holders` | 내부자/기관 비율, 기관명, 보유량 |
| 3순위 | WebSearch | `"{종목명} 주주현황 지분율 최대주주"` | 주주구성 비율, 운용사별 보유 |

**DART API 호출** (1순위):
```python
import requests
url = 'https://opendart.fss.or.kr/api/hyslrSttus.json'
params = {
    'crtfc_key': DART_API_KEY,
    'corp_code': '{DART 고유번호}',   # corpCode.xml에서 종목코드로 조회
    'bsns_year': '{최근년도}',        # 2024, 2023 순차 시도
    'reprt_code': '11011'            # 사업보고서 (없으면 11012 반기)
}
```

**DART corp_code 조회**: corpCode.xml 다운로드 → stock_code 매칭
- 또는 DARTProvider.resolve_corp_code() 사용

**리포트 출력 형식**:
```markdown
### 주주현황
| 주주명 | 관계 | 보유주식수 | 지분율(%) |
|--------|------|-----------|:---------:|
| {최대주주} | 본인 | {주수} | {비율} |
| {특수관계인} | {관계} | {주수} | {비율} |
| **최대주주 등 합계** | | {합계} | **{합계비율}** |

- 내부자 지분율: {yfinance insidersPercentHeld}%
- 기관 지분율: {yfinance institutionsPercentHeld}%
- 유동주식 비율: {100 - 최대주주등 - 자사주}%
```

### WebSearch 수집 쿼리

```
"{종목명} 사업 개요 핵심기술 경쟁력"
"{종목명} 제품 파이프라인 신사업 전망"
"{종목명} 수주 글로벌 진출 해외매출"
"{종목명} 특허 기술력 R&D"
```

### 섹터별 조사 포인트

| 섹터 | 핵심 조사 항목 |
|------|--------------|
| 반도체 | 공정 노드, 주요 고객사, 장비 국산화율, HBM/AI 관련성 |
| 바이오 | 적응증, 임상 단계, FDA/MFDS 승인, 플랫폼 기술 |
| 자동차 | 전기차/자율주행 비중, OEM 고객, 수주잔고 |
| 조선 | 선종 비중, 수주잔고, LNG/암모니아 추진 기술 |
| 방산 | 수출 비중, 핵심 무기체계, 수주잔고 |
| 2차전지 | 양극/음극/전해액 기술, 고객사 CAPA, ESS 비중 |
| 전력기기 | 변압기/차단기 기술, 수주잔고, 해외 비중 |
| IT | 플랫폼/SaaS/게임 분류, MAU/ARR, AI 적용 |
| 기타 | 업종 특성에 맞는 핵심 경쟁력 조사 |

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

## 매수구간/매도타점 (Buy Zone & Sell Target)

종합 분석 완료 후 투자 등급에 따라 **구체적인 매수 가격대와 매도 가격대**를 산출한다.

### 매수구간 산출

| 항목 | 산출 기준 | 비중 |
|------|----------|:----:|
| 1차 매수 | 지지선 중 현재가 대비 -3%~-10% 범위 최고가 | 50% |
| 2차 매수 | 지지선 중 1차 대비 -5%~-15% 범위, 52주저×1.05 폴백 | 50% |
| 손절가 | MA120×0.97, 2차매수×0.95 중 최저 | 전량 |

### 매도타점 산출

| 항목 | 산출 기준 | 비중 |
|------|----------|:----:|
| 1차 목표 | 저항선/컨센서스 중 현재가 +5%~+20% 범위 최저가 | 50% |
| 2차 목표 | 컨센서스 상단, 52주 고가, 1차×1.10 중 최저 | 잔량 |
| 트레일링 스탑 | Beta>1.5→15%, Beta<0.8→7%, 기본 10% | 전량 |

### 등급별 표시 규칙

| 등급 | 매수구간 | 매도타점 |
|------|:-------:|:-------:|
| STRONG_BUY | ✅ 적극 매수구간 | ✅ 목표가 |
| BUY | ✅ 매수구간 | ✅ 목표가 |
| HOLD | ❌ (보유 유지) | ✅ 매도타점 |
| SELL | ❌ | ✅ 청산 기준 |
| STRONG_SELL | ❌ | ✅ 즉시 청산 |

### R/R Ratio 판단

| R/R | 판단 |
|:---:|------|
| ≥ 3.0 | 매우 유리 |
| ≥ 2.0 | 유리 |
| ≥ 1.0 | 보통 |
| < 1.0 | 불리 — 진입 재고 필요 |

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
