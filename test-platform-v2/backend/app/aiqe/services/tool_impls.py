"""V16-019：内建只读工具实现（真实 DB 事实，不接受调用方 Facts）。

未实现/需要写副作用的工具保持 ``UNAVAILABLE``，Agent Plan 不得把它们当可用；
生产环境默认只开放 READ 工具。
"""
from __future__ import annotations

from pathlib import Path
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


def read_requirements(
    db: Session, *, project_id: int, requirement_id: str = "", limit: int = 20, **_: Any
) -> dict[str, Any]:
    """读取本项目的需求契约与验收标准（只读、项目隔离）。

    V16-019 补齐：A1/A2/A5 需要真实需求事实，不能依赖调用方 Facts。
    """
    from app.aiqe.models.contract import AcceptanceCriterion, RequirementContract

    query = select(RequirementContract).where(
        RequirementContract.project_id == int(project_id)
    )
    if requirement_id:
        query = query.where(RequirementContract.requirement_id == str(requirement_id))
    contracts = list(
        db.scalars(
            query.order_by(RequirementContract.id.desc()).limit(max(1, min(int(limit), 100)))
        )
    )
    items: list[dict[str, Any]] = []
    for contract in contracts:
        acs = list(
            db.scalars(
                select(AcceptanceCriterion).where(AcceptanceCriterion.contract_id == contract.id)
            )
        )
        items.append(
            {
                "contract_id": contract.id,
                "requirement_id": contract.requirement_id,
                "status": contract.status,
                "revision": contract.revision,
                "revision_checksum": contract.revision_checksum,
                "acceptance_criteria": [
                    {
                        "ac_id": ac.ac_id,
                        "given": ac.given,
                        "when": ac.when,
                        "then": list(ac.then_json or []),
                        "priority": ac.priority,
                        "oracle_type": ac.oracle_type,
                        "oracle_ref": ac.oracle_ref,
                        "approval_status": ac.approval_status,
                    }
                    for ac in acs
                ],
            }
        )
    return {"project_id": int(project_id), "count": len(items), "items": items}


def read_git_diff(
    db: Session,
    *,
    project_id: int,
    base_sha: str,
    head_sha: str,
    max_files: int = 200,
    **_: Any,
) -> dict[str, Any]:
    """读取服务器侧 Git diff 并做影响面分析（SHAs 严格校验，仓库路径不可由调用方指定）。

    V16-019/V16-014 补齐：A5 必须基于真实 diff/AST/route/migration 证据，
    不能由调用方提交一份算好的 impact_analysis。
    """
    import re

    from app.aiqe.services.change_impact import analyze_change_impact
    from app.aiqe.services.impact_service import _run_git, collect_changes

    sha_pattern = re.compile(r"^[0-9a-f]{40}$")
    base = str(base_sha or "").strip().lower()
    head = str(head_sha or "").strip().lower()
    for name, value in (("base_sha", base), ("head_sha", head)):
        if not sha_pattern.match(value):
            raise ValueError(f"{name} 必须是完整 40 位小写 SHA")
    repo_root = Path(__file__).resolve().parents[5]
    files, symbols, routes, migrations, components = collect_changes(str(repo_root), base, head)
    if not files:
        raise ValueError("diff 为空或 SHA 不在仓库历史中")
    diff_text = _run_git(str(repo_root), ["diff", "--unified=0", f"{base}..{head}"])
    analysis = analyze_change_impact(
        base_sha=base,
        head_sha=head,
        repo_root=str(repo_root),
        changed_files=[item.path for item in files],
        diff_text=diff_text[:200_000],
    )
    limit = max(1, min(int(max_files), 500))
    return {
        "project_id": int(project_id),
        "base_sha": base,
        "head_sha": head,
        "file_count": len(files),
        "files": [
            {"path": item.path, "status": item.status, "added": item.added, "removed": item.removed}
            for item in files[:limit]
        ],
        "symbols": symbols,
        "routes": routes,
        "migrations": migrations,
        "components": components,
        "analysis": analysis,
        "derived_by": "server:impact_service+change_impact",
    }


READ_TOOLS: dict[str, Any] = {
    "read_project_context": read_project_context,
    "read_openapi": read_openapi,
    "read_run_evidence": read_run_evidence,
    "read_defects": read_defects,
    "read_noise_rules": read_noise_rules,
    "read_benchmark_dataset": read_benchmark_dataset,
    "read_requirements": read_requirements,
    "read_git_diff": read_git_diff,
}

#: 未实现真实实现（或需要写副作用审批）的工具必须显式 UNAVAILABLE。
#: 写工具（create_*）保持不可用：必须走审批与副作用门禁，不能为了“工具全绿”放开。
UNAVAILABLE_TOOLS = frozenset(
    {
        "create_draft",
        "create_regression_plan",
        "create_learning_candidate",
    }
)

__all__ = ["READ_TOOLS", "UNAVAILABLE_TOOLS"]
