# Claude Code 작업 지침서 — Korean Stock Skills

> **이 문서는 개발 프로세스 지침서입니다.**
> 스킬 실행 시 동작(데이터 소스, 분석 방법, 리포트 출력)은 각 SKILL.md와
> `_kr_common/templates/report_rules.md`를 따릅니다.

## 필수 규칙

### 1. Git Commit & Push (필수)

스킬 파일(SKILL.md, scripts/, references/, tests/) 또는 프로젝트 설정(install.sh, README.md, .pdca-status.json)을 수정한 경우:

1. 수정 완료 후 반드시 `git add` → `git commit` → `git push origin main` 실행
2. `~/.claude/skills/`에도 변경된 SKILL.md 동기화
3. 커밋 메시지에 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` 포함

### 2. 스킬 수 동기화

새 스킬 추가/삭제 시 아래 3곳의 숫자를 일치시킨다:
- `README.md` 헤더 ("N개 전문 스킬")
- `README.md` Skills Reference 섹션 ("Skills Reference (N개)")
- `install.sh` ("N skills for KOSPI/KOSDAQ analysis")

### 2-1. README.md 동기화 (필수)

스킬 추가/수정 또는 프로젝트 설정 변경 시 `README.md`도 함께 업데이트한다:

| 변경 사항 | README.md 업데이트 대상 |
|-----------|----------------------|
| 새 스킬 추가/삭제 | 스킬 수, Skills Reference 섹션에 스킬 설명 추가/제거 |
| `_kr_common/` 공통 모듈 변경 (프로바이더 추가 등) | Tier 구조 설명, 설치 의존성(`pip install` 목록) |
| 데이터 소스 변경 (API 추가/제거) | Tier 구조 배지, Environment Variables 섹션 |
| `install.sh` 변경 | Installation 섹션 |
| 새 SKILL.md에 사용법 추가 | Skills Reference에 `/스킬명` 예시 추가 |

> **원칙**: `README.md`는 외부 사용자가 보는 문서이므로, 내부 변경이 사용자에게 영향을 주는 경우(설치 방법, 의존성, 사용 가능한 스킬, 데이터 소스 등) 반드시 반영한다.

### 3. 새 스킬 작성 규칙

새 스킬의 SKILL.md에는 아래 섹션을 반드시 포함한다:

| 필수 섹션 | 설명 | 참고 템플릿 |
|----------|------|-----------|
| 데이터 소스 우선순위 | 해당 스킬이 사용하는 데이터 소스와 폴백 순서 | 기존 SKILL.md 참고 |
| Output Rule | 리포트 저장 경로, 형식 | `_kr_common/templates/report_rules.md` |
| US 통화정책 오버레이 | 해당 시 스킬 자체에 절차 포함 | 기존 12개 스킬 SKILL.md 참고 |

- **리포트 템플릿**: `_kr_common/templates/` 에서 관리
  - `report_rules.md` — 공통 포맷팅 규칙 + 이메일 발송
  - `report_stock.md` — 개별 종목 분석 (Type A)
  - `report_screener.md` — 스크리닝 (Type B)
  - `report_macro.md` — 매크로/전략 (Type C)
- 템플릿 수정 시 `install.sh` 실행 필수 (`_kr_common/` 변경이므로)

### 4. 스킬 설치 동기화 (Deploy)

스킬 파일(SKILL.md, scripts/, references/, tests/) **또는 공통 모듈(`_kr_common/`)** 변경 시 **반드시** 아래 절차를 수행한다:

#### 4-1. 동기화 대상 범위
| 변경 대상 | 동기화 방법 | 비고 |
|-----------|-----------|------|
| 개별 스킬 (SKILL.md, scripts/) | `cp -r` 또는 `install.sh` | 해당 스킬만 |
| **`_kr_common/` (kr_client.py, providers/, utils/, config.py, templates/)** | **반드시 `install.sh` 실행** | **전 스킬이 참조하는 공통 모듈** |
| install.sh, README.md | 해당 없음 (소스 직접 참조) | |

#### 4-2. 개별 스킬 동기화 (`~/.claude/skills/`)
```bash
# 변경된 스킬만 동기화
cp -r skills/{skill_name}/ ~/.claude/skills/{skill_name}/

# 여러 스킬 변경 시
for s in {skill_1} {skill_2} {skill_3}; do
  cp -r skills/$s/ ~/.claude/skills/$s/
done
```

#### 4-3. 전체 재설치 (공통 모듈 변경 시 필수)
```bash
./install.sh
```

#### 4-4. 동기화 검증
```bash
diff <(cat skills/{skill_name}/SKILL.md) <(cat ~/.claude/skills/{skill_name}/SKILL.md)
```

### 5. 테스트

스크립트 수정 시 해당 스킬의 테스트를 실행하여 기존 테스트가 깨지지 않았는지 확인한다:
```bash
cd skills/{skill_name}/scripts && python -m pytest tests/ -v
```

---

## 프로젝트 구조

| 디렉토리 | 용도 |
|---------|------|
| `skills/kr-*/`, `skills/us-*/`, `skills/daily-*/` | 개별 스킬 |
| `skills/_kr_common/` | 공통 모듈 (providers, utils, templates) |
| `docs/01-plan/` ~ `docs/04-report/` | PDCA 문서 |
| `docs/archive/YYYY-MM/` | 아카이브 |
| `reports/` | 리포트 출력 (.gitignore 대상) |
| `.pdca-status.json` | PDCA 상태 |

## 현재 상태

- 총 54개 스킬 (Phase 1-9 + 9 Patch + 2 Filter)
- 누적 2,039+ 테스트

---

## 개발자 참고 (Reference)

> 아래는 개발 시 참고용 정보입니다. 스킬 실행 시 동작은 각 SKILL.md를 따릅니다.

### 가용 데이터 소스 (2026-03-07 기준)

| Tier | 소스 | 제공 데이터 | 상태 |
|:----:|------|-----------|------|
| 0 | KRX Open API | OHLCV, 시총, 지수 | 전 서비스 승인 완료 |
| 1 | yfinance | PER/PBR/재무제표/밸류에이션 | 무료, 무제한 |
| 2 | KRClient (pykrx/FDR) | 투자자별 매매, 공매도 등 | KRX 차단 시 불가 |
| 3 | KIS Open API | 실시간 시세, 주문 | 계좌 기반 |
| 4 | WebSearch | 모든 데이터 (폴백) | 항상 가용 |

- KRX API 미제공: PER/PBR, 투자자별 매매동향 → yfinance(Tier 1)로 보완
- 프로바이더: `_kr_common/providers/krx_openapi_provider.py`, `yfinance_provider.py`

### US 통화정책 오버레이 적용 스킬 (12개)

아래 스킬은 SKILL.md에 US 통화정책 오버레이 절차가 포함되어 있음:

- 스코어링: kr-stock-analysis, kr-sector-analyst, kr-growth-outlook, kr-portfolio-manager, kr-strategy-synthesizer
- 컨텍스트: kr-macro-regime, kr-market-environment, kr-market-breadth, kr-scenario-analyzer, kr-earnings-trade, kr-economic-calendar, kr-weekly-strategy
