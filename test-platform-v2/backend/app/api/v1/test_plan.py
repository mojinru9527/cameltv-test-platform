"""测试计划 API 路由 — /api/v1/test-plans/*"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.test_plan import (
    ExecutionCreate,
    ExecutionOut,
    PlanCaseAdd,
    PlanCaseOut,
    PlanCaseSort,
    PlanCreate,
    PlanDetailOut,
    PlanOut,
    PlanStats,
    PlanUpdate,
)
from app.services import audit_service, test_plan_service

import logging
logger = logging.getLogger("test_plan")


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


router = APIRouter(prefix="/test-plans", tags=["测试计划"])


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


# ═══════════════════════════════════════════════════════════
# 计划 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("", response_model=R[Page[PlanOut]])
def list_plans(
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    current: CurrentUser = Depends(require_permission("testplan:list")),
    db: Session = Depends(get_db),
):
    items, total = test_plan_service.list_plans(
        db,
        project_id=current.project_id or 0,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok(Page(total=total, page=page, page_size=page_size, items=[PlanOut(**it) for it in items]))


@router.post("", response_model=R[PlanOut])
def create_plan(
    body: PlanCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:create")),
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    row = test_plan_service.create_plan(db, data, creator_id=current.user.id, project_id=current.project_id or 0)
    _audit(req, current, db, "plan:create", f"#{row['id']} {row['name']}")
    return R.ok(PlanOut(**row))


@router.get("/{plan_id}", response_model=R[PlanDetailOut])
def get_plan(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.get_plan(db, plan_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="计划不存在")
    detail = PlanDetailOut(
        **{k: v for k, v in row.items() if k not in ("cases", "stats")},
        cases=[PlanCaseOut(**c) for c in row.get("cases", [])],
        stats=PlanStats(**row.get("stats", {})),
    )
    return R.ok(detail)


@router.put("/{plan_id}", response_model=R[PlanOut])
def update_plan(
    plan_id: int,
    body: PlanUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:update")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.update_plan(db, plan_id, body.model_dump(exclude_none=True), project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="计划不存在")
    _audit(req, current, db, "plan:update", f"#{row['id']} {row['name']}")
    return R.ok(PlanOut(**row))


@router.delete("/{plan_id}", response_model=R[dict])
def delete_plan(
    plan_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:delete")),
    db: Session = Depends(get_db),
):
    ok = test_plan_service.delete_plan(db, plan_id, project_id=current.project_id or 0)
    if not ok:
        return R(code=404, msg="计划不存在或无权操作")
    _audit(req, current, db, "plan:delete", f"#{plan_id}")
    return R.ok({"deleted": plan_id})


# ═══════════════════════════════════════════════════════════
# 用例关联
# ═══════════════════════════════════════════════════════════

@router.post("/{plan_id}/cases", response_model=R[dict])
def add_cases_to_plan(
    plan_id: int,
    body: PlanCaseAdd,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:update")),
    db: Session = Depends(get_db),
):
    added = test_plan_service.add_cases(db, plan_id, body.case_ids, project_id=current.project_id or 0)
    _audit(req, current, db, "plan:add_cases", f"plan #{plan_id}", f"added {added} cases")
    return R.ok({"added": added})


@router.delete("/{plan_id}/cases", response_model=R[dict])
def remove_cases_from_plan(
    plan_id: int,
    body: PlanCaseAdd,               # 复用 case_ids 字段
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:update")),
    db: Session = Depends(get_db),
):
    removed = test_plan_service.remove_cases(db, plan_id, body.case_ids, project_id=current.project_id or 0)
    _audit(req, current, db, "plan:remove_cases", f"plan #{plan_id}", f"removed {removed} cases")
    return R.ok({"removed": removed})


@router.put("/{plan_id}/cases/{pcase_id}/sort", response_model=R[dict])
def update_case_sort(
    plan_id: int,
    pcase_id: int,
    body: PlanCaseSort,
    current: CurrentUser = Depends(require_permission("testplan:update")),
    db: Session = Depends(get_db),
):
    ok = test_plan_service.update_case_sort(db, pcase_id, body.sort_order, project_id=current.project_id or 0)
    if not ok:
        return R(code=404, msg="关联不存在或无权操作")
    return R.ok({"updated": pcase_id})


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

    # P1-4: Background notification via BackgroundTasks (replaces fire-and-forget
    # asyncio.create_task — runs in its own DB session to avoid session-closed errors).
    plan = test_plan_service.get_plan(db, plan_id, current.project_id or 0)
    stats = plan.get("stats", {}) if plan else {}
    background_tasks.add_task(
        _run_notify_in_new_session,
        current.project_id or 0,
        "plan_done",
        {
            "plan_name": plan.get("name", "") if plan else "",
            "result_summary": f"通过 {stats.get('pass_',0)} / 失败 {stats.get('fail',0)} / 跳过 {stats.get('skip',0)}",
            "link": "",
        },
    )

    return R.ok(ExecutionOut(**row))


class AutoExecuteBody(BaseModel):
    environment_id: int | None = None

@router.post("/{plan_id}/auto-execute", response_model=R[dict], summary="自动执行计划中的 API 用例")
def auto_execute_api_cases(
    plan_id: int,
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


@router.get("/{plan_id}/stats", response_model=R[PlanStats])
def get_plan_stats(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.get_plan(db, plan_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="计划不存在")
    return R.ok(PlanStats(**row.get("stats", {})))


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
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:execute")),
    db: Session = Depends(get_db),
):
    """批量执行（更新状态）计划中选中的用例，适用于手动测试场景。"""
    if not body.pcase_ids:
        return R(code=1, msg="pcase_ids 不能为空")
    executed = 0
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
        except Exception as e:
            errors.append(f"pcase #{pcase_id}: {e}")
    _audit(req, current, db, "plan:batch_execute", f"plan #{plan_id}",
           f"executed={executed}, errors={len(errors)}")
    return R.ok({"executed": executed, "errors": errors})


class BatchAssignBody(BaseModel):
    pcase_ids: list[int] = []
    assignee_id: int = 0

@router.put("/{plan_id}/cases/assign", response_model=R[dict], summary="批量指派用例")
def batch_assign_cases(
    plan_id: int,
    body: BatchAssignBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("testplan:update")),
    db: Session = Depends(get_db),
):
    """批量指派计划中的用例给执行人。"""
    if not body.pcase_ids:
        return R(code=1, msg="pcase_ids 不能为空")
    count = test_plan_service.batch_assign(
        db,
        plan_id=plan_id,
        pcase_ids=body.pcase_ids,
        assignee_id=body.assignee_id,
        project_id=current.project_id or 0,
    )
    _audit(req, current, db, "plan:batch_assign", f"plan #{plan_id}",
           f"assigned {count} cases to user #{body.assignee_id}")
    return R.ok({"assigned": count})
