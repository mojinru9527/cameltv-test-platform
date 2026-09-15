from __future__ import annotations

from app.modules.aitde.execution.models import ExecutionRun
from app.modules.campaign_execution import service


def _run(db, project_id: int = 1, capabilities: str = "{}") -> ExecutionRun:
    row = ExecutionRun(
        project_id=project_id,
        mission_id=0,
        scenario_id=1,
        scenario_version_id=2,
        contract_version_id=3,
        adapter_id=None,
        environment_id=4,
        environment_snapshot_id=5,
        runtime_status="QUEUED",
        runner_capabilities_json=capabilities,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_claim_is_project_scoped_and_capability_aware(db_session) -> None:
    run = _run(db_session, project_id=100, capabilities='{"api": true}')
    assert service.claim_execution_run(db_session, project_id=200, runner_id="r1", capabilities={"api": True}) is None
    claimed = service.claim_execution_run(db_session, project_id=100, runner_id="r1", capabilities={"api": True})
    assert claimed is not None and claimed.id == run.id
    assert claimed.runtime_status == "RUNNING"
    assert claimed.runner_id == "r1"
    assert service.claim_execution_run(db_session, project_id=100, runner_id="r2", capabilities={"api": True}) is None


def test_heartbeat_requires_owner(db_session) -> None:
    run = _run(db_session)
    service.claim_execution_run(db_session, project_id=1, runner_id="runner-a", capabilities={})
    assert service.heartbeat_execution_run(db_session, run_id=run.id, project_id=1, runner_id="runner-b") is False
    assert service.heartbeat_execution_run(db_session, run_id=run.id, project_id=1, runner_id="runner-a") is True


def test_report_requires_owner_and_finishes_run(db_session) -> None:
    run = _run(db_session)
    service.claim_execution_run(db_session, project_id=1, runner_id="runner-a", capabilities={})
    assert (
        service.report_execution_run(
            db_session, run_id=run.id, project_id=1, runner_id="runner-b", runtime_status="FINISHED", outcome="PASS"
        )
        is None
    )
    reported = service.report_execution_run(
        db_session, run_id=run.id, project_id=1, runner_id="runner-a", runtime_status="FINISHED", outcome="PASS"
    )
    assert reported is not None
    assert reported.runtime_status == "FINISHED"
    assert reported.outcome == "PASS"
    assert reported.runner_id == ""


def test_cancel_only_active_run(db_session) -> None:
    run = _run(db_session)
    cancelled = service.cancel_execution_run(db_session, run_id=run.id, project_id=1)
    assert cancelled is not None and cancelled.runtime_status == "CANCELLED"
    assert service.cancel_execution_run(db_session, run_id=run.id, project_id=1) is None
