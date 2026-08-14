"""测试计划 API 路由（执行/triage/缺陷草稿） — /api/v1/test-plans/*

Batch 181（FIX-173-P2-10）路由拆分：原 test_plan.py 拆分为
test_plan_crud.py / test_plan_execution.py（本文件）。
端点函数体逐字移动，仅调整 import。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.test_plan import (
    ExecutionCreate,
    ExecutionOut,
)
from app.services import audit_service, test_plan_service, triage_service

logger = logging.getLogger("test_plan")

router = APIRouter(prefix="/test-plans", tags=["测试计划-执行"])


def _run_notify_in_new_session(project_id: int, event: str, data: dict) -> None:
    """P1-4: 在独立 DB session 中发送通知（供 BackgroundTasks 调用）。

    必须使用独立的 SessionLocal()，因为 BackgroundTasks 在响应返回后执行，
    原请求的 db session 可能已关闭。
    """
    from app.core.db import SessionLocal
    from app.services.notify_service import notify_sync

    db = SessionLocal()
    try:
        notify_sync(db, project_id, event, data)
    except Exception:
        logger.exception("Background notification failed: event=%s project=%s", event, project_id)
    finally:
        db.close()


def _run_failure_auto_chain_in_new_session(plan_id: int, project_id: int, creator_id: int) -> None:
    """C147-6（Batch 155）：失败自动转缺陷/报告/通知，独立 session 后台执行。"""
    from app.core.db import SessionLocal
    from app.services.test_plan_service import run_failure_auto_chain

    db = SessionLocal()
    try:
        run_failure_auto_chain(db, plan_id, project_id=project_id, creator_id=creator_id)
    except Exception:
        logger.exception("Failure auto chain failed: plan=%s", plan_id)
    finally:
        db.close()


def _queue_failure_auto_chain_if_enabled(
    background_tasks: BackgroundTasks,
    db: Session,
    *,
    plan_id: int,
    project_id: int,
    creator_id: int,
    failed_count: int,
) -> None:
    """Batch 161：计划失败且 auto_defect_on_fail 开启时，后台触发 失败→缺陷/报告/通知 链路。

    execute-all / auto-execute / batch-execute 三个写路径统一走此入口，避免漏触发。
    """
    if failed_count <= 0:
        return
    _plan = test_plan_service.get_plan(db, plan_id, project_id)
    if _plan and _plan.get("auto_defect_on_fail"):
        background_tasks.add_task(
            _run_failure_auto_chain_in_new_session,
            plan_id,
            project_id,
            creator_id,
        )


def _queue_plan_done_if_complete(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    project_id: int,
    plan_id: int,
) -> None:
    """Notify only when the whole plan has no pending cases."""
    plan = test_plan_service.get_plan(db, plan_id, project_id)
    stats = plan.get("stats", {}) if plan else {}
    if not plan or not stats.get("total") or stats.get("pending", 0) > 0:
        return
    background_tasks.add_task(
        _run_notify_in_new_session,
        project_id,
        "plan_done",
        {
            "plan_name": plan.get("name", ""),
            "result_summary": (
                f"通过 {stats.get('pass_', 0)} / 失败 {stats.get('fail', 0)} / "
                f"跳过 {stats.get('skip', 0)}"
            ),
            "link": "",
        },
    )


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    audit_service.write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username,
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )
    # Most plan services commit their business mutation before returning.  The
    # audit insert therefore starts a new transaction and must be committed
    # explicitly; get_db() only closes the session and would roll it back.
    db.commit()


# ═══════════════════════════════════════════════════════════
# 执行记录
# ═══════════════════════════════════════════════════════════

@router.post("/{plan_id}/cases/{pcase_id}/execute", response_model=R[ExecutionOut])
def execute_case(
    plan_id: int,
    pcase_id: int,
    body: ExecutionCreate,
    req: Request,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.execute_case(
        db,
        plan_id=plan_id,
        pcase_id=pcase_id,
        executor_id=current.user.id,
        status=body.status,
        actual_result=body.actual_result,
        notes=body.notes,
        project_id=current.project_id or 0,
    )
    if not row:
        return R(code=404, msg="关联不存在或无权操作")
    _audit(req, current, db, "plan:execute", f"plan #{plan_id} case #{pcase_id}", f"status={body.status}")

    _queue_plan_done_if_complete(
        db,
        background_tasks,
        project_id=current.project_id or 0,
        plan_id=plan_id,
    )

    return R.ok(ExecutionOut(**row))


class AutoExecuteBody(BaseModel):
    environment_id: int | None = None


class ExecuteAllBody(BaseModel):
    environment_id: int | None = None
    auto_ui: bool = True  # batch-167: manual P0/P1 自动转 UI 执行
    ui_environment_id: int | None = None  # batch-168 D7: UI 自动化独立执行环境
    async_mode: bool = False  # batch-169 C168-2: true 时后台执行并立即返回


@router.post("/{plan_id}/execute-all", response_model=R[dict], summary="一键批量执行计划全部用例")
def execute_all_cases(
    plan_id: int,
    background_tasks: BackgroundTasks,
    body: ExecuteAllBody | None = None,
    req: Request = None,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    """一键执行计划中全部用例：API 用例自动执行，人工/UI 用例标记为 skip。

    batch-169：async_mode=true 时后台执行并立即返回，避免多 UI 用例超过网关 300s。
    """
    if body and body.async_mode:
        background_tasks.add_task(
            test_plan_service.run_async_execute_all,
            plan_id=plan_id,
            executor_id=current.user.id,
            environment_id=body.environment_id,
            ui_environment_id=body.ui_environment_id,
            auto_ui=body.auto_ui,
            project_id=current.project_id or 0,
        )
        _audit(req, current, db, "plan:execute_all:async", f"plan #{plan_id}",
               f"environment={body.environment_id}, ui_environment={body.ui_environment_id}, auto_ui={body.auto_ui}")
        return R.ok({"async": True, "message": "计划已在后台执行，请稍后刷新执行记录"})

    try:
        result = test_plan_service.execute_all_cases(
            db,
            plan_id=plan_id,
            executor_id=current.user.id,
            environment_id=body.environment_id if body else None,
            auto_ui=(body.auto_ui if body else True),
            ui_environment_id=(body.ui_environment_id if body else None),
            project_id=current.project_id or 0,
        )
    except ValueError as e:
        return R(code=1, msg=str(e))
    except Exception as e:
        return R(code=1, msg=f"批量执行失败: {e}")

    _audit(req, current, db, "plan:execute_all", f"plan #{plan_id}",
           f"total={result['total']}, passed={result['passed']}, failed={result['failed']}, skipped={result['skipped']}")
    _queue_failure_auto_chain_if_enabled(
        background_tasks,
        db,
        plan_id=plan_id,
        project_id=current.project_id or 0,
        creator_id=current.user.id,
        failed_count=result.get("failed", 0),
    )
    _queue_plan_done_if_complete(
        db,
        background_tasks,
        project_id=current.project_id or 0,
        plan_id=plan_id,
    )
    return R.ok(result)


@router.post("/{plan_id}/auto-execute", response_model=R[dict], summary="自动执行计划中的 API 用例")
def auto_execute_api_cases(
    plan_id: int,
    background_tasks: BackgroundTasks,
    body: AutoExecuteBody | None = None,
    req: Request = None,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    """自动执行计划中所有 case_type='api' 的用例，生成执行记录。"""
    try:
        result = test_plan_service.auto_execute_api_cases(
            db,
            plan_id=plan_id,
            executor_id=current.user.id,
            environment_id=body.environment_id if body else None,
            project_id=current.project_id or 0,
        )
    except ValueError as e:
        return R(code=1, msg=str(e))
    except Exception as e:
        return R(code=1, msg=f"批量执行失败: {e}")

    _audit(req, current, db, "plan:auto_execute", f"plan #{plan_id}",
           f"executed={result['executed']}, passed={result['passed']}, failed={result['failed']}")
    _queue_failure_auto_chain_if_enabled(
        background_tasks,
        db,
        plan_id=plan_id,
        project_id=current.project_id or 0,
        creator_id=current.user.id,
        failed_count=result.get("failed", 0),
    )
    _queue_plan_done_if_complete(
        db,
        background_tasks,
        project_id=current.project_id or 0,
        plan_id=plan_id,
    )
    return R.ok(result)


@router.get("/{plan_id}/executions", response_model=R[Page[ExecutionOut]])
def list_executions(
    plan_id: int,
    pcase_id: int = 0,
    page: int = 1,
    page_size: int = 50,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    items, total = test_plan_service.get_executions(
        db, plan_id,
        pcase_id=pcase_id,
        page=page, page_size=page_size,
        project_id=current.project_id or 0,
    )
    return R.ok(Page(total=total, page=page, page_size=page_size, items=[ExecutionOut(**it) for it in items]))


@router.post("/{plan_id}/triage", response_model=R[dict], summary="分析计划中的失败执行")
def triage_plan_failures(
    plan_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    result = triage_service.triage_failed_cases(
        db,
        plan_id,
        project_id=current.project_id or 0,
    )
    if result.get("error"):
        return R(code=404, msg=result["error"])
    _audit(
        req,
        current,
        db,
        "plan:triage",
        f"plan #{plan_id}",
        f"failures={result['total_failures']}, method={result['analysis_method']}",
    )
    return R.ok(result)


@router.post(
    "/{plan_id}/triage/{execution_id}/draft-defect",
    response_model=R[dict],
    summary="从失败执行生成缺陷草稿",
)
def draft_defect_from_failure(
    plan_id: int,
    execution_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("defect:create")),
    db: Session = Depends(get_db),
):
    result = triage_service.triage_failed_cases(
        db,
        plan_id,
        project_id=current.project_id or 0,
        use_llm=False,
    )
    failure = next(
        (item for item in result.get("classified", []) if item["execution_id"] == execution_id),
        None,
    )
    if failure is None:
        return R(code=404, msg="失败执行记录不存在或不属于当前计划")

    draft = triage_service.generate_defect_draft(failure)
    _audit(
        req,
        current,
        db,
        "plan:triage:draft_defect",
        f"plan #{plan_id} execution #{execution_id}",
    )
    return R.ok(draft)


# ═══════════════════════════════════════════════════════
# 批量操作
# ═══════════════════════════════════════════════════════

class BatchExecuteBody(BaseModel):
    pcase_ids: list[int] = []
    status: str = "pass"  # pass/fail/skip/block
    actual_result: str = ""
    notes: str = ""


@router.post("/{plan_id}/batch-execute", response_model=R[dict], summary="批量执行计划中的用例")
def batch_execute_cases(
    plan_id: int,
    body: BatchExecuteBody,
    background_tasks: BackgroundTasks,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    """批量执行（更新状态）计划中选中的用例，适用于手动测试场景。

    Batch 161：手动标记失败的用例同样进入 失败→缺陷/报告/通知 自动链路
    （前提：计划开启 auto_defect_on_fail）。
    """
    if not body.pcase_ids:
        return R(code=1, msg="pcase_ids 不能为空")
    executed = 0
    failed = 0
    errors: list[str] = []
    for pcase_id in body.pcase_ids:
        try:
            test_plan_service.execute_case(
                db,
                plan_id=plan_id,
                pcase_id=pcase_id,
                executor_id=current.user.id,
                status=body.status,
                actual_result=body.actual_result,
                notes=body.notes,
                project_id=current.project_id or 0,
            )
            executed += 1
            if body.status == "fail":
                failed += 1
        except Exception as e:
            errors.append(f"pcase #{pcase_id}: {e}")
    _queue_failure_auto_chain_if_enabled(
        background_tasks,
        db,
        plan_id=plan_id,
        project_id=current.project_id or 0,
        creator_id=current.user.id,
        failed_count=failed,
    )
    _audit(req, current, db, "plan:batch_execute", f"plan #{plan_id}",
           f"executed={executed}, failed={failed}, errors={len(errors)}")
    return R.ok({"executed": executed, "failed": failed, "errors": errors})
