"""VersionTask API — 版本验收任务唯一事实源（B6）。

端点按「主链路」拆：建任务 / 单任务 / 状态流转 / 关联执行与缺陷 / 旧数据只读兼容映射。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import Page, R
from app.schemas.version_task import (
    DefectLinkIn,
    ExecutionLinkIn,
    PlanItemCreate,
    PlanItemOut,
    PlanItemReview,
    VersionTaskRunOut,
    VersionTaskCreate,
    VersionTaskListItem,
    VersionTaskOut,
    VersionTaskTransition,
    VersionTaskUpdate,
)
from app.services import audit_service, version_task_service

router = APIRouter(prefix="/version-tasks", tags=["版本验收任务"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── 旧数据只读兼容映射（VersionMission -> VersionTask 视图，不双写）──
@router.get("/compat/missions", response_model=R[Page[dict]], summary="旧智能测试任务兼容列表")
def compat_mission_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    items, total = version_task_service.compat_mission_list(
        db, current.project_id or 0, page=page, page_size=page_size
    )
    return R.ok(Page(total=total, page=page, page_size=page_size, items=items))


@router.get("/compat/missions/{mission_id}", response_model=R[dict], summary="旧智能测试任务兼容详情")
def compat_mission_detail(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(version_task_service.compat_mission_view(db, mission_id))


# ── CRUD ──
@router.get("", response_model=R[Page[VersionTaskListItem]], summary="版本验收任务列表")
def list_tasks(
    status: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    rows, total = version_task_service.list_tasks(
        db, current.project_id or 0, status=status, keyword=keyword, page=page, page_size=page_size
    )
    items = [VersionTaskListItem.model_validate(r) for r in rows]
    return R.ok(Page(total=total, page=page, page_size=page_size, items=items))


@router.post("", response_model=R[VersionTaskOut], summary="创建版本验收任务")
def create_task(
    data: VersionTaskCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:create")),
    db: Session = Depends(get_db),
):
    task = version_task_service.create_task(
        db,
        project_id=current.project_id or 0,
        title=data.title,
        version=data.version,
        source=data.source,
        source_mission_id=data.source_mission_id,
        source_bundle_id=data.source_bundle_id,
        requirement_doc_id=data.requirement_doc_id,
        release_bundle_id=data.release_bundle_id,
        environment_id=data.environment_id,
        scope=data.scope,
        created_by=current.user.id if current.user else 0,
        qa_owner_id=data.qa_owner_id,
    )
    _audit(req, current, db, "version_task:create", f"{task.id}", task.title)
    return R.ok(VersionTaskOut.model_validate(task))


@router.get("/{task_id}", response_model=R[VersionTaskOut], summary="版本验收任务详情")
def get_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    task = version_task_service.get_task(db, task_id)
    return R.ok(VersionTaskOut.model_validate(task))


@router.patch("/{task_id}", response_model=R[VersionTaskOut], summary="更新版本验收任务")
def update_task(
    task_id: int,
    data: VersionTaskUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    task = version_task_service.update_task(db, task_id, data.model_dump(exclude_unset=True))
    _audit(req, current, db, "version_task:update", f"{task_id}")
    return R.ok(VersionTaskOut.model_validate(task))


@router.post("/{task_id}/transition", response_model=R[VersionTaskOut], summary="版本任务状态流转")
def transition(
    task_id: int,
    data: VersionTaskTransition,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    task = version_task_service.transition_task(
        db, task_id, data.status, verdict=data.verdict, summary=data.summary
    )
    _audit(req, current, db, "version_task:transition", f"{task_id}", f"{task.status}")
    return R.ok(VersionTaskOut.model_validate(task))


@router.post("/{task_id}/executions", response_model=R[dict], summary="关联一条执行记录")
def add_execution(
    task_id: int,
    data: ExecutionLinkIn,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    link = version_task_service.add_execution(db, task_id, data.execution_type, data.execution_id, data.ref)
    return R.ok({"id": link.id, "task_id": link.task_id})


@router.post("/{task_id}/defects", response_model=R[dict], summary="关联一个缺陷")
def add_defect(
    task_id: int,
    data: DefectLinkIn,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    link = version_task_service.add_defect(db, task_id, data.defect_id)
    return R.ok({"id": link.id, "task_id": link.task_id})


# ── B7: AI 验收方案生成 + 审核面板 ──
@router.get("/{task_id}/plan", response_model=R[list[PlanItemOut]], summary="版本验收方案条目列表")
def get_plan(
    task_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    items = version_task_service.get_plan(db, task_id)
    return R.ok([PlanItemOut.model_validate(i) for i in items])


@router.post("/{task_id}/plan/generate", response_model=R[list[PlanItemOut]], summary="生成/写入 AI 验收方案条目")
def generate_plan(
    task_id: int,
    data: list[PlanItemCreate],
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:generate")),
    db: Session = Depends(get_db),
):
    items = version_task_service.generate_plan(db, task_id, [i.model_dump() for i in data])
    _audit(req, current, db, "version_task:plan_generate", f"{task_id}", f"{len(items)}")
    return R.ok([PlanItemOut.model_validate(i) for i in items])


@router.post("/{task_id}/plan/{item_id}/review", response_model=R[PlanItemOut], summary="审核方案条目")
def review_plan_item(
    task_id: int,
    item_id: int,
    data: PlanItemReview,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    item = version_task_service.review_plan_item(
        db, item_id, action=data.action, patch=data.model_dump(exclude_unset=True)
    )
    _audit(req, current, db, "version_task:plan_review", f"{task_id}/{item_id}", f"{data.action}")
    return R.ok(PlanItemOut.model_validate(item))


# ── B8: 一键运行 + 进度 + 证据回放 + 失败分类→缺陷草稿 ──
@router.post("/{task_id}/run", response_model=R[VersionTaskRunOut], summary="一键运行版本任务")
def start_run(
    task_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("mission:generate")),
    db: Session = Depends(get_db),
):
    run = version_task_service.start_run(db, task_id)
    _audit(req, current, db, "version_task:run", f"{task_id}", f"run:{run.id}")
    return R.ok(VersionTaskRunOut.model_validate(run))


@router.get("/{task_id}/runs", response_model=R[list[VersionTaskRunOut]], summary="版本任务运行记录列表")
def list_runs(
    task_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    runs = version_task_service.list_runs(db, task_id)
    return R.ok([VersionTaskRunOut.model_validate(r) for r in runs])


@router.get("/{task_id}/runs/{run_id}", response_model=R[VersionTaskRunOut], summary="运行记录详情（含证据回放）")
def get_run(
    task_id: int,
    run_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    run = version_task_service.get_run(db, run_id)
    if run.task_id != task_id:
        raise not_found("运行记录不属于该任务")
    return R.ok(VersionTaskRunOut.model_validate(run))


@router.post("/{task_id}/runs/{run_id}/defect/{failure_index}", response_model=R[dict], summary="失败条目转缺陷草稿")
def create_defect_draft(
    task_id: int,
    run_id: int,
    failure_index: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("defect:create")),
    db: Session = Depends(get_db),
):
    defect = version_task_service.create_defect_draft(
        db, run_id, failure_index, creator_id=current.user.id if current.user else 0
    )
    _audit(req, current, db, "version_task:defect_draft", f"{task_id}/{run_id}", f"defect:{defect.id}")
    return R.ok({"defect_id": defect.id, "status": defect.status})
