"""리포트 이메일 발송 모듈.

Gmail SMTP (App Password)를 통해 리포트 MD 파일을 발송한다.
Python 표준 라이브러리만 사용 (smtplib, email).
발송 실패 시 예외를 raise하지 않는다 (fail-safe).
"""

import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

# config.py import (상대 경로)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import get_email_config


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
    try:
        cfg = get_email_config()

        if not cfg.is_configured:
            print("[EMAIL] 이메일 비활성화 또는 설정 미완료 — 스킵")
            return False

        path = Path(report_path)
        if not path.exists():
            print(f"[EMAIL] 파일 없음: {report_path}")
            return False

        body = path.read_text(encoding='utf-8')

        if not subject:
            subject = _build_subject(report_path, skill_name, cfg.subject_prefix)

        from_addr = cfg.from_addr or cfg.smtp_user
        message = _build_message(
            from_addr=from_addr,
            to_addr=cfg.to_addr,
            cc_addr=cfg.cc_addr,
            subject=subject,
            body_text=body,
            attachment_path=str(path),
            attachment_name=path.name,
        )

        _send_smtp(cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_password, message)
        print(f"[EMAIL] 발송 성공: {cfg.to_addr} ← {path.name}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] 인증 실패: Gmail App Password를 확인하세요")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"[EMAIL] 연결 실패: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] SMTP 에러: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] 발송 실패: {e}")
        return False


def _build_subject(report_path: str, skill_name: str, prefix: str) -> str:
    """파일명에서 이메일 제목을 자동 생성한다.

    파일명 패턴: {skill_name}_{identifier}_{name}_{YYYYMMDD}.md
    생성 제목: {prefix} {skill_name}: {name} ({YYYY-MM-DD})
    """
    filename = Path(report_path).stem
    parts = filename.split('_')

    if len(parts) >= 4:
        skill = parts[0]
        name = parts[2]
        date_str = parts[-1]
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
        return f"{prefix} {skill}: {name} ({date_fmt})"
    elif len(parts) >= 3:
        skill = parts[0]
        name = parts[2] if len(parts) > 2 and parts[1] == 'market' else parts[1]
        date_str = parts[-1]
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
        return f"{prefix} {skill}: {name} ({date_fmt})"
    else:
        return f"{prefix} {filename}"


def _build_message(
    from_addr: str,
    to_addr: str,
    cc_addr: str,
    subject: str,
    body_text: str,
    attachment_path: str,
    attachment_name: str,
) -> MIMEMultipart:
    """이메일 메시지 객체를 생성한다."""
    msg = MIMEMultipart('mixed')
    msg['From'] = from_addr
    msg['To'] = to_addr
    if cc_addr:
        msg['Cc'] = cc_addr
    msg['Subject'] = subject

    # 본문: MD 원본 텍스트
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    # 첨부: MD 파일
    file_bytes = Path(attachment_path).read_bytes()
    attachment = MIMEApplication(file_bytes, Name=attachment_name)
    attachment['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
    msg.attach(attachment)

    return msg


def _send_smtp(
    host: str,
    port: int,
    user: str,
    password: str,
    message: MIMEMultipart,
) -> None:
    """SMTP STARTTLS로 이메일을 발송한다."""
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.send_message(message)


if __name__ == '__main__':
    # CLI: python email_sender.py <report_path> [skill_name]
    if len(sys.argv) < 2:
        print("Usage: python email_sender.py <report_path> [skill_name]")
        sys.exit(1)
    path = sys.argv[1]
    skill = sys.argv[2] if len(sys.argv) > 2 else ""
    result = send_report_email(path, skill)
    sys.exit(0 if result else 1)
