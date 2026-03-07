# Design: 리포트 이메일 발송 기능

> **Feature**: report-email-notification
> **Phase**: Design
> **Created**: 2026-03-07
> **Plan Reference**: `docs/01-plan/features/report-email-notification.plan.md`

---

## 1. 설계 개요

리포트 MD 파일 생성 후 Gmail SMTP를 통해 이메일을 자동 발송하는 공통 모듈.
기존 38개 스킬 코드 수정 없이, `_kr_common/utils/email_sender.py` 단일 모듈과
CLAUDE.md 지침만으로 전체 스킬에 적용.

### 설계 원칙
1. **Gmail App Password 인증** — OAuth2 없이 간편 설정
2. **Fail-safe** — 발송 실패가 리포트 생성을 중단하지 않음
3. **Zero dependency** — Python 표준 라이브러리만 사용 (`smtplib`, `email`)
4. **단일 진입점** — `send_report_email()` 하나로 통일

---

## 2. Gmail SMTP 설정

### 2.1 Gmail App Password 발급 절차

```
1. Google 계정 → 보안 → 2단계 인증 활성화
2. Google 계정 → 보안 → 앱 비밀번호
3. "메일" + "기타(맞춤 이름)" 선택 → "KR-Stock-Skills" 입력
4. 생성된 16자리 앱 비밀번호를 .env에 설정
```

### 2.2 Gmail SMTP 서버 정보

| 항목 | 값 |
|------|------|
| Host | `smtp.gmail.com` |
| Port | `587` (STARTTLS) |
| 인증 | App Password (16자리) |
| TLS | STARTTLS 필수 |
| 일일 발송 한도 | 500통 (개인) / 2,000통 (Workspace) |

### 2.3 .env 설정 항목

```bash
# ── Email Notification ──────────────────────
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-gmail@gmail.com
EMAIL_SMTP_PASSWORD=abcd efgh ijkl mnop
EMAIL_FROM=your-gmail@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_CC=
EMAIL_SUBJECT_PREFIX=[KR-Stock]
```

> `.env`는 이미 `.gitignore`에 포함 확인 완료.

---

## 3. 모듈 설계

### 3.1 파일 구조

```
skills/_kr_common/
├── config.py                      # EmailConfig 추가
├── utils/
│   ├── __init__.py
│   ├── email_sender.py            # [신규] 핵심 모듈
│   ├── ta_utils.py
│   ├── ticker_utils.py
│   ├── date_utils.py
│   └── cache.py
└── tests/
    └── test_email_sender.py       # [신규] 테스트
```

### 3.2 EmailConfig (config.py 확장)

```python
@dataclass
class EmailConfig:
    """이메일 발송 설정."""
    enabled: bool = field(
        default_factory=lambda: os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
    )
    smtp_host: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
    )
    smtp_port: int = field(
        default_factory=lambda: int(os.getenv('EMAIL_SMTP_PORT', '587'))
    )
    smtp_user: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_USER', '')
    )
    smtp_password: str = field(
        default_factory=lambda: os.getenv('EMAIL_SMTP_PASSWORD', '')
    )
    from_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_FROM', '')
    )
    to_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_TO', '')
    )
    cc_addr: str = field(
        default_factory=lambda: os.getenv('EMAIL_CC', '')
    )
    subject_prefix: str = field(
        default_factory=lambda: os.getenv('EMAIL_SUBJECT_PREFIX', '[KR-Stock]')
    )

    @property
    def is_configured(self) -> bool:
        """발송에 필요한 최소 설정이 완료되었는지 확인."""
        return bool(self.enabled and self.smtp_user and self.smtp_password and self.to_addr)
```

`get_config()` 패턴과 동일하게 싱글턴:

```python
_email_config = None

def get_email_config() -> EmailConfig:
    global _email_config
    if _email_config is None:
        _email_config = EmailConfig()
    return _email_config
```

### 3.3 email_sender.py 상세 설계

```python
"""리포트 이메일 발송 모듈.

Gmail SMTP (App Password)를 통해 리포트 MD 파일을 발송한다.
Python 표준 라이브러리만 사용 (smtplib, email).
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path


def send_report_email(
    report_path: str,
    skill_name: str = "",
    subject: str = "",
) -> bool:
    """리포트 MD 파일을 이메일로 발송한다.

    Args:
        report_path: 생성된 MD 파일의 절대/상대 경로
        skill_name: 스킬명 (제목 자동 생성용, 없으면 파일명에서 추출)
        subject: 커스텀 제목 (빈 문자열이면 자동 생성)

    Returns:
        True: 발송 성공
        False: 발송 실패, 비활성화, 또는 설정 미완료
    """


def _build_subject(report_path: str, skill_name: str, prefix: str) -> str:
    """파일명에서 이메일 제목을 자동 생성한다.

    파일명 패턴: {skill_name}_{identifier}_{name}_{YYYYMMDD}.md
    생성 제목: {prefix} {skill_name}: {name} ({YYYY-MM-DD})
    """


def _build_message(
    from_addr: str,
    to_addr: str,
    cc_addr: str,
    subject: str,
    body_text: str,
    attachment_path: str,
    attachment_name: str,
) -> MIMEMultipart:
    """이메일 메시지 객체를 생성한다.

    구조:
    - Content-Type: multipart/mixed
      ├── text/plain: MD 원본 텍스트 (본문)
      └── application/octet-stream: MD 파일 첨부
    """


def _send_smtp(
    host: str,
    port: int,
    user: str,
    password: str,
    message: MIMEMultipart,
) -> None:
    """SMTP STARTTLS로 이메일을 발송한다.

    Gmail 587 포트 전용:
    1. smtplib.SMTP(host, port)
    2. ehlo()
    3. starttls()
    4. login(user, password)
    5. send_message(message)
    6. quit()
    """
```

### 3.4 함수 흐름도

```
send_report_email(report_path, skill_name)
│
├── get_email_config()
│   └── is_configured == False → return False (로그: "이메일 비활성화")
│
├── Path(report_path).read_text(encoding='utf-8')
│   └── FileNotFoundError → return False (로그: "파일 없음")
│
├── _build_subject(report_path, skill_name, prefix)
│   └── 파일명 파싱 → "[KR-Stock] kr-stock-analysis: 테크윙 (2026-03-07)"
│
├── _build_message(from, to, cc, subject, body, path, filename)
│   ├── MIMEMultipart('mixed')
│   ├── attach(MIMEText(body, 'plain', 'utf-8'))  ← MD 원본 본문
│   └── attach(MIMEApplication(file_bytes))        ← MD 파일 첨부
│
├── _send_smtp(host, port, user, password, message)
│   ├── SMTP(host, port, timeout=30)
│   ├── starttls()
│   ├── login(user, password)
│   └── send_message(message)
│
└── return True
    └── 예외 발생 시: print(f"[EMAIL] 발송 실패: {e}"), return False
```

### 3.5 에러 처리

| 예외 | 처리 | 로그 |
|------|------|------|
| `FileNotFoundError` | return False | `[EMAIL] 파일 없음: {path}` |
| `smtplib.SMTPAuthenticationError` | return False | `[EMAIL] 인증 실패: App Password 확인 필요` |
| `smtplib.SMTPConnectError` | return False | `[EMAIL] 연결 실패: {host}:{port}` |
| `smtplib.SMTPException` | return False | `[EMAIL] SMTP 에러: {e}` |
| `Exception` (기타) | return False | `[EMAIL] 발송 실패: {e}` |

모든 예외는 `try-except`로 포착하여 **절대 raise하지 않는다** (fail-safe).

---

## 4. 제목 자동 생성 규칙

### 4.1 파일명 파싱 로직

```python
# 파일명: kr-stock-analysis_089030_테크윙_20260307.md
# 분리: ['kr-stock-analysis', '089030', '테크윙', '20260307']

filename = Path(report_path).stem  # 확장자 제거
parts = filename.split('_')

if len(parts) >= 4:
    skill = parts[0]           # kr-stock-analysis
    identifier = parts[1]      # 089030
    name = parts[2]            # 테크윙
    date_str = parts[3]        # 20260307
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    subject = f"{prefix} {skill}: {name} ({date_fmt})"
elif len(parts) >= 3:
    # market 유형: kr-weekly-strategy_market_주간전략_20260307
    skill = parts[0]
    name = parts[2] if parts[1] == 'market' else parts[1]
    date_str = parts[-1]
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    subject = f"{prefix} {skill}: {name} ({date_fmt})"
else:
    subject = f"{prefix} {filename}"
```

### 4.2 제목 예시

| 파일명 | 생성 제목 |
|--------|----------|
| `kr-stock-analysis_089030_테크윙_20260307.md` | `[KR-Stock] kr-stock-analysis: 테크윙 (2026-03-07)` |
| `kr-weekly-strategy_market_주간전략_20260307.md` | `[KR-Stock] kr-weekly-strategy: 주간전략 (2026-03-07)` |
| `kr-canslim-screener_market_KOSDAQ_20260307.md` | `[KR-Stock] kr-canslim-screener: KOSDAQ (2026-03-07)` |
| `custom_report.md` | `[KR-Stock] custom_report` |

---

## 5. 이메일 본문 구조

```
┌─────────────────────────────────────┐
│ From: your-gmail@gmail.com          │
│ To: recipient@example.com           │
│ Subject: [KR-Stock] kr-stock-...    │
├─────────────────────────────────────┤
│                                     │
│  (MD 원본 텍스트 - plain text)       │
│  # 테크윙 (089030.KQ) 종합 분석     │
│  > 분석일: 2026-03-07               │
│  ...                                │
│                                     │
├─────────────────────────────────────┤
│ 첨부: kr-stock-analysis_089030_     │
│       테크윙_20260307.md            │
└─────────────────────────────────────┘
```

- **본문**: MD 원본을 plain text로 그대로 포함 (대부분의 메일 클라이언트에서 읽기 가능)
- **첨부**: MD 파일 원본 첨부 (다운로드하여 마크다운 뷰어로 열기 가능)

---

## 6. 통합 설계

### 6.1 CLAUDE.md 추가 지침

```markdown
### 8. 리포트 이메일 발송

리포트 MD 파일(`reports/` 디렉토리)을 생성한 후, 이메일 발송을 시도한다:

\```bash
cd ~/stock && python3 -c "
import sys; sys.path.insert(0, 'skills/_kr_common')
from utils.email_sender import send_report_email
send_report_email('{리포트_파일_경로}', '{스킬명}')
"
\```

- `EMAIL_ENABLED=false`이면 자동 스킵 (로그만 출력)
- 발송 실패 시에도 리포트 생성은 정상 완료로 간주
- `.env` 설정이 없으면 무시
```

### 6.2 report_rules.md 추가 섹션

```markdown
## 8. 이메일 발송 (선택)

리포트 생성 후 `.env`의 `EMAIL_ENABLED=true` 설정 시 자동 발송:

1. `email_sender.send_report_email(path, skill_name)` 호출
2. Gmail SMTP (App Password) 사용
3. 발송 실패 시 리포트 생성에 영향 없음 (fail-safe)

설정: `.env` 파일의 `EMAIL_*` 항목 참조
```

---

## 7. 테스트 설계

### 7.1 테스트 파일: `_kr_common/tests/test_email_sender.py`

```python
class TestBuildSubject:
    """제목 자동 생성 테스트."""

    def test_stock_report_subject(self):
        """개별 종목 리포트 → 종목명 포함 제목."""
        result = _build_subject(
            'reports/kr-stock-analysis_089030_테크윙_20260307.md',
            'kr-stock-analysis', '[KR-Stock]'
        )
        assert result == '[KR-Stock] kr-stock-analysis: 테크윙 (2026-03-07)'

    def test_market_report_subject(self):
        """매크로 리포트 → market 생략, 대상명 제목."""
        result = _build_subject(
            'reports/kr-weekly-strategy_market_주간전략_20260307.md',
            'kr-weekly-strategy', '[KR-Stock]'
        )
        assert result == '[KR-Stock] kr-weekly-strategy: 주간전략 (2026-03-07)'

    def test_short_filename_subject(self):
        """짧은 파일명 → 파일명 그대로."""
        result = _build_subject('reports/custom.md', '', '[KR-Stock]')
        assert result == '[KR-Stock] custom'

    def test_custom_prefix(self):
        """커스텀 prefix 적용."""
        result = _build_subject(
            'reports/kr-stock-analysis_005930_삼성전자_20260307.md',
            '', '[MyStock]'
        )
        assert '[MyStock]' in result


class TestEmailConfig:
    """이메일 설정 테스트."""

    def test_default_disabled(self):
        """기본값: 비활성화."""
        # EMAIL_ENABLED 미설정 시
        cfg = EmailConfig()
        assert cfg.enabled is False

    def test_is_configured_requires_all(self):
        """최소 설정: enabled + user + password + to."""
        cfg = EmailConfig()
        cfg.enabled = True
        cfg.smtp_user = 'test@gmail.com'
        cfg.smtp_password = 'apppassword'
        cfg.to_addr = 'to@example.com'
        assert cfg.is_configured is True

    def test_not_configured_without_password(self):
        """비밀번호 없으면 미설정."""
        cfg = EmailConfig()
        cfg.enabled = True
        cfg.smtp_user = 'test@gmail.com'
        assert cfg.is_configured is False


class TestBuildMessage:
    """메시지 생성 테스트."""

    def test_message_has_subject(self):
        """메시지에 제목 포함."""
        msg = _build_message(
            'from@test.com', 'to@test.com', '',
            'Test Subject', 'body text',
            '/tmp/test.md', 'test.md'
        )
        assert msg['Subject'] == 'Test Subject'

    def test_message_has_from_to(self):
        """From/To 헤더 설정."""
        msg = _build_message(
            'from@test.com', 'to@test.com', '',
            'Sub', 'body', '/tmp/test.md', 'test.md'
        )
        assert msg['From'] == 'from@test.com'
        assert msg['To'] == 'to@test.com'

    def test_message_has_cc(self):
        """CC 설정 시 헤더에 포함."""
        msg = _build_message(
            'from@test.com', 'to@test.com', 'cc@test.com',
            'Sub', 'body', '/tmp/test.md', 'test.md'
        )
        assert msg['Cc'] == 'cc@test.com'

    def test_message_no_cc_when_empty(self):
        """CC 미설정 시 헤더 없음."""
        msg = _build_message(
            'from@test.com', 'to@test.com', '',
            'Sub', 'body', '/tmp/test.md', 'test.md'
        )
        assert msg['Cc'] is None

    def test_message_has_attachment(self):
        """첨부파일 포함 확인."""
        msg = _build_message(
            'from@test.com', 'to@test.com', '',
            'Sub', 'body', '/tmp/test.md', 'report.md'
        )
        payloads = msg.get_payload()
        assert len(payloads) == 2  # text + attachment


class TestSendReportEmail:
    """통합 테스트 (SMTP 미접속)."""

    def test_disabled_returns_false(self, monkeypatch):
        """EMAIL_ENABLED=false → False 반환."""
        monkeypatch.setenv('EMAIL_ENABLED', 'false')
        result = send_report_email('/tmp/test.md', 'test')
        assert result is False

    def test_missing_file_returns_false(self, monkeypatch):
        """존재하지 않는 파일 → False 반환."""
        monkeypatch.setenv('EMAIL_ENABLED', 'true')
        monkeypatch.setenv('EMAIL_SMTP_USER', 'u')
        monkeypatch.setenv('EMAIL_SMTP_PASSWORD', 'p')
        monkeypatch.setenv('EMAIL_TO', 'to@test.com')
        result = send_report_email('/nonexistent/file.md', 'test')
        assert result is False

    def test_smtp_failure_returns_false(self, monkeypatch, tmp_path):
        """SMTP 연결 실패 → False 반환 (예외 미발생)."""
        monkeypatch.setenv('EMAIL_ENABLED', 'true')
        monkeypatch.setenv('EMAIL_SMTP_USER', 'u')
        monkeypatch.setenv('EMAIL_SMTP_PASSWORD', 'p')
        monkeypatch.setenv('EMAIL_TO', 'to@test.com')
        monkeypatch.setenv('EMAIL_SMTP_HOST', 'invalid.host.example')
        monkeypatch.setenv('EMAIL_SMTP_PORT', '9999')
        test_file = tmp_path / 'test.md'
        test_file.write_text('# Test Report')
        result = send_report_email(str(test_file), 'test')
        assert result is False  # fail-safe: 예외 없이 False
```

### 7.2 테스트 실행

```bash
cd ~/stock/skills/_kr_common && python -m pytest tests/test_email_sender.py -v
```

예상: **12 tests passed**

---

## 8. 구현 순서

| Step | 작업 | 파일 | 의존성 |
|:----:|------|------|--------|
| 1 | `.env`에 EMAIL 설정 추가 | `.env` | - |
| 2 | `EmailConfig` 추가 | `_kr_common/config.py` | Step 1 |
| 3 | `email_sender.py` 작성 | `_kr_common/utils/email_sender.py` | Step 2 |
| 4 | 테스트 작성 및 실행 | `_kr_common/tests/test_email_sender.py` | Step 3 |
| 5 | `report_rules.md` 업데이트 | `_kr_common/templates/report_rules.md` | Step 3 |
| 6 | `CLAUDE.md` 업데이트 | `CLAUDE.md` | Step 3 |
| 7 | `install.sh` 실행 | - | Step 3-6 |
| 8 | 실제 Gmail 발송 테스트 | - | Step 7 + App Password |
| 9 | Git commit & push | - | Step 8 |

---

## 9. .env.example 업데이트

```bash
# ── Email Notification (Optional) ───────────
# Gmail App Password 설정 방법:
#   1. Google 계정 → 보안 → 2단계 인증 활성화
#   2. 보안 → 앱 비밀번호 → "메일" + "기타" → 생성
#   3. 16자리 비밀번호를 EMAIL_SMTP_PASSWORD에 입력
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-gmail@gmail.com
EMAIL_SMTP_PASSWORD=abcd efgh ijkl mnop
EMAIL_FROM=your-gmail@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_CC=
EMAIL_SUBJECT_PREFIX=[KR-Stock]
```

---

## 10. 검증 기준 (Check Phase용)

| ID | 검증 항목 | 기준 |
|----|----------|------|
| V-01 | `email_sender.py` 존재 | 파일 존재 |
| V-02 | `EmailConfig` dataclass | `config.py`에 포함 |
| V-03 | `send_report_email()` 인터페이스 | Plan 문서 시그니처와 일치 |
| V-04 | fail-safe 동작 | SMTP 실패 시 예외 미발생 + False 반환 |
| V-05 | 제목 자동 생성 | 3가지 패턴 정상 파싱 |
| V-06 | 첨부파일 포함 | MD 파일 첨부 확인 |
| V-07 | disabled 시 스킵 | `EMAIL_ENABLED=false` → 즉시 False |
| V-08 | CLAUDE.md 지침 추가 | 섹션 8 존재 |
| V-09 | report_rules.md 업데이트 | 이메일 섹션 존재 |
| V-10 | `.env` EMAIL 항목 | 9개 항목 존재 |
| V-11 | 테스트 통과 | 12 tests passed |
| V-12 | Gmail 실제 발송 | 수신 확인 |
