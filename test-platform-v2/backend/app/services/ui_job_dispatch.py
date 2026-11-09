"""batch-277b / P0-4：把 /uitest 执行派发到 cameltv-node（feature-flag `node` 模式）。

控制面职责不变：读 spec、静态安全拦截、解析环境变量、记录 run；
真实 Playwright 执行由节点完成，结果/证据通过 ExecutionJob 回传并投影到 UiTestRun。

默认 `settings.uitest_execution_mode == "local"`，本模块只在显式切到 `node` 时被调用。
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.execution_job import ExecutionJob
from app.models.ui_test import UiTestJob, UiTestRun
from app.services import execution_evidence_store as evidence_store
from app.services import execution_job_service

logger = logging.getLogger("ui.node_dispatch")

MAX_SPEC_BYTES = 2 * 1024 * 1024
_STATUS_MAP = {"completed": "done", "failed": "fail", "cancelled": "cancelled"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def build_payload(
    db: Session,
    job: UiTestJob,
    *,
    project_id: int,
    base_url: str,
) -> dict[str, Any]:
    """读取 spec 内容并构建节点可执行载荷；不通过安全拦截则抛 ValueError。"""
    from app.core import spec_guard
    from app.services import playwright_executor as pw

    spec = (job.test_spec or "").strip()
    runner_root = pw._runner_dir().resolve()
    spec_path = (runner_root / spec).resolve()
    if not spec or not spec_path.is_relative_to(runner_root):
        raise ValueError(f"测试脚本不存在: {spec or '(未指定)'}")
    if not spec_path.exists():
        pw._restore_generated_spec(runner_root, spec)
    if not spec_path.exists():
        raise ValueError(f"测试脚本不存在: {spec}")

    try:
        content = spec_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:  # pragma: no cover - 权限/IO 异常
        raise ValueError(f"读取测试脚本失败: {exc}") from exc
    if len(content.encode("utf-8")) > MAX_SPEC_BYTES:
        raise ValueError("测试脚本超过 2MB 上限")

    findings = spec_guard.assert_spec_safe(content)
    if findings:
        raise ValueError("用例代码包含禁止使用的 API，已拒绝执行：\n" + "\n".join(findings))

    env = pw._resolve_environment_variables(db, job.environment_id)
    entry = spec_path.relative_to(runner_root).as_posix()
    return {
        "mode": "spec",
        "entry": entry,
        "files": [{"name": entry, "content": content}],
        "browser": (job.browser or "chromium").strip() or "chromium",
        "base_url": base_url or "",
        "env": env,
        "timeout_seconds": int(settings.ui_runner_timeout_seconds),
    }


def dispatch(
    db: Session,
    job: UiTestJob,
    run: UiTestRun,
    *,
    project_id: int,
    payload: dict[str, Any],
) -> ExecutionJob:
    """创建 ExecutionJob(kind="ui") 并绑定到 run（不阻塞请求）。"""
    exec_job = execution_job_service.create_job(
        db,
        project_id=project_id,
        kind="ui",
        case_refs=[str(job.test_spec or ""), f"ui-job:{job.id}"],
        env_ref=str(job.environment_id or ""),
        timeout_seconds=int(settings.uitest_node_timeout_seconds),
        payload=payload,
    )
    run.execution_job_id = exec_job.id
    run.status = "pending"
    db.commit()
    logger.info("Dispatched ui run #%s as execution job #%s", run.id, exec_job.id)
    return exec_job


def find_run(db: Session, execution_job_id: int) -> UiTestRun | None:
    return db.scalar(select(UiTestRun).where(UiTestRun.execution_job_id == execution_job_id))


def sync_run_from_job(db: Session, exec_job: ExecutionJob) -> UiTestRun | None:
    """把节点上报后的 ExecutionJob 投影回 UiTestRun（幂等）。"""
    run = find_run(db, exec_job.id)
    if run is None:
        return None
    new_status = _STATUS_MAP.get(exec_job.status, run.status)
    run.status = new_status
    run.result = exec_job.result_json or "{}"
    run.error_message = exec_job.error_message or ""
    if exec_job.finished_at is not None:
        run.finished_at = exec_job.finished_at
    elif new_status in ("done", "fail", "cancelled"):
        run.finished_at = _utcnow()
    attempt = max(1, int(exec_job.attempt or 1))
    run.artifact_dir = str(evidence_store.bundle_dir(exec_job.id, attempt)).replace("\\", "/")

    ui_job = db.get(UiTestJob, run.job_id)
    if ui_job is not None:
        ui_job.status = "done" if new_status == "done" else ("fail" if new_status == "fail" else ui_job.status)
        ui_job.last_result = run.result
    db.commit()
    db.refresh(run)

    if ui_job is not None:
        try:
            from app.services.ui_test_service import writeback_case_result

            writeback_case_result(db, ui_job, run)
            db.commit()
        except Exception:  # 回写失败不影响节点结果投影
            logger.exception("writeback_case_result failed for ui run #%s", run.id)
    return run


def payload_for_node(exec_job: ExecutionJob) -> dict[str, Any]:
    raw = exec_job.payload_json or "{}"
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


__all__ = [
    "MAX_SPEC_BYTES",
    "build_payload",
    "dispatch",
    "find_run",
    "payload_for_node",
    "sync_run_from_job",
]
