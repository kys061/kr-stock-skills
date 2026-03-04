# kr-breadth-chart (한국 시장폭 차트 분석)

## 개요

| 항목 | 값 |
|------|-----|
| US 원본 | breadth-chart-analyst |
| 복잡도 | Low |
| 스크립트 | 없음 |
| 역할 | kr-market-breadth / kr-uptrend-analyzer 출력 차트의 시각적 해석 |

한국 주식 시장의 시장폭(Market Breadth) 차트를 분석하는 가이드 스킬.
kr-market-breadth 및 kr-uptrend-analyzer (Phase 2)가 생성한 데이터의
차트 이미지를 해석하여 시장 건전성을 판단한다.

## 분석 대상

1. **KOSPI Breadth 차트**: 200MA 위 종목 비율 추이
2. **KOSDAQ Breadth 차트**: 200MA 위 종목 비율 추이
3. **업종별 업트렌드 비율 히트맵**: 17개 KRX 업종별 건전성
4. **KOSPI 지수 vs Breadth 오버레이**: 다이버전스 감지

## 해석 프레임워크

### 1. 시장폭 존 (Breadth Zones)

| 200MA 위 종목 비율 | 존 | 해석 | 행동 지침 |
|:-----------------:|------|------|----------|
| 70%+ | Strong Bull | 건전한 강세장, 광범위 참여 | 적극 매수, 추세 추종 |
| 50-70% | Normal | 정상적 참여, 건강한 시장 | 정상 운영 |
| 30-50% | Weak | 참여 약화, 시장 체력 저하 | 신규 매수 축소, 손절 강화 |
| < 30% | Bear | 약세장 또는 조정 국면 | 방어적 포지셔닝 |

### 2. 다이버전스 패턴

#### 약세 다이버전스 (Bearish Divergence) — 천장 경고
```
KOSPI:   ──────/\────/\──   ← 고점 갱신 (Higher High)
Breadth: ──/\──────/\────   ← 고점 하향 (Lower High)

해석: 지수는 오르지만 참여 종목 감소 → 천장 임박 가능
행동: 이익실현 시작, 신규 진입 중단
```

#### 강세 다이버전스 (Bullish Divergence) — 바닥 시그널
```
KOSPI:   ──\/────\/──────   ← 저점 갱신 (Lower Low)
Breadth: ────\/──\/──────   ← 저점 상향 (Higher Low)

해석: 지수는 내리지만 참여 종목 증가 → 바닥 형성 가능
행동: 관심 종목 준비, FTD 대기
```

### 3. 크로스오버 시그널

| 시그널 | 조건 | 해석 |
|--------|------|------|
| 골든크로스 | Breadth 50MA > 200MA | 시장폭 장기 개선 → 강세 전환 |
| 데드크로스 | Breadth 50MA < 200MA | 시장폭 장기 악화 → 약세 전환 |
| 50% 돌파 | Breadth가 50% 상향 돌파 | 다수 종목 상승 추세 → 매수 유리 |
| 50% 이탈 | Breadth가 50% 하향 이탈 | 과반 종목 하락 → 방어 전환 |

### 4. 업종별 히트맵 해석

kr-uptrend-analyzer의 업종별 업트렌드 비율을 히트맵으로 시각화:

| 히트맵 패턴 | 해석 |
|-----------|------|
| 전체 녹색 (70%+) | 광범위 강세, 건강한 시장 |
| 성장 섹터만 녹색 | 성장주 주도 장세, 선별적 |
| 방어 섹터만 녹색 | 위험 회피, 방어적 로테이션 |
| 전체 적색 (< 30%) | 광범위 약세, 현금 보유 |
| 일부 섹터만 녹색 | 테마/섹터 장세, 선별 매수 |

### 4대 업종 그룹:
- **경기민감**: 자동차, 철강, 건설, 유통
- **방어**: 통신, 음식료, 의약품, 전기가스
- **성장**: 전기전자, 서비스업(IT), 반도체 관련
- **금융**: 은행, 증권, 보험

## kr-market-breadth JSON 연동

Phase 2에서 구현한 kr-market-breadth의 JSON 출력을 참조:

```json
{
  "analysis_date": "2026-02-28",
  "market": "KOSPI",
  "breadth_ratio": 52.3,
  "composite_score": 65.0,
  "zone": "Normal",
  "components": {
    "breadth_level": {"score": 60, "raw": 52.3},
    "crossover": {"score": 70, "raw": "golden_cross"},
    "cycle": {"score": 55, "raw": "rising"},
    "bearish": {"score": 80, "raw": 0},
    "percentile": {"score": 45, "raw": 45.0},
    "divergence": {"score": 65, "raw": "none"}
  },
  "warnings": []
}
```

### 핵심 확인 포인트:
1. `breadth_ratio` → 현재 시장폭 존 확인
2. `composite_score` → 종합 건전성 (0-100)
3. `zone` → 현재 상태 (Strong Bull / Normal / Weak / Bear)
4. `components.divergence` → 다이버전스 여부
5. `warnings` → 경고 시그널 (late_cycle, high_spread, divergence)

## kr-uptrend-analyzer JSON 연동

```json
{
  "analysis_date": "2026-02-28",
  "overall_uptrend_ratio": 48.5,
  "composite_score": 55.0,
  "zone": "Neutral",
  "group_averages": {
    "cyclical": 42.0,
    "defensive": 58.0,
    "growth": 45.0,
    "financial": 55.0
  },
  "warnings": ["high_spread"]
}
```

### 핵심 확인 포인트:
1. `overall_uptrend_ratio` → 전체 업트렌드 비율
2. `group_averages` → 4대 그룹별 건전성 비교
3. **방어 > 성장** 패턴 → 방어적 로테이션 경고
4. `warnings` → 경고 시그널

## Phase 3 스킬과의 연계

| Phase 3 스킬 | 시장폭 차트 활용 |
|-------------|---------------|
| kr-market-top-detector | 약세 다이버전스 → Component 4 (Breadth Divergence) |
| kr-ftd-detector | 시장폭 개선 → Component 4 (Breadth Confirmation) |
| kr-bubble-detector | 시장폭 이상 → Indicator 4 (Breadth Anomaly) |

## 차트 분석 워크플로우

```
1. kr-market-breadth JSON 최신 결과 확인
   → breadth_ratio, zone, warnings 체크

2. KOSPI Breadth 차트 확인
   → 현재 존 + 추세 방향 (상승/하락/횡보)

3. KOSPI 지수 vs Breadth 오버레이
   → 다이버전스 존재 여부 판단

4. 업종별 히트맵 확인
   → 로테이션 패턴 (성장→방어 or 방어→성장)

5. 종합 판단
   → Phase 3 스킬 결과와 종합하여 시장 포지셔닝
```
