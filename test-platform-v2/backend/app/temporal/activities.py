"""AITDE V3.4 Execution Activities (V34-004).

Temporal Activity wrappers for the ScenarioExecutionWorkflow. Each Activity is
declared with a start/schedule timeout and retry policy in the workflow; replayed
deliveries are deduplicated by the IdempotencyService so a crash/replay never
repeats a business side effect.

Activities run OUTSIDE the workflow sandbox, so they may open a DB session and
delegate to the existing V3.2 data runtime, V3.3 command/action executor and the
execution evidence/outcome services. The activity payload carries the ``run_id``
+ ``scenario_version_id`` when real execution is requested; absent a ``run_id``
the activity falls back to a deterministic echo (used by the skeleton test).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from temporalio import activity


@dataclass
class StepResult:
    """A durable step result: status + summary + optional evidence refs."""

    status: str
    summary: str = ""
    evidence_refs: list[str] | None = None


# Pluggable executor hooks (default = pass-through echo). These are replaced by
# the real driver closures as the version grows — they must stay pure/deterministic.
_EXEC_HOOKS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def register_exec_hook(step_key: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """Register (or replace) the executor hook for a step key."""
    _EXEC_HOOKS[step_key] = fn


def _echo(payload: dict[str, Any]) -> dict[str, Any]:
    return {"echo": payload}


# ── idempotency guard (V34-012) ──────────────────────────────────────────────


def _run_idempotent(step_key: str, payload: dict[str, Any]):
    """Return (executed_result) with a DB-scoped idempotency key.

    When the payload carries a ``run_id`` a key is acquired for
    ``(scope=step_key, key=run_id)``; a duplicate delivery returns the prior
    result marker instead of repeating the side effect. The guard is best-effort:
    if the idempotency store isn't provisioned (e.g. an in-memory Temporal test
    whose SQLite has no runtime tables) it degrades to "first delivery" so the
    Activity still executes deterministically.
    """
    run_id = payload.get("run_id")
    if not run_id:
        return None
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        from app.modules.aitde.common.enums import IdempotencyStatus, RuntimeResourceType
        from app.modules.aitde.workflow.policy import idempotency_service

        row, created = idempotency_service.acquire(
            db, step_key, str(run_id), RuntimeResourceType.ACTIVITY.value
        )
        if not created:
            # Duplicate delivery — skip the business side effect.
            return {"duplicate": True, "status": IdempotencyStatus.PENDING.value}
        db.commit()
        return None  # first delivery: caller executes + marks COMPLETED
    except Exception:  # noqa: BLE001 — store not provisioned: proceed as first
        db.rollback()
        return None
    finally:
        db.close()


def _mark_idempotent_done(step_key: str, payload: dict[str, Any]) -> None:
    run_id = payload.get("run_id")
    if not run_id:
        return
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        from app.modules.aitde.common.enums import IdempotencyStatus
        from app.modules.aitde.workflow import repository as wf_repo

        wf_repo.mark_idempotency_done(db, step_key, str(run_id), IdempotencyStatus.COMPLETED.value)
    except Exception:  # noqa: BLE001 — store not provisioned: no-op
        db.rollback()
    finally:
        db.close()


def _run_inner(step_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    hook = _EXEC_HOOKS.get(step_key)
    dup = _run_idempotent(step_key, payload)
    if dup is not None:
        return dup
    try:
        if hook is not None:
            return hook(payload)
        return {"step": step_key, **_echo(payload)}
    finally:
        _mark_idempotent_done(step_key, payload)


@activity.defn
async def capture_environment_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("capture_environment_snapshot", payload)


@activity.defn
async def plan_data(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("plan_data", payload)


@activity.defn
async def ensure_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("ensure_fixture", payload)


@activity.defn
async def resolve_command_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("resolve_command_plan", payload)


@activity.defn
async def policy_check(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("policy_check", payload)


@activity.defn
async def execute_commands(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("execute_commands", payload)


@activity.defn
async def evaluate_oracles(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("evaluate_oracles", payload)


@activity.defn
async def collect_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("collect_evidence", payload)


@activity.defn
async def classify_outcome(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("classify_outcome", payload)


@activity.defn
async def cleanup_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("cleanup_fixture", payload)


@activity.defn
async def build_replay(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("build_replay", payload)
