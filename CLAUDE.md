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

### 5. 테스트

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
