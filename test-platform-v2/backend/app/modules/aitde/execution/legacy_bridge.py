"""LegacyExecutionBridge (V31-009 / V31-010 / v331-gap A1/A3).

Bridges existing API task items and UI runs into the unified
Scenario -> ExecutionRun -> Step -> Evidence model WITHOUT modifying the legacy
records. It is idempotent via ``legacy_execution_links``.

API: reuses ApiExecutionTaskItem response/request data.
UI: registers screenshots / video / trace / artifacts as EvidenceArtifact.

v331-gap A1 (deep wiring): the real execution chain (api_task_worker /
playwright_executor) now calls the bridge after execution. When no unified
``run_id`` is supplied the bridge creates its own run
(``trigger_type=LEGACY_BRIDGE``, zero scenario bindings — strict binding
validation is a scenario-run requirement and does not apply to bridged legacy
executions), writes the evidence + mapped assertions, then finalizes the run:
outcome is frozen through the EvidenceCompletenessPolicy + OutcomeClassifier
(never a silent PASS).

v331-gap A3: legacy assertions that can be mapped are persisted as
AssertionResult rows (oracle_id=0 sentinel, ``source=legacy_bridge`` snapshot)
so ``compute_outcome`` sees real PASS/FAIL rows instead of an empty list.

Missing required evidence degrades the outcome to INCONCLUSIVE (never a silent
PASS).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    EvidenceType,
    LegacyExecutionType,
    RunStatus,
    StepType,
    TriggerType,
)
from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import ExecutionRun, LegacyExecutionLink

logger = logging.getLogger(__name__)

# Sentinel oracle_id for legacy-mapped assertions (no TestOracle row exists).
_LEGACY_ORACLE_ID = 0
_ORACLE_TYPE_KEY = "oracle_type"


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return str(value).encode("utf-8")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _read_artifact_bytes(artifact_dir: str | None, path: str) -> bytes | None:
    """Read a legacy artifact's real bytes; None when unreadable/absent."""
    if not artifact_dir or not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(artifact_dir) / path
    try:
        if candidate.is_file():
            return candidate.read_bytes()
    except OSError:
        logger.warning("legacy bridge: artifact unreadable: %s", candidate)
    return None


def find_link(
    db: Session, legacy_type: LegacyExecutionType, legacy_id: int
) -> LegacyExecutionLink | None:
    return db.scalar(
        select(LegacyExecutionLink).where(
            LegacyExecutionLink.legacy_type == legacy_type.value,
            LegacyExecutionLink.legacy_id == legacy_id,
        )
    )


def create_link(
    db: Session, run_id: int, legacy_type: LegacyExecutionType, legacy_id: int
) -> LegacyExecutionLink:
    row = LegacyExecutionLink(run_id=run_id, legacy_type=legacy_type.value, legacy_id=legacy_id)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def step_for_run(
    db: Session, run_id: int, step_key: str, step_type: str, status: str, sequence: int = 1
) -> Any:
    return repository.add_step(
        db,
        {
            "run_id": run_id,
            "sequence": sequence,
            "step_key": step_key,
            "step_type": step_type,
            "status": status,
        },
    )


# ── v331-gap A1: bridge-owned runs ──────────────────────────────────────────


def _ensure_legacy_run(
    db: Session, project_id: int, *, environment_id: int = 0
) -> ExecutionRun:
    """Create the unified run a bridged legacy execution lands on.

    Bridge runs carry zero scenario bindings (scenario/contract = 0) and
    ``trigger_type=LEGACY_BRIDGE``; they start RUNNING so ``finish_run`` can
    freeze the outcome once evidence + assertions are written.
    """
    return repository.create_run(
        db,
        {
            "project_id": project_id,
            "mission_id": 0,
            "scenario_id": 0,
            "scenario_version_id": 0,
            "contract_version_id": 0,
            "environment_id": environment_id,
            "environment_snapshot_id": None,
            "runtime_status": RunStatus.RUNNING.value,
            "trigger_type": TriggerType.LEGACY_BRIDGE.value,
            "started_at": _utcnow(),
        },
        user_id=0,
    )


def finalize_bridge_run(db: Session, run: ExecutionRun) -> str:
    """Freeze the run's outcome via the completeness policy + classifier."""
    from app.modules.aitde.execution import service as run_service

    evidence_ok = run_service.resolve_evidence_complete(db, run)
    assertions = repository.list_assertions(db, run.id, run.project_id)
    outcome = run_service.compute_outcome(assertions, evidence_ok)
    run_service.finish_run(db, run.id, run.project_id, outcome_str=outcome)
    return outcome


# ── v331-gap A3: legacy assertion mapping ───────────────────────────────────


def _persist_legacy_assertions(
    db: Session,
    run_id: int,
    step_id: int,
    assertions: list[Any] | None,
    *,
    oracle_type: str,
    evidence_refs: list[int],
) -> list[dict[str, Any]]:
    """Map legacy assertion dicts (passed/expected/actual/...) to AssertionResult.

    ``passed`` True/False maps to PASS/FAIL; anything else (or missing) maps to
    NOT_EVALUATED — a legacy assertion can never become a silent PASS.
    """
    written: list[dict[str, Any]] = []
    for rule in assertions or []:
        if not isinstance(rule, dict):
            continue
        passed = rule.get("passed")
        if passed is True:
            result = "PASS"
        elif passed is False:
            result = "FAIL"
        else:
            result = "NOT_EVALUATED"
        snapshot = {
            "source": "legacy_bridge",
            "type": rule.get("type", ""),
            "operator": rule.get("operator", ""),
            _ORACLE_TYPE_KEY: oracle_type,
        }
        row = repository.add_assertion(
            db,
            {
                "run_id": run_id,
                "step_id": step_id,
                "oracle_id": _LEGACY_ORACLE_ID,
                "oracle_snapshot_json": json.dumps(
                    snapshot, ensure_ascii=False, sort_keys=True
                ),
                "expected_json": json.dumps(
                    rule.get("expected"), ensure_ascii=False, default=str
                ),
                "actual_json": json.dumps(
                    rule.get("actual"), ensure_ascii=False, default=str
                ),
                "result": result,
                "reason_code": "legacy_mapped",
                "evidence_refs_json": json.dumps(evidence_refs),
                "evaluated_at": _utcnow(),
            },
        )
        written.append({"id": row.id, "result": row.result})
    return written


# ── v331-gap C4: project-scoped legacy loaders (v2 endpoint seam) ───────────


def load_api_item_for_project(
    db: Session, legacy_id: int, project_id: int
) -> tuple[Any, Any]:
    """Return (ApiExecutionTaskItem, ApiExecutionTask) or raise 404 on
    missing record / cross-project access."""
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

    item = db.get(ApiExecutionTaskItem, legacy_id)
    task = db.get(ApiExecutionTask, item.task_id) if item else None
    if not item or not task or task.project_id != project_id:
        raise APIException(code=404, msg="历史执行记录不存在", http_status=404)
    return item, task


def load_ui_run_for_project(
    db: Session, legacy_id: int, project_id: int
) -> tuple[Any, Any]:
    """Return (UiTestRun, UiTestJob) or raise 404 on missing record /
    cross-project access."""
    from app.models.ui_test import UiTestJob, UiTestRun

    run = db.get(UiTestRun, legacy_id)
    job = db.get(UiTestJob, run.job_id) if run else None
    if not run or not job or job.project_id != project_id:
        raise APIException(code=404, msg="历史执行记录不存在", http_status=404)
    return run, job


# ── bridge entry points ─────────────────────────────────────────────────────


def bridge_api_item(
    db: Session,
    *,
    project_id: int,
    run_id: int | None = None,
    legacy_id: int,
    request: str | dict[str, Any] | None = None,
    response: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    assertions: list[Any] | None = None,
    environment_id: int = 0,
    step_status: str = "SUCCEEDED",
) -> dict[str, Any]:
    """Register an API task item into the unified model (idempotent).

    ``run_id=None`` auto-creates a LEGACY_BRIDGE run and finalizes its outcome.
    """
    existing = find_link(db, LegacyExecutionType.API_TASK_ITEM, legacy_id)
    if existing is not None:
        return {"run_id": existing.run_id, "already_linked": True}

    auto_run = run_id is None
    if auto_run:
        run_row = _ensure_legacy_run(db, project_id, environment_id=environment_id)
    else:
        # Tenant boundary: an explicit run must belong to the caller's project.
        run_row = repository.get_run(db, run_id, project_id)
        if run_row is None:
            raise APIException(code=404, msg="统一执行记录不存在", http_status=404)
    run_id = run_row.id

    step = step_for_run(db, run_id, f"api-{legacy_id}", StepType.API.value, step_status)
    artifacts: list[dict[str, Any]] = []
    if request is not None:
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.REQUEST.value,
            data=_to_bytes(request), content_type="application/json", step_id=step.id, headers=headers,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.REQUEST.value})
    if response is not None:
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.RESPONSE.value,
            data=_to_bytes(response), content_type="application/json", step_id=step.id, headers=headers,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.RESPONSE.value})
    mapped = _persist_legacy_assertions(
        db, run_id, step.id, assertions,
        oracle_type="API", evidence_refs=[a["id"] for a in artifacts],
    )
    create_link(db, run_id, LegacyExecutionType.API_TASK_ITEM, legacy_id)
    result: dict[str, Any] = {
        "run_id": run_id, "step_id": step.id, "artifacts": artifacts, "assertions": mapped,
    }
    if auto_run:
        result["outcome"] = finalize_bridge_run(db, run_row)
    return result


def bridge_ui_run(
    db: Session,
    *,
    project_id: int,
    run_id: int | None = None,
    legacy_id: int,
    screenshots: list[str] | None = None,
    video_url: str | None = None,
    trace_id: str | None = None,
    artifact_dir: str | None = None,
    result_summary: dict[str, Any] | None = None,
    console_text: str | None = None,
    assertions: list[Any] | None = None,
    environment_id: int = 0,
    step_status: str = "SUCCEEDED",
) -> dict[str, Any]:
    """Register a UI run into the unified model (idempotent).

    When ``artifact_dir`` is supplied, screenshot/video/trace files are read and
    their real bytes registered; unreadable paths degrade to the path string.
    ``run_id=None`` auto-creates a LEGACY_BRIDGE run and finalizes its outcome.
    """
    existing = find_link(db, LegacyExecutionType.UI_RUN, legacy_id)
    if existing is not None:
        return {"run_id": existing.run_id, "already_linked": True}

    auto_run = run_id is None
    if auto_run:
        run_row = _ensure_legacy_run(db, project_id, environment_id=environment_id)
    else:
        # Tenant boundary: an explicit run must belong to the caller's project.
        run_row = repository.get_run(db, run_id, project_id)
        if run_row is None:
            raise APIException(code=404, msg="统一执行记录不存在", http_status=404)
    run_id = run_row.id

    step = step_for_run(db, run_id, f"ui-{legacy_id}", StepType.UI.value, step_status)
    artifacts: list[dict[str, Any]] = []
    shot_list = screenshots if isinstance(screenshots, list) else []
    for idx, shot in enumerate(shot_list):
        data = _read_artifact_bytes(artifact_dir, str(shot))
        if data is not None:
            row = store_artifact(
                db, project_id=project_id, run_id=run_id,
                evidence_type=EvidenceType.SCREENSHOT.value,
                data=data, content_type="image/png", step_id=step.id,
            )
        else:
            row = store_artifact(
                db, project_id=project_id, run_id=run_id,
                evidence_type=EvidenceType.SCREENSHOT.value,
                data=_to_bytes(shot), content_type="text/plain", step_id=step.id,
            )
        artifacts.append({"id": row.id, "type": EvidenceType.SCREENSHOT.value, "idx": idx})
    if video_url:
        data = _read_artifact_bytes(artifact_dir, video_url)
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.VIDEO.value,
            data=data if data is not None else _to_bytes(video_url),
            content_type="video/webm" if data is not None else "text/plain", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.VIDEO.value})
    if trace_id:
        data = _read_artifact_bytes(artifact_dir, trace_id)
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.PW_TRACE.value,
            data=data if data is not None else _to_bytes(trace_id),
            content_type="application/zip" if data is not None else "text/plain", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.PW_TRACE.value})
    if console_text:
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.CONSOLE.value,
            data=_to_bytes(console_text), content_type="text/plain", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.CONSOLE.value})
    mapped = _persist_legacy_assertions(
        db, run_id, step.id, assertions,
        oracle_type="UI", evidence_refs=[a["id"] for a in artifacts],
    )
    create_link(db, run_id, LegacyExecutionType.UI_RUN, legacy_id)
    result: dict[str, Any] = {
        "run_id": run_id, "step_id": step.id, "artifacts": artifacts, "assertions": mapped,
    }
    if auto_run:
        result["outcome"] = finalize_bridge_run(db, run_row)
    return result
