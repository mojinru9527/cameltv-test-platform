"""C102-1/C117-2 — AI 生成/提取异步任务（DB 队列，多 worker 可消费）。

请求先返回 task_id；后台 worker 从 DB 原子认领 pending 任务执行（任何进程的
worker 都可认领，避免单进程注册表在多 worker 部署下丢任务）。前端轮询
GET /requirements/ai-task/{task_id}。

Batch 181（FIX-173-P2-06）：认领/回收/循环骨架收敛到 app.core.task_queue 统一原语；
模型补 locked_by 列（20260816_b181_task_queue_locks）。
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.core.db import SessionLocal
from app.core.task_queue import (
    QueueSpec,
    QueueWorkerLoop,
    atomic_claim,
    utcnow,
)
from app.models.ai_task import AiTask

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

# 认领失联阈值：锁超时即视为执行器失联，可被重认领（原 5 分钟，与 DSH 对齐为 300s）
_STALE_CLAIM_SECONDS = 300

_AI_QUEUE = QueueSpec(
    model=AiTask,
    id_col="id",
    status_col="status",
    pending="pending",
    running="running",
    failed="failed",
    lock_by_col="locked_by",
    lock_at_col="locked_at",
    order_col="created_at",
    order_asc=True,
)

_loop = QueueWorkerLoop(name="ai-task-worker", poll_interval=1.0, on_tick=lambda: _poll_once())


def _now() -> datetime:
    return utcnow()


def _to_dict(row: AiTask) -> dict:
    return {
        "id": row.id,
        "type": row.task_type,
        "project_id": row.project_id,
        "document_id": row.document_id,
        "status": row.status,
        "progress": row.progress,
        "result": json.loads(row.result_json) if row.result_json and row.result_json != "null" else None,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def submit_ai_task(*, document_id: int, task_type: str, project_id: int) -> dict:
    """插入 pending 任务并唤醒 worker（多 worker 部署下任何进程均可认领）。"""
    task_id = f"ai-{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        db.add(AiTask(
            id=task_id,
            task_type=task_type,
            project_id=project_id,
            document_id=document_id,
            status="pending",
            progress=0,
            result_json="null",
            error="",
        ))
        db.commit()
    finally:
        db.close()
    ensure_worker_running()
    _loop.kick()
    return get_ai_task(task_id) or {"id": task_id, "status": "pending"}


def get_ai_task(task_id: str) -> dict | None:
    db = SessionLocal()
    try:
        row = db.get(AiTask, task_id)
        return _to_dict(row) if row else None
    finally:
        db.close()


def claim_next_task(db, now: datetime | None = None) -> AiTask | None:
    """认领最早的 pending 任务（stale 锁可重认领），Batch 181 起走统一原语。

    条件 UPDATE + rowcount 校验保证多 worker 下同一条任务仅一个认领者。
    """
    task = atomic_claim(db, _AI_QUEUE, worker_id="ai-worker", stale_seconds=_STALE_CLAIM_SECONDS)
    if task is not None:
        # 保留原语义：认领即进度 5%
        task.progress = 5
        db.commit()
    return task


def _run_extract(db, document_id: int, project_id: int = 0) -> dict:
    from app.services.requirement_service import get_requirement

    # Batch 161 follow-up：必须按任务所属项目查询，否则跨项目文档内容为空 → AI 提取 0 模块
    doc = get_requirement(db, document_id, project_id=project_id) or {}
    content = doc.get("content") or doc.get("requirement_text") or ""
    import asyncio
    from app.services.ai_service import extract_features as _ai_extract

    result = asyncio.run(_ai_extract(
        content,
        file_type=doc.get("file_type", ""),
        source_ref=str(doc.get("source_ref") or ""),
    ))
    # Batch 161 follow-up2：异步拆分结果必须持久化（否则 UI 看不到/无法确认拆分）
    from app.services.requirement_service import update_extraction

    update_extraction(db, document_id, result, commit=False)
    return result


def _run_generate(db, document_id: int, project_id: int = 0) -> dict:
    from app.services.requirement_service import get_extraction, get_requirement

    # Batch 161 follow-up：按任务所属项目查询（否则内容为空 → AI 返回 0 用例）
    doc = get_requirement(db, document_id, project_id=project_id) or {}
    content = doc.get("content") or doc.get("requirement_text") or ""
    from app.services.ai_service import generate_test_cases as _ai_gen
    from app.services.coverage_report import build_coverage_report

    # 已确认的功能拆分作为引导上下文（与同步 /generate 路径对齐）
    extraction = None
    try:
        if doc.get("extraction_status") == "confirmed":
            extraction = get_extraction(db, document_id, project_id=project_id)
    except Exception:  # noqa: BLE001 - 提取读取失败不影响内容生成
        extraction = None
    extraction_modules = (extraction or {}).get("modules") or []

    import asyncio

    result = asyncio.run(_ai_gen(
        content,
        file_type=doc.get("file_type", ""),
        source_ref=str(doc.get("source_ref") or ""),
        extraction={"modules": extraction_modules} if extraction_modules else None,
    ))
    result["coverage_report"] = build_coverage_report({"modules": extraction_modules}, result)
    # Batch 161 follow-up2：异步生成结果必须持久化（否则 UI 查看/导入为空）
    from app.services.requirement_service import update_ai_result

    update_ai_result(db, document_id, result, commit=False)
    return result


def _dispatch(task_type: str, document_id: int, db, project_id: int = 0) -> dict:
    if task_type == "extract":
        return _run_extract(db, document_id, project_id)
    if task_type == "generate":
        return _run_generate(db, document_id, project_id)
    raise ValueError(f"未知任务类型: {task_type}")


def execute_task(db, task: AiTask, dispatch=None) -> None:
    """执行已认领任务并写回结果/错误。dispatch 可注入用于测试。"""
    dispatch = dispatch or _dispatch
    try:
        result = dispatch(task.task_type, task.document_id, db, project_id=task.project_id)
        task.status = "done"
        task.progress = 100
        task.result_json = json.dumps(result, ensure_ascii=False, default=str)
        task.locked_at = None
        task.locked_by = ""
        task.finished_at = _now()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 任务失败写回
        task.status = "failed"
        task.error = str(exc)[:500]
        task.locked_at = None
        task.locked_by = ""
        task.finished_at = _now()
        db.commit()


def _poll_once() -> None:
    """单次轮询：原子认领一条任务并提交到执行池。"""
    db = SessionLocal()
    try:
        task = claim_next_task(db)
        if task is not None:
            _executor.submit(_process_claimed, task.id)
    except Exception as exc:  # noqa: BLE001 - 轮询失败不退出
        logger.warning("AI task worker poll error: %s", exc)
    finally:
        db.close()


def _process_claimed(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(AiTask, task_id)
        if task is None or task.status != "running":
            return
        execute_task(db, task)
    finally:
        db.close()


def ensure_worker_running() -> None:
    """启动后台轮询线程（幂等）。每个进程一个 worker，均可认领 DB 中的任务。"""
    _loop.start()


def shutdown_worker(timeout: float = 5.0) -> None:
    """优雅关闭 worker 线程。"""
    _loop.shutdown(timeout=timeout)
