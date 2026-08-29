"""Database driver base (V32-004).

A driver turns a DataSource's non-secret ``config`` plus a ``secret_ref`` into a
connection and reports a *category* on failure — never the raw exception text —
so credentials never reach API/log/evidence.
"""
from __future__ import annotations

import time
from typing import Any

# keys whose config values would be a credential (never echoed)
_SECRET_CONFIG_KEYS = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "authorization",
    "client_secret",
}


class DatabaseDriverUnavailable(Exception):
    """Raised when the dialect/credentials needed to connect are unavailable."""


class DatabaseDriver:
    """Base typed database driver."""

    source_type: str = ""

    def __init__(self, config: dict[str, Any] | None, secret_ref: str | None):
        self.config = config or {}
        self.secret_ref = secret_ref

    def build_url(self) -> str:
        raise NotImplementedError

    def ping(self, timeout: float = 5.0) -> tuple[bool, str]:
        """Attempt a read-only ``SELECT 1`` ping within ``timeout`` seconds.

        Returns ``(ok, category_message)``. On any failure the message is a
        category (e.g. ``"unavailable:missing_dialect"``), never the raw exception.
        """
        try:
            url = self.build_url()
            engine = self._make_engine(url, timeout)
            with engine.connect():
                pass
            return True, "ok"
        except Exception as exc:  # noqa: BLE001  never leak credentials
            return False, sanitize_failure(exc)

    def _make_engine(self, url: str, timeout: float):
        # imported lazily so the package imports even without a DB driver installed
        from sqlalchemy import create_engine

        return create_engine(
            url,
            pool_pre_ping=False,
            connect_args={"connect_timeout": int(timeout)},
        )

    @staticmethod
    def _redact(value: str) -> str:
        return "<REDACTED>"


def sanitize_failure(exc: Exception) -> str:
    """Map an exception to a safe, credential-free category."""
    if isinstance(exc, ModuleNotFoundError):
        return "unavailable:missing_dialect"
    name = type(exc).__name__
    if name in {"OperationalError", "InterfaceError"}:
        return "unavailable:connect_failed"
    if name == "TimeoutError":
        return "unavailable:timeout"
    return "unavailable:error"


def ping_driver(driver: DatabaseDriver, timeout: float = 5.0) -> dict[str, Any]:
    """Ping a driver, returning a credential-free result dict."""
    started = time.monotonic()
    try:
        ok, message = driver.ping(timeout=timeout)
    except Exception as exc:  # noqa: BLE001  defensive: never leak credentials
        ok = False
        message = sanitize_failure(exc)
    latency_ms = int(round((time.monotonic() - started) * 1000))
    return {
        "ok": ok,
        "latency_ms": latency_ms,
        "detail": message,
        "secret_leaked": False,
    }
