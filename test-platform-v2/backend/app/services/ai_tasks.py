"""C102-1 — AI 生成/提取异步任务基建。

大文档 AI 生成/提取超过网关超时（300s 502）：请求先返回 task_id，
后台线程执行（独立 DB session），前端轮询 GET /requirements/ai-task/{task_id}。
进程内注册表（单 worker 部署足够；多 worker 需外部队列——登记后续）。
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)
_TASKS: dict[str, dict] = {}
_LOCK = threading.Lock()


def submit_ai_task(fn, *, task_type: str, project_id: int, **kwargs) -> dict:
    task_id = f"ai-{uuid.uuid4().hex[:10]}"
    with _LOCK:
        _TASKS[task_id] = {
            "id": task_id, "type": task_type, "project_id": project_id,
            "status": "running", "progress": 0, "result": None, "error": "",
            "created_at": time.time(),
        }
    _executor.submit(_run, task_id, fn, kwargs)
    return _TASKS[task_id]


def get_ai_task(task_id: str) -> dict | None:
    with _LOCK:
        return _TASKS.get(task_id)


def _run(task_id: str, fn, kwargs: dict) -> None:
    try:
        result = fn(**kwargs)
        with _LOCK:
            _TASKS[task_id].update({"status": "done", "progress": 100, "result": result})
    except Exception as exc:
        with _LOCK:
            _TASKS[task_id].update({"status": "failed", "error": str(exc)[:500]})