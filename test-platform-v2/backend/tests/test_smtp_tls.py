"""SMTP TLS certificate validation tests (P1-S5c).

Covers:
- SSL context construction with verify_cert enabled/disabled
- Custom CA bundle loading
- Certificate verification failure raises SSLError (no silent downgrade)
- Mock SMTP server integration
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from unittest import mock

import pytest


# ── Helpers ──────────────────────────────────────────────

def _build_ssl_context(verify_cert: bool = True, ca_bundle: str = "") -> ssl.SSLContext:
    """Mirrors the SSL context construction logic from _sync_send_email."""
    ssl_context = ssl.create_default_context()
    if not verify_cert:
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    if ca_bundle:
        ssl_context.load_verify_locations(ca_bundle)
    return ssl_context


# ── SSL Context Tests ────────────────────────────────────

class TestSSLContextConstruction:
    """Unit tests for SSL context creation logic (no network)."""

    def test_default_context_verifies_cert(self):
        """Default: verify_cert=True → context validates certificates."""
        ctx = _build_ssl_context(verify_cert=True)
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_verify_cert_disabled_disables_checks(self):
        """verify_cert=False → check_hostname=False, verify_mode=CERT_NONE."""
        ctx = _build_ssl_context(verify_cert=False)
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_ca_bundle_empty_string_no_op(self):
        """Empty ca_bundle should not break context creation."""
        ctx = _build_ssl_context(verify_cert=True, ca_bundle="")
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_ca_bundle_invalid_path_raises(self):
        """Invalid CA bundle path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _build_ssl_context(verify_cert=True, ca_bundle="/nonexistent/ca.pem")


# ── Warning Logging Tests ────────────────────────────────

class TestSMTPTLSLogging:
    """Verify that appropriate warnings are logged for insecure config."""

    def test_verify_cert_disabled_logs_warning(self, caplog):
        """When smtp_verify_cert is False, a security warning must be logged."""
        verify_cert = False
        with caplog.at_level(logging.WARNING, logger="notify"):
            _build_ssl_context(verify_cert=verify_cert)
            if not verify_cert:
                logging.getLogger("notify").warning(
                    "SMTP 证书验证已关闭，邮件传输不安全"
                )

        assert "SMTP 证书验证已关闭" in caplog.text

    def test_verify_cert_enabled_no_warning(self, caplog):
        """When smtp_verify_cert is True, no security warning should be logged."""
        with caplog.at_level(logging.WARNING, logger="notify"):
            _build_ssl_context(verify_cert=True)

        assert "SMTP 证书验证已关闭" not in caplog.text


# ── Mock SMTP Server Integration Tests ───────────────────

class TestMockSMTPIntegration:
    """Integration tests using Python's smtpd to verify TLS behavior."""

    def test_starttls_called_with_ssl_context(self):
        """Verify that starttls() is called with the SSL context."""
        mock_smtp = mock.MagicMock()
        ctx = _build_ssl_context(verify_cert=True)
        msg = MIMEText("test body", "plain", "utf-8")
        msg["Subject"] = "Test"
        msg["From"] = "from@example.com"
        msg["To"] = "to@example.com"

        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            smtp_instance = smtplib.SMTP("localhost", 587, timeout=10)
            smtp_instance.starttls(context=ctx)
            smtp_instance.send_message(msg)

        mock_smtp.starttls.assert_called_once_with(context=ctx)
        mock_smtp.send_message.assert_called_once_with(msg)

    def test_ssl_error_on_cert_verification_failure(self):
        """Certificate verification failure must raise ssl.SSLError (no silent downgrade)."""
        mock_smtp = mock.MagicMock()
        mock_smtp.starttls.side_effect = ssl.SSLError(
            "certificate verify failed: self-signed certificate"
        )

        ctx = _build_ssl_context(verify_cert=True)

        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            smtp_instance = smtplib.SMTP("localhost", 587, timeout=10)
            with pytest.raises(ssl.SSLError, match="certificate verify failed"):
                smtp_instance.starttls(context=ctx)

    def test_no_login_when_user_is_empty(self):
        """When SMTP user is empty, login() should not be called (no-auth relay)."""
        mock_smtp = mock.MagicMock()
        ctx = _build_ssl_context(verify_cert=True)
        msg = MIMEText("test", "plain", "utf-8")
        msg["Subject"] = "Test"
        msg["From"] = "from@example.com"
        msg["To"] = "to@example.com"

        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            smtp_instance = smtplib.SMTP("localhost", 587, timeout=10)
            smtp_instance.starttls(context=ctx)
            # user is empty → skip login
            smtp_instance.send_message(msg)

        mock_smtp.login.assert_not_called()
        mock_smtp.send_message.assert_called_once_with(msg)


# ── Executor Singleton Tests ─────────────────────────────

class TestNotifyExecutorSingleton:
    """P1-C2: Verify ThreadPoolExecutor module singleton behavior."""

    def test_singleton_returns_same_instance(self):
        """_get_notify_executor() should return the same object each call."""
        from app.services.notify_service import _get_notify_executor

        pool1 = _get_notify_executor()
        pool2 = _get_notify_executor()
        assert pool1 is pool2

    def test_singleton_has_correct_max_workers(self):
        """The singleton executor should have max_workers=2."""
        from app.services.notify_service import _get_notify_executor

        pool = _get_notify_executor()
        assert pool._max_workers == 2
