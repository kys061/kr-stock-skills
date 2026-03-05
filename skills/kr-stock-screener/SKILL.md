---
name: kr-stock-screener
description: KRClient 기반 PER/PBR/배당수익률/시가총액 등 다조건 필터 종목 스크리닝. KOSPI/KOSDAQ 전 종목 대상.
---

# kr-stock-screener: 한국 종합 주식 스크리닝 도구

> KRClient 기반 다조건 필터 스크리닝 도구.
> 자연어 요청을 KRClient 메서드 조합으로 변환하여 한국 주식을 스크리닝합니다.
> **KRClient 불가 시 WebSearch 폴백으로 스크리닝을 계속한다.**

## 데이터 소스 우선순위

```
1순위: KRX Open API (인증키) → 전 종목 정량 스크리닝
2순위: KRClient (pykrx/FDR) → 프로그래밍 스크리닝
3순위: WebSearch 폴백 → 다축 검색 기반 정성 스크리닝
```

### WebSearch 폴백 실행 절차

KRClient 실패(403/에러) 시 아래 절차로 스크리닝한다:

1. **시총 상위 수집**: `"{시장} 시가총액 상위 종목 {년도}"` 검색
2. **수익성 상위 수집**: `"{시장} 영업이익률 상위 종목 실적"` 검색
3. **수급 상위 수집**: `"{시장} 외국인 기관 순매수 상위"` 검색
4. **성장 테마 수집**: `"{시장} 유망주 성장주 증권사 추천"` 검색
5. **저평가 수집**: `"{시장} 저PER 저PBR 고ROE"` 검색
6. **후보 통합**: 5개 축에서 수집된 종목을 병합, 중복 출현 종목 우선 순위 부여
7. **정성 스코어링**: 수익성/성장성/수급/밸류/모멘텀 5팩터 1-5점 평가

### WebSearch 폴백 시 리포트 표기
```markdown
> **데이터 소스**: WebSearch 폴백 (KRX API 미가용)
> **정밀도 한계**: 정량 필터링 불가, 뉴스/리포트 기반 정성 평가
```

## 사용 시점

- 사용자가 특정 조건으로 한국 주식을 필터링하고 싶을 때
- "PER 10 이하이면서 배당수익률 3% 이상인 종목" 같은 다조건 스크리닝
- 밸류에이션, 배당, 수급, 기술적 조건을 조합할 때

## 스크리닝 조건 카테고리

### 밸류에이션
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| PER | 주가수익비율 | `get_fundamentals()` → `PER` |
| PBR | 주가순자산비율 | `get_fundamentals()` → `PBR` |
| EPS | 주당순이익 | `get_fundamentals()` → `EPS` |

### 배당
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| 배당수익률 | DIV/Y | `get_fundamentals()` → `DIV` |
| 배당 정보 | 배당금/배당성향 | `get_dividend_info()` |

### 시가총액 / 유동성
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| 시가총액 | 원 단위 | `get_market_cap()` |
| 거래량 | 일별 거래량 | `get_ohlcv()` → `Volume` |

### 수급
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| 외국인 순매수 | N일 연속 | `get_investor_trading()` |
| 기관 순매수 | 기관 합산 | `get_investor_trading(detail=True)` |
| 외국인 지분율 | 소진율 | `get_foreign_exhaustion()` |
| 공매도 비율 | 공매도잔고/거래량 | `get_short_selling()` |

### 재무
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| ROE | 자기자본이익률 | `get_financial_ratios()` |
| 부채비율 | D/E ratio | `get_financial_ratios()` |
| 영업이익률 | OPM | `get_financial_ratios()` |
| 매출성장률 | YoY | `get_financial_statements()` |

### 기술적
| 조건 | 설명 | 구현 방법 |
|------|------|----------|
| RSI | 상대강도지수 | `get_ohlcv()` + `ta_utils.rsi()` |
| 이동평균 | SMA/EMA | `get_ohlcv()` + `ta_utils.sma()/ema()` |
| 볼린저 밴드 | 밴드 위치 | `get_ohlcv()` + `ta_utils.bollinger_bands()` |
| MACD | 시그널 교차 | `get_ohlcv()` + `ta_utils.macd()` |

### 섹터/업종
| 조건 | 설명 | KRClient 메서드 |
|------|------|----------------|
| 업종 필터 | KRX 업종 분류 | `get_ticker_list()` → Sector |
| 섹터 수익률 | 섹터별 성과 | `get_sector_performance()` |

## 스크리닝 패턴 예시

### 패턴 1: 저PER 고배당
```python
from _kr_common.kr_client import KRClient

client = KRClient()
tickers = client.get_ticker_list(market='ALL')
fundamentals = client.get_fundamentals(market='ALL')

# 필터: PER ≤ 10, 배당수익률 ≥ 3%
result = fundamentals[
    (fundamentals['PER'] > 0) &
    (fundamentals['PER'] <= 10) &
    (fundamentals['DIV'] >= 3.0)
].sort_values('DIV', ascending=False)
```

### 패턴 2: 외국인 순매수 + 기술적 강세
```python
from _kr_common.kr_client import KRClient
from _kr_common.ta_utils import sma, rsi

client = KRClient()
# 최근 5일 외국인 순매수 종목 필터링
# → get_investor_trading() 기간 조회
# → 종가 > 200일 SMA + RSI > 50
```

### 패턴 3: 시가총액 상위 + 저PBR
```python
from _kr_common.kr_client import KRClient

client = KRClient()
market_cap = client.get_market_cap(market='ALL')
fundamentals = client.get_fundamentals(market='ALL')

# 시총 1조원 이상 + PBR ≤ 1.0
merged = market_cap.merge(fundamentals, left_index=True, right_index=True)
result = merged[
    (merged['시가총액'] >= 1_000_000_000_000) &
    (merged['PBR'] > 0) &
    (merged['PBR'] <= 1.0)
]
```

### 패턴 4: RSI 과매도 + 재무 건전
```python
from _kr_common.kr_client import KRClient
from _kr_common.ta_utils import rsi

client = KRClient()
# RSI(14) ≤ 30 종목 스크리닝
# → get_ohlcv() → rsi() 계산
# → get_financial_ratios() → ROE > 10%, 부채비율 < 100%
```

### 패턴 5: 배당 성장주
```python
from _kr_common.kr_client import KRClient

client = KRClient()
# 3년 연속 배당 증가 + 현재 배당수익률 ≥ 2%
# → get_dividend_info() 3개년 조회
# → 배당금 증가 추세 확인
```

### 패턴 6: KOSPI200 구성종목 중 52주 신고가
```python
from _kr_common.kr_client import KRClient

client = KRClient()
constituents = client.get_index_constituents('1028')  # KOSPI200
# 각 종목 get_ohlcv(260일) → 52주 고가 대비 현재가 비교
```

### 패턴 7: 공매도 비율 하락 + 가격 반등
```python
from _kr_common.kr_client import KRClient

client = KRClient()
# get_short_selling() → 공매도 비율 하락 추세
# + get_ohlcv() → 최근 5일 양봉
```

### 패턴 8: 업종별 저평가 리더
```python
from _kr_common.kr_client import KRClient

client = KRClient()
# get_ticker_list() → 업종별 그룹핑
# → 업종 내 PER 최저 + ROE 최고 종목
```

### 패턴 9: 기관/외국인 동시 순매수
```python
from _kr_common.kr_client import KRClient

client = KRClient()
# get_investor_trading(detail=True)
# → 기관 합산 순매수 + 외국인 순매수 동시 발생
```

### 패턴 10: 볼린저 밴드 하단 + 거래량 증가
```python
from _kr_common.kr_client import KRClient
from _kr_common.ta_utils import bollinger_bands, volume_ratio

client = KRClient()
# 볼린저 하단 터치 + 거래량 > 20일 평균 × 2
```

## 한국 시장 스크리닝 팁

### 외국인 지분율 기준
- **20-50%**: 적정 외국인 관심, 유동성 양호
- **50%+**: 외국인 과집중 주의 (매도 시 급락 위험)
- **5% 미만**: 외국인 무관심, 소형주 리스크

### 신용잔고 기준
- **신용비율 > 3%**: 과열 주의
- **신용비율 < 1%**: 매물 압력 낮음

### 거래세 고려
- **매도 시 0.23%** (코스피), **0.23%** (코스닥, 2023년~)
- 단기 매매 시 거래비용 부담 고려 필요

### 배당 캘린더
- **12월 결산법인**: 대부분의 상장사
- **배당락일**: 통상 12월 마지막 거래일 2영업일 전
- **배당금 지급**: 주주총회 후 (통상 3-4월)

## 관련 스킬

| 스킬 | 용도 |
|------|------|
| kr-value-dividend | 배당 가치주 심층 스크리닝 |
| kr-canslim-screener | CANSLIM 성장주 발굴 |
| kr-vcp-screener | VCP 패턴 브레이크아웃 |
| kr-dividend-pullback | 배당 성장 풀백 타이밍 |
| kr-pead-screener | 실적 드리프트 패턴 |
| kr-pair-trade | 페어 트레이딩 후보 |

---

## Output Rule (마크다운 리포트 저장)

- 분석 완료 후 결과를 **마크다운 파일로 저장**한다
- 저장 경로: `reports/{skill_name}_{identifier}_{name}_{YYYYMMDD}.md`
  - `{identifier}`: 종목코드 (없으면 `market`)
  - `{name}`: 종목명 또는 분석 대상명 (한글 가능)
  - 예: `reports/kr-stock-analysis_005930_삼성전자_20260305.md`
- 파일 구조:
  ```markdown
  # {스킬명} 분석 리포트
  > 생성일: {YYYY-MM-DD HH:MM} | 대상: {identifier}

  ## 요약
  (핵심 결론 2-3줄)

  ## 상세 분석
  (스킬별 분석 결과를 마크다운 테이블, 리스트, 헤더로 구조화)

  ## 판단 근거
  (점수, 등급, 시그널 등 정량 데이터)

  ---
  *Generated by {skill_name}*
  ```
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)
