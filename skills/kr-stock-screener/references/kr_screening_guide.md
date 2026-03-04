# 한국 주식 스크리닝 가이드

## KRClient 스크리닝 메서드 요약

### 기본 데이터
| 메서드 | 반환 | 용도 |
|--------|------|------|
| `get_ticker_list(market)` | DataFrame(Ticker, Name, Sector) | 종목 유니버스 |
| `get_ohlcv(ticker, start, end)` | DataFrame(Open, High, Low, Close, Volume) | 가격/거래량 |
| `get_fundamentals(market)` | DataFrame(PER, PBR, EPS, DIV, BPS) | 밸류에이션 |
| `get_market_cap(market)` | DataFrame(시가총액, 거래량, 거래대금, 상장주식수) | 시가총액 |

### 재무 데이터
| 메서드 | 반환 | 용도 |
|--------|------|------|
| `get_financial_statements(ticker, year, report_type)` | dict | DART 재무제표 |
| `get_financial_ratios(ticker, year)` | dict(ROE, ROA, OPM, NPM, DE_ratio) | 재무비율 |
| `get_dividend_info(ticker, year)` | dict(DPS, Yield, Payout) | 배당 정보 |

### 수급 데이터
| 메서드 | 반환 | 용도 |
|--------|------|------|
| `get_investor_trading(ticker, start, end)` | DataFrame(기관, 외국인, 개인...) | 투자자별 매매 |
| `get_investor_trading(ticker, detail=True)` | DataFrame(12분류) | 상세 수급 |
| `get_foreign_exhaustion(ticker)` | dict(지분율, 한도소진율) | 외국인 지분 |
| `get_short_selling(ticker, start, end)` | DataFrame(공매도량, 잔고) | 공매도 |

### 지수 데이터
| 메서드 | 반환 | 용도 |
|--------|------|------|
| `get_index(index_code, start, end)` | DataFrame(Close) | 지수 가격 |
| `get_index_constituents(index_code)` | list[str] | 지수 구성종목 |
| `get_sector_performance(market, period)` | DataFrame(Sector, Return) | 섹터 수익률 |

## 자주 사용하는 스크리닝 조합

### 1. 가치주 기본
- PER ≤ 10 + PBR ≤ 1.0 + 시총 ≥ 5,000억

### 2. 고배당 안정
- 배당수익률 ≥ 3% + 3년 무삭감 + 배당성향 < 70%

### 3. 성장주 모멘텀
- EPS 성장 ≥ 20% + 매출 성장 ≥ 15% + RS Rank ≥ 80

### 4. 수급 강세
- 외국인 5일 연속 순매수 + 기관 3일 순매수 + 거래량 증가

### 5. 기술적 반등
- RSI ≤ 30 + 볼린저 하단 + ROE ≥ 10%

### 6. 대형 저평가
- KOSPI200 구성 + PER ≤ 평균 - 1σ + ROE ≥ 15%

### 7. 소형 성장
- 시총 3,000억~1조 + EPS CAGR ≥ 30% + 매출 성장 ≥ 20%

### 8. 배당 성장
- 3년 배당 CAGR ≥ 10% + 현재 수익률 ≥ 2% + 부채비율 < 100%

### 9. 턴어라운드
- 전분기 적자 → 당분기 흑자 + 매출 성장 양전환

### 10. 52주 신고가 근접
- 현재가 ≥ 52주 고가 × 0.95 + 거래량 > 50일 평균 × 1.5

### 11. 역발상 (공매도 감소)
- 공매도 잔고 20일 감소 추세 + 외국인 순매수 전환

### 12. 업종 리더
- 업종 내 시총 1위 + 업종 ROE 상위 20% + 업종 PER 하위 30%

### 13. 현금 부자
- 현금/시총 > 30% + 무차입 + ROE > 8%

### 14. KOSDAQ 우량
- KOSDAQ150 구성 + PER ≤ 15 + ROE ≥ 12% + 3년 배당

### 15. 이벤트 드리븐
- DART 공시 (대규모 자사주 매입, 대주주 지분 변동) 필터링

## 한국 시장 핵심 스크리닝 지표

### 외국인 지분율 해석
| 지분율 | 의미 | 투자 시사점 |
|--------|------|-----------|
| 50%+ | 외국인 과집중 | 글로벌 리스크에 민감 |
| 20-50% | 적정 관심 | 유동성/정보 양호 |
| 5-20% | 보통 | 소외주 가능 |
| < 5% | 무관심 | 높은 변동성 리스크 |

### PER 해석 (한국 기준)
| PER 범위 | KOSPI 평균 대비 | 의미 |
|---------|:-------------:|------|
| < 8 | 극단적 저평가 | 가치 함정 주의 |
| 8-12 | 저평가 | 가치주 후보 |
| 12-15 | 적정 | 시장 평균 |
| 15-25 | 고평가 | 성장 프리미엄 |
| > 25 | 극단적 고평가 | 성장주 또는 거품 |

### 배당수익률 (한국 기준)
| 수익률 | 의미 | 참고 |
|--------|------|------|
| ≥ 5% | 고배당 | 지속가능성 확인 필수 |
| 3-5% | 양호 | 일반 배당주 |
| 2-3% | 보통 | KOSPI 평균 수준 |
| < 2% | 저배당 | 성장주 성격 |

### 거래세 (2023년~)
- KOSPI: 매도 시 0.05% (농특세 포함 0.23%)
- KOSDAQ: 매도 시 0.20% (농특세 포함 0.23%)
- 배당소득세: 15.4% (소득세 14% + 지방세 1.4%)
- 양도세: 대주주 22-27.5% (2025년~ 금투세 도입 예정이었으나 유예)
