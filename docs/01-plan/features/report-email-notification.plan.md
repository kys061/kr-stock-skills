# Plan: 리포트 이메일 발송 기능

> **Feature**: report-email-notification
> **Phase**: Plan
> **Created**: 2026-03-07
> **Status**: Draft

---

## 1. 개요

### 1.1 목표
리포트 MD 파일을 생성하는 모든 스킬이 파일 생성 완료 후 지정된 이메일 주소로 리포트를 자동 발송하는 기능을 추가한다.

### 1.2 배경
- 현재 46개 스킬 중 **38개 스킬**이 `reports/` 디렉토리에 MD 파일을 생성
- 리포트 생성 후 수동으로 확인해야 하는 불편함 존재
- 모바일/외부에서 분석 결과를 즉시 확인하고 싶은 니즈

### 1.3 대상 스킬 (38개)

| 유형 | 템플릿 | 스킬 수 | 대표 스킬 |
|------|--------|:------:|----------|
| 개별 종목 | report_stock.md | 12 | kr-stock-analysis, kr-growth-outlook, kr-earnings-trade |
| 스크리닝 | report_screener.md | 8 | kr-canslim-screener, kr-vcp-screener, kr-stock-screener |
| 매크로/전략 | report_macro.md | 18 | kr-weekly-strategy, kr-market-environment, kr-scenario-analyzer |

---

## 2. 요구사항

### 2.1 기능 요구사항 (FR)

| ID | 요구사항 | 우선순위 |
|----|---------|:-------:|
| FR-01 | 리포트 MD 파일 생성 후 이메일 자동 발송 | P0 |
| FR-02 | 이메일 ON/OFF 설정 (기본: OFF) | P0 |
| FR-03 | 수신자 이메일 주소 설정 (.env 또는 config) | P0 |
| FR-04 | MD → HTML 변환 후 본문에 포함 (가독성) | P1 |
| FR-05 | MD 원본 파일 첨부 | P1 |
| FR-06 | 발송 실패 시 리포트 생성 자체는 영향 없음 (fail-safe) | P0 |
| FR-07 | 발송 로그 기록 | P2 |
| FR-08 | 다수 수신자 지원 (CC) | P2 |

### 2.2 비기능 요구사항 (NFR)

| ID | 요구사항 |
|----|---------|
| NFR-01 | 외부 패키지 최소화 (Python 표준 라이브러리 `smtplib`, `email` 우선) |
| NFR-02 | SMTP 인증 정보는 `.env` 파일에서만 관리 (코드에 하드코딩 금지) |
| NFR-03 | 발송 실패가 스킬 실행 흐름을 중단하지 않아야 함 (try-except) |
| NFR-04 | 기존 스킬 코드 수정 최소화 (공통 모듈에서 처리) |

---

## 3. 아키텍처

### 3.1 설계 방향

```
스킬 실행 → MD 파일 생성 → [공통 모듈] email_sender.py 호출 → SMTP 발송
                                        ↓
                                  MD → HTML 변환
                                  제목 자동 생성
                                  .env에서 SMTP 설정 로드
```

### 3.2 핵심 컴포넌트

| 컴포넌트 | 위치 | 역할 |
|---------|------|------|
| `email_sender.py` | `_kr_common/utils/` | SMTP 발송 핵심 로직 |
| `.env` 설정 | 프로젝트 루트 | SMTP 서버/계정/수신자 설정 |
| `config.py` 확장 | `_kr_common/` | 이메일 설정 로드 |
| CLAUDE.md 지침 | 프로젝트 루트 | 리포트 생성 후 이메일 발송 지침 추가 |

### 3.3 통합 방식 (2가지 안)

#### **안 A: CLAUDE.md 지침 방식 (권장)**
- CLAUDE.md의 Output Rule에 "리포트 MD 파일 생성 후 `email_sender.py`로 발송" 지침 추가
- Claude Code가 Write 도구로 리포트 파일 생성한 직후, Bash로 email_sender.py 호출
- **장점**: 기존 스킬 SKILL.md/스크립트 수정 불필요, 한 곳에서 제어
- **단점**: Claude Code가 지침을 매번 따라야 함

#### **안 B: report_rules.md 템플릿 방식**
- `_kr_common/templates/report_rules.md`에 이메일 발송 절차 추가
- 모든 스킬이 이미 report_rules.md를 참조하므로 자동 적용
- **장점**: 리포트 규칙과 통합
- **단점**: 안 A와 동일 (Claude Code 지침 기반)

→ **안 A + B 병행** 권장: CLAUDE.md에 필수 지침 + report_rules.md에 절차 문서화

### 3.4 SMTP 설정 (.env)

```bash
# Email Notification Settings
EMAIL_ENABLED=true
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_CC=                          # optional, comma-separated
EMAIL_SUBJECT_PREFIX=[KR-Stock]    # 제목 접두사
```

### 3.5 이메일 제목 자동 생성 규칙

```
[KR-Stock] {skill_name}: {대상명} ({날짜})
```

| 예시 |
|------|
| `[KR-Stock] kr-stock-analysis: 테크윙 (2026-03-07)` |
| `[KR-Stock] kr-weekly-strategy: 주간전략 (2026-03-07)` |
| `[KR-Stock] kr-canslim-screener: KOSDAQ Top5 (2026-03-07)` |

---

## 4. 구현 범위 (Scope)

### 4.1 Phase 1 (MVP) — P0

| 작업 | 산출물 |
|------|--------|
| `email_sender.py` 개발 | `_kr_common/utils/email_sender.py` |
| `.env` 설정 항목 추가 | `.env.example` 업데이트 |
| `config.py`에 이메일 설정 로드 | `_kr_common/config.py` 수정 |
| CLAUDE.md에 발송 지침 추가 | `CLAUDE.md` 수정 |
| `report_rules.md`에 발송 절차 추가 | `_kr_common/templates/report_rules.md` 수정 |
| 테스트 | `_kr_common/tests/test_email_sender.py` |

### 4.2 Phase 2 (Enhancement) — P1/P2

| 작업 | 설명 |
|------|------|
| MD → HTML 변환 | `markdown` 패키지 또는 자체 변환 |
| 다수 수신자 (CC) | comma-separated CC 지원 |
| 발송 로그 | `reports/.email_log` |
| Gmail OAuth2 | App Password 대신 OAuth2 인증 |

---

## 5. 영향 분석

### 5.1 변경 파일

| 파일 | 변경 유형 | 영향도 |
|------|----------|:------:|
| `_kr_common/utils/email_sender.py` | **신규** | - |
| `_kr_common/config.py` | 수정 | 낮음 |
| `_kr_common/templates/report_rules.md` | 수정 | 낮음 |
| `CLAUDE.md` | 수정 | 낮음 |
| `.env.example` | 수정 | 낮음 |
| `_kr_common/tests/test_email_sender.py` | **신규** | - |
| `README.md` | 수정 | 낮음 |
| `install.sh` | 수정 없음 | 없음 |

### 5.2 기존 스킬 영향

**영향 없음**. 이메일 발송은 `_kr_common` 공통 모듈에서 처리하며, Claude Code가 리포트 생성 후 별도 호출하는 구조. 기존 스킬 SKILL.md나 scripts 수정 불필요.

### 5.3 리스크

| 리스크 | 확률 | 대응 |
|--------|:----:|------|
| SMTP 인증 실패 | 중 | Gmail App Password 가이드 제공 |
| 발송 실패로 스킬 중단 | 낮음 | try-except로 fail-safe 보장 |
| `.env` 누출 | 낮음 | `.gitignore`에 `.env` 포함 확인 |
| 대량 발송 제한 (Gmail 500/일) | 낮음 | 일 사용량 현실적으로 10건 미만 |

---

## 6. 기술 스택

| 항목 | 선택 | 비고 |
|------|------|------|
| SMTP 라이브러리 | Python `smtplib` (표준) | 추가 설치 불필요 |
| 이메일 구성 | Python `email.mime` (표준) | 추가 설치 불필요 |
| 환경변수 | `python-dotenv` | 기존 사용 여부 확인 필요 |
| MD→HTML | `markdown` 패키지 (Phase 2) | Phase 1에서는 MD 원본 첨부 |
| 설정 관리 | `.env` 파일 | 보안 우선 |

---

## 7. email_sender.py 인터페이스 (초안)

```python
# _kr_common/utils/email_sender.py

def send_report_email(
    report_path: str,          # 생성된 MD 파일 경로
    skill_name: str = "",      # 스킬명 (제목 생성용)
    subject: str = "",         # 커스텀 제목 (없으면 자동 생성)
    convert_html: bool = False # MD→HTML 변환 여부 (Phase 2)
) -> bool:
    """
    리포트 MD 파일을 이메일로 발송한다.

    Returns:
        True: 발송 성공
        False: 발송 실패 또는 이메일 비활성화
    """
```

### CLI 사용법

```bash
# Claude Code에서 리포트 생성 후 호출
python3 -c "
import sys; sys.path.insert(0, 'skills/_kr_common/utils')
from email_sender import send_report_email
send_report_email('reports/kr-stock-analysis_089030_테크윙_20260307.md', 'kr-stock-analysis')
"
```

---

## 8. CLAUDE.md 추가 지침 (초안)

```markdown
### 8. 리포트 이메일 발송 (선택)

리포트 MD 파일 생성 후, EMAIL_ENABLED=true 설정 시 자동 발송한다:

1. Write 도구로 `reports/` 에 MD 파일 생성
2. Bash로 `email_sender.py` 호출:
   python3 -c "
   import sys; sys.path.insert(0, 'skills/_kr_common/utils')
   from email_sender import send_report_email
   send_report_email('{파일경로}', '{스킬명}')
   "
3. 발송 실패 시 리포트 생성은 정상 완료로 간주 (fail-safe)
```

---

## 9. 체크리스트

- [ ] `.env`에 SMTP 설정 항목 정의
- [ ] `email_sender.py` 개발
- [ ] `config.py`에 이메일 설정 로드 함수 추가
- [ ] `report_rules.md`에 이메일 발송 절차 추가
- [ ] `CLAUDE.md`에 발송 지침 추가
- [ ] 테스트 작성 및 실행
- [ ] Gmail App Password 발급 가이드 (README 또는 별도 문서)
- [ ] install.sh 실행하여 `_kr_common` 동기화
- [ ] 실제 발송 테스트

---

## 10. 일정 추정

| Phase | 작업 | 예상 |
|:-----:|------|------|
| Design | 상세 설계 | 다음 단계 |
| Do | email_sender.py + config + 테스트 | MVP 구현 |
| Check | Gap 분석 | 검증 |
