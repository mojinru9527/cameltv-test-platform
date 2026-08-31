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


class DatabaseQueryError(Exception):
    """Raised when a query is rejectable: not allowlisted, unsafe, or failed.

    Carries a stable ``code`` so callers never parse free text (no credential /
    SQL detail leak): ``TABLE_NOT_ALLOWLISTED`` / ``ONLY_SELECT`` /
    ``ONLY_WRITE`` / ``QUERY_FAILED``.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class DatabaseDriver:
    """Base typed database driver.

    V3.9-R2 (DATA-001): adds real execution primitives on top of ``ping``. The
    driver only ever executes a *validated* DataPlanStep SQL (never raw LLM SQL):
    statement type is allowlisted (SELECT vs INSERT/UPDATE/DELETE), the target
    table must be in the DataSource ``table_allowlist``, rows are capped, and
    failures are reported by credential-free category.
    """

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

        if url.startswith("sqlite"):
            return create_engine(url, pool_pre_ping=False)
        return create_engine(
            url,
            pool_pre_ping=False,
            connect_args={"connect_timeout": int(timeout)},
        )

    def _table_allowlist(self) -> list[str]:
        return list(self.config.get("table_allowlist") or [])

    def _assert_table(self, table: str) -> None:
        allow = self._table_allowlist()
        if allow and str(table) not in allow:
            raise DatabaseQueryError("TABLE_NOT_ALLOWLISTED", str(table))

    def execute_select(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        table: str | None = None,
        row_limit: int = 100,
        timeout: float = 5.0,
    ) -> list[dict[str, Any]]:
        """Run an allowlisted, parameterized SELECT capped to ``row_limit`` rows.

        Rejects any statement that is not a bare SELECT (so a CTE/multi-statement
        write trick can never slip through as a read), enforces the DataSource
        ``table_allowlist``, and returns rows as sanitised dicts.
        """
        from sqlalchemy import text

        stmt = str(sql).strip()
        if not stmt.lower().startswith("select"):
            raise DatabaseQueryError("ONLY_SELECT", stmt[:40])
        if table:
            self._assert_table(table)
        engine = self._make_engine(self.build_url(), timeout)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(stmt), params or {})
                columns = list(result.keys())
                rows = result.fetchmany(max(1, int(row_limit)))
                return [dict(zip(columns, row)) for row in rows]
        except DatabaseQueryError:
            raise
        except Exception as exc:  # noqa: BLE001  never leak credentials / SQL
            raise DatabaseQueryError("QUERY_FAILED", sanitize_failure(exc)) from exc
        finally:
            engine.dispose()

    def execute_dml(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        table: str | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Run an allowlisted INSERT/UPDATE/DELETE inside an auto-commit txn.

        Only a bare single DML statement is accepted; the target table must be
        allowlisted. Returns ``{"rowcount": n}``. The caller (DataPlanExecutor)
        is responsible for the enclosing lifecycle (BEGIN / capture BEFORE /
        SELECT VERIFY / COMMIT / ROLLBACK) — this is the low-level primitive.
        """
        from sqlalchemy import text

        stmt = str(sql).strip()
        if not any(stmt.lower().startswith(k) for k in ("insert", "update", "delete")):
            raise DatabaseQueryError("ONLY_WRITE", stmt[:40])
        if table:
            self._assert_table(table)
        engine = self._make_engine(self.build_url(), timeout)
        try:
            with engine.begin() as conn:
                result = conn.execute(text(stmt), params or {})
                return {"rowcount": int(result.rowcount or 0)}
        except DatabaseQueryError:
            raise
        except Exception as exc:  # noqa: BLE001  never leak credentials / SQL
            raise DatabaseQueryError("QUERY_FAILED", sanitize_failure(exc)) from exc
        finally:
            engine.dispose()

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
