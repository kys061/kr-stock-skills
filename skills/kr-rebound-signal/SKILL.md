---
name: kr-rebound-signal
description: 한국 주식시장 급락 시 14개 반등 시그널(VIX/CNN F&G/Put-Call/EWY/선물/인사이더/외국인/공매도/신용/HY스프레드/환율/RSI/정부대책/뉴스톤) 체크리스트 점검 및 종합 판단.
---

# kr-rebound-signal: 폭락 발생 시 반등 시그널 체크

> 한국 주식시장 급락 발생 시 14개 반등 시그널을 체계적으로 점검합니다.
> 공포 심리, 야간 선행, 수급/포지셔닝, 신용/채권, 기술적/뉴스 5개 카테고리로 구성.
> YES 개수에 따라 분할 매수(3+) / 적극 매수(5+) / 역사적 반등(7+) 판단.

## 데이터 소스 우선순위

```
1순위: yfinance (VIX/EWY/S&P선물/USD-KRW/KOSPI RSI 프로그래밍 조회)
2순위: WebFetch (지정 URL에서 직접 수집)
3순위: WebSearch 폴백 (검색 기반 수집)
```

### 스크립트 실행 (1순위)

```bash
cd ~/stock/skills/kr-rebound-signal/scripts
python3 rebound_check.py
```

yfinance로 5개 자동 시그널(#1 VIX, #4 EWY, #5 S&P선물, #11 USD/KRW, #12 KOSPI RSI)을 수집한다.
나머지 9개 시그널은 WebSearch/WebFetch로 보완.

## 14개 반등 시그널 체크리스트

### A. 공포 심리 지표 (3개)

#### 1. VIX 전일 대비 -10% 이상 급락 (급락→전환이 핵심)

- **티커**: `^VIX`
- **판정 기준**: 전일 대비 변화율 ≤ -10%
- **의미**: 공포가 피크를 찍고 급격히 해소되는 시그널

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://finance.yahoo.com/quote/%5EVIX/ | https://www.cboe.com/tradable_products/vix/ |

#### 2. CNN Fear & Greed Index < 20 (Extreme Fear)

- **범위**: 0~100
- **판정 기준**: 수치 < 20
- **의미**: 시장 심리 극단적 공포 → 역발상 매수 구간

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://www.cnn.com/markets/fear-and-greed | https://en.macromicro.me/charts/50108/cnn-fear-and-greed |

#### 3. CBOE Put/Call Ratio > 1.0 (풋옵션 과매수)

- **판정 기준**: Equity Put/Call Ratio > 1.0
- **의미**: 풋옵션 매수 폭증 = 극공포 → 반전 가능성

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://www.cboe.com/us/options/market_statistics/daily/ | https://www.barchart.com/stocks/quotes/CBOE/put-call-ratios |

### B. 야간 선행 지표 (3개)

#### 4. EWY(한국 ETF) 미국장 +1% 이상 반등

- **티커**: `EWY`
- **판정 기준**: 전일 대비 변화율 ≥ +1.0%
- **의미**: 미국 투자자들의 한국 시장 선행 매수

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://finance.yahoo.com/quote/EWY/ | https://www.investing.com/etfs/ishares-msci-south-korea |

#### 5. S&P 500 선물(ES=F) 양전

- **티커**: `ES=F`
- **판정 기준**: 변화율 > 0%
- **의미**: 글로벌 리스크 온 전환

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://finance.yahoo.com/quote/ES=F/ | https://www.investing.com/indices/us-spx-500-futures |

#### 6. 인사이더 클러스터 매수 10건 이상 (7일 이내)

- **판정 기준**: 최근 7일 내 CEO/CFO/Director 매수 ≥ 10건
- **의미**: 내부자가 자사주 매수 → 바닥 확신 신호

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| http://openinsider.com/charts | http://openinsider.com/latest-buys |

### C. 수급/포지셔닝 (3개)

#### 7. 외국인 한국 주식 순매수 전환

- **판정 기준**: KOSPI 외국인 순매수 전환 (전일 순매도 → 당일 순매수)
- **의미**: 외국인 자금 유입 재개

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://data.krx.co.kr/ | https://finance.daum.net/domestic/influential_investors |

> WebSearch 키워드: `"외국인 순매수 KOSPI"`

#### 8. 공매도 잔고 감소 전환

- **판정 기준**: KOSPI 공매도 잔고 전일 대비 감소
- **의미**: 숏커버 시작 → 하방 압력 완화

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://short.krx.co.kr/ | https://data.krx.co.kr/ |

#### 9. 신용잔고 고점 대비 30% 이상 급감 (반대매매 소진)

- **판정 기준**: 신용잔고 고점 대비 감소율 ≥ 30%
- **의미**: 레버리지 강제 청산 완료 → 매물 소진

| 1순위 URL | WebSearch |
|-----------|-----------|
| https://freesis.kofia.or.kr/ | `"신용잔고 반대매매"` |

### D. 신용/채권 시장 (2개)

#### 10. 하이일드 스프레드(HY OAS) 축소 전환

- **판정 기준**: 전일 대비 HY OAS 감소
- **의미**: 신용 리스크 완화 → 위험 자산 선호 복귀

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://fred.stlouisfed.org/series/BAMLH0A0HYM2 | https://fred.stlouisfed.org/series/BAMLH0A3HYC |

#### 11. USD/KRW 환율 하락 전환 (원화 강세)

- **티커**: `KRW=X`
- **판정 기준**: 전일 대비 변화율 < 0%
- **의미**: 외국인 자금 이탈 중단, 원화 안정

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://www.investing.com/currencies/usd-krw | https://finance.yahoo.com/quote/KRW=X/ |

### E. 기술적/뉴스 (3개)

#### 12. KOSPI RSI(14) < 30 (과매도)

- **티커**: `^KS11`
- **판정 기준**: RSI(14) < 30
- **의미**: 기술적 과매도 → 단기 반등 확률 상승

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://www.tradingview.com/symbols/KRX-KOSPI/ | https://www.investing.com/indices/kospi-technical |

#### 13. 정부 시장 안정화 대책 발표

- **판정 기준**: 금융위/기재부의 공식 안정화 조치 발표 여부
- **의미**: 정책적 하방 지지 → 심리적 바닥 형성

| 1순위 URL | 2순위 URL |
|-----------|-----------|
| https://www.fsc.go.kr/ | https://www.moef.go.kr/ |

> WebSearch 키워드: `"정부 시장 안정화 대책"` OR `"금융위원회 시장"`

#### 14. 뉴스 톤 전환 ("폭락/공포" → "안정/반등")

- **판정 기준**: 주요 뉴스 헤드라인의 톤 변화 (공포→안정)
- **의미**: 미디어 센티먼트 바닥 통과

| 한국 뉴스 | 영문 뉴스 |
|-----------|-----------|
| https://search.naver.com/search.naver?where=news&query=KOSPI | https://www.cnbc.com/asia-markets/ |

> WebSearch 키워드: `"KOSPI 반등"` / `"KOSPI rebound"` / `"Korea stock market recovery"`

## 출력 형식

```markdown
# Rebound Signal Check - {YYYY-MM-DD}

| # | 카테고리 | 시그널 | 결과 | 근거 데이터 | 출처 |
|---|----------|--------|------|------------|------|
| 1 | 공포 심리 | VIX -10% 급락 | YES/NO | VIX XX.XX (-X.X%) | yfinance |
| 2 | 공포 심리 | CNN F&G < 20 | YES/NO | F&G: XX | WebSearch |
| 3 | 공포 심리 | Put/Call > 1.0 | YES/NO | P/C: X.XX | WebSearch |
| 4 | 야간 선행 | EWY +1% 반등 | YES/NO | $XX.XX (+X.X%) | yfinance |
| 5 | 야간 선행 | S&P선물 양전 | YES/NO | X,XXX (+X.X%) | yfinance |
| 6 | 야간 선행 | 인사이더 10건+ | YES/NO | XX건 (7일) | WebFetch |
| 7 | 수급 | 외국인 순매수 전환 | YES/NO | +XXX억원 | WebSearch |
| 8 | 수급 | 공매도 잔고 감소 | YES/NO | -X.X% | WebSearch |
| 9 | 수급 | 신용잔고 -30% | YES/NO | X.X조 (고점 대비 -XX%) | WebSearch |
| 10 | 채권 | HY스프레드 축소 | YES/NO | X.XX% (-Xbp) | WebFetch |
| 11 | 채권 | USD/KRW 하락 | YES/NO | X,XXX (-X.X%) | yfinance |
| 12 | 기술적 | KOSPI RSI < 30 | YES/NO | RSI: XX.X | yfinance |
| 13 | 뉴스 | 정부 안정화 대책 | YES/NO | (내용 요약) | WebSearch |
| 14 | 뉴스 | 뉴스 톤 전환 | YES/NO | (톤 변화 요약) | WebSearch |

> **YES 개수**: X/14
> **종합 판단**: {관망 유지 / 분할 매수 고려 / 적극 매수 고려 / 역사적 반등 가능성}
> **핵심 시그널**: {가장 강력한 2~3개 시그널 요약}
> **주의사항**: {아직 확인되지 않은 리스크 요인}
```

## 종합 판단 로직

14개 시그널의 YES 개수로 4단계 판정:

| YES 개수 | 판단 | 의미 |
|:--------:|------|------|
| 0~2 | **관망 유지** | 반등 근거 부족, 추가 하락 가능 |
| 3~4 | **분할 매수 고려** | 일부 시그널 확인, 소규모 진입 검토 |
| 5~6 | **적극 매수 고려** | 다수 시그널 확인, 적극적 진입 검토 |
| 7+ | **역사적 반등 가능성** | 복합 바닥 시그널, 강한 반등 기대 |

### 카테고리별 가중치 참고

| 카테고리 | 항목 수 | 특성 |
|----------|:------:|------|
| A. 공포 심리 | 3 | 역발상 지표 (극공포 = 매수) |
| B. 야간 선행 | 3 | 다음 한국장 방향 선행 |
| C. 수급/포지셔닝 | 3 | 실제 자금 흐름 전환 |
| D. 신용/채권 | 2 | 시스템 리스크 완화 |
| E. 기술적/뉴스 | 3 | 기술적 바닥 + 정책/심리 |

> 카테고리 C(수급)와 D(신용/채권)의 YES가 동시 발생 시 신뢰도가 특히 높음.

## 사용 시점

- 한국 주식시장 급락 발생 시 (KOSPI -3% 이상 하락)
- 글로벌 패닉 셀오프 후 반등 가능성 점검
- 분할 매수 진입 타이밍 판단
- VIX 급등 후 하락 전환 확인

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| daily-market-check | 매일 6지표 체크 (평상시) vs 급락 시 14시그널 (위기 시) |
| kr-ftd-detector | FTD는 반등 시그널 중 하나, 이 스킬은 14개 종합 |
| kr-market-top-detector | 천장 탐지 ↔ 바닥 탐지 (공격/방어 페어) |
| kr-bubble-detector | 버블 → 붕괴 → 반등 시퀀스의 마지막 단계 |
| kr-credit-monitor | 신용잔고(#9)가 이 스킬의 시그널 중 하나 |
| kr-market-breadth | 시장폭 회복으로 반등 확인 |

> 급락 시: rebound-signal(바닥 확인) → ftd-detector(FTD 확인) → market-breadth(회복 확인)

---

## Output Rule (마크다운 리포트 저장)

- **템플릿**: `_kr_common/templates/report_macro.md` 의 구조를 참조
- **공통 규칙**: `_kr_common/templates/report_rules.md` 참조
- 저장 경로: `reports/kr-rebound-signal_market_{YYYYMMDD}.md`
- `reports/` 디렉토리가 없으면 자동 생성
- 동일 파일명이 존재하면 덮어쓰기 (같은 날 재분석 시)
