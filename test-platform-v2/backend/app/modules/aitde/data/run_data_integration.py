"""RunDataIntegration (V32-014).

Appends the V3.2 data-provisioning steps to a run's timeline, records data
evidence (DATA_PLAN / FIXTURE_MANIFEST / DB_BEFORE / DB_AFTER / DB_CLEANUP_VERIFY)
and classifies a data failure as ``DATA_FAIL`` — never a business failure — while
preserving an already-evaluated business outcome and recording cleanup health.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    EvidenceIntegrityStatus,
    EvidenceType,
    Outcome,
    SanitizationStatus,
    StepStatus,
    StepType,
)
from app.modules.aitde.execution.models import EvidenceArtifact, ExecutionRun, ExecutionStep

logger = logging.getLogger(__name__)


def _plan_evidence_payload(db: Session, plan: Any) -> str:
    """Serialize a DataPlan into an evidence payload (strategy + steps)."""
    if plan is None:
        return "{}"
    from app.modules.aitde.data.models import DataPlanStep

    steps = db.scalars(
        select(DataPlanStep)
        .where(DataPlanStep.data_plan_id == plan.id)
        .order_by(DataPlanStep.sequence)
    ).all()
    return json.dumps(
        {
            "strategy": plan.strategy,
            "plan_hash": plan.plan_hash,
            "steps": [
                {"step_type": s.step_type, "command": json.loads(s.command_json or "{}")}
                for s in steps
            ],
        },
        ensure_ascii=False,
    )

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
    """Legacy import path. V3.9-R2 (DATA-004): a data-evidence row MUST point at a
    real stored object (non-empty storage_uri + valid content_hash); an empty fake
    row is rejected so ``COMPLETE`` can never be satisfied by a phantom artifact."""
    if evidence_type not in _VALID_EVIDENCE:
        raise APIException(code=400, msg=f"非法证据类型：{evidence_type}", http_status=400)
    if not storage_uri or not content_hash:
        raise APIException(
            code=400,
            msg="数据证据必须指向已存储对象（storage_uri + content_hash 均非空）",
            http_status=400,
        )
    artifact = EvidenceArtifact(
        project_id=project_id,
        run_id=run_id,
        evidence_type=evidence_type,
        storage_uri=storage_uri,
        content_hash=content_hash,
        integrity_status=EvidenceIntegrityStatus.VERIFIED.value,
        sanitization_status=SanitizationStatus.SANITIZED.value,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def store_data_evidence(
    db: Session,
    run_id: int,
    evidence_type: str,
    *,
    project_id: int = 0,
    data: bytes,
    content_type: str = "application/json",
) -> EvidenceArtifact:
    """Route data evidence through EvidenceService.store_artifact (sanitize →
    object storage → content hash → integrity VERIFIED). Never a fake row."""
    if evidence_type not in _VALID_EVIDENCE:
        raise APIException(code=400, msg=f"非法证据类型：{evidence_type}", http_status=400)
    from app.modules.aitde.evidence.service import store_artifact

    return store_artifact(
        db,
        project_id=project_id,
        run_id=run_id,
        evidence_type=evidence_type,
        data=data,
        content_type=content_type,
    )


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


def prepare_run_data(db: Session, run: ExecutionRun, project_id: int) -> dict[str, Any]:
    """Automatically provision data for a run whose scenario has data requirements.

    Called at run start. Idempotent per (scenario_version, data_plan, environment) —
    reuses an existing fixture for the same environment and links it to the run.
    On data failure the run's outcome is set to ``DATA_FAIL`` (never a business
    failure).
    """
    from app.modules.aitde.data import repository as data_repository
    from app.modules.aitde.data import fixture_service as data_fixture_service
    from app.modules.aitde.data.models import DataFixture

    requirements = data_repository.list_requirements_by_scenario_version(
        db, run.scenario_version_id
    )
    if not requirements:
        return {"prepared": False, "reason": "no_requirements"}

    plans = data_repository.list_data_plans_by_scenario_version(
        db, run.scenario_version_id
    )
    plan_ids = [p.id for p in plans]
    # §93: fixtures are environment-scoped — never reuse across environments.
    env = run.environment_id or None

    try:
        # Reuse a fixture already provisioned for this scenario's plan + environment.
        existing = None
        if plan_ids:
            existing = db.scalar(
                select(DataFixture).where(
                    DataFixture.scenario_version_id == run.scenario_version_id,
                    DataFixture.data_plan_id.in_(plan_ids),
                    DataFixture.environment_id == env,
                )
            )
        if existing:
            fixture = existing
            fixture.run_id = run.id
            db.commit()
        else:
            plan = next(
                (
                    p
                    for p in plans
                    if p.status in ("APPROVED", "EXECUTING")
                    or (p.status == "DRAFT" and p.risk_level in ("P2", "P3"))
                ),
                None,
            )
            if plan is None:
                return {"prepared": False, "reason": "no_plan"}
            fixture = data_fixture_service.provision_fixture_from_plan(
                db, plan.id, project_id, env, None
            )
            fixture.run_id = run.id
            db.commit()

        add_run_data_timeline(db, run.id)
        fixture_plan = next((p for p in plans if p.id == fixture.data_plan_id), None)
        plan_content = _plan_evidence_payload(db, fixture_plan)
        # DATA-004: data evidence must be real stored artifacts (never a fake row).
        # A storage failure degrades evidence (never a business failure).
        try:
            store_data_evidence(
                db, run.id, EvidenceType.DATA_PLAN.value, project_id=project_id,
                data=plan_content.encode("utf-8"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("data_plan evidence store failed run=%s: %s", run.id, exc)
        try:
            store_data_evidence(
                db, run.id, EvidenceType.FIXTURE_MANIFEST.value, project_id=project_id,
                data=(fixture.manifest_json or "{}").encode("utf-8"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("fixture_manifest evidence store failed run=%s: %s", run.id, exc)
        return {"prepared": True, "fixture_id": fixture.id}
    except Exception as exc:  # noqa: BLE001 — data failure is never a business failure
        set_run_data_fail(db, run.id)
        db.rollback()
        return {"prepared": False, "reason": "data_fail", "error": str(exc)}
