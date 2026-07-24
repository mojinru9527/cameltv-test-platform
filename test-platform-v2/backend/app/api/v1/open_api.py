"""Open API for CI/CD integration — authenticated via API Token."""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import APIException
from app.core.rate_limit import open_api_limiter
from app.models.api_token import ApiToken
from app.schemas.common import R

router = APIRouter(prefix="/open", tags=["开放API"])

# Allow-listed health check path (no auth required)
_HEALTH_PATH = "/open/health"


def _check_rate_limit(token: ApiToken) -> None:
    """Enforce 60 req/min per token. Raises 429 if exceeded."""
    allowed, wait = open_api_limiter.is_allowed(token.token_hash)
    if not allowed:
        raise APIException(
            code=429,
            msg=f"请求过于频繁，请 {wait}s 后重试 (限制: 60次/分钟)",
            http_status=429,
        )


def verify_api_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> ApiToken:
    """Validate `Bearer tpat_xxx` against stored hashes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise APIException(code=401, msg="缺少 API Token (Authorization: Bearer tpat_xxx)", http_status=401)

    plain = authorization[len("Bearer "):]
    token_hash = hashlib.sha256(plain.encode()).hexdigest()

    row = db.scalar(
        select(ApiToken).where(ApiToken.token_hash == token_hash, ApiToken.enabled == True)
    )
    if not row:
        raise APIException(code=401, msg="无效或已禁用的 API Token", http_status=401)

    # Rate limit check (after auth so we know which token)
    _check_rate_limit(row)

    return row


# ── Health ────────────────────────────────────────────

@router.get("/health", summary="连通性检查")
def health_check():
    """轻量健康检查，无需鉴权。CI 可在触发前调用以验证 API 可达。"""
    return R.ok({"status": "ok", "version": "2.3.0"})


@router.post("/plans/{plan_id}/trigger", response_model=R[dict], summary="CI 触发测试计划执行")
def ci_trigger_plan(
    plan_id: int,
    req: Request,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI (Jenkins/GitHub Actions) 通过 API Token 触发测试计划。

    触发后返回执行摘要。结果可通过 GET /open/runs/{run_id} 查询。
    """
    from app.models.test_plan import TestPlan, TestPlanCase, TestExecution
    from datetime import datetime, timezone

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == token.project_id)
    )
    if not plan:
        raise APIException(code=404, msg="计划不存在")

    # Execute all cases in the plan
    pcases = db.scalars(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
    ).all()

    now = datetime.now(timezone.utc)
    executed = 0
    for pc in pcases:
        exec_row = TestExecution(
            plan_case_id=pc.id, executor_id=0, status="pending",
            actual_result="", notes=f"[CI 自动触发] token={token.name}",
            executed_at=now,
        )
        db.add(exec_row)
        pc.last_status = "pending"
        pc.last_executed_at = now
        executed += 1

    # Update token last_used
    token.last_used_at = now

    db.commit()

    # Background notification
    try:
        from app.services.notify_service import notify_sync
        notify_sync(db, token.project_id, "plan_done", {
            "plan_name": plan.name,
            "result_summary": f"CI 触发 {executed} 条用例已入队",
            "link": "",
        })
    except Exception:
        pass

    return R.ok({
        "triggered": True,
        "plan_id": plan_id,
        "plan_name": plan.name,
        "cases_queued": executed,
        "triggered_by": token.name,
    })


@router.get("/runs/{run_id}", response_model=R[dict], summary="查询执行结果")
def ci_get_run(
    run_id: int,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 查询某次执行的状态与结果。"""
    from app.models.test_plan import TestExecution, TestPlanCase

    exec_row = db.scalar(
        select(TestExecution).where(TestExecution.id == run_id)
    )
    if not exec_row:
        raise APIException(code=404, msg="执行记录不存在")

    # Project isolation via plan_case → plan
    plan_case = db.scalar(
        select(TestPlanCase).where(TestPlanCase.id == exec_row.plan_case_id)
    )
    if not plan_case or plan_case.plan.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此执行记录")

    return R.ok({
        "run_id": exec_row.id,
        "plan_case_id": exec_row.plan_case_id,
        "case_id": plan_case.case_id,
        "status": exec_row.status,
        "actual_result": exec_row.actual_result,
        "notes": exec_row.notes,
        "trace_id": exec_row.trace_id,
        "executed_at": exec_row.executed_at.isoformat() if exec_row.executed_at else None,
    })


@router.post("/results", response_model=R[dict], summary="回写执行结果")
def ci_post_results(
    body: dict,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 回写执行结果 (status, actual_result, trace_id, notes)。

    Body: { run_id: int, status: str, actual_result?: str, trace_id?: str, notes?: str }
    """
    from datetime import datetime, timezone
    from app.models.test_plan import TestExecution, TestPlanCase

    run_id = body.get("run_id")
    if not run_id:
        raise APIException(code=400, msg="缺少 run_id")

    exec_row = db.scalar(
        select(TestExecution).where(TestExecution.id == run_id)
    )
    if not exec_row:
        raise APIException(code=404, msg="执行记录不存在")

    # Project isolation
    plan_case = db.scalar(
        select(TestPlanCase).where(TestPlanCase.id == exec_row.plan_case_id)
    )
    if not plan_case or plan_case.plan.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此执行记录")

    # Update fields
    if "status" in body:
        valid_statuses = {"pass", "fail", "skip", "block", "pending"}
        if body["status"] not in valid_statuses:
            raise APIException(code=400, msg=f"无效状态值，允许: {', '.join(sorted(valid_statuses))}")
        exec_row.status = body["status"]
        # Also update plan_case last_status
        plan_case.last_status = body["status"]
        plan_case.last_executed_at = datetime.now(timezone.utc)

    if "actual_result" in body:
        exec_row.actual_result = body["actual_result"]
    if "trace_id" in body:
        exec_row.trace_id = body["trace_id"]
    if "notes" in body:
        exec_row.notes = body["notes"]

    exec_row.executed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(exec_row)

    # Notify on terminal status
    if body.get("status") in ("pass", "fail"):
        try:
            from app.services.notify_service import notify_sync
            notify_sync(db, token.project_id, "plan_done", {
                "plan_name": getattr(plan_case.plan, "name", ""),
                "result_summary": f"执行 #{run_id}: {body['status']}",
                "link": "",
            })
        except Exception:
            pass

    return R.ok({
        "run_id": exec_row.id,
        "status": exec_row.status,
        "updated": True,
    })


# ── UI 测试触发 ────────────────────────────────────────

@router.post("/ui-tests/{job_id}/trigger", response_model=R[dict], summary="CI 触发 UI 自动化测试")
def ci_trigger_ui_test(
    job_id: int,
    req: Request,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI (Jenkins/GitHub Actions) 通过 API Token 触发 UI 自动化任务。

    返回 run 记录，可通过轮询 GET /api/v1/open/ui-tests/runs/{run_id} 查询状态。
    """
    from app.models.ui_test import UiTestJob, UiTestRun
    from datetime import datetime, timezone

    job = db.scalar(
        select(UiTestJob).where(
            UiTestJob.id == job_id, UiTestJob.project_id == token.project_id
        )
    )
    if not job:
        raise APIException(code=404, msg="UI 测试任务不存在")

    if job.status == "running":
        raise APIException(code=400, msg="任务正在执行中，请等待完成后再触发")

    # 检查 Playwright
    from app.services.playwright_executor import _check_playwright_installed
    pw_ok, pw_msg = _check_playwright_installed()

    # 解析环境 base_url
    base_url = ""
    if job.environment_id:
        from app.models.environment import Environment
        env = db.get(Environment, job.environment_id)
        base_url = env.base_url if env else ""

    now = datetime.now(timezone.utc)
    job.status = "running" if pw_ok else "fail"
    job.last_result = json.dumps({} if pw_ok else {"error": pw_msg}, ensure_ascii=False)

    run = UiTestRun(
        job_id=job_id,
        status="pending" if pw_ok else "fail",
        base_url=base_url,
        started_at=now,
        result=json.dumps({}, ensure_ascii=False),
    )
    if not pw_ok:
        run.status = "fail"
        run.finished_at = now
        run.error_message = f"Playwright 不可用: {pw_msg}"
        run.result = json.dumps({"error": pw_msg}, ensure_ascii=False)

    db.add(run)

    # Update token last_used
    token.last_used_at = now
    db.commit()
    db.refresh(run)

    # 后台执行 (仅当 Playwright 可用)
    if pw_ok:
        try:
            from app.services.ui_test_service import execute_playwright_async
            # Use a separate thread since open_api doesn't have BackgroundTasks
            import threading
            t = threading.Thread(
                target=execute_playwright_async,
                args=(run.id, job_id, token.project_id),
                daemon=True,
                name=f"ci-ui-run-{run.id}",
            )
            t.start()
        except Exception:
            pass

    return R.ok({
        "triggered": True,
        "job_id": job_id,
        "job_name": job.name,
        "run_id": run.id,
        "run_status": run.status,
        "triggered_by": token.name,
    })


@router.get("/ui-tests/runs/{run_id}", response_model=R[dict], summary="CI 查询 UI 测试运行状态")
def ci_get_ui_run(
    run_id: int,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 查询 UI 测试运行的状态与结果。"""
    from app.models.ui_test import UiTestRun, UiTestJob

    run = db.get(UiTestRun, run_id)
    if not run:
        raise APIException(code=404, msg="运行记录不存在")

    # Project isolation via job
    job = db.get(UiTestJob, run.job_id)
    if not job or job.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此运行记录")

    import json as _json
    result = {}
    try:
        result = _json.loads(run.result) if run.result else {}
    except (_json.JSONDecodeError, TypeError):
        pass

    return R.ok({
        "run_id": run.id,
        "job_id": run.job_id,
        "job_name": job.name,
        "status": run.status,
        "result": result,
        "error_message": run.error_message,
        "base_url": run.base_url,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    })


# ── 质量门禁检查 (CI/CD) ──────────────────────────────

@router.get("/reports/{report_id}/gate/check", summary="CI/CD 质量门禁检查")
def ci_check_report_gate(
    report_id: int,
    token: ApiToken = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """CI/CD pipeline 质量门禁检查（API Token 鉴权）。

    门禁不通过时返回 HTTP 409 Conflict 阻止构建流水线。
    返回: {"blocked": bool, "details": [...], "gate_status": "pass"|"fail"|"warn"}
    """
    from fastapi.responses import JSONResponse

    from app.services.report_service import get_report_gate

    gate = get_report_gate(db, report_id, token.project_id)
    if not gate:
        raise APIException(code=404, msg="报告不存在")

    status = gate.get("gate_status", "unknown")
    details = gate.get("gate_details", [])
    blocked = status == "fail"

    if blocked:
        return JSONResponse(
            status_code=409,
            content={"blocked": True, "details": details, "gate_status": status},
        )
    return {"blocked": False, "details": details, "gate_status": status}
