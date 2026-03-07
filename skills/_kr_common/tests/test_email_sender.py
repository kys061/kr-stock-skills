"""email_sender 모듈 테스트."""

import sys
from pathlib import Path

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'utils'))

from config import EmailConfig
from utils.email_sender import _build_subject, _build_message, send_report_email


class TestBuildSubject:
    """제목 자동 생성 테스트."""

    def test_stock_report_subject(self):
        result = _build_subject(
            'reports/kr-stock-analysis_089030_테크윙_20260307.md',
            'kr-stock-analysis', '[KR-Stock]'
        )
        assert result == '[KR-Stock] kr-stock-analysis: 테크윙 (2026-03-07)'

    def test_market_report_subject(self):
        result = _build_subject(
            'reports/kr-weekly-strategy_market_주간전략_20260307.md',
            'kr-weekly-strategy', '[KR-Stock]'
        )
        assert result == '[KR-Stock] kr-weekly-strategy: 주간전략 (2026-03-07)'

    def test_short_filename_subject(self):
        result = _build_subject('reports/custom.md', '', '[KR-Stock]')
        assert result == '[KR-Stock] custom'

    def test_custom_prefix(self):
        result = _build_subject(
            'reports/kr-stock-analysis_005930_삼성전자_20260307.md',
            '', '[MyStock]'
        )
        assert '[MyStock]' in result
        assert '삼성전자' in result

    def test_screener_report_subject(self):
        result = _build_subject(
            'reports/kr-canslim-screener_market_KOSDAQ_20260307.md',
            'kr-canslim-screener', '[KR-Stock]'
        )
        assert 'KOSDAQ' in result or 'market' in result


class TestEmailConfig:
    """이메일 설정 테스트."""

    def test_default_disabled(self, monkeypatch):
        monkeypatch.delenv('EMAIL_ENABLED', raising=False)
        cfg = EmailConfig()
        assert cfg.enabled is False

    def test_is_configured_requires_all(self):
        cfg = EmailConfig()
        cfg.enabled = True
        cfg.smtp_user = 'test@gmail.com'
        cfg.smtp_password = 'apppassword'
        cfg.to_addr = 'to@example.com'
        assert cfg.is_configured is True

    def test_not_configured_without_password(self):
        cfg = EmailConfig()
        cfg.enabled = True
        cfg.smtp_user = 'test@gmail.com'
        cfg.smtp_password = ''
        assert cfg.is_configured is False

    def test_not_configured_when_disabled(self):
        cfg = EmailConfig()
        cfg.enabled = False
        cfg.smtp_user = 'test@gmail.com'
        cfg.smtp_password = 'pass'
        cfg.to_addr = 'to@test.com'
        assert cfg.is_configured is False


class TestBuildMessage:
    """메시지 생성 테스트."""

    def _make_test_file(self, tmp_path):
        f = tmp_path / 'test.md'
        f.write_text('# Test Report\nContent here')
        return str(f), f.name

    def test_message_has_subject(self, tmp_path):
        path, name = self._make_test_file(tmp_path)
        msg = _build_message('f@t.com', 't@t.com', '', 'Test Subject', 'body', path, name)
        assert msg['Subject'] == 'Test Subject'

    def test_message_has_from_to(self, tmp_path):
        path, name = self._make_test_file(tmp_path)
        msg = _build_message('from@t.com', 'to@t.com', '', 'Sub', 'body', path, name)
        assert msg['From'] == 'from@t.com'
        assert msg['To'] == 'to@t.com'

    def test_message_has_cc(self, tmp_path):
        path, name = self._make_test_file(tmp_path)
        msg = _build_message('f@t.com', 't@t.com', 'cc@t.com', 'Sub', 'body', path, name)
        assert msg['Cc'] == 'cc@t.com'

    def test_message_no_cc_when_empty(self, tmp_path):
        path, name = self._make_test_file(tmp_path)
        msg = _build_message('f@t.com', 't@t.com', '', 'Sub', 'body', path, name)
        assert msg['Cc'] is None

    def test_message_has_attachment(self, tmp_path):
        path, name = self._make_test_file(tmp_path)
        msg = _build_message('f@t.com', 't@t.com', '', 'Sub', 'body', path, name)
        payloads = msg.get_payload()
        assert len(payloads) == 2  # text + attachment


class TestSendReportEmail:
    """통합 테스트 (SMTP 미접속)."""

    def test_disabled_returns_false(self, monkeypatch):
        monkeypatch.setenv('EMAIL_ENABLED', 'false')
        # 싱글턴 리셋
        import config
        config._email_config = None
        result = send_report_email('/tmp/test.md', 'test')
        assert result is False

    def test_missing_file_returns_false(self, monkeypatch):
        monkeypatch.setenv('EMAIL_ENABLED', 'true')
        monkeypatch.setenv('EMAIL_SMTP_USER', 'u')
        monkeypatch.setenv('EMAIL_SMTP_PASSWORD', 'p')
        monkeypatch.setenv('EMAIL_TO', 'to@test.com')
        import config
        config._email_config = None
        result = send_report_email('/nonexistent/file.md', 'test')
        assert result is False

    def test_smtp_failure_returns_false(self, monkeypatch, tmp_path):
        monkeypatch.setenv('EMAIL_ENABLED', 'true')
        monkeypatch.setenv('EMAIL_SMTP_USER', 'u')
        monkeypatch.setenv('EMAIL_SMTP_PASSWORD', 'p')
        monkeypatch.setenv('EMAIL_TO', 'to@test.com')
        monkeypatch.setenv('EMAIL_SMTP_HOST', 'invalid.host.example')
        monkeypatch.setenv('EMAIL_SMTP_PORT', '9999')
        import config
        config._email_config = None
        test_file = tmp_path / 'test_report.md'
        test_file.write_text('# Test Report')
        result = send_report_email(str(test_file), 'test')
        assert result is False  # fail-safe
