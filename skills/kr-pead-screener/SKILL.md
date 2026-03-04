---
name: kr-pead-screener
description: 실적 발표 후 갭업 종목의 주봉 캔들 패턴(Red Candle Pullback→Breakout) 분석. Post-Earnings Announcement Drift 패턴 탐지.
---

# kr-pead-screener: 한국 실적 드리프트 스크리닝 (PEAD)

> Post-Earnings Announcement Drift: 실적 발표 후 갭업 종목의 주봉 캔들 패턴 분석.
> 적색 캔들 형성 후 브레이크아웃 타이밍으로 진입.
> US pead-screener의 한국 적용 버전.

## 사용 시점

- 실적 서프라이즈 후 갭업한 종목의 후속 패턴을 분석할 때
- DART 정기보고서 공시 후 실적 드리프트 패턴 발견
- 한국 실적 시즌 (잠정실적/확정실적 2단계) 활용

## 방법론

### 4-Stage 분류

| Stage | 정의 | 액션 |
|-------|------|------|
| MONITORING | 실적 갭업, 아직 적색 캔들 없음 | 관찰, 주간 체크 |
| SIGNAL_READY | 적색 주봉 캔들 형성 | 적색 캔들 고가에 알림 |
| BREAKOUT | 녹색 캔들 + 적색 고가 돌파 | 진입 (스탑: 적색 저가) |
| EXPIRED | 5주 초과 | 리스트 제거 |

### 스코어링 (0-100)

| 컴포넌트 | 가중치 | 설명 |
|---------|:------:|------|
| Gap Size | 30% | 갭 크기 |
| Pattern Quality | 25% | 적색 캔들 + 거래량 감소 |
| Earnings Surprise | 25% | 실적 서프라이즈 크기 |
| Risk/Reward | 20% | 진입가 vs 스탑 vs 목표가 |

## 한국 실적 시즌

| 시기 | 보고서 | DART 공시 |
|------|--------|----------|
| 1-2월 | 4Q 잠정 | 주요사항보고서 |
| 3월 | 4Q 확정 | 사업보고서 |
| 5월 | 1Q | 분기보고서 |
| 8월 | 2Q | 반기보고서 |
| 11월 | 3Q | 분기보고서 |

## 실행 방법

```bash
cd ~/stock/skills/kr-pead-screener/scripts
python kr_pead_screener.py --output-dir ./output
python kr_pead_screener.py --days 30 --output-dir ./output
```

## 관련 스킬

| 스킬 | 관계 |
|------|------|
| kr-canslim-screener | C 컴포넌트 (분기 실적) 상호 참조 |
| kr-stock-screener | 다조건 필터 도구 |
