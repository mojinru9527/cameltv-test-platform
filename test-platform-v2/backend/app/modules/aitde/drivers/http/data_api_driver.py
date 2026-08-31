"""AITDE V3.9-R2 (DATA-002) — DataApiDriver: real HTTP calls for API_BUILDER.

Turns a DataSource API ``config`` + ``secret_ref`` into typed POST / GET / DELETE
calls against a test-environment REST API. Only the ``secret_ref`` (a reference
into the secret store) is carried and applied to the ``Authorization`` header at
transport time; the raw secret value is never stored, logged, or echoed back.

Failures are reported by a stable, credential-free ``code`` (``CREATE_REJECTED``
/ ``VERIFY_FAILED`` / ``REQUEST_FAILED``) — never the raw exception text — so the
API key and request body never reach API/log/evidence.
"""
from __future__ import annotations

from typing import Any

import httpx


class DataApiError(Exception):
    """Raised when an API call is rejectable or failed.

    Carries a stable ``code`` so callers never parse raw HTTP text:
    ``CREATE_REJECTED`` / ``VERIFY_FAILED`` / ``REQUEST_FAILED``.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class DataApiDriver:
    """Minimal, policy-constrained HTTP client for a DATA-source REST API."""

    source_type = "API"

    def __init__(
        self,
        config: dict[str, Any] | None,
        secret_ref: str | None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.config = config or {}
        self.secret_ref = secret_ref
        self._transport = transport

    # ── endpoint helpers ───────────────────────────────────────────────────
    def base_url(self) -> str:
        return str(self.config.get("base_url") or "").rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        scheme = str(self.config.get("auth_scheme") or "Bearer").strip()
        # secret_ref is the reference into the secret store; the store resolves
        # it to a live value out-of-band. Never a literal credential in code.
        if self.secret_ref:
            headers["Authorization"] = f"{scheme} {self.secret_ref}"
        return headers

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url(),
            headers=self._headers(),
            timeout=float(self.config.get("timeout", 15)),
            transport=self._transport,
        )

    # ── typed verbs ────────────────────────────────────────────────────────
    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """POST a JSON payload to a create endpoint."""
        with self._client() as client:
            try:
                resp = client.post(path, json=payload)
            except Exception as exc:  # noqa: BLE001 — category only
                raise DataApiError("REQUEST_FAILED", _safe_category(exc)) from exc
            status, data = _safe_json(resp)
            if status not in (200, 201):
                raise DataApiError("CREATE_REJECTED", f"status={status}")
            return status, data

    def get(self, path: str) -> tuple[int, dict[str, Any]]:
        """GET a resource (used to VERIFY a created entity physically exists)."""
        with self._client() as client:
            try:
                resp = client.get(path)
            except Exception as exc:  # noqa: BLE001 — category only
                raise DataApiError("REQUEST_FAILED", _safe_category(exc)) from exc
            status, data = _safe_json(resp)
            if status >= 400:
                raise DataApiError("VERIFY_FAILED", f"status={status}")
            return status, data

    def delete(self, path: str) -> int:
        """DELETE a created resource (used by compensation)."""
        with self._client() as client:
            try:
                resp = client.delete(path)
            except Exception as exc:  # noqa: BLE001 — category only
                raise DataApiError("REQUEST_FAILED", _safe_category(exc)) from exc
            return int(resp.status_code)


def _safe_json(resp: httpx.Response) -> tuple[int, dict[str, Any]]:
    """Return ``(status, json_body)`` with a guarded body decode."""
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body is fine, treat as empty
        body = {}
    if not isinstance(body, dict):
        body = {}
    return int(resp.status_code), body


def _safe_category(exc: Exception) -> str:
    """Map an httpx transport failure to a credential-free category."""
    name = type(exc).__name__
    if name in {"ConnectError", "ConnectTimeout", "HTTPError", "NetworkError"}:
        return "unavailable:connect_failed"
    if name in {"TimeoutException", "ReadTimeout", "PoolTimeout"}:
        return "unavailable:timeout"
    return "unavailable:error"
