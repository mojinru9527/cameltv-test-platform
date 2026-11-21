"""V16-020 验收：统一终态与 Comparison Snapshot（仅真实终态 Run）。"""
from __future__ import annotations

import pytest

from app.aiqe.models.artifact import ArtifactType, ArtifactUploadStatus, RunArtifact
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.services.regression_terminal import (
    aggregate_regression_status,
    handle_run_terminal,
)
from app.models.defect import Defect, DefectRegression


def _defect(db, project_id: int = 1) -> Defect:
    from app.models.project import Project

    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()
    row = Defect(project_id=project_id, defect_id="BUG-T", title="x", severity="P1", status="open")
    db.add(row)
    db.flush()
    return row


def _run(db, *, key: str, status: str = "COMPLETED", outcome: str | None = "PASS") -> TestRun:
    run = TestRun(project_id=1, run_key=key, status=status, outcome=outcome)
    db.add(run)
    db.flush()
    return run


def _node_with_assertion(
    db, run: TestRun, *, status: str, assertion_status: str, required: bool = True
) -> None:
    node = NodeRun(run_id=run.id, node_key="ui", driver_key="http", status=status)
    db.add(node)
    db.flush()
    attempt = StepAttempt(node_run_id=node.id, step_key="ui", attempt_no=1, status=status)
    db.add(attempt)
    db.flush()
    db.add(
        RunAssertionResult(
            step_attempt_id=attempt.id,
            assertion_key="ui.ok",
            assertion_type="exists",
            status=assertion_status,
            required=required,
            oracle_layer="REQ",
            severity="P0",
        )
    )
    db.flush()


def _regression(db, defect: Defect, source: TestRun, verification: TestRun) -> DefectRegression:
    row = DefectRegression(
        defect_id=defect.id,
        fixed_sha="a" * 40,
        previous_run_id=source.id,
        source_run_id=source.id,
        verification_run_id=verification.id,
        status="QUEUED",
    )
    db.add(row)
    db.flush()
    return row


def test_non_terminal_run_cannot_generate_comparison(db_session):
    defect = _defect(db_session)
    source = _run(db_session, key="SRC", outcome="FAIL")
    _node_with_assertion(db_session, source, status="FAILED", assertion_status="FAIL")
    running = _run(db_session, key="VERIFY", status="RUNNING", outcome=None)
    _node_with_assertion(db_session, running, status="RUNNING", assertion_status="PASS")
    _regression(db_session, defect, source, running)
    result = handle_run_terminal(db_session, run_id=running.id)
    assert result.skipped is True
    assert result.reason == "RUN_NOT_TERMINAL"
    assert result.comparison_id is None


def test_terminal_pass_generates_immutable_comparison_and_is_idempotent(db_session):
    defect = _defect(db_session)
    source = _run(db_session, key="SRC2", outcome="FAIL", status="COMPLETED")
    _node_with_assertion(db_session, source, status="FAILED", assertion_status="FAIL")
    verify = _run(db_session, key="VERIFY2", outcome="PASS", status="COMPLETED")
    _node_with_assertion(db_session, verify, status="PASSED", assertion_status="PASS")
    artifact = RunArtifact(
        project_id=1,
        run_id=verify.id,
        artifact_type=ArtifactType.SCREENSHOT,
        storage_uri="artifact://x",
        sha256="b" * 64,
        upload_status=ArtifactUploadStatus.AVAILABLE,
        size_bytes=1,
    )
    db_session.add(artifact)
    db_session.flush()
    _regression(db_session, defect, source, verify)

    result = handle_run_terminal(db_session, run_id=verify.id)
    assert result.status == "PASS"
    assert result.suggestion == "READY_FOR_HUMAN_CLOSE"
    assert result.comparison_id
    from app.models.defect import RunComparisonSnapshot

    snapshot = db_session.get(RunComparisonSnapshot, result.comparison_id)
    assert snapshot.outcome == "PASS"
    assert f"artifact:{artifact.id}" in snapshot.evidence_refs_json
    assert snapshot.fixed_failures_json == ["ui:ui.ok"]
    assert defect.status == "open"  # AI 不得自动关闭缺陷

    again = handle_run_terminal(db_session, run_id=verify.id)
    assert again.skipped is True
    assert again.reason == "ALREADY_HANDLED"
    assert again.comparison_id == result.comparison_id


def test_required_failure_maps_to_fail_and_needs_more_fix(db_session):
    defect = _defect(db_session)
    source = _run(db_session, key="SRC3", outcome="FAIL")
    _node_with_assertion(db_session, source, status="FAILED", assertion_status="FAIL")
    verify = _run(db_session, key="VERIFY3", outcome="FAIL")
    _node_with_assertion(db_session, verify, status="FAILED", assertion_status="FAIL")
    regression = _regression(db_session, defect, source, verify)
    result = handle_run_terminal(db_session, run_id=verify.id)
    assert result.status == "FAIL"
    assert result.suggestion == "NEEDS_MORE_FIX"
    assert regression.failing_case_ids_json == ["ui:ui.ok"]


def test_outcome_pass_without_assertions_is_unknown(db_session):
    defect = _defect(db_session)
    source = _run(db_session, key="SRC4", outcome="FAIL")
    verify = _run(db_session, key="VERIFY4", outcome="PASS")
    node = NodeRun(run_id=verify.id, node_key="ui", driver_key="http", status="PASSED")
    db_session.add(node)
    db_session.flush()
    _regression(db_session, defect, source, verify)
    status, summary, _failing, _blocked = aggregate_regression_status(db_session, verify)
    assert status == "UNKNOWN"
    assert summary["reason"] == "NO_REQUIRED_ASSERTIONS"
    result = handle_run_terminal(db_session, run_id=verify.id)
    assert result.status == "UNKNOWN"
    assert result.suggestion == "INCONCLUSIVE"


def test_blocked_required_assertion_maps_to_blocked(db_session):
    defect = _defect(db_session)
    source = _run(db_session, key="SRC5", outcome="FAIL")
    _node_with_assertion(db_session, source, status="FAILED", assertion_status="FAIL")
    verify = _run(db_session, key="VERIFY5", outcome="INCOMPLETE")
    _node_with_assertion(db_session, verify, status="BLOCKED", assertion_status="BLOCKED")
    _regression(db_session, defect, source, verify)
    result = handle_run_terminal(db_session, run_id=verify.id)
    assert result.status == "BLOCKED"
    assert result.suggestion == "NEEDS_MORE_FIX"
