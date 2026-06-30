"""POST /api/datafactory/generate  — 测试数据生成。"""
from fastapi import APIRouter

from server.dependencies import get_context
from server.task_store import create_task, finish_task

router = APIRouter(tags=["datafactory"])


@router.post("/datafactory/generate")
def generate_data(req: dict = None):
    env = (req or {}).get("env", "test")
    template = (req or {}).get("template", "")
    count = (req or {}).get("count", 10)
    task_id = create_task("datafactory", env)

    try:
        from tools.data_factory import run_gen
        ctx = get_context(env)

        if template:
            rule_path = ""
            run_gen(ctx, rule=rule_path, count=count, template=template, output="db")
        else:
            return {"status": "error", "message": "请提供 template 名称"}

        finish_task(task_id, "passed", f"template={template} count={count}")
        return {"status": "ok", "env": env, "template": template, "count": count}
    except Exception as e:
        finish_task(task_id, "failed", str(e))
        return {"status": "error", "message": str(e)}
