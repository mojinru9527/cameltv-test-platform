"""POST /api/api-test/run | pull-swagger  — API 测试触发与结果查询。"""
from fastapi import APIRouter

from server.dependencies import get_context
from server.task_store import create_task, finish_task

router = APIRouter(tags=["api-test"])


@router.post("/api-test/run")
def run_api_test(req: dict = None):
    env = (req or {}).get("env", "test")
    filter_ = (req or {}).get("filter", "")
    task_id = create_task("api-test", env)

    try:
        from tools.api_tester import run_tests
        ctx = get_context(env)
        result = run_tests(ctx, filter_=filter_)
        status = "passed" if result.get("failed", 1) == 0 else "failed"
        summary = f"total={result.get('total')} passed={result.get('passed')} failed={result.get('failed')}"
        finish_task(task_id, status, summary)
        return {"status": status, "env": env, "result": result}
    except SystemExit as e:
        finish_task(task_id, "failed", str(e))
        return {"status": "failed", "env": env, "message": str(e)}
    except Exception as e:
        finish_task(task_id, "failed", str(e))
        return {"status": "error", "env": env, "message": str(e)}


@router.post("/api-test/pull-swagger")
def pull_swagger(req: dict = None):
    source = (req or {}).get("source", "")
    if not source:
        return {"status": "error", "message": "缺少 source 参数（Swagger URL 或路径）"}

    try:
        from tools.api_tester import pull_swagger
        pull_swagger(source)
        return {"status": "ok", "message": f"Swagger 拉取完成 → tests/api-testing/generated/"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
