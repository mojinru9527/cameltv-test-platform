"""Database migration step for production releases (ADR-0015 §4).

The API container does **not** run migrations on startup, so a release that ships
code depending on a new schema could go live against an unmigrated database
(2026-09-17 incident: ``ai_jobs.model_name does not exist`` → 500 on
``/api/v1/ai/jobs``). This module owns the release-time migration contract:

* the manifest must carry a **real** ``database.target_revision`` (never the
  ``see-verified-head`` placeholder used before this batch);
* the migration runs as an isolated one-off container **before** the new
  application containers are started;
* the applied revision is verified against the manifest target, so a mismatch
  aborts the release instead of shipping a half-migrated production;
* rollbacks never migrate (see ``tencent_executor.rollback_runtime_override``):
  an old image cannot resolve a newer revision.
"""
from __future__ import annotations

import re
import shlex

PLACEHOLDER_REVISION = "see-verified-head"

_REVISION = re.compile(r"^[0-9a-zA-Z_]{1,128}$")
_NOISE_PREFIXES = ("INFO", "Running", "ERROR", "FAILED", "Context impl", "Will assume")


class MigrationNotConfigured(RuntimeError):
    """The manifest does not carry a usable target revision."""


class MigrationFailed(RuntimeError):
    """The migration step could not be planned or verified."""


def target_revision(manifest: dict) -> str:
    """Return the validated target revision from a registered manifest."""
    database = manifest.get("database") if isinstance(manifest, dict) else None
    target = str((database or {}).get("target_revision", "")).strip()
    if not target or target == PLACEHOLDER_REVISION:
        raise MigrationNotConfigured(
            "manifest database.target_revision must be a real alembic revision "
            f"(got {target or 'empty'!r})"
        )
    if not _REVISION.match(target):
        raise MigrationFailed(f"invalid target revision: {target!r}")
    return target


def single_head(output: str) -> str:
    """Parse ``alembic heads`` output, requiring exactly one head."""
    heads = set()
    for raw in (output or "").splitlines():
        line = raw.strip()
        if not line or line.startswith(_NOISE_PREFIXES):
            continue
        heads.add(line.split()[0])
    if len(heads) != 1:
        raise MigrationFailed(f"expected exactly one alembic head, got {sorted(heads)}")
    return heads.pop()


def migration_commands(compose, *, target: str) -> list[str]:
    """Build the remote commands that migrate and verify production.

    ``compose`` is a callable that renders a ``docker compose`` invocation
    (``TencentSshExecutor._compose``); keeping it injected lets the planning
    logic be unit tested without SSH.
    """
    if not _REVISION.match(str(target or "")):
        raise MigrationFailed(f"invalid target revision: {target!r}")
    resolved = str(target)
    upgrade = compose(
        "run", "--rm", "-T", "--no-deps", "backend",
        "python", "-m", "alembic", "upgrade", resolved,
    )
    current = compose(
        "run", "--rm", "-T", "--no-deps", "backend",
        "python", "-m", "alembic", "current",
    )
    verify = (
        "test \"$("
        f"{current} 2>/dev/null | tail -n 1 | awk '{{print $1}}'"
        f")\" = {shlex.quote(resolved)}"
    )
    return [upgrade, verify]
