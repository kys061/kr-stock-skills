# Phase 8 통합 맵 (Integration Architecture)

**목적**: Phase 8 메타 스킬이 Phase 1-7의 모든 업스트림 스킬을 어떻게 통합하는지 시각화

---

## 1. 스킬 통합 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: 공통 모듈 (_kr-common)          │
│              (KRClient, DARTProvider, MarketUtils)          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
        ┌─────────────────┐   ┌──────────────────┐
        │  Phase 2: 시장  │   │  Phase 3: 마켓  │
        │  분석 스킬 (7개)│   │  타이밍 (5개)   │
        │ - 시장 환경    │   │ - 천장 탐지     │
        │ - 뉴스 분석    │   │ - FTD 상태      │
        │ - 시장 폭      │   │ - 버블 탐지     │
        │ - 업트렌드     │   │ - 레짐 분류     │
        │ - 섹터 분석    │   │ - 폭 차트       │
        │ - 테마 탐지    │   └──────────────────┘
        │ - 기술 분석    │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
    ┌─────────────────┐  ┌──────────────────┐
    │  Phase 4: 종목 │  │  Phase 5: 캘린 │
    │  스크리닝 (7개)│  │  더/실적 (4개)  │
    │ - CANSLIM     │  │ - 경제 캘린더   │
    │ - VCP         │  │ - 실적 캘린더   │
    │ - Value-Div   │  │ - 실적 트레이드 │
    │ - Dividend    │  │ - 기관 수급     │
    │ - Pair Trade  │  └──────────────────┘
    │ - PEAD        │
    │ - Screener    │
    └────────┬────────┘
             │
        ┌────┴──────────────────────┐
        ▼                           ▼
    ┌──────────────────┐    ┌──────────────────┐
    │  Phase 6: 전략  │    │  Phase 7: 배당  │
    │  & 리스크 (9개) │    │  & 세제 (3개)   │
    │ - Backtest     │    │ - Dividend SOP  │
    │ - Options      │    │ - Dividend Mon  │
    │ - Portfolio    │    │ - Tax Optimizer │
    │ - Scenario     │    └──────────────────┘
    │ - Edge (4개)   │
    │ - Strategy     │
    └────────┬────────┘
             │
        ┌────┴────────────────────────┐
        ▼                             ▼
    ┌──────────────────────────────────────────────┐
    │  Phase 8: 메타 & 유틸리티 (4개) ◄── 통합   │
    │                                              │
    │  ┌─────────────────────────────────────┐    │
    │  │ kr-stock-analysis                   │    │
    │  │ (개별 종목 종합 분석)                 │    │
    │  │ ├─ 펀더멘털 (DART)                 │    │
    │  │ ├─ 기술적 (PyKRX OHLCV)            │    │
    │  │ ├─ 수급 (Phase 5 kr-institutional)│    │
    │  │ └─ 종합 점수 (0-100)              │    │
    │  └─────────────────────────────────────┘    │
    │                                              │
    │  ┌─────────────────────────────────────┐    │
    │  │ kr-strategy-synthesizer             │    │
    │  │ (전략 통합 & 확신도)                  │    │
    │  │ ├─ market_structure  ◄─ Phase 2    │    │
    │  │ ├─ distribution_risk ◄─ Phase 3    │    │
    │  │ ├─ bottom_confirm    ◄─ Phase 3    │    │
    │  │ ├─ macro_alignment   ◄─ Phase 3    │    │
    │  │ ├─ theme_quality     ◄─ Phase 2    │    │
    │  │ ├─ setup_avail       ◄─ Phase 4    │    │
    │  │ ├─ signal_converge   ◄─ All phases │    │
    │  │ └─ 확신도 + 패턴 분류 (0-100)      │    │
    │  └─────────────────────────────────────┘    │
    │                                              │
    │  ┌─────────────────────────────────────┐    │
    │  │ kr-skill-reviewer                   │    │
    │  │ (메타 스킬 품질 리뷰)                 │    │
    │  │ ├─ Auto Axis (5 체크)              │    │
    │  │ ├─ LLM Axis (깊이 리뷰)            │    │
    │  │ └─ 품질 등급 (0-100)               │    │
    │  └─────────────────────────────────────┘    │
    │                                              │
    │  ┌─────────────────────────────────────┐    │
    │  │ kr-weekly-strategy                  │    │
    │  │ (주간 전략 워크플로우)                 │    │
    │  │ ├─ 시장 환경 분석 ◄─ Phase 2,3    │    │
    │  │ ├─ 섹터 전략 ◄─ Phase 2            │    │
    │  │ ├─ 리스크 관리 ◄─ Phase 6           │    │
    │  │ └─ 운용 가이드                     │    │
    │  └─────────────────────────────────────┘    │
    │                                              │
    │  Phase 8 = Phase 1-7 모든 스킬의 "최종 통합" │
    │  유즈 케이스: 종목 분석, 주간 전략 수립     │
    └──────────────────────────────────────────────┘
             │
             └─► Phase 9: 한국 전용 신규 스킬 (5개)
```

---

## 2. kr-strategy-synthesizer의 7 컴포넌트 통합

```
kr-strategy-synthesizer 확신도 계산

┌─────────────────────────────────────────────────────────┐
│                 7 컴포넌트 확신도 (가중합)                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ [market_structure]         (가중치: 0.18)              │
│   ├─ kr-market-breadth (Phase 2) → 시장 폭            │
│   └─ kr-uptrend-analyzer (Phase 2) → 업트렌드 비율     │
│                                                         │
│ [distribution_risk]        (가중치: 0.18)              │
│   └─ kr-market-top-detector (Phase 3) → 천장 리스크   │
│                                                         │
│ [bottom_confirmation]      (가중치: 0.12)              │
│   └─ kr-ftd-detector (Phase 3) → FTD 확인            │
│                                                         │
│ [macro_alignment]          (가중치: 0.18)              │
│   └─ kr-macro-regime (Phase 3) → 레짐 분류           │
│                                                         │
│ [theme_quality]            (가중치: 0.12)              │
│   └─ kr-theme-detector (Phase 2) → 테마 모멘텀       │
│                                                         │
│ [setup_availability]       (가중치: 0.10)              │
│   ├─ kr-vcp-screener (Phase 4) → VCP 셋업            │
│   └─ kr-canslim-screener (Phase 4) → CANSLIM 셋업   │
│                                                         │
│ [signal_convergence]       (가중치: 0.12)              │
│   └─ ALL 6 skills → 신호 수렴도                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  최종 확신도 (0-100) + 4 패턴 분류                      │
│  → 자산 배분 추천 (equity%, cash%)                      │
└─────────────────────────────────────────────────────────┘
```

---

## 3. kr-stock-analysis의 멀티 소스 데이터 흐름

```
kr-stock-analysis 종합 분석

개별 종목 입력
    │
    ├──► [펀더멘털 분석]
    │    ├─ DART API (Phase 1 _kr-common)
    │    │  └─ 재무제표 (BS, IS, CF)
    │    └─ PyKRX (Phase 1 _kr-common)
    │       └─ PER, PBR, EPS, DIV, BPS
    │       └─ 시가총액, 상장주식수
    │
    ├──► [기술적 분석]
    │    └─ PyKRX OHLCV (Phase 1 _kr-common)
    │       ├─ MA (20, 60, 120)
    │       ├─ RSI (14)
    │       ├─ MACD (12, 26, 9)
    │       ├─ Bollinger Bands (20, 2)
    │       └─ Volume Analysis
    │
    ├──► [수급 분석] ◄──────────── (KR 고유!)
    │    └─ Phase 5 kr-institutional-flow
    │       └─ PyKRX 투자자별 매매동향
    │          ├─ 외국인
    │          ├─ 기관
    │          └─ 개인
    │
    └──► [종합 스코어]
         └─ 4 컴포넌트 가중치
            ├─ 펀더멘털 (0.35)
            ├─ 기술적 (0.25)
            ├─ 수급 (0.25)
            └─ 밸류에이션 (0.15)

         → STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
         → 종합 점수 (0-100)
```

---

## 4. kr-weekly-strategy의 입력 소스

```
kr-weekly-strategy 주간 전략

주간 시작
    │
    ├──► [시장 환경 분석]
    │    ├─ Phase 2: kr-market-environment
    │    │  └─ KOSPI, KOSDAQ 추세
    │    ├─ Phase 3: kr-macro-regime
    │    │  └─ 거시 레짐
    │    └─ PyKRX + DART
    │       └─ 외국인, 기관 수급
    │
    ├──► [섹터 전략]
    │    └─ Phase 2: kr-sector-analyst
    │       └─ 14개 한국 섹터별 점수
    │       └─ 로테이션 제약 (±15%)
    │
    ├──► [시나리오 계획]
    │    ├─ Base 시나리오
    │    ├─ Bull 시나리오
    │    └─ Bear 시나리오
    │
    └──► [리스크 관리]
         └─ Phase 6: kr-portfolio-manager
            └─ 현금 비중 관리
            └─ 포지션 사이징

    → 주간 전략 리포트
      ├─ 시장 요약 (3줄)
      ├─ 이번 주 액션
      ├─ 시나리오별 계획
      ├─ 섹터 배분
      ├─ 리스크 관리
      └─ 겸업 투자자 가이드
```

---

## 5. Phase 1-8 데이터 흐름 통합도

```
                    ┌─────────────────────────────────┐
                    │   마켓 데이터 소스 통합 (Phase 1) │
                    │                                 │
                    │ PyKRX + DART + FinanceDataReader│
                    └────────┬────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    ┌──────────────┐ ┌────────────┐ ┌──────────────┐
    │ 시장 데이터  │ │ 재무 데이터 │ │ 수급 데이터  │
    │ (OHLCV)      │ │ (BS/IS/CF) │ │ (투자자 분류)│
    └──────┬───────┘ └─────┬──────┘ └──────┬───────┘
           │               │               │
        Phase 2-4        Phase 2-6        Phase 5
     시장/섹터/종목      재무/배당/세    기관/외국인
     분석 스킬          제 스킬          수급 스킬
           │               │               │
           └───────┬───────┴───────┬───────┘
                   ▼               ▼
           ┌─────────────────────────────────┐
           │ Phase 8: 메타 스킬 통합          │
           │                                 │
           │ kr-stock-analysis (종목)        │
           │ kr-strategy-synthesizer (전략)  │
           │ kr-skill-reviewer (품질)        │
           │ kr-weekly-strategy (주간)       │
           └─────────────────────────────────┘
                   │
                   ▼
         ┌──────────────────────┐
         │  투자 의사 결정 지원   │
         │                      │
         │ - 종목 분석           │
         │ - 포트폴리오 구성     │
         │ - 주간 리밸런싱       │
         │ - 리스크 관리         │
         └──────────────────────┘
```

---

## 6. 컴포넌트 간 의존성 매트릭스

| Phase 8 스킬 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
|:------------:|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| **kr-stock-analysis** |  | | | ✅ | | |
| kr-strategy-synthesizer | ✅ | ✅ | ✅ | | | |
| kr-skill-reviewer | | | | | | |
| kr-weekly-strategy | ✅ | ✅ | | | ✅ | |

**범례**:
- ✅ 의존성 있음 (입력 데이터 사용)
- 빈칸 = 직접 의존성 없음

---

## 7. Phase 8 이후 Phase 9 준비

```
Phase 9: 한국 전용 신규 스킬 (5개)

┌────────────────────────────────────────┐
│ kr-supply-demand-analyzer              │
│ (수급 종합 분석 - kr-stock-analysis와 │
│  kr-strategy-synthesizer 입력으로 사용)│
│                                        │
│ kr-short-sale-tracker                  │
│ (공매도 분석 - 시장 위험 신호)         │
│                                        │
│ kr-credit-monitor                      │
│ (신용 과열 모니터링)                   │
│                                        │
│ kr-program-trade-analyzer              │
│ (프로그램 매매 분석)                   │
│                                        │
│ kr-dart-disclosure-monitor             │
│ (DART 공시 실시간 모니터링)            │
└────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ 44 스킬 완성 & 최종 통합 검증        │
│ (39 US 포팅 + 5 KR 전용)           │
└─────────────────────────────────────┘
```

---

## 8. 단일 종목 분석 워크플로우 예시

```
시스템 사용자가 삼성전자(005930)를 분석하려 할 때:

Step 1: kr-stock-analysis 호출
  └─ 입력: 종목코드 '005930'
  └─ 처리:
     ├─ Phase 1 (_kr-common) DART에서 재무제표 조회
     ├─ Phase 1 (_kr-common) PyKRX에서 OHLCV, PER/PBR 조회
     ├─ Phase 5 (kr-institutional-flow) 수급 데이터 조회
     ├─ 펀더멘털 점수 계산
     ├─ 기술적 지표 계산 (MA, RSI, MACD 등)
     ├─ 수급 신호 분석
     └─ 종합 점수 계산 (0-100)
  └─ 출력: {score: 75, grade: "BUY", recommendation: "매수"}

Step 2: kr-strategy-synthesizer 호출 (선택)
  └─ 입력: kr-stock-analysis 결과 + Phase 2-4 스킬 결과
  └─ 처리: 7 컴포넌트 확신도 계산
  └─ 출력: {conviction: 65, zone: "HIGH", allocation: {equity: 70%, cash: 30%}}

Step 3: kr-skill-reviewer 호출 (리뷰)
  └─ 입력: kr-stock-analysis 품질 검증
  └─ 출력: {score: 85, grade: "USABLE"}

Step 4: 주간 계획에 kr-weekly-strategy 포함
  └─ 삼성전자의 기술/수급 신호를 반도체 섹터 전략에 반영
```

---

## 9. 파일 및 경로 맵핑

| Phase 8 컴포넌트 | 위치 | 종속 파일 |
|:---------------:|------|----------|
| **kr-stock-analysis** | `skills/kr-stock-analysis/` | DART (Phase 1), PyKRX (Phase 1), kr-institutional-flow (Phase 5) |
| **kr-strategy-synthesizer** | `skills/kr-strategy-synthesizer/` | kr-market-breadth (P2), kr-uptrend-analyzer (P2), kr-market-top-detector (P3), kr-ftd-detector (P3), kr-macro-regime (P3), kr-theme-detector (P2), kr-vcp-screener (P4), kr-canslim-screener (P4) |
| **kr-skill-reviewer** | `skills/kr-skill-reviewer/` | 모든 KR 스킬 |
| **kr-weekly-strategy** | `skills/kr-weekly-strategy/` | kr-market-environment (P2), kr-sector-analyst (P2), kr-macro-regime (P3), kr-portfolio-manager (P6) |

---

## 결론

**Phase 8은 Phase 1-7을 통해 구축된 32개 스킬의 최종 통합 포인트이다.**

- **kr-stock-analysis**: 개별 종목을 PyKRX+DART+수급 데이터로 분석
- **kr-strategy-synthesizer**: 6개 스킬의 신호를 통합하여 확신도 계산
- **kr-skill-reviewer**: 모든 스킬의 품질을 메타적으로 검증
- **kr-weekly-strategy**: 주간 투자 전략 수립을 위한 통합 워크플로우

이들이 없으면 개별 스킬들이 검증되지 않고, 종합 분석과 주간 계획 수립이 어렵다.

**Phase 9에서는 5개 한국 전용 스킬을 추가하여 44개 스킬 완성을 목표로 한다.**

---

**버전**: 1.0
**작성일**: 2026-03-04
**검토**: Phase 8 완료 후
