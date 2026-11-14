"""batch-341 + v1.4 FIX-011：缺陷修复回归请求 → 真实新 Run 派发。

与旧实现的区别：
- 不再只插入一条 QUEUED Run 冒充“回归已启动”；
- 固定原失败 Run 的 Workflow 快照/checksum，不随当前最新版本漂移；
- 必须验证 `deployed_sha == fixed_sha`，否则 Run BLOCKED（不执行）；
- 复用正常 `launch_run` 路径创建 NodeRun/ExecutionJob，旧 Run 只读不变；
- 没有可执行 Workflow 快照时创建 BLOCKED Run 并给出明确 reason，绝不 QUEUED 悬挂。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import TestRun
from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services.run_launch import LaunchError, launch_run
from app.aiqe.services.workflow_validator import workflow_checksum
from app.models.defect import Defect, DefectRegression


class RegressionError(ValueError):
    pass


class RegressionNotFound(LookupError):
    pass


def _workflow_snapshot(db: Session, previous: TestRun) -> tuple[dict | None, str, str | None]:
    graph = dict(previous.workflow_snapshot_json or {})
    checksum = previous.workflow_checksum or ""
    workflow_id = previous.workflow_definition_id
    if not graph and workflow_id:
        workflow = db.get(WorkflowDefinition, workflow_id)
        if workflow is not None and int(workflow.project_id or 0) == int(previous.project_id or 0):
            graph = dict(workflow.graph_json or {})
            checksum = checksum or workflow.checksum
    if graph and not checksum:
        checksum = workflow_checksum(graph)
    return (graph or None), checksum, workflow_id


def create_regression(
    db: Session,
    *,
    project_id: int,
    defect_id: int,
    fixed_sha: str,
    previous_run_id: str | None = None,
    deployed_sha: str = "",
    environment_snapshot: dict | None = None,
    launch_key: str = "",
) -> tuple[DefectRegression, TestRun]:
    sha = (fixed_sha or "").strip()
    if len(sha) < 7:
        raise RegressionError("fixed_sha 至少 7 位")
    defect = db.get(Defect, defect_id)
    if defect is None or int(defect.project_id or 0) != int(project_id):
        raise RegressionError(f"缺陷不存在: {defect_id}")

    previous: TestRun | None = None
    if previous_run_id:
        previous = db.get(TestRun, previous_run_id)
        if previous is None or int(previous.project_id or 0) != int(project_id):
            raise RegressionError(f"旧 Run 不存在: {previous_run_id}")

    now = datetime.now(UTC)
    snapshot = {
        "fixed_sha": sha,
        "deployed_sha": deployed_sha,
        "defect_id": defect_id,
        "previous_run_id": previous_run_id,
        **(environment_snapshot or {}),
    }

    if previous is None:
        run = TestRun(
            project_id=project_id,
            run_key=f"REG-{sha[:7]}-{uuid.uuid4().hex[:8]}",
            source_type="regression",
            retest_of=None,
            commit_sha=sha,
            status="BLOCKED",
            environment_snapshot_json={
                **snapshot,
                "reason": "REGRESSION_PREVIOUS_RUN_REQUIRED",
            },
            created_at=now,
        )
        db.add(run)
        db.flush()
    else:
        graph, checksum, workflow_id = _workflow_snapshot(db, previous)
        if not graph:
            run = TestRun(
                project_id=project_id,
                run_key=f"REG-{sha[:7]}-{uuid.uuid4().hex[:8]}",
                source_type="regression",
                retest_of=previous.id,
                commit_sha=sha,
                status="BLOCKED",
                workflow_definition_id=workflow_id,
                workflow_checksum=checksum,
                environment_snapshot_json={
                    **snapshot,
                    "reason": "REGRESSION_WORKFLOW_MISSING",
                },
                created_at=now,
            )
            db.add(run)
            db.flush()
        else:
            if not deployed_sha:
                run = TestRun(
                    project_id=project_id,
                    run_key=f"REG-{sha[:7]}-{uuid.uuid4().hex[:8]}",
                    source_type="regression",
                    retest_of=previous.id,
                    commit_sha=sha,
                    status="BLOCKED",
                    workflow_definition_id=workflow_id,
                    workflow_checksum=checksum,
                    workflow_snapshot_json=graph,
                    environment_snapshot_json={
                        **snapshot,
                        "reason": "FIXED_SHA_NOT_VERIFIED",
                    },
                    created_at=now,
                )
                db.add(run)
                db.flush()
            elif not (
                deployed_sha == sha
                or deployed_sha.startswith(sha)
                or sha.startswith(deployed_sha)
            ):
                run = TestRun(
                    project_id=project_id,
                    run_key=f"REG-{sha[:7]}-{uuid.uuid4().hex[:8]}",
                    source_type="regression",
                    retest_of=previous.id,
                    commit_sha=sha,
                    status="BLOCKED",
                    workflow_definition_id=workflow_id,
                    workflow_checksum=checksum,
                    workflow_snapshot_json=graph,
                    environment_snapshot_json={
                        **snapshot,
                        "reason": "FIXED_SHA_MISMATCH",
                    },
                    created_at=now,
                )
                db.add(run)
                db.flush()
            else:
                try:
                    run = launch_run(
                        db,
                        project_id=project_id,
                        user_id=None,
                        workflow_definition_id=workflow_id,
                        graph_override=graph,
                        expected_checksum=checksum,
                        retest_of=previous.id,
                        commit_sha=sha,
                        launch_key=launch_key or f"regression-{defect_id}-{sha[:7]}-{uuid.uuid4().hex[:8]}",
                        source_type="regression",
                        source_id=str(defect_id),
                        environment_snapshot={
                            **snapshot,
                            "fixture_strategy": (environment_snapshot or {}).get(
                                "fixture_strategy", "isolated"
                            ),
                            "selection_reason": "failed_scenario+p0_smoke+impact_set",
                        },
                    )
                except LaunchError as exc:
                    raise RegressionError(f"{exc.code}: {exc}") from exc

    row = DefectRegression(
        defect_id=defect_id,
        fixed_sha=sha,
        previous_run_id=previous_run_id or None,
        verification_run_id=run.id,
        status=(
            "pending" if run.status in {"RUNNING", "QUEUED"} else "blocked"
        ),
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row, run


def get_regression(db: Session, regression_id: int, project_id: int) -> DefectRegression:
    row = db.get(DefectRegression, regression_id)
    if row is None:
        raise RegressionNotFound(str(regression_id))
    defect = db.get(Defect, row.defect_id)
    if defect is None or int(defect.project_id or 0) != int(project_id):
        raise RegressionNotFound(str(regression_id))
    return row


def list_regressions(
    db: Session, project_id: int, *, defect_id: int | None = None, limit: int = 100
) -> list[DefectRegression]:
    stmt = (
        select(DefectRegression)
        .join(Defect, Defect.id == DefectRegression.defect_id)
        .where(Defect.project_id == project_id)
        .order_by(DefectRegression.created_at.desc())
        .limit(limit)
    )
    if defect_id is not None:
        stmt = stmt.where(DefectRegression.defect_id == defect_id)
    return list(db.scalars(stmt))


def get_verification_run(db: Session, row: DefectRegression) -> TestRun | None:
    if not row.verification_run_id:
        return None
    return db.get(TestRun, row.verification_run_id)
