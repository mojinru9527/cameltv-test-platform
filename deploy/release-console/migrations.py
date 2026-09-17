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

# C249-4：迁移校验无论成功失败都打印目标 revision 与实际 current，失败时控制面
# 才能把「迁移没生效」写进发布事件，而不是只留一句 `rc=1`。
STATUS_MARKER = "CAMELTV_MIGRATION"

_REVISION = re.compile(r"^[0-9a-zA-Z_]{1,128}$")
_NOISE_PREFIXES = ("INFO", "Running", "ERROR", "FAILED", "Context impl", "Will assume")
_STATUS = re.compile(rf"{STATUS_MARKER} target=(\S+) actual=(\S+)")


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
    # 先取实际 current 并打印（成功/失败都会进控制面日志），再断言等于 target。
    # 这样校验失败时输出里有 `target=X actual=Y`，控制面可直接落进发布事件。
    verify = (
        f"migration_actual=$("
        f"{current} 2>/dev/null | tail -n 1 | awk '{{print $1}}'); "
        f"printf '{STATUS_MARKER} target=%s actual=%s\\n' "
        f"{shlex.quote(resolved)} \"${{migration_actual:-<none>}}\"; "
        f"test \"${{migration_actual}}\" = {shlex.quote(resolved)}"
    )
    return [upgrade, verify]


def migration_status(output: str) -> dict | None:
    """Parse the last ``CAMELTV_MIGRATION`` status line from remote output."""
    for raw in reversed((output or "").splitlines()):
        match = _STATUS.search(raw)
        if match:
            return {"target": match.group(1), "actual": match.group(2)}
    return None


def migration_failure_detail(manifest: dict, output: str) -> str | None:
    """Return ``migration target=X actual=Y`` when the migration did not land.

    Returns ``None`` when the output carries no status line (the failure
    happened elsewhere) or when the observed revision already equals the
    manifest target, so callers can fall back to their plain failure reason.
    """
    status = migration_status(output)
    if status is None:
        return None
    try:
        expected = target_revision(manifest)
    except (MigrationNotConfigured, MigrationFailed):
        expected = ""
    if expected and status["actual"] == expected:
        return None
    if expected:
        return f"migration target={expected} actual={status['actual']}"
    return f"migration actual={status['actual']}"


def migration_success_detail(manifest: dict, output: str) -> str | None:
    """Return ``migration target=X actual=X`` when the migration verified."""
    status = migration_status(output)
    if status is None:
        return None
    try:
        expected = target_revision(manifest)
    except (MigrationNotConfigured, MigrationFailed):
        return None
    if status["actual"] != expected:
        return None
    return f"migration target={expected} actual={status['actual']}"
