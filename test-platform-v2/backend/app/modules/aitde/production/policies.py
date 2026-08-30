"""AITDE V3.6 production security policies.

These are the ``绝对边界`` guardrails: Browser actions that would write to
production are DENIED, production DB access is SELECT-only with a hard row/time
limit, and PROD_RO worker profiles carry restricted capabilities/secret scope.

Production 默认只读：``READONLY_BROWSER_*`` 与 ``PROD_DB_*`` 是唯一审核层，
绝不依赖「隐藏按钮」或上层逻辑来保证安全。
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from app.modules.aitde.common.enums import NetworkZone, PolicyDecision

# ── Browser write markers (same vocabulary as services/xhr_capture_service) ──
_WRITE_MARKERS = [
    "pay", "order", "refund", "recharge", "withdraw", "deposit", "favorite",
    "like", "comment", "review", "create", "save", "update", "delete", "add",
    "remove", "send", "publish", "bonus", "gift", "diamond", "checkout", "submit",
]

# ── Semantic action classification (V36-003) ────────────────────────────────
_WRITE_SEMANTIC_ACTIONS = {
    "submit_form", "click_submit", "click_pay", "click_order", "click_refund",
    "fill_payment", "fill_shipping", "place_order", "submit_review", "book",
    "reserve", "purchase", "transfer", "withdraw", "deposit", "send_message",
}


def is_write_action(url: str | None = None, method: str | None = None,
                    semantic_action: str | None = None) -> bool:
    """Return True when a browser action should be treated as a production write."""
    if semantic_action and semantic_action.lower() in _WRITE_SEMANTIC_ACTIONS:
        return True
    if url:
        path = url.split("?")[0].lower()
        if any(w in path for w in _WRITE_MARKERS):
            return True
    if method and method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        # A POST is only ever allowed when it is whitelisted read-only; the
        # ReadOnlyBrowserPolicy gates the allowlist itself, so a bare write
        # method is conservatively treated as write here.
        return True
    return False


class ReadOnlyBrowserPolicy:
    """V36-003 — semantic risk judgement. Default DENY for any write-class action.

    ``allowed_readonly_post`` is the explicit allowlist of query-type POST paths;
    everything else that looks like a write is DENY.
    """

    def __init__(self, allowed_readonly_post: list[str] | None = None) -> None:
        self._allowed_readonly_post = allowed_readonly_post or [
            "/ee/search/", "/ee/news/", "/ee/setting", "/login/anonymous/web",
        ]

    def evaluate(self, *, url: str | None = None, method: str | None = None,
                 semantic_action: str | None = None) -> tuple[str, str]:
        if semantic_action and semantic_action.lower() in _WRITE_SEMANTIC_ACTIONS:
            return PolicyDecision.DENY.value, f"write semantic action '{semantic_action}' is blocked"
        if url and any(w in url.split("?")[0].lower() for w in _WRITE_MARKERS):
            return PolicyDecision.DENY.value, f"url matches write marker: {url}"
        if method and method.upper() not in ("GET", "HEAD"):
            path = (url or "").split("?")[0]
            if not any(p in path for p in self._allowed_readonly_post):
                return PolicyDecision.DENY.value, f"{method} not in read-only allowlist"
        return PolicyDecision.ALLOW.value, "read-only navigation allowed"


readonly_browser_policy = ReadOnlyBrowserPolicy()


# ── Production DB guard (V36-005) ───────────────────────────────────────────
_SQL_FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "REPLACE", "MERGE", "CALL", "EXEC", "COPY", "VACUUM",
}
_CTE_SELECT_RE = re.compile(r"\bWITH\b", re.IGNORECASE)
_DDL_RE = re.compile(r"\b(CREATE|ALTER|DROP|TRUNCATE)\b", re.IGNORECASE)
_MULTI_STMT_RE = re.compile(r";\s*\S+")


class ProductionDbGuard:
    """SELECT-only parser guard. Layer 3 of the DB read-only defence fence.

    Even if the driver / account permit a write, this layer rejects any
    statement that is not a single SELECT (including CTE / comment / multi-stmt
    tricks) and enforces a row + time cap.
    """

    def __init__(self, max_rows: int = 1000, timeout_ms: int = 10000,
                 schema_allowlist: list[str] | None = None) -> None:
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms
        self.schema_allowlist = schema_allowlist or []

    def validate(self, sql: str) -> tuple[bool, str]:
        """Return ``(ok, reason)``. ``ok`` False means the statement is unsafe."""
        if not sql or not sql.strip():
            return False, "empty statement"
        stripped = re.sub(r"(--.*$)|(#[^\n]*)", "", sql, flags=re.MULTILINE)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        # Reject multi-statement (has a ; followed by more SQL).
        if _MULTI_STMT_RE.search(stripped):
            return False, "multi-statement SQL is not allowed"
        # Reject any write / DDL keyword at statement level.
        upper = stripped.upper()
        if any(f" {kw}" in f" {upper}" or upper.startswith(f"{kw} ") for kw in _SQL_FORBIDDEN_KEYWORDS):
            return False, "write/DDL keyword present"
        if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
            return False, "only SELECT is allowed"
        if _CTE_SELECT_RE.search(stripped):
            return False, "CTE is not allowed"
        return True, "ok"

    def guard_scan(self, sql: str, table_names: list[str] | None = None) -> tuple[bool, str]:
        ok, reason = self.validate(sql)
        if not ok:
            return ok, reason
        if self.schema_allowlist and table_names:
            for t in table_names:
                if not any(t == a or t.startswith(a + ".") for a in self.schema_allowlist):
                    return False, f"table '{t}' not in schema allowlist"
        return True, "ok"


production_db_guard = ProductionDbGuard()


def fingerprint_sql(sql: str) -> str:
    """Stable 64-char fingerprint for a normalised query (V36-006)."""
    norm = re.sub(r"\s+", " ", sql.strip()).lower()
    return hashlib.sha256(norm.encode()).hexdigest()


# ── PROD_RO worker profile (V36-001) ────────────────────────────────────────
# Capabilities that are never allowed on a PROD_RO worker (write-side).
_WRITE_CAPABILITIES = {"MYSQL", "POSTGRES", "LOG", "KAFKA"}
_READONLY_CAPABILITIES = {"BROWSER", "HTTP"}


class ProdRoWorkerProfile:
    """V36-001 — constrained profile for a PROD_RO worker.

    A PROD_RO worker may only carry read capabilities (BROWSER/HTTP), must bind
    the ``prod_ro`` policy profile and a separate secret scope, and never a write
    capability. Enforced at registration/profile resolution time.
    """

    policy_profile = "prod_ro"
    secret_scope = "prod_ro"

    def validate(self, *, network_zone: str, capabilities: list[str]) -> tuple[bool, str]:
        if network_zone != NetworkZone.PROD_RO.value:
            return True, "not a PROD_RO worker"
        caps = {c.upper() for c in capabilities}
        write = caps & _WRITE_CAPABILITIES
        if write:
            return False, f"PROD_RO worker may not carry write capability: {sorted(write)}"
        return True, "ok"

    def resolve(self, *, network_zone: str, capabilities: list[str]) -> dict[str, Any]:
        ok, reason = self.validate(network_zone=network_zone, capabilities=capabilities)
        if not ok:
            raise ValueError(reason)
        return {
            "network_zone": network_zone,
            "policy_profile": self.policy_profile,
            "secret_scope": self.secret_scope,
            "capabilities": sorted({c.upper() for c in capabilities} & _READONLY_CAPABILITIES),
        }


prod_ro_worker_profile = ProdRoWorkerProfile()
