# Claude Code 작업 지침서 — Korean Stock Skills

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

### 3. Output Rule

모든 스킬 실행 결과는 마크다운 파일로 저장한다:
- 경로: `reports/{skill_name}_{종목코드}_{종목명}_{YYYYMMDD}.md`
- 종목 없는 분석: `reports/{skill_name}_market_{YYYYMMDD}.md`

### 4. 스킬 설치 동기화

`skills/` 하위 파일 변경 시 `~/.claude/skills/`에도 반영한다:
```bash
cp -r skills/{skill_name}/ ~/.claude/skills/{skill_name}/
```

### 5. US 통화정책 오버레이 (필수)

아래 12개 스킬 실행 시 **반드시** US 통화정책 분석을 포함한다:

**스코어링 오버레이 적용 (점수 조정)**:
- `kr-stock-analysis` — 종합 점수에 B방식 오버레이 가산
- `kr-sector-analyst` — 섹터별 민감도 반영 영향도 평가
- `kr-growth-outlook` — 금리 환경의 할인율 영향 반영
- `kr-portfolio-manager` — 자산배분에 통화정책 방향 반영
- `kr-strategy-synthesizer` — 확신도에 오버레이 가산

**컨텍스트 필수 포함 (정성 분석)**:
- `kr-macro-regime` — Fed 정책의 한국 레짐 전환 영향
- `kr-market-environment` — US 통화정책 현황 별도 섹션
- `kr-market-breadth` — 글로벌 유동성과 시장폭 관계
- `kr-scenario-analyzer` — 시나리오에 Fed 정책 경로 포함
- `kr-earnings-trade` — 통화정책 환경의 실적 모멘텀 영향
- `kr-economic-calendar` — FOMC 일정 병행 표시
- `kr-weekly-strategy` — 주간 체크리스트에 Fed 변수 추가

**공통 절차**:
1. WebSearch로 현재 Fed 금리, FOMC 기조, DXY, BOK 금리, 한미 금리차 조회
2. US Regime Score 산출 (stance×0.35 + rate×0.30 + liquidity×0.35)
3. 리포트에 US 통화정책 섹션 필수 포함

### 6. 테스트

스크립트 수정 시 해당 스킬의 테스트를 실행하여 기존 테스트가 깨지지 않았는지 확인한다:
```bash
cd skills/{skill_name}/scripts && python -m pytest tests/ -v
```

## 프로젝트 구조

- **스킬**: `skills/kr-*/`, `skills/us-*/`
- **공통 모듈**: `skills/_kr-common/`
- **PDCA 문서**: `docs/01-plan/`, `docs/02-design/`, `docs/03-analysis/`, `docs/04-report/`
- **아카이브**: `docs/archive/YYYY-MM/`
- **리포트 출력**: `reports/` (.gitignore 대상)
- **PDCA 상태**: `.pdca-status.json`

## 현재 상태

- 총 46개 스킬 (Phase 1-9 + 2 Patch)
- 누적 1,970+ 테스트
- Phase 3-9 + 2 Patch 연속 10회 97% Match Rate
