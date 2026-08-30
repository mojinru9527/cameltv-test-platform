"""AITDE V3.4 WorkerSecretResolver (V34-009).

Resolves a ``SecretRef`` to its value ONLY at worker runtime, in process memory,
then discards it. The Control Plane never holds the value; only the metadata
(provider + external_ref + scope) is persisted and returned to the frontend.

Security invariants (plan §5):
- Secret value NEVER enters TaskQueue/Workflow History, CommandPlan JSON,
  ExecutionStep input/output, Evidence, AI prompt, or ordinary logs.
- ``redact`` masks a resolved value before it could be serialized.
- The resolver is a best-effort local provider (env / file / literal); a real
  Secret Manager / vault can be dropped in by adding a provider branch.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from app.modules.aitde.common.enums import SecretRefStatus


class WorkerSecretResolver:
    """Resolve a SecretRef metadata into a one-shot value at runtime."""

    def resolve(self, secret_ref: Any) -> str | None:
        """Return the secret value, or None when the ref is inactive/unresolvable.

        The value is loaded, returned once and never cached; callers must
        ``redact`` it if it leaves process memory.
        """
        if getattr(secret_ref, "status", SecretRefStatus.ACTIVE.value) != SecretRefStatus.ACTIVE.value:
            return None
        provider = (getattr(secret_ref, "provider", "") or "env").lower()
        external_ref = getattr(secret_ref, "external_ref", "") or ""
        scope = _parse_scope(getattr(secret_ref, "scope_json", "{}"))

        # env provider: the external_ref names an environment variable.
        if provider == "env":
            return os.environ.get(external_ref)

        # file provider: external_ref is a path; read once into memory.
        if provider == "file":
            path = Path(external_ref)
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except OSError:
                    return None
            return None

        # literal provider: scope carries the value (dev/test convenience only;
        # never for production secrets).
        if provider == "literal":
            value = scope.get("value") if isinstance(scope, dict) else None
            return str(value) if value is not None else None

        return None

    def redact(self, value: str | None) -> str:
        """Mask a value for any output that leaves the worker (never the value)."""
        if value is None:
            return "<redacted>"
        return f"<redacted:{hashlib.sha256(value.encode()).hexdigest()[:8]}>"

    def contains_secret(self, text: str, refs: list[Any]) -> bool:
        """True when any resolved secret value appears verbatim in ``text``.

        Used to assert that Secret values never leak into Workflow History /
        logs during tests and audits (V34-009 "Temporal History 无 secret").
        """
        for ref in refs:
            try:
                value = self.resolve(ref)
            except Exception:  # noqa: BLE001 — unresolvable ref never matches
                continue
            if value and value in text:
                return True
        return False


def _parse_scope(raw: str) -> Any:
    import json

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


worker_secret_resolver = WorkerSecretResolver()
