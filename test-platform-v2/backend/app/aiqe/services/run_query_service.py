"""M1 / TA-008：Run Console 只读查询服务（路由层禁止 ORM，查询收敛于此）。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services.artifact_service import list_artifacts
from app.aiqe.services.event_service import list_events


class RunNotFoundError(LookupError):
    pass


def list_runs(
    db: Session,
    *,
    project_id: int,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TestRun], int]:
    base = select(TestRun).where(TestRun.project_id == project_id)
    if status:
        base = base.where(TestRun.status == status)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(base.order_by(TestRun.created_at.desc()).offset(offset).limit(limit))
    )
    return rows, int(total)


def get_run(db: Session, run_id: str, project_id: int) -> TestRun:
    run = db.get(TestRun, run_id)
    if run is None or run.project_id != project_id:
        raise RunNotFoundError(run_id)
    return run


def get_run_detail(db: Session, run_id: str, project_id: int) -> dict:
    run = get_run(db, run_id, project_id)
    return {
        "run": run,
        "events": list_events(db, run_id, limit=200),
        "artifacts": list_artifacts(db, run_id, project_id),
    }


def get_events(
    db: Session, run_id: str, project_id: int, *, after_seq: int = 0, limit: int = 500
):
    get_run(db, run_id, project_id)
    return list_events(db, run_id, after_seq=after_seq, limit=limit)


def get_artifacts(db: Session, run_id: str, project_id: int):
    get_run(db, run_id, project_id)
    return list_artifacts(db, run_id, project_id)

def get_run_attempts(
    db: Session, run_id: str, project_id: int
) -> tuple[TestRun, list[tuple[NodeRun, list[StepAttempt]]]]:
    """batch-340：节点执行尝试时间线（失败 attempt 与重试都保留）。"""
    run = get_run(db, run_id, project_id)
    nodes = list(
        db.scalars(
            select(NodeRun).where(NodeRun.run_id == run.id).order_by(NodeRun.node_key)
        )
    )
    attempts: list[StepAttempt] = []
    if nodes:
        attempts = list(
            db.scalars(
                select(StepAttempt)
                .where(StepAttempt.node_run_id.in_([node.id for node in nodes]))
                .order_by(StepAttempt.attempt_no)
            )
        )
    by_node: dict[str, list[StepAttempt]] = {}
    for attempt in attempts:
        by_node.setdefault(attempt.node_run_id, []).append(attempt)
    return run, [(node, by_node.get(node.id, [])) for node in nodes]
