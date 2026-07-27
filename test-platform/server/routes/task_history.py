"""GET /api/task-history  — 任务执行历史。"""
from fastapi import APIRouter

from server.task_store import list_tasks

router = APIRouter(tags=["task-history"])


@router.get("/task-history")
def get_task_history(limit: int = 50):
    tasks = list_tasks(limit=limit)
    return {"tasks": tasks, "total": len(tasks)}
