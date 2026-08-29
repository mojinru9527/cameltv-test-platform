"""LegacyExecutionBridge (V31-009 / V31-010).

Bridges existing API task items and UI runs into the unified
Scenario -> ExecutionRun -> Step -> Evidence model WITHOUT modifying the legacy
records. It is idempotent via ``legacy_execution_links``.

API: reuses ApiExecutionTaskItem response/request data.
UI: registers screenshots / video / trace / artifacts as EvidenceArtifact.
Missing required evidence degrades the outcome to INCONCLUSIVE (never a silent PASS).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import (
    EvidenceType,
    LegacyExecutionType,
    StepType,
)
from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import LegacyExecutionLink


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return str(value).encode("utf-8")


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


def bridge_api_item(
    db: Session,
    *,
    project_id: int,
    run_id: int,
    legacy_id: int,
    request: str | dict[str, Any] | None = None,
    response: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Register an API task item into the unified model (idempotent)."""
    if find_link(db, LegacyExecutionType.API_TASK_ITEM, legacy_id) is not None:
        run = repository.get_run(db, run_id, project_id)
        return {"run_id": run_id, "already_linked": bool(run)}

    step = step_for_run(db, run_id, f"api-{legacy_id}", StepType.API.value, "SUCCEEDED")
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
    create_link(db, run_id, LegacyExecutionType.API_TASK_ITEM, legacy_id)
    return {"run_id": run_id, "step_id": step.id, "artifacts": artifacts}


def bridge_ui_run(
    db: Session,
    *,
    project_id: int,
    run_id: int,
    legacy_id: int,
    screenshots: list[str] | None = None,
    video_url: str | None = None,
    trace_id: str | None = None,
    artifact_dir: str | None = None,
    result_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register a UI run into the unified model (idempotent)."""
    if find_link(db, LegacyExecutionType.UI_RUN, legacy_id) is not None:
        run = repository.get_run(db, run_id, project_id)
        return {"run_id": run_id, "already_linked": bool(run)}

    step = step_for_run(db, run_id, f"ui-{legacy_id}", StepType.UI.value, "SUCCEEDED")
    artifacts: list[dict[str, Any]] = []
    shot_list = screenshots if isinstance(screenshots, list) else []
    for idx, shot in enumerate(shot_list):
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.SCREENSHOT.value,
            data=_to_bytes(shot), content_type="image/png", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.SCREENSHOT.value, "idx": idx})
    if video_url:
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.VIDEO.value,
            data=_to_bytes(video_url), content_type="text/plain", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.VIDEO.value})
    if trace_id:
        row = store_artifact(
            db, project_id=project_id, run_id=run_id, evidence_type=EvidenceType.PW_TRACE.value,
            data=_to_bytes(trace_id), content_type="text/plain", step_id=step.id,
        )
        artifacts.append({"id": row.id, "type": EvidenceType.PW_TRACE.value})
    create_link(db, run_id, LegacyExecutionType.UI_RUN, legacy_id)
    return {"run_id": run_id, "step_id": step.id, "artifacts": artifacts}
