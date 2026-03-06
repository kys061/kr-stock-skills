# Plan: Multi-Tier Data Fallback 체계 구축

> Feature: `multi-tier-data-fallback`
> Created: 2026-03-06
> Status: Plan

---

## 1. 문제 정의

현재 데이터 소스 상태:

| Tier | 소스 | 상태 | 문제점 |
|:----:|------|:----:|--------|
| 0 | KRX Open API | 401 | 개별 서비스 승인 대기 |
| 1 | KIS API | 미설정 | 계좌 필요 |
| 2 | PyKRX/FDR | 403 | KRX 차단 |
| 3 | WebSearch | 가용 | 정량 데이터 정밀도 낮음 |

**핵심 문제**: Tier 0~2가 모두 불가하여 WebSearch(Tier 3)에만 의존. 정량 분석 정밀도가 떨어지고, 전종목 스크리닝이 불가능.

---

## 2. 추가 가능한 API 분석

첨부 이미지 기반 평가:

| API | 무료 | 한국 종목 | 수집 데이터 | Python | 추천 |
|-----|:----:|:--------:|-----------|--------|:----:|
| **yfinance** | O | O (093370.KQ) | OHLCV, 재무제표, PER/PBR | `yfinance` | **S** |
| **공공데이터포털 금융위** | O (1만회/일) | O | 일별 OHLCV (T+1) | `requests` | **A** |
| **ECOS (한국은행)** | O | - | 금리, 환율, 경제지표 | config에 필드 있음 | **A** |
| **Twelve Data** | 800회/일 | 일부 | OHLCV, 기술지표 | `twelvedata` | B |
| **FMP** | 250회/일 | 일부 | 재무제표 | `requests` | B |
| Alpha Vantage | 25회/일 | X | US만 | - | C |
| Polygon.io | 유료 $29/월 | X | US만 | - | C |

### 우선순위 결정 기준
1. 한국 종목 지원 필수
2. 무료 & 충분한 호출 제한
3. OHLCV + 밸류에이션(PER/PBR) 동시 제공
4. Python 라이브러리 성숙도

---

## 3. 신규 Tier 아키텍처

```
Tier 0: KRX Open API (인증키, 1만회/일)        ← 승인 대기
Tier 1: yfinance (무료, 무제한, OHLCV+재무)     ← 신규 추가 [S급]
Tier 2: 공공데이터포털 금융위 (1만회/일, T+1)    ← 신규 추가 [A급]
Tier 3: PyKRX/FDR (비공식 스크래핑)              ← 기존 (현재 차단)
Tier 4: KIS API (한투 계좌 기반)                 ← 기존 (미설정)
Tier 5: WebSearch 폴백 (항상 가용)               ← 기존
```

### 추가 보조 소스 (매크로 전용)
- **ECOS**: config.py에 이미 `ecos_api_key` 필드 존재 → 금리/환율/경제지표용
- **Twelve Data**: 기술지표(RSI/MACD/BB) 보강용 (선택)
- **FMP**: 재무제표 보강용 (선택)

---

## 4. yfinance 프로바이더 설계

### 4.1 종목코드 매핑
```
KOSPI:  005930 → 005930.KS (삼성전자)
KOSDAQ: 093370 → 093370.KQ (후성)
```

### 4.2 제공 데이터
| 메서드 | yfinance API | 용도 |
|--------|-------------|------|
| `get_price()` | `Ticker.info` | 현재가, 시총, 52주 고저 |
| `get_ohlcv()` | `Ticker.history()` | OHLCV 시계열 |
| `get_fundamentals()` | `Ticker.info` | PER, PBR, EPS, ROE |
| `get_financials()` | `Ticker.financials` | 매출, 영업이익, 순이익 |
| `get_market_cap()` | `Ticker.info['marketCap']` | 시가총액 |

### 4.3 장점/한계
- **장점**: 무료, 무제한, 글로벌 커버리지, 재무제표 포함
- **한계**: 실시간 아님 (15분 지연), 투자자별 매매동향 없음, 공매도 없음

---

## 5. 공공데이터포털 프로바이더 설계

### 5.1 API 정보
- 엔드포인트: `apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService`
- 인증: ServiceKey (공공데이터포털 발급)
- 제한: 일 1만회
- 데이터: 일별 OHLCV (T+1 지연)

### 5.2 제공 데이터
| 메서드 | 용도 |
|--------|------|
| `get_stock_daily()` | 전종목 일별 시세 |
| `get_stock_info()` | 종목 기본정보 |

### 5.3 장점/한계
- **장점**: 공식 API, 안정적, KRX 데이터 그대로
- **한계**: T+1 지연, PER/PBR 미제공, 별도 키 발급 필요

---

## 6. 구현 계획

### Phase 1: yfinance 프로바이더 (즉시 효과, 최우선)
1. `pip install yfinance` 설치
2. `providers/yfinance_provider.py` 생성
3. `kr_client.py`에 Tier 1 통합 (KRX API → yfinance → PyKRX 순)
4. 종목코드 변환 유틸 추가 (`ticker_utils.py`에 `.KS/.KQ` 매핑)
5. 테스트 작성 및 실행

### Phase 2: 공공데이터포털 프로바이더 (키 발급 후)
1. data.go.kr에서 "금융위원회_주식시세정보" 서비스 키 발급
2. `providers/data_go_kr_provider.py` 생성
3. `config.py`에 `DATA_GO_KR_KEY` 추가
4. `kr_client.py`에 Tier 2 통합

### Phase 3: ECOS 프로바이더 활성화 (매크로 보강)
1. `ecos_api_key` 활용하여 `providers/ecos_provider.py` 생성
2. 금리/환율/경제지표 조회 연동
3. `us-monetary-regime`, `kr-macro-regime` 스킬에서 직접 활용

### Phase 4: config.py / CLAUDE.md 최종 업데이트
1. 전체 Tier 구조 반영
2. 9개 SKILL.md 데이터 소스 섹션 업데이트
3. install.sh 동기화

---

## 7. 우선순위 및 예상 효과

| Phase | 작업 | 효과 | 소요 |
|:-----:|------|------|:----:|
| **1** | yfinance 통합 | OHLCV+PER/PBR+재무제표 **즉시 가용** | 빠름 |
| 2 | 공공데이터포털 | KRX 공식 데이터 안정적 폴백 | 키 발급 필요 |
| 3 | ECOS | 매크로 지표 정밀도 향상 | 보통 |
| 4 | 문서 정리 | 전체 Tier 체계 문서화 | 빠름 |

### Phase 1 완료 시 기대 효과
- **전종목 스크리닝 가능** (yfinance로 KOSPI/KOSDAQ 전 종목 PER/PBR 조회)
- **WebSearch 의존도 대폭 감소** (정량 데이터는 yfinance, 정성은 WebSearch)
- **분석 리포트 정밀도 향상** (실제 재무제표 데이터 활용)

---

## 8. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| yfinance 한국 종목 데이터 누락 | 일부 종목 조회 실패 | 공공데이터포털/WebSearch 폴백 |
| yfinance 비공식 스크래핑 차단 | PyKRX와 같은 문제 | 공공데이터포털 + KRX API로 이중화 |
| 공공데이터포털 키 발급 지연 | Phase 2 지연 | Phase 1(yfinance)으로 우선 커버 |
| 호출 제한 초과 | 전종목 스크리닝 시 | 캐시 적극 활용 + 호출 최적화 |

---

*Plan created by PDCA workflow*
