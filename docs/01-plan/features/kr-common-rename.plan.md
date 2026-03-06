# Plan: `_kr-common` → `_kr_common` 디렉토리 리네임

> **Feature**: kr-common-rename
> **Date**: 2026-03-06
> **Status**: Plan

---

## 1. 배경 및 목적

### 문제
- 디렉토리명 `_kr-common` (하이픈)은 Python 모듈명으로 유효하지 않음
- Python import는 `from _kr_common import ...` (언더스코어) 사용
- 현재 심링크 `_kr_common → _kr-common`으로 우회 중
- 순환 심링크 `_kr-common/_kr-common → _kr-common` 버그 존재

### 목표
- 디렉토리명을 `_kr_common`으로 통일하여 심링크 의존 제거
- Python 네이밍 컨벤션 준수 (PEP 8: 모듈명은 소문자 + 언더스코어)

---

## 2. 영향 범위 분석

### Category A: 실행 코드 (에러 발생 가능 — 반드시 수정)

| # | 파일 | 변경 내용 | 위험도 |
|---|------|----------|--------|
| A1 | `install.sh:84-85` | 심링크 생성 로직 제거 | HIGH |
| A2 | `skills/_kr-common/tests/test_kr_client.py:11` | `sys.path` 경로 `_kr-common` → `_kr_common` | HIGH |
| A3 | `skills/kr-stock-analysis/SKILL.md:157-158` | 템플릿 경로 `_kr-common/templates/` → `_kr_common/templates/` | MED |

### Category B: 프로젝트 설정/문서 (동작에 직접 영향 — 수정 필요)

| # | 파일 | 참조 수 | 설명 |
|---|------|:------:|------|
| B1 | `CLAUDE.md` | 12 | 공통 모듈 경로, diff 명령어, 동기화 안내 |
| B2 | `README.md` | 3 | 디렉토리 트리, 설명 |

### Category C: PDCA 문서 (과거 기록 — 선택적 수정)

| # | 파일 | 참조 수 | 판단 |
|---|------|:------:|------|
| C1 | `docs/01-plan/features/kr-stock-skills*.md` | 5 | 역사 문서, 수정 불필요 |
| C2 | `docs/02-design/features/kr-stock-skills-phase*.md` | 8 | 역사 문서, 수정 불필요 |
| C3 | `docs/03-analysis/kr-stock-skills-phase1.analysis.md` | 2 | 역사 문서, 수정 불필요 |
| C4 | `docs/04-report/features/kr-stock-skills-phase*.md` | 12 | 역사 문서, 수정 불필요 |
| C5 | `docs/04-report/changelog.md` | 1 | 역사 문서, 수정 불필요 |
| C6 | `docs/04-report/PHASE8_INTEGRATION_MAP.md` | 6 | 역사 문서, 수정 불필요 |

### Category D: Worktree 복사본 (.claude/worktrees/)

- **untracked** 디렉토리, git 추적 대상 아님
- 자동 정리 또는 무시

### Category E: Python import (변경 불필요)

- 모든 Python 코드가 이미 `from _kr_common import ...` 사용
- 디렉토리명이 `_kr_common`이 되면 심링크 없이 바로 동작
- **변경 0건**

---

## 3. 실행 계획

### Step 1: 심링크 정리
```bash
rm skills/_kr_common                    # 기존 심링크 제거
rm skills/_kr-common/_kr-common         # 순환 심링크 제거
```

### Step 2: 디렉토리 리네임
```bash
git mv skills/_kr-common skills/_kr_common
```

### Step 3: 실행 코드 수정 (Category A)
- `install.sh`: 심링크 생성 로직 제거
- `skills/_kr_common/tests/test_kr_client.py`: sys.path 경로 수정
- `skills/kr-stock-analysis/SKILL.md`: 템플릿 경로 수정

### Step 4: 프로젝트 설정 수정 (Category B)
- `CLAUDE.md`: 전체 `_kr-common` → `_kr_common` 치환
- `README.md`: 전체 `_kr-common` → `_kr_common` 치환

### Step 5: 배포 및 검증
```bash
./install.sh                            # 재배포
python3 -c "from _kr_common.kr_client import KRClient; print('OK')"
```

### Step 6: 커밋/푸시

---

## 4. 수정하지 않는 항목 (Category C)

PDCA 과거 문서(plan, design, analysis, report)는 **작성 시점의 실제 상태를 기록한 역사 문서**이므로 수정하지 않는다.
해당 문서에서 `_kr-common`은 "당시에는 그 이름이었다"는 사실의 기록이다.

---

## 5. 리스크 및 대응

| 리스크 | 확률 | 대응 |
|--------|:----:|------|
| `~/.claude/skills/`에 구 `_kr-common` 잔존 | 높음 | install.sh에서 구 디렉토리 삭제 로직 추가 |
| worktree에서 구 경로 참조 | 낮음 | worktree는 필요시 재생성 |
| 다른 사용자가 clone 후 구버전 install.sh 실행 | 낮음 | install.sh에 하위호환 처리 |

---

## 6. 체크리스트

- [ ] 심링크 2개 제거
- [ ] git mv 실행
- [ ] install.sh 수정 (심링크 제거 + 구 디렉토리 정리)
- [ ] test_kr_client.py sys.path 수정
- [ ] kr-stock-analysis/SKILL.md 경로 수정
- [ ] CLAUDE.md 경로 치환
- [ ] README.md 경로 치환
- [ ] install.sh 재실행
- [ ] import 테스트
- [ ] 커밋/푸시
