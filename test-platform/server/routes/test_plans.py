"""测试计划管理 REST API — CRUD + 执行。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from server.store import (
    list_plans, get_plan, create_plan, update_plan, delete_plan,
    create_plan_run, finish_plan_run, update_plan_item, get_case,
)
from core.config_loader import ROOT

router = APIRouter(tags=["test-plans"])


# ── Request models ──────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    description: str = ""
    env: str = "test"
    status: str = "draft"
    case_ids: list[int] = Field(default_factory=list)


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    env: str | None = None
    status: str | None = None
    case_ids: list[int] | None = None


# ── Routes ───────────────────────────────────────────────────────

@router.get("/test-plans")
def list_test_plans(status: str = "", limit: int = 50, offset: int = 0):
    plans, total = list_plans(status=status, limit=limit, offset=offset)
    return {"plans": plans, "total": total}


@router.get("/test-plans/{plan_id}")
def get_test_plan(plan_id: int):
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "测试计划不存在")
    return plan


@router.post("/test-plans")
def create_test_plan(body: PlanCreate):
    return create_plan(body.model_dump())


@router.put("/test-plans/{plan_id}")
def update_test_plan(plan_id: int, body: PlanUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    plan = update_plan(plan_id, data)
    if not plan:
        raise HTTPException(404, "测试计划不存在")
    return plan


@router.delete("/test-plans/{plan_id}")
def delete_test_plan(plan_id: int):
    ok = delete_plan(plan_id)
    if not ok:
        raise HTTPException(404, "测试计划不存在")
    return {"deleted": True}


@router.post("/test-plans/{plan_id}/run")
def run_test_plan(plan_id: int, background_tasks: BackgroundTasks):
    """执行测试计划：按 item 顺序逐个运行 API 用例。"""
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "测试计划不存在")
    if not plan.get("items"):
        raise HTTPException(400, "测试计划没有关联用例")

    # 创建执行记录
    run_id = create_plan_run(plan_id)

    # 后台异步执行
    background_tasks.add_task(_execute_plan, plan_id, run_id, plan)
    return {"run_id": run_id, "status": "running", "plan": plan["name"]}


def _execute_plan(plan_id: int, run_id: int, plan: dict) -> None:
    """后台执行计划内所有用例（调用 Playwright API 测试引擎）。"""
    total = len(plan["items"])
    passed = failed = skipped = 0

    for item in plan["items"]:
        case = get_case(item["case_id"])
        if not case:
            update_plan_item(item["id"], "skip", "用例已被删除")
            skipped += 1
            continue

        try:
            # 对于 API 类型用例，调用 Playwright 子进程执行单条测试
            if case["type"] == "api" and case.get("api_spec_ref"):
                result = _run_single_api_test(case)
                if result["status"] == "passed":
                    update_plan_item(item["id"], "pass", result.get("message", ""))
                    passed += 1
                else:
                    update_plan_item(item["id"], "fail", result.get("message", ""))
                    failed += 1
            else:
                # 非 API 用例标记为跳过
                update_plan_item(item["id"], "skip", f"暂不支持 {case['type']} 类型自动执行")
                skipped += 1
        except Exception as exc:
            update_plan_item(item["id"], "fail", str(exc))
            failed += 1

    # 更新计划通过率
    rate = round(passed / total * 100, 1) if total else 0
    status = "passed" if failed == 0 else "failed"
    finish_plan_run(run_id, status, {
        "total": total, "passed": passed, "failed": failed,
        "skipped": skipped, "pass_rate": rate,
    })


def _run_single_api_test(case: dict) -> dict:
    """执行单条 API 用例（grep 精确匹配）。"""
    generated_dir = ROOT / "tests" / "api-testing" / "generated"
    config_path = generated_dir / "playwright.config.ts"

    if not config_path.exists():
        return {"status": "skipped", "message": "Playwright 配置不存在，请先 pull swagger"}

    # 用用例标题作 grep 匹配
    test_name = case.get("title", "").replace('"', '\\"')
    env_vars = {"CAMELTV_BASE_URL": "https://api.cameltv.live"}

    try:
        proc = subprocess.run(
            ["npx", "playwright", "test",
             f"--config={config_path}",
             f"--grep={test_name}",
             "--reporter=json"],
            cwd=str(generated_dir),
            capture_output=True, text=True,
            timeout=120, env={**__import__("os").environ, **env_vars},
        )
        if proc.returncode == 0:
            return {"status": "passed", "message": "OK"}
        else:
            return {"status": "failed", "message": proc.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "message": "执行超时 (120s)"}
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}
