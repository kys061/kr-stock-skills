# DART Open API 가이드

## 주요 엔드포인트

### 1. 공시검색
- `list.json` — 공시 목록 조회
- Parameters: corp_code, bgn_de, end_de, pblntf_ty

### 2. 대량보유 (5% Rule)
- `majorstock.json` — 대량보유 상황보고서
- 5% 이상 보유 변동 시 의무 보고

### 3. 임원 등의 특정증권등 소유상황보고서
- `elestock.json` — 임원/주요주주 매매 내역

### 4. 자사주
- `tesstkAcqsDspsSttus.json` — 자사주 취득/처분

## DART Report Codes (kr-earnings-calendar 참조)
- A001: 사업보고서
- A002: 반기보고서
- A003: 분기보고서
- D001: 잠정실적
- D002: 영업실적
