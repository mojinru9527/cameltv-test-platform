"""POST /api/ui-auto/run  — UI 自动化触发。"""
from fastapi import APIRouter

from server.task_store import create_task, finish_task

router = APIRouter(tags=["ui-auto"])


@router.post("/ui-auto/run")
def run_ui_auto(req: dict = None):
    env = (req or {}).get("env", "test")
    task_id = create_task("ui-auto", env)

    try:
        import subprocess
        from pathlib import Path

        ui_dir = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "automation" / "ui"
        if not ui_dir.exists():
            finish_task(task_id, "failed", "ui 目录不存在")
            return {"status": "error", "message": "UI 自动化项目目录不存在，请先 npm install"}

        env_vars = {"TEST_ENV": env, "CI": "true"}
        result = subprocess.run(
            ["npx", "playwright", "test"],
            cwd=str(ui_dir),
            env={**__import__("os").environ, **env_vars},
            capture_output=True, text=True, timeout=600,
        )
        passed = result.returncode == 0
        finish_task(task_id, "passed" if passed else "failed",
                    f"exit_code={result.returncode}")
        return {
            "status": "passed" if passed else "failed",
            "env": env,
            "exit_code": result.returncode,
        }
    except Exception as e:
        finish_task(task_id, "failed", str(e))
        return {"status": "error", "env": env, "message": str(e)}
