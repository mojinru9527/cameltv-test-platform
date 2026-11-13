"""batch-341（M9-2）：AIQE 缺陷修复回归请求（DefectRegression + 新 TestRun）。

与既有 `POST /defects/{id}/regressions` 的区别：
- 本服务一次调用同时创建 **verification TestRun**（`source_type=regression`，`retest_of=旧 Run`，
  `commit_sha=fixed_sha`），并回填 `defect_regressions.verification_run_id`；
- 旧 Run 只读引用，不被修改；
- 项目隔离：缺陷/旧 Run 必须属于当前项目。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import TestRun
from app.models.defect import Defect, DefectRegression


class RegressionError(ValueError):
    pass


class RegressionNotFound(LookupError):
    pass


def create_regression(
    db: Session,
    *,
    project_id: int,
    defect_id: int,
    fixed_sha: str,
    previous_run_id: str | None = None,
    environment_snapshot: dict | None = None,
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
    run = TestRun(
        project_id=project_id,
        run_key=f"REG-{sha[:7]}-{uuid.uuid4().hex[:8]}",
        source_type="regression",
        retest_of=previous_run_id or None,
        commit_sha=sha,
        status="QUEUED",
        environment_snapshot_json={
            "fixed_sha": sha,
            "defect_id": defect_id,
            "previous_run_id": previous_run_id,
            **(environment_snapshot or {}),
        },
        created_at=now,
    )
    db.add(run)
    db.flush()

    row = DefectRegression(
        defect_id=defect_id,
        fixed_sha=sha,
        previous_run_id=previous_run_id or None,
        verification_run_id=run.id,
        status="pending",
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
