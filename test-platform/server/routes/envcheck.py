"""POST /api/envcheck  — 环境健康检查。"""
from fastapi import APIRouter

from server.dependencies import get_context
from server.task_store import create_task, finish_task

router = APIRouter(tags=["envcheck"])


@router.post("/envcheck")
def run_envcheck(req: dict = None):
    env = (req or {}).get("env", "test")
    task_id = create_task("envcheck", env)

    try:
        from tools.env_check import run_check as _run_check
        ctx = get_context(env)
        ok = _run_check(ctx)
        status = "passed" if ok else "failed"
        finish_task(task_id, status, f"envcheck {env}: {'ok' if ok else 'failed'}")
        return {
            "status": status,
            "env": env,
            "message": f"环境健康检查完成: {'✓ 正常' if ok else '✗ 不通'}",
        }
    except Exception as e:
        finish_task(task_id, "failed", str(e))
        return {"status": "error", "env": env, "message": str(e)}
