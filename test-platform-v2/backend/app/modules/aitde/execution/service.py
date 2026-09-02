"""ExecutionRunService (V31-002).

Owns run lifecycle: creation (must bind scenario_version_id +
contract_version_id + environment_snapshot_id), legal runtime_status
transitions and parent/child retry. ``runtime_status`` (scheduler) is kept
separate from ``outcome`` (business conclusion).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.core.config import settings
from app.modules.aitde.common.enums import (
    EvidenceStatus,
    Outcome,
    RunStatus,
    TriggerType,
)
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion

_VALID_RUN_STATUSES = {s.value for s in RunStatus}


def _utcnow() -> datetime:
    """Naive UTC timestamp matching the naive DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Legal runtime_status (scheduler) transitions. Outcome is decided by the
# classifier, not via this table.
ALLOWED_RUN_TRANSITIONS: dict[str, set[str]] = {
    RunStatus.QUEUED.value: {RunStatus.RUNNING.value, RunStatus.CANCELLED.value},
    RunStatus.RUNNING.value: {RunStatus.FINISHED.value, RunStatus.CANCELLED.value},
    RunStatus.FINISHED.value: set(),
    RunStatus.CANCELLED.value: set(),
}


def _validate_run_binding(
    db: Session,
    project_id: int,
    scenario_id: int,
    scenario_version_id: int,
    contract_version_id: int,
) -> None:
    """A run binds a project-owned scenario version and its frozen contract version."""
    scenario = db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )
    if not scenario:
        raise APIException(code=400, msg="场景不属于当前项目", http_status=400)

    version = db.scalar(
        select(TestScenarioVersion).where(
            TestScenarioVersion.id == scenario_version_id,
            TestScenarioVersion.scenario_id == scenario_id,
        )
    )
    if not version:
        raise APIException(code=400, msg="场景版本不存在或不匹配", http_status=400)
    if version.contract_version_id != contract_version_id:
        raise APIException(
            code=400, msg="场景版本与契约版本不匹配", http_status=400
        )


def _build_scenario_input(row: ExecutionRun) -> dict[str, Any]:
    """Build the ScenarioExecutionWorkflow ``scenario_input`` payload.

    V4.0 生产黑盒复盘 AITDE-UX-003：run 创建后从未提交 Temporal，Workflow 永不启动。
    The workflow's activities run against DB by these identifiers; the model/snapshot
    are loaded inside the activities from ``scenario_version_id`` / ``environment_snapshot_id``.
    """
    return {
        "run_id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "scenario_id": row.scenario_id,
        "scenario_version_id": row.scenario_version_id,
        "contract_version_id": row.contract_version_id,
        "environment_id": row.environment_id,
        "environment_snapshot_id": row.environment_snapshot_id,
        "trigger_type": row.trigger_type,
        "worker_id": "temporal",
    }


def _submit_to_temporal(db: Session, project_id: int, row: ExecutionRun) -> None:
    """Submit the run to Temporal (Durable Runtime) so a Worker executes it.

    AITDE-UX-003: previously ``start_scenario_execution`` had no caller; runs
    stayed QUEUED forever with a live Worker polling an empty queue.
    """
    from app.modules.aitde.workflow import service as workflow_service

    try:
        workflow_service.start_scenario_execution(
            db,
            project_id=project_id,
            workflow_id=f"scenario-run-{row.id}",
            scenario_input=_build_scenario_input(row),
            run_id=row.id,
            mission_id=row.mission_id,
            network_zone=None,
            required_capabilities=None,
        )
    except Exception as exc:  # noqa: BLE001 - 提交失败不应把已创建的 run 置为失败
        # 记录到 run 的原始错误，避免静默；run 仍保持 QUEUED，可由 retry 重试。
        logger = __import__("logging").getLogger(__name__)
        logger.warning("[execution] submit scenario-run-%s to Temporal failed: %s", row.id, exc)


def create_run(
    db: Session,
    data: dict[str, Any],
    project_id: int,
    user_id: int,
) -> ExecutionRun:
    scenario_id = int(data.get("scenario_id") or 0)
    scenario_version_id = int(data.get("scenario_version_id") or 0)
    contract_version_id = int(data.get("contract_version_id") or 0)
    environment_snapshot_id = data.get("environment_snapshot_id")
    mission_id = int(data.get("mission_id") or 0)
    environment_id = int(data.get("environment_id") or 0)

    if not scenario_id or not scenario_version_id or not contract_version_id:
        raise APIException(
            code=400, msg="场景、场景版本与契约版本必须全部绑定", http_status=400
        )
    if not environment_snapshot_id:
        raise APIException(
            code=400, msg="Run 必须绑定环境快照（environment_snapshot_id）", http_status=400
        )

    _validate_run_binding(db, project_id, scenario_id, scenario_version_id, contract_version_id)

    trigger_type = data.get("trigger_type") or TriggerType.MANUAL.value
    row = repository.create_run(
        db,
        {
            "project_id": project_id,
            "mission_id": mission_id,
            "scenario_id": scenario_id,
            "scenario_version_id": scenario_version_id,
            "contract_version_id": contract_version_id,
            "adapter_id": data.get("adapter_id"),
            "environment_id": environment_id,
            "environment_snapshot_id": environment_snapshot_id,
            "runtime_status": RunStatus.QUEUED.value,
            "evidence_status": EvidenceStatus.PENDING.value,
            "trigger_type": trigger_type,
        },
        user_id,
    )

    # AITDE-UX-003：Temporal 启用时提交 Workflow，否则 Run 永久 QUEUED（Worker 空转）。
    if settings.temporal_enabled and row.id:
        _submit_to_temporal(db, project_id, row)

    return row


def get_run(db: Session, run_id: int, project_id: int) -> ExecutionRun:
    row = repository.get_run(db, run_id, project_id)
    if not row:
        raise APIException(code=404, msg="执行记录不存在", http_status=404)
    return row


def list_runs(
    db: Session,
    project_id: int,
    mission_id: int | None = None,
    outcome: str | None = None,
    runtime_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ExecutionRun], int]:
    if outcome and outcome not in {o.value for o in Outcome} and outcome != "null":
        raise APIException(code=400, msg=f"非法结果：{outcome}", http_status=400)
    if runtime_status and runtime_status not in _VALID_RUN_STATUSES:
        raise APIException(code=400, msg=f"非法运行状态：{runtime_status}", http_status=400)
    return repository.list_runs(
        db,
        project_id,
        mission_id=mission_id,
        outcome=outcome,
        runtime_status=runtime_status,
        page=page,
        page_size=page_size,
    )


def transition_runtime_status(row: ExecutionRun, target: str) -> None:
    """Refuse illegal scheduler-state jumps (identity is a no-op)."""
    if row.runtime_status == target:
        return
    allowed = ALLOWED_RUN_TRANSITIONS.get(row.runtime_status, set())
    if target not in allowed:
        raise APIException(
            code=400,
            msg=f"非法运行状态迁移：{row.runtime_status} → {target}",
            http_status=400,
        )


def mark_running(db: Session, run_id: int, project_id: int) -> ExecutionRun:
    row = get_run(db, run_id, project_id)
    transition_runtime_status(row, RunStatus.RUNNING.value)
    updated = repository.update_run(
        db, row, {"runtime_status": RunStatus.RUNNING.value, "started_at": _utcnow()}
    )
    # V32-014: at run start, provision data + data timeline + evidence for runs
    # whose scenario has data requirements. Data failure → DATA_FAIL (never business).
    from app.modules.aitde.data.run_data_integration import prepare_run_data

    try:
        prepare_run_data(db, updated, project_id)
    except Exception:  # noqa: BLE001 — must not block the run itself
        db.rollback()
    db.refresh(updated)
    return updated


def finish_run(db: Session, run_id: int, project_id: int, outcome_str: str) -> ExecutionRun:
    row = get_run(db, run_id, project_id)
    transition_runtime_status(row, RunStatus.FINISHED.value)
    # A data failure is authoritative over a business outcome for that run.
    if row.outcome == Outcome.DATA_FAIL.value:
        outcome_str = Outcome.DATA_FAIL.value
    now = _utcnow()
    started = row.started_at
    duration_ms = int((now - started).total_seconds() * 1000) if started else None
    return repository.update_run(
        db,
        row,
        {
            "runtime_status": RunStatus.FINISHED.value,
            "outcome": outcome_str,
            "finished_at": now,
            "duration_ms": duration_ms,
        },
    )


def cancel_run(db: Session, run_id: int, project_id: int) -> ExecutionRun:
    row = get_run(db, run_id, project_id)
    transition_runtime_status(row, RunStatus.CANCELLED.value)
    return repository.update_run(
        db,
        row,
        {"runtime_status": RunStatus.CANCELLED.value, "finished_at": _utcnow()},
    )


def retry_run(db: Session, run_id: int, project_id: int, user_id: int) -> ExecutionRun:
    """Create a child run (parent_run_id set, retry_no = parent.retry_no + 1)."""
    parent = get_run(db, run_id, project_id)
    child = repository.create_run(
        db,
        {
            "project_id": parent.project_id,
            "mission_id": parent.mission_id,
            "scenario_id": parent.scenario_id,
            "scenario_version_id": parent.scenario_version_id,
            "contract_version_id": parent.contract_version_id,
            "adapter_id": parent.adapter_id,
            "environment_id": parent.environment_id,
            "environment_snapshot_id": parent.environment_snapshot_id,
            "runtime_status": RunStatus.QUEUED.value,
            "evidence_status": EvidenceStatus.PENDING.value,
            "trigger_type": parent.trigger_type,
            "parent_run_id": parent.id,
            "retry_no": parent.retry_no + 1,
        },
        user_id,
    )
    # AITDE-UX-003：retry 的子 run 同样提交 Temporal，否则仍永久 QUEUED。
    if settings.temporal_enabled and child.id:
        _submit_to_temporal(db, project_id, child)
    return child


def compute_outcome(assertions: list, evidence_sanitized_ok: bool) -> str:
    """Aggregate assertion results + evidence state into a frozen Outcome."""
    from app.modules.aitde.execution.outcome_classifier import DecisionInput, classify

    passed = sum(1 for a in assertions if a.result == "PASS")
    failed = sum(1 for a in assertions if a.result == "FAIL")
    not_eval = sum(1 for a in assertions if a.result == "NOT_EVALUATED")
    defined = len(assertions)
    di = DecisionInput(
        required_oracle_pass=passed,
        required_oracle_fail=failed,
        required_oracle_not_evaluated=not_eval,
        required_oracle_defined=defined,
        evidence_complete=evidence_sanitized_ok,
        evidence_failed=not evidence_sanitized_ok,
    )
    return classify(di)


# ── v331-gap A2: EvidenceCompletenessPolicy wiring ──────────────────────────


def _resolve_adapter_type(db: Session, run: ExecutionRun) -> str:
    """Adapter type of the run: bound adapter first, else inferred from steps."""
    from app.modules.aitde.common.enums import AdapterType, StepType

    if run.adapter_id:
        adapter = repository.get_adapter(db, run.adapter_id, run.project_id)
        if adapter:
            return adapter.adapter_type
    step_types = {s.step_type for s in repository.list_steps(db, run.id, run.project_id)}
    if StepType.API.value in step_types:
        return AdapterType.API.value
    if StepType.UI.value in step_types:
        return AdapterType.UI.value
    if StepType.DB.value in step_types:
        return AdapterType.DB.value
    return ""


def _resolve_oracle_type(db: Session, run: ExecutionRun) -> str:
    """Oracle type of the run: frozen scenario oracles first, else the
    oracle_type recorded in legacy-mapped assertion snapshots."""
    import json as _json

    oracle_types: set[str] = set()
    if run.scenario_version_id:
        from app.modules.aitde.scenario.models import TestOracle

        oracle_types = set(
            db.scalars(
                select(TestOracle.oracle_type).where(
                    TestOracle.scenario_version_id == run.scenario_version_id
                )
            ).all()
        )
    if len(oracle_types) == 1:
        return oracle_types.pop()
    for assertion in repository.list_assertions(db, run.id, run.project_id):
        try:
            snapshot = _json.loads(assertion.oracle_snapshot_json or "{}")
        except ValueError:
            continue
        if isinstance(snapshot, dict) and snapshot.get("oracle_type"):
            return str(snapshot["oracle_type"])
    return ""


def resolve_evidence_complete(db: Session, run: ExecutionRun) -> bool:
    """True only when every evidence type required by the run's
    (adapter_type, oracle_type) pair is present AND sanitized.

    Unknown adapter/oracle pairs fall back to the policy's conservative
    requirement (RESPONSE + SCREENSHOT) — an unknown run can never be a silent
    PASS (V3.1 plan invariant 4).
    """
    from app.modules.aitde.assertion.completeness import is_complete, required_evidence
    from app.modules.aitde.common.enums import SanitizationStatus

    evidence = repository.list_evidence(db, run.id, run.project_id)
    present = {
        e.evidence_type
        for e in evidence
        if e.sanitization_status == SanitizationStatus.SANITIZED.value
    }
    required = required_evidence(
        _resolve_adapter_type(db, run), _resolve_oracle_type(db, run)
    )
    return is_complete(present, required)
