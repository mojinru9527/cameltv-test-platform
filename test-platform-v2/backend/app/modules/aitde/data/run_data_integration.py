"""RunDataIntegration (V32-014).

Appends the V3.2 data-provisioning steps to a run's timeline, records data
evidence (DATA_PLAN / FIXTURE_MANIFEST / DB_BEFORE / DB_AFTER / DB_CLEANUP_VERIFY)
and classifies a data failure as ``DATA_FAIL`` — never a business failure — while
preserving an already-evaluated business outcome and recording cleanup health.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    EvidenceType,
    Outcome,
    StepStatus,
    StepType,
)
from app.modules.aitde.execution.models import EvidenceArtifact, ExecutionRun, ExecutionStep

# Ordered V3.2 data runtime timeline (V32-014).
DATA_TIMELINE = [
    "DATA PLAN",
    "DATA FIND / CREATE",
    "LEASE",
    "DB BEFORE",
    "ACTION",
    "DB AFTER",
    "ASSERT DB",
    "CLEANUP",
    "CLEANUP VERIFY",
]

_VALID_EVIDENCE = {e.value for e in EvidenceType}


def add_run_data_timeline(
    db: Session, run_id: int, *, status: str = StepStatus.PENDING.value
) -> list[ExecutionStep]:
    run = db.get(ExecutionRun, run_id)
    if not run:
        raise APIException(code=404, msg="ExecutionRun 不存在", http_status=404)
    steps = []
    for i, key in enumerate(DATA_TIMELINE, start=1):
        step = ExecutionStep(
            run_id=run_id, sequence=i, step_key=key,
            step_type=StepType.DATA.value, status=status,
        )
        db.add(step)
        db.flush()
        steps.append(step)
    db.commit()
    return steps


def record_data_evidence(
    db: Session,
    run_id: int,
    evidence_type: str,
    *,
    project_id: int = 0,
    storage_uri: str = "",
    content_hash: str = "",
) -> EvidenceArtifact:
    if evidence_type not in _VALID_EVIDENCE:
        raise APIException(code=400, msg=f"非法证据类型：{evidence_type}", http_status=400)
    artifact = EvidenceArtifact(
        project_id=project_id,
        run_id=run_id,
        evidence_type=evidence_type,
        storage_uri=storage_uri,
        content_hash=content_hash,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def set_run_data_fail(db: Session, run_id: int) -> ExecutionRun:
    """Classify DATA_FAIL only when no business outcome has been evaluated yet."""
    run = db.get(ExecutionRun, run_id)
    if not run:
        raise APIException(code=404, msg="ExecutionRun 不存在", http_status=404)
    if run.outcome is None:
        run.outcome = Outcome.DATA_FAIL.value
        db.commit()
        db.refresh(run)
    return run


def record_cleanup_health(
    db: Session, run_id: int, cleanup_ok: bool
) -> ExecutionRun:
    """Record cleanup health without mutating the business outcome."""
    run = db.get(ExecutionRun, run_id)
    if not run:
        raise APIException(code=404, msg="ExecutionRun 不存在", http_status=404)
    max_seq = db.scalar(
        select(func.max(ExecutionStep.sequence)).where(ExecutionStep.run_id == run_id)
    ) or 0
    db.add(
        ExecutionStep(
            run_id=run_id,
            sequence=max_seq + 1,
            step_key="CLEANUP HEALTH",
            step_type=StepType.SYSTEM.value,
            status=StepStatus.SUCCEEDED.value if cleanup_ok else StepStatus.FAILED.value,
            output_snapshot_json=f'{{"cleanup_ok": {str(cleanup_ok).lower()}}}',
        )
    )
    db.commit()
    db.refresh(run)
    return run


def to_run_data_context(db: Session, run_id: int) -> dict[str, Any]:
    """Summary of the data runtime context for a run (evidence + steps)."""
    run = db.get(ExecutionRun, run_id)
    if not run:
        raise APIException(code=404, msg="ExecutionRun 不存在", http_status=404)
    steps = db.scalars(
        select(ExecutionStep)
        .where(ExecutionStep.run_id == run_id, ExecutionStep.step_type == StepType.DATA.value)
        .order_by(ExecutionStep.sequence.asc())
    ).all()
    artifacts = db.scalars(
        select(EvidenceArtifact).where(EvidenceArtifact.run_id == run_id)
    ).all()
    return {
        "run_id": run_id,
        "outcome": run.outcome,
        "data_steps": [
            {"sequence": s.sequence, "step_key": s.step_key, "status": s.status}
            for s in steps
        ],
        "evidence": [
            {
                "evidence_type": a.evidence_type,
                "storage_uri": a.storage_uri,
                "content_hash": a.content_hash,
            }
            for a in artifacts
            if a.evidence_type in {"DATA_PLAN", "FIXTURE_MANIFEST", "DB_BEFORE", "DB_AFTER", "DB_CLEANUP_VERIFY"}
        ],
    }
