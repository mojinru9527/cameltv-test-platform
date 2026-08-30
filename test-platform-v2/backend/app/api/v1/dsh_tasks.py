"""DSH 任务执行模块 API —— /api/v1/dsh-tasks/*（Batch 172）。

提交自然语言任务，平台通过 DeepSeek Harness 后台执行，列表/详情可追溯。
权限复用 agent:view（读）/ agent:run（写）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.dsh import DshHealthOut, DshTaskCancelResponse, DshTaskCreate, DshTaskOut
from app.services.dsh import dsh_attachment_service, dsh_task_service
from app.services.dsh.dsh_runner import runtime_available

router = APIRouter(prefix="/dsh-tasks", tags=["DSH 任务"])


@router.get("/health", response_model=R[DshHealthOut], summary="DSH 运行可用性")
def dsh_health(
    current: CurrentUser = Depends(require_permission("agent:view")),
):
    ok, reason = runtime_available()
    return R.ok(DshHealthOut(available=ok, reason=reason))


@router.get("/model-pool", response_model=R[dict], summary="DSH 可用模型池（阶段 3）")
def dsh_model_pool(
    current: CurrentUser = Depends(require_permission("agent:view")),
):
    """可用模型清单（模型池配置；未配置池时返回默认模型）。设置页/新建任务下拉用。"""
    pool = settings.dsh_model_pool_list
    return R.ok({
        "models": pool,
        "default_model": settings.dsh_model or settings.ai_model,
        "pool_configured": bool(pool),
    })


@router.post("/upload-image", response_model=R[dict], summary="上传 DSH 任务图片附件")
async def upload_task_image(
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("agent:run")),
):
    """图片附件上传（PNG/JPEG/WebP/GIF，≤10MB）。返回 file_id，提交任务时
    经 params.image_files 引用；执行时自动落任务工作区供模型 read_image 查看。"""
    data = await file.read()
    try:
        result = dsh_attachment_service.save_upload(
            data, file.filename or "", file.content_type or ""
        )
    except ValueError as exc:
        return R(code=400, msg=str(exc))
    return R.ok(result)


@router.post("", response_model=R[DshTaskOut], summary="提交 DSH 任务")
def create_dsh_task(
    body: DshTaskCreate,
    current: CurrentUser = Depends(require_permission("agent:run")),
    db: Session = Depends(get_db),
):
    ok, reason = runtime_available()
    if not ok:
        return R(code=503, msg=f"DSH 不可用: {reason}")
    # DSH 测试 Agent 框架（阶段 3）：模型池准入——配置了池则只允许池内模型
    model = (body.params or {}).get("model")
    if model and not settings.dsh_model_allowed(model):
        return R(code=400, msg=f"模型不在可用模型池内: {model}（可选: {', '.join(settings.dsh_model_pool_list) or '未配置池'}）")
    row = dsh_task_service.submit_task(
        db,
        project_id=current.project_id or 0,
        task=body.task,
        params=body.params,
        mode=body.mode,
        operator_id=current.user.id,
    )
    return R.ok(DshTaskOut.model_validate(row))


@router.get("", response_model=R[Page[DshTaskOut]], summary="DSH 任务列表")
def list_dsh_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("agent:view")),
    db: Session = Depends(get_db),
):
    rows, total = dsh_task_service.list_tasks(
        db,
        current.project_id or 0,
        status=status,
        page=page,
        page_size=page_size,
    )
    return R.ok(Page(
        total=total,
        page=page,
        page_size=page_size,
        items=[DshTaskOut.model_validate(r) for r in rows],
    ))


@router.get("/{task_id}", response_model=R[DshTaskOut], summary="DSH 任务详情")
def get_dsh_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("agent:view")),
    db: Session = Depends(get_db),
):
    row = dsh_task_service.get_task(db, task_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="DSH 任务不存在")
    return R.ok(DshTaskOut.model_validate(row))


@router.get("/{task_id}/artifacts", response_model=R[list], summary="DSH 任务产物（审核台条目）")
def dsh_task_artifacts(
    task_id: int,
    current: CurrentUser = Depends(require_permission("agent:view")),
    db: Session = Depends(get_db),
):
    """B2 产物闭环：任务落库的 AI 产物回链（类型/标题/审核状态/导入结果）。"""
    row = dsh_task_service.get_task(db, task_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="DSH 任务不存在")
    from app.services.dsh.dsh_artifact_service import list_task_artifacts

    rows = list_task_artifacts(db, task_id, current.project_id or 0)
    return R.ok([
        {
            "id": a.id,
            "artifact_type": a.artifact_type,
            "title": a.title,
            "review_status": a.review_status,
            "imported_ref_type": a.imported_ref_type,
            "imported_ref_id": a.imported_ref_id,
        }
        for a in rows
    ])


@router.post("/{task_id}/cancel", response_model=R[DshTaskCancelResponse], summary="取消 DSH 任务")
def cancel_dsh_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("agent:run")),
    db: Session = Depends(get_db),
):
    row = dsh_task_service.cancel_task(db, task_id, current.project_id or 0)
    if row is None:
        return R(code=404, msg="任务不存在或不可取消（仅 pending 可取消）")
    return R.ok(DshTaskCancelResponse(id=row.id, status=row.status, message="任务已取消"))
