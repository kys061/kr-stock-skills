# Sector Sensitivity to US Monetary Policy

## Sensitivity Map (14 Korean Sectors)

| Sector | Key | Sensitivity | Rationale |
|--------|-----|:-----------:|-----------|
| 반도체 | semiconductor | 1.3 | 수출 비중 높음, 글로벌 수요 민감, 성장주 특성, 외국인 비중 높음 |
| 2차전지 | secondary_battery | 1.3 | 글로벌 EV 수요 연동, 자본집약적, 성장주 밸류에이션 |
| 바이오 | bio | 1.2 | 장기 듀레이션 자산, DCF 할인율 민감, 글로벌 라이선스 |
| IT | it | 1.2 | 수출 비중, 성장주 밸류에이션, NASDAQ 상관관계 |
| 자동차 | auto | 1.1 | 글로벌 수요 연동, 환율 영향 (달러 결제), 수출 비중 높음 |
| 조선 | shipbuilding | 1.0 | 수출 100%, 달러 결제, 그러나 수주 사이클이 통화정책과 약결합 |
| 철강 | steel | 0.9 | 글로벌 수요 일부, 내수 비중 상당, 원자재 가격 연동 |
| 화학 | chemical | 0.9 | 원자재 가격 연동, 수출 비중 중간, 경기 민감도 |
| 건설 | construction | 0.8 | 국내 금리 민감(BOK 기준), US 정책은 간접 영향 |
| 금융 | finance | 0.7 | NIM 영향 있지만 BOK 기준금리 기반, US 정책은 간접 |
| 보험 | insurance | 0.6 | 장기 투자수익률 영향, 그러나 국내 채권 위주 |
| 유통 | retail | 0.5 | 내수 소비 중심, 환율 간접 영향(수입 원가) |
| 방산 | defense | 0.4 | 정부 예산 기반, 금리 둔감, 지정학 이벤트가 더 중요 |
| 음식료 | food | 0.3 | 필수 소비재, 내수 중심, 통화정책 거의 무관 |

## Default Sensitivity

- 미분류 섹터: 0.7 (14섹터 평균에 근접)

## Sensitivity Tiers

| Tier | Sensitivity | Sectors | Characteristic |
|------|:-----------:|---------|---------------|
| High | >= 1.2 | semiconductor, secondary_battery, bio, it | 수출+성장주 |
| Medium-High | 1.0~1.1 | auto, shipbuilding | 수출+경기순환 |
| Medium | 0.8~0.9 | steel, chemical, construction | 내수+수출 혼합 |
| Low | <= 0.7 | finance, insurance, retail, defense, food | 내수+방어 |
