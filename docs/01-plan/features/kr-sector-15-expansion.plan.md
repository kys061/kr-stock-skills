# Plan: 한국 15개 섹터 확장 (에너지/유틸리티 → 에너지/유틸리티 + 원전)

> **Feature**: kr-sector-15-expansion
> **Date**: 2026-03-06
> **Status**: Plan

---

## 1. 배경 및 목적

### 문제
- 현재 14개 섹터에서 **원전**이 `에너지/유틸리티`에 포함되어 있음
- 두산에너빌리티, 한전기술, 한전산업 등 원전 종목은 독립 테마로 움직임
- 에너지/유틸리티(한전, 가스공사)와 원전(두산에너빌리티, KHNP)은 투자 성격이 다름
- 2026년 원전은 AI 데이터센터 전력 수요 + 탄소중립으로 독립 섹터급 투자 테마

### 변경 내용
```
기존 14개 → 15개 섹터

변경: "에너지/유틸리티" 유지 + "원전" 신규 추가

최종 15개 섹터:
 1. 반도체         2. 자동차          3. 조선/해운
 4. 철강/화학      5. 바이오/제약      6. 금융/은행
 7. 유통/소비      8. 건설/부동산      9. IT/소프트웨어
10. 통신          11. 에너지/유틸리티  12. 엔터테인먼트
13. 방산          14. 2차전지         15. 원전 (신규)
```

### 원전 섹터 정의
| 항목 | 내용 |
|------|------|
| 섹터명 | 원전 (Nuclear Power) |
| 영문 키 | `nuclear` |
| 대표 종목 | 두산에너빌리티, 한전기술, 한전산업, 한국전력(일부 중복) |
| 특징 | SMR/대형원전 수출, AI 전력 수요, 탄소중립 정책 |
| 통화정책 민감도 | 0.6 (방어적, 정책 의존형) |

---

## 2. 영향 범위 분석

### Category A: Python 코드 (KR_SECTORS 리스트 하드코딩) — 반드시 수정

| # | 파일 | 변수명 | 줄 번호 | 테스트 영향 |
|---|------|--------|:------:|------------|
| A1 | `kr-scenario-analyzer/scripts/kr_scenario_analyzer.py` | `KR_SECTORS` | 32-36 | `assert len == 14` → 15 |
| A2 | `kr-weekly-strategy/scripts/sector_strategy.py` | `KR_SECTORS` | 6-11 | `assert len == 14` → 15 |
| A3 | `kr-supply-demand-analyzer/scripts/sector_flow_mapper.py` | `KR_SECTORS` | 5-10 | `assert len == 14` → 15 |
| A4 | `kr-portfolio-manager/scripts/portfolio_analyzer.py` | `KRX_SECTORS` | 63-67 | 테스트 미확인 |
| A5 | `kr-stock-analysis/scripts/comprehensive_scorer.py` | `_SECTOR_SENSITIVITY` | 156-171 | `nuclear: 0.6` 추가 |
| A6 | `kr-stock-analysis/scripts/growth_quick_scorer.py` | `SECTOR_TAM_CAGR` + `POLICY_TAILWIND` | 59-77 | `nuclear` 항목 추가 |

### Category B: Python 테스트 (assert len == 14) — 반드시 수정

| # | 파일 | 줄 번호 | 변경 |
|---|------|:------:|------|
| B1 | `kr-weekly-strategy/scripts/tests/test_weekly_strategy.py` | 52-59 | `== 14` → `== 15` |
| B2 | `kr-scenario-analyzer/scripts/tests/test_scenario_analyzer.py` | 35-36 | `== 14` → `== 15` |
| B3 | `kr-supply-demand-analyzer/scripts/tests/test_supply_demand.py` | 79-85 | `== 14` → `== 15` |

### Category C: Markdown 참조 문서 — 수정 필요

| # | 파일 | 내용 |
|---|------|------|
| C1 | `kr-weekly-strategy/references/kr_sector_list.md` | 14개 섹터 테이블 → 15개로 확장 |
| C2 | `kr-scenario-analyzer/references/kr_sector_sensitivity.md` | 원전 이벤트 민감도 추가 |

### Category D: SKILL.md — 수정 필요

| # | 파일 | 변경 내용 |
|---|------|----------|
| D1 | `kr-weekly-strategy/SKILL.md` | "14개 섹터" → "15개 섹터", 원전 추가 |
| D2 | `kr-sector-analyst/SKILL.md` | 섹터 목록에 원전 추가 |
| D3 | `kr-stock-analysis/SKILL.md` | 섹터 민감도 테이블에 nuclear 0.6 추가 |
| D4 | `kr-supply-demand-analyzer/SKILL.md` | 섹터 목록 업데이트 |
| D5 | `kr-scenario-analyzer/SKILL.md` | 섹터 목록 업데이트 |
| D6 | `kr-theme-detector/SKILL.md` | 테마 목록에 원전 포함 확인 |

### Category E: 프로젝트 설정

| # | 파일 | 변경 |
|---|------|------|
| E1 | `README.md` | "14개 섹터" → "15개 섹터" 일괄 치환 |
| E2 | `CLAUDE.md` | 해당 없음 (섹터 수 미기재) |

### Category F: 영향 없음 (변경 불필요)

아래 스킬은 섹터를 "텍스트로 언급"하지만 하드코딩된 리스트가 없음:
- kr-market-news-analyst, kr-market-top-detector, kr-macro-regime
- kr-edge-concept, kr-breadth-chart, kr-pair-trade
- kr-stock-screener, kr-uptrend-analyzer, kr-growth-outlook

---

## 3. 실행 계획

### Step 1: Python 코드 수정 (Category A, 6개 파일)
- 4개 파일의 `KR_SECTORS`/`KRX_SECTORS` 리스트에 `'원전'` 추가
- `comprehensive_scorer.py`의 `_SECTOR_SENSITIVITY`에 `'nuclear': 0.6` 추가
- `growth_quick_scorer.py`에 `nuclear` TAM/정책 항목 추가

### Step 2: 테스트 수정 (Category B, 3개 파일)
- `assert len(KR_SECTORS) == 14` → `== 15`

### Step 3: 참조 문서 수정 (Category C, 2개 파일)
- `kr_sector_list.md`: 15번 원전 행 추가
- `kr_sector_sensitivity.md`: 원전 이벤트 민감도 추가

### Step 4: SKILL.md 수정 (Category D, 6개 파일)
- 섹터 목록/테이블에 원전 추가
- "14" 숫자 → "15" 변경

### Step 5: README.md 수정 (Category E)
- "14개 섹터" → "15개 섹터"

### Step 6: 테스트 실행
```bash
cd skills/kr-weekly-strategy/scripts && python -m pytest tests/ -v
cd skills/kr-scenario-analyzer/scripts && python -m pytest tests/ -v
cd skills/kr-supply-demand-analyzer/scripts && python -m pytest tests/ -v
```

### Step 7: 배포 및 커밋
```bash
./install.sh
git add -A && git commit && git push
```

---

## 4. 원전 섹터 상세 정의

### 4.1 대표 종목

| 종목 | 코드 | 시총 | 특징 |
|------|------|------|------|
| 두산에너빌리티 | 034020 | ~12조 | 원전 EPC, SMR 수출 |
| 한전기술 | 052690 | ~2조 | 원전 설계, NSSS |
| 한전산업 | 130660 | ~5천억 | 원전 정비, O&M |
| 비에이치아이 | 083650 | ~3천억 | 보일러, 원전 기자재 |

### 4.2 통화정책 민감도 근거
- **0.6** (중간-방어적): 정부 정책/규제 의존형 → 금리보다 에너지 정책이 핵심 드라이버
- 장기 계약 기반으로 금리 변동에 덜 민감
- 다만 대형 CAPEX 프로젝트 특성상 완전 무관하지 않음

### 4.3 Growth Quick 파라미터

| 항목 | 값 | 근거 |
|------|------|------|
| TAM CAGR | 8% | 글로벌 원전 시장 CAGR 7-9% |
| 정책 순풍 | `strong_tailwind` | 탄소중립, AI 전력 수요, SMR 지원 |

---

## 5. 체크리스트

- [ ] KR_SECTORS 4개 파일에 '원전' 추가
- [ ] _SECTOR_SENSITIVITY에 'nuclear': 0.6 추가
- [ ] growth_quick_scorer에 nuclear TAM/정책 추가
- [ ] 테스트 3개 파일 assert 14 → 15
- [ ] kr_sector_list.md 15번 원전 행 추가
- [ ] kr_sector_sensitivity.md 원전 추가
- [ ] SKILL.md 6개 파일 업데이트
- [ ] README.md "14개 섹터" → "15개 섹터"
- [ ] 테스트 통과 확인
- [ ] install.sh 실행
- [ ] 커밋/푸시
