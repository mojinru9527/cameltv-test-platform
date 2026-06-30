"""工作台聚合统计 API。"""
from __future__ import annotations

from fastapi import APIRouter

from server.store import workspace_stats, list_tasks

router = APIRouter(tags=["workspace"])


@router.get("/workspace/stats")
def get_workspace_stats():
    stats = workspace_stats()
    # 最近 10 条任务
    recent_tasks = list_tasks(limit=10)
    stats["recent_tasks"] = recent_tasks
    return stats
