"""SMTP end-to-end integration tests (C4).

Validates real SMTP email sending using a local debug SMTP server.
These tests are gated behind @pytest.mark.integration — skip in unit test runs.

The debug server handles basic SMTP commands (EHLO, MAIL FROM, RCPT TO, DATA)
and captures received messages. For tests that exercise _sync_send_email
(which requires STARTTLS), the smtplib.SMTP class is patched to intercept
and verify the full send flow including SSL context, authentication, and
message content.
"""
from __future__ import annotations

import logging
import smtplib
import socket
import ssl
import threading
from email.mime.text import MIMEText
from email.parser import Parser
from unittest import mock

import pytest

from app.services.notify_service import _sync_send_email


# ── Helper ──────────────────────────────────────────────────


def _make_mock_smtp() -> mock.MagicMock:
    """Return a MagicMock suitable for use as a patched smtplib.SMTP.

    The important detail: ``_sync_send_email`` uses SMTP as a context manager
    (``with smtplib.SMTP(...) as smtp:``).  MagicMock.__enter__ returns a
    *child* mock by default, so ``smtp.starttls(...)`` would be recorded on the
    child, not on the mock we hold.  Setting ``__enter__.return_value`` to the
    same mock ensures that all assertions target the correct object.
    """
    m = mock.MagicMock()
    m.__enter__.return_value = m
    return m


# ── Mini debug SMTP server (stdlib-only, no external deps) ───────


class _MiniSMTPServer:
    """Minimal single-connection SMTP server for integration testing.

    Listens on a random port, speaks just enough SMTP to receive one
    message, and captures envelope + data in ``received_messages``.

    Does NOT implement real TLS negotiation — when STARTTLS is issued the
    server acknowledges it but continues in plain text.  Tests that need
    TLS validation should mock ``smtplib.SMTP`` instead.
    """

    def __init__(self):
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self.port: int = 0
        self.host: str = "127.0.0.1"
        self.received_messages: list[dict] = []
        self._ready = threading.Event()
        self._stop = threading.Event()

    # ── public API ──────────────────────────────────────────

    def start(self) -> int:
        """Bind, start accept loop in a daemon thread, return *port*."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, 0))
        self._sock.listen(1)
        self._sock.settimeout(5.0)
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
        return self.port

    def stop(self):
        """Signal the accept loop to exit and join the thread."""
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=5)

    # ── internals ───────────────────────────────────────────

    def _serve(self):
        self._ready.set()
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except (socket.timeout, OSError):
                continue
            try:
                self._handle_client(conn)
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _handle_client(self, conn: socket.socket):
        conn.settimeout(3.0)
        rf = conn.makefile("r", encoding="utf-8", errors="replace")

        # Greeting
        conn.sendall(b"220 localhost ESMTP MiniDebug\r\n")

        mailfrom = ""
        rcpttos: list[str] = []

        for line in rf:
            line = line.strip()
            upper = line.upper()

            if upper.startswith("EHLO") or upper.startswith("HELO"):
                conn.sendall(b"250-localhost\r\n250 STARTTLS\r\n")
            elif upper == "STARTTLS":
                # Acknowledge but stay in plain text — real TLS
                # negotiation is not needed for plain-smtp tests.
                conn.sendall(b"220 Ready to start TLS\r\n")
            elif upper.startswith("MAIL FROM:"):
                mailfrom = line[10:].strip("<> ")
                conn.sendall(b"250 Ok\r\n")
            elif upper.startswith("RCPT TO:"):
                rcpt = line[8:].strip("<> ")
                rcpttos.append(rcpt)
                conn.sendall(b"250 Ok\r\n")
            elif upper == "DATA":
                conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                data_lines: list[str] = []
                for data_line in rf:
                    if data_line.rstrip("\r\n") == ".":
                        break
                    # Un-stuff leading dot (transparency)
                    if data_line.startswith(".."):
                        data_line = data_line[1:]
                    data_lines.append(data_line)
                data = "".join(data_lines)
                self.received_messages.append({
                    "mailfrom": mailfrom,
                    "rcpttos": list(rcpttos),
                    "data": data,
                })
                conn.sendall(b"250 Ok: queued\r\n")
            elif upper == "QUIT":
                conn.sendall(b"221 Bye\r\n")
                break
            else:
                conn.sendall(b"500 Unrecognized command\r\n")


# ═══════════════════════════════════════════════════════════════
# Integration tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSMTPIntegration:
    """End-to-end SMTP tests using a local debug server and patched SMTP."""

    # ── Real socket-server tests ────────────────────────────

    def test_send_email_to_local_smtp_server(self):
        """A plain SMTP message is received intact by the local debug server."""
        server = _MiniSMTPServer()
        port = server.start()
        try:
            msg = MIMEText("Hello, this is a test email body.", "plain", "utf-8")
            msg["Subject"] = "Integration Test Email"
            msg["From"] = "sender@test.local"
            msg["To"] = "recipient@test.local"

            with smtplib.SMTP(server.host, port, timeout=10) as smtp:
                smtp.send_message(msg)

            assert len(server.received_messages) == 1
            rcvd = server.received_messages[0]
            assert "recipient@test.local" in rcvd["rcpttos"]
            assert "sender@test.local" in rcvd["mailfrom"]

            # smtplib.send_message may base64-encode the body — use
            # email.parser to decode and verify the content.
            parsed = Parser().parsestr(rcvd["data"])
            assert parsed["Subject"] == "Integration Test Email"
            assert parsed["From"] == "sender@test.local"
            assert parsed["To"] == "recipient@test.local"
            body = parsed.get_payload(decode=True)
            assert body is not None
            assert b"Hello, this is a test email body." in body
        finally:
            server.stop()

    def test_send_email_with_multiple_recipients(self):
        """Multiple RCPT TO addresses are all captured."""
        server = _MiniSMTPServer()
        port = server.start()
        try:
            msg = MIMEText("Multi-recipient body.", "plain", "utf-8")
            msg["Subject"] = "Multi Test"
            msg["From"] = "sender@test.local"
            msg["To"] = "alice@test.local, bob@test.local"

            with smtplib.SMTP(server.host, port, timeout=10) as smtp:
                smtp.send_message(msg)

            assert len(server.received_messages) == 1
            rcvd = server.received_messages[0]
            assert "alice@test.local" in rcvd["rcpttos"]
            assert "bob@test.local" in rcvd["rcpttos"]
        finally:
            server.stop()

    # ── _sync_send_email integration (patched smtplib.SMTP) ──

    def test_sync_send_email_full_flow(self):
        """_sync_send_email performs the correct SMTP call sequence."""
        msg = MIMEText("Test body content.", "plain", "utf-8")
        msg["Subject"] = "Test Subject"
        msg["From"] = "from@test.local"
        msg["To"] = "to@test.local"

        mock_smtp = _make_mock_smtp()
        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", True):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", ""):
                    _sync_send_email(
                        host="smtp.example.com",
                        port=587,
                        user="testuser",
                        password="testpass",
                        msg=msg,
                    )

        # Verify the full SMTP handshake
        mock_smtp.starttls.assert_called_once()
        # Verify starttls received an SSLContext with correct verify settings
        ctx_arg = mock_smtp.starttls.call_args.kwargs.get("context")
        assert ctx_arg is not None
        assert isinstance(ctx_arg, ssl.SSLContext)
        assert ctx_arg.verify_mode == ssl.CERT_REQUIRED
        assert ctx_arg.check_hostname is True

        mock_smtp.login.assert_called_once_with("testuser", "testpass")
        mock_smtp.send_message.assert_called_once()

        # Verify the sent message has correct content
        sent_msg = mock_smtp.send_message.call_args.args[0]
        assert sent_msg["Subject"] == "Test Subject"
        assert sent_msg["From"] == "from@test.local"
        assert sent_msg["To"] == "to@test.local"

    def test_sync_send_email_no_auth_when_user_empty(self):
        """When SMTP user is empty, login() is skipped (no-auth relay)."""
        msg = MIMEText("Body", "plain", "utf-8")
        msg["Subject"] = "S"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"

        mock_smtp = _make_mock_smtp()
        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", True):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", ""):
                    _sync_send_email("localhost", 587, "", "", msg)

        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_not_called()
        mock_smtp.send_message.assert_called_once()

    # ── SSL context / certificate verification ─────────────

    def test_email_verify_cert_disabled_warns(self, caplog):
        """When smtp_verify_cert=False, the security warning is logged."""
        msg = MIMEText("Body", "plain", "utf-8")
        msg["Subject"] = "S"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"

        mock_smtp = _make_mock_smtp()
        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", False):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", ""):
                    with caplog.at_level(logging.WARNING, logger="notify"):
                        _sync_send_email("localhost", 587, "", "", msg)

        assert "SMTP 证书验证已关闭" in caplog.text

        # Context should have verification disabled
        ctx_arg = mock_smtp.starttls.call_args.kwargs.get("context")
        assert ctx_arg.verify_mode == ssl.CERT_NONE
        assert ctx_arg.check_hostname is False

    def test_email_verify_cert_enabled_no_warning(self, caplog):
        """When smtp_verify_cert=True, no security warning is logged."""
        msg = MIMEText("Body", "plain", "utf-8")
        msg["Subject"] = "S"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"

        mock_smtp = _make_mock_smtp()
        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", True):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", ""):
                    with caplog.at_level(logging.WARNING, logger="notify"):
                        _sync_send_email("localhost", 587, "", "", msg)

        assert "SMTP 证书验证已关闭" not in caplog.text

    def test_ssl_error_propagates_no_silent_downgrade(self):
        """TLS cert failure must raise ssl.SSLError (no silent downgrade)."""
        msg = MIMEText("Body", "plain", "utf-8")
        msg["Subject"] = "S"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"

        mock_smtp = _make_mock_smtp()
        mock_smtp.starttls.side_effect = ssl.SSLError(
            "certificate verify failed: self-signed certificate"
        )

        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", True):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", ""):
                    with pytest.raises(ssl.SSLError, match="certificate verify failed"):
                        _sync_send_email("localhost", 587, "", "", msg)

    def test_custom_ca_bundle_is_applied(self):
        """When smtp_ca_bundle is set, the SSL context loads it."""
        msg = MIMEText("Body", "plain", "utf-8")
        msg["Subject"] = "S"
        msg["From"] = "a@b.com"
        msg["To"] = "c@d.com"

        mock_smtp = _make_mock_smtp()
        with mock.patch("smtplib.SMTP", return_value=mock_smtp):
            with mock.patch("app.core.config.settings.smtp_verify_cert", True):
                with mock.patch("app.core.config.settings.smtp_ca_bundle", "/etc/ssl/custom-ca.pem"):
                    with mock.patch.object(
                        ssl.SSLContext, "load_verify_locations"
                    ) as mock_load:
                        _sync_send_email("localhost", 587, "", "", msg)

        # load_verify_locations should have been called with the CA bundle path
        mock_load.assert_called()
        assert mock_load.call_args.args == ("/etc/ssl/custom-ca.pem",)
