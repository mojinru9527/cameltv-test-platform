"""AITDE V3.4 Execution driver bindings (V34-004).

Registers the real executor hooks for the ScenarioExecutionWorkflow chain by
delegating to the existing V3.2 data runtime (fixture provision + evidence) and
V3.1 execution outcome/evidence services. Importing this module registers the
hooks; the Activities stay import-light and sandbox-clean.

All hooks open their own DB session from ``SessionLocal`` (they run on the
Temporal worker, outside the FastAPI request scope) and are idempotent.
"""
from __future__ import annotations

import logging
from typing import Any

from app.temporal.activities import register_exec_hook

logger = logging.getLogger(__name__)


def _db():
    from app.core.db import SessionLocal

    return SessionLocal()


def _real_run_id(payload: dict[str, Any]) -> int | None:
    run_id = payload.get("run_id")
    return int(run_id) if run_id else None


# ── V34-004 data/fixture + evidence + outcome delegation ─────────────────────


def _plan_data_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"prepared": False, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import prepare_run_data
        from app.modules.aitde.execution.models import ExecutionRun

        run = db.get(ExecutionRun, run_id)
        if run is None:
            return {"prepared": False, "reason": "run_not_found"}
        return prepare_run_data(db, run, payload.get("project_id") or 0)
    finally:
        db.close()


def _ensure_fixture_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"echo": True, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import to_run_data_context

        return to_run_data_context(db, run_id)
    finally:
        db.close()


def _collect_evidence_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"evidence": [], "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.evidence.service import list_evidence

        items = list_evidence(db, run_id, payload.get("project_id") or 0)
        return {"evidence": [{"id": e.id, "type": e.evidence_type} for e in items]}
    finally:
        db.close()


def _classify_outcome_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"outcome": None, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.execution import repository, service

        run = repository.get_run(db, run_id, payload.get("project_id") or 0)
        if run is None:
            return {"outcome": None, "reason": "run_not_found"}
        assertions = repository.list_assertions(db, run_id, payload.get("project_id") or 0)
        evidence_ok = service.resolve_evidence_complete(db, run)
        outcome = service.compute_outcome(assertions, evidence_ok)
        return {"outcome": outcome, "evidence_complete": evidence_ok}
    finally:
        db.close()


def _cleanup_fixture_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"cleanup": "echo", "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import record_cleanup_health

        record_cleanup_health(db, run_id, cleanup_ok=True)
        return {"cleanup": "ok"}
    finally:
        db.close()


def _build_replay_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"manifest": None, "view": None, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.evidence.replay import build_replay_view, get_manifest, manifest_dict

        manifest = get_manifest(db, run_id, payload.get("project_id") or 0)
        if manifest is None:
            return {"manifest": None, "view": None}
        return {"manifest": manifest_dict(manifest), "view": build_replay_view(manifest_dict(manifest))}
    finally:
        db.close()


def register_driver_hooks() -> None:
    """Register the real driver hooks (idempotent — safe to call repeatedly)."""
    register_exec_hook("plan_data", _plan_data_hook)
    register_exec_hook("ensure_fixture", _ensure_fixture_hook)
    register_exec_hook("collect_evidence", _collect_evidence_hook)
    register_exec_hook("classify_outcome", _classify_outcome_hook)
    register_exec_hook("cleanup_fixture", _cleanup_fixture_hook)
    register_exec_hook("build_replay", _build_replay_hook)


register_driver_hooks()
