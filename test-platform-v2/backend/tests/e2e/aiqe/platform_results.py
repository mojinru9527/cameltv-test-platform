"""V16-017 平台链路 E2E 机器结果采集。

设计边界
--------
- 平台链路 E2E 只产出 ``TC-PLATFORM-*`` 命名空间的机器结果，**不是**产品 TC 验收。
- 结果文件默认写到 ``work-logs/evidence/aiqe-v16/platform-results.json``（CI artifact），
  本地归档时可用环境变量 ``AIQE_PLATFORM_RESULTS`` 指向
  ``docs/aiqe/v1.6/e2e/platform-results.json``。
- 只记录真实持久化对象（TestRun/ExecutionJob/NodeRun/RunAssertionResult/RunArtifact），
  没有任何 ID 的场景必须显式 ``status=NOT_RUN`` 并给出原因，禁止用“跑过”冒充通过。
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

_DEFAULT_PATH = "work-logs/evidence/aiqe-v16/platform-results.json"
_RESULTS: dict[str, dict[str, Any]] = {}


def _repo_root() -> Path:
    backend = Path(__file__).resolve().parents[3]
    return backend.parents[1]


def _commit_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover - 非 git 环境
        return "unknown"


def _collect_ids(db: Any, run: Any) -> dict[str, Any]:
    from app.aiqe.models.artifact import RunArtifact
    from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt

    node_ids = [
        str(row)
        for row in db.scalars(select(NodeRun.id).where(NodeRun.run_id == run.id))
        if row is not None
    ]
    assertion_ids = [
        str(row)
        for row in db.scalars(
            select(RunAssertionResult.id)
            .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
            .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
            .where(NodeRun.run_id == run.id)
        )
        if row is not None
    ]
    artifact_ids: list[str] = []
    try:
        artifact_ids = [
            str(row)
            for row in db.scalars(
                select(RunArtifact.id).where(RunArtifact.run_id == run.id)
            )
            if row is not None
        ]
    except Exception:  # pragma: no cover - artifact 表不可用时按空处理
        artifact_ids = []
    from app.models.execution_job import ExecutionJob

    job_ids = [
        str(row)
        for row in db.scalars(select(ExecutionJob.id).where(ExecutionJob.run_id == run.id))
        if row is not None
    ]
    return {
        "run_id": str(run.id),
        "project_id": int(run.project_id) if run.project_id is not None else None,
        "workflow_snapshot_hash": str(getattr(run, "workflow_checksum", "") or ""),
        "job_ids": job_ids,
        "node_run_ids": node_ids,
        "assertion_ids": assertion_ids,
        "artifact_refs": artifact_ids,
        "run_status": str(getattr(run, "status", "") or ""),
        "run_outcome": str(getattr(run, "outcome", "") or ""),
    }


def record_tc(
    tc_id: str,
    db: Any = None,
    run: Any = None,
    *,
    status: str = "PASS",
    blocked_reason: str = "",
    duration_ms: int = 0,
    driver_image_digest: str = "",
) -> None:
    """登记一个平台链路 TC 的机器结果（重复登记以最后一次为准）。"""
    record: dict[str, Any] = {
        "tc_id": tc_id,
        "status": status.upper(),
        "blocked_reason": blocked_reason,
        "duration_ms": int(duration_ms or 0),
        "driver_image_digest": driver_image_digest,
    }
    if db is not None and run is not None:
        record.update(_collect_ids(db, run))
    _RESULTS[tc_id] = record


def pending_jobs(db: Any, run: Any) -> list[int]:
    """返回仍处于 pending 的 Job（用于断言“没有人工 fallback 消费”）。"""
    from app.models.execution_job import ExecutionJob

    return [
        int(row)
        for row in db.scalars(
            select(ExecutionJob.id).where(
                ExecutionJob.run_id == run.id, ExecutionJob.status == "pending"
            )
        )
        if row is not None
    ]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    if not _RESULTS:
        return
    target = Path(os.environ.get("AIQE_PLATFORM_RESULTS") or _DEFAULT_PATH)
    if not target.is_absolute():
        target = _repo_root() / target
    payload = {
        "schema_version": "1.0",
        "artifact_kind": "platform-chain-e2e",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": _commit_sha(),
        "ci_run": os.environ.get("GITHUB_RUN_ID") or "local",
        "environment": os.environ.get("AIQE_ENVIRONMENT") or "local",
        "tests": sorted(_RESULTS.values(), key=lambda item: item["tc_id"]),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"\n[aiqe-e2e] platform results written: {target} ({len(_RESULTS)} TC)")
