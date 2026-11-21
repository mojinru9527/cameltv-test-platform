"""V16-019：内建只读工具实现（真实 DB 事实，不接受调用方 Facts）。

未实现/需要写副作用的工具保持 ``UNAVAILABLE``，Agent Plan 不得把它们当可用；
生产环境默认只开放 READ 工具。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.benchmark import BenchmarkDataset, BenchmarkSample
from app.aiqe.models.event import RunEvent
from app.aiqe.models.noise_rule import NoiseRule
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.models.defect import Defect
from app.models.environment import Environment
from app.models.project import Project

_OPENAPI_PATHS: int | None = None


def read_project_context(db: Session, *, project_id: int, **_: Any) -> dict[str, Any]:
    project = db.get(Project, int(project_id))
    if project is None:
        raise PermissionError("项目不存在或无权限")
    env_count = db.scalar(
        select(func.count()).select_from(Environment).where(Environment.project_id == int(project_id))
    )
    return {
        "project_id": int(project_id),
        "name": project.name,
        "status": project.status,
        "environments": int(env_count or 0),
    }


def read_openapi(db: Session, *, project_id: int, **_: Any) -> dict[str, Any]:
    global _OPENAPI_PATHS
    if _OPENAPI_PATHS is None:
        from app.main import app

        _OPENAPI_PATHS = len(app.openapi().get("paths") or {})
    return {"project_id": int(project_id), "path_count": int(_OPENAPI_PATHS)}


def read_run_evidence(
    db: Session, *, project_id: int, run_id: str, **_: Any
) -> dict[str, Any]:
    run = db.get(TestRun, str(run_id))
    if run is None or int(run.project_id or 0) != int(project_id):
        raise PermissionError("Run 不存在或无权限")
    node_ids = [str(item) for item in db.scalars(select(NodeRun.id).where(NodeRun.run_id == run.id))]
    assertion_count = 0
    if node_ids:
        assertion_count = int(
            db.scalar(
                select(func.count())
                .select_from(RunAssertionResult)
                .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
                .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
                .where(NodeRun.run_id == run.id)
            )
            or 0
        )
    artifact_count = int(
        db.scalar(
            select(func.count())
            .select_from(RunArtifact)
            .where(RunArtifact.run_id == run.id, RunArtifact.deleted_at.is_(None))
        )
        or 0
    )
    last_event = db.scalar(
        select(RunEvent.id).where(RunEvent.run_id == run.id).order_by(RunEvent.seq.desc())
    )
    return {
        "run_id": run.id,
        "status": run.status,
        "outcome": run.outcome,
        "node_count": len(node_ids),
        "assertion_count": assertion_count,
        "artifact_count": artifact_count,
        "last_event_id": last_event,
        "evidence_refs": ([f"run:{run.id}"] + ([f"event:{last_event}"] if last_event else [])),
    }


def read_defects(db: Session, *, project_id: int, limit: int = 20, **_: Any) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(Defect)
            .where(Defect.project_id == int(project_id))
            .order_by(Defect.id.desc())
            .limit(max(1, min(int(limit), 100)))
        )
    )
    return {
        "project_id": int(project_id),
        "count": len(rows),
        "items": [
            {"id": row.id, "title": row.title, "severity": row.severity, "status": row.status}
            for row in rows
        ],
    }


def read_noise_rules(db: Session, *, project_id: int, limit: int = 50, **_: Any) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(NoiseRule)
            .where(NoiseRule.project_id == int(project_id))
            .limit(max(1, min(int(limit), 200)))
        )
    )
    return {"project_id": int(project_id), "count": len(rows)}


def read_benchmark_dataset(
    db: Session, *, project_id: int, dataset_id: str, **_: Any
) -> dict[str, Any]:
    dataset = db.get(BenchmarkDataset, str(dataset_id))
    if dataset is None or int(dataset.project_id or 0) != int(project_id):
        raise PermissionError("数据集不存在或无权限")
    samples = int(
        db.scalar(
            select(func.count())
            .select_from(BenchmarkSample)
            .where(BenchmarkSample.dataset_id == dataset.id)
        )
        or 0
    )
    return {
        "dataset_id": dataset.id,
        "status": dataset.status,
        "content_hash": dataset.content_hash,
        "sample_count": samples,
    }


READ_TOOLS: dict[str, Any] = {
    "read_project_context": read_project_context,
    "read_openapi": read_openapi,
    "read_run_evidence": read_run_evidence,
    "read_defects": read_defects,
    "read_noise_rules": read_noise_rules,
    "read_benchmark_dataset": read_benchmark_dataset,
}

#: 未实现真实实现（或需要写副作用审批）的工具必须显式 UNAVAILABLE。
UNAVAILABLE_TOOLS = frozenset(
    {
        "read_requirements",
        "read_git_diff",
        "create_draft",
        "create_regression_plan",
        "create_learning_candidate",
    }
)

__all__ = ["READ_TOOLS", "UNAVAILABLE_TOOLS"]
