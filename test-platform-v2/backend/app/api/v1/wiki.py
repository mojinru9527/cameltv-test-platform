"""LLM-Wiki 知识库 API 路由 —— /api/v1/wiki/*

VNext-1..3：蓝湖导入 → Raw Source → Wiki 编译 → RAG vs Wiki 差异对比 → 待审产物。
所有能力受配置开关门禁（默认 OFF，raise APIException(503)）与 RBAC（wiki:*）保护。

已落地：切片 0 GET /config；切片 1 蓝湖导入 + Raw Source 列表/详情。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.models.wiki import WikiDiffItem, WikiDiffTask, WikiIngestJob
from app.schemas.common import Page, R
from app.schemas.wiki import (
    LanhuImportRequest,
    LanhuImportResult,
    WikiConfigOut,
    WikiDiffCreateArtifactRequest,
    WikiDiffCreateArtifactResult,
    WikiDiffCreateRequest,
    WikiDiffItemOut,
    WikiDiffItemReviewRequest,
    WikiDiffTaskBrief,
    WikiDiffTaskOut,
    WikiIngestJobCreate,
    WikiIngestJobOut,
    WikiLinkOut,
    WikiPageBrief,
    WikiPageOut,
    WikiRawSourceBrief,
    WikiRawSourceOut,
    WikiReviewRequest,
)
from app.services import audit_service
from app.services.wiki import (
    compare_service, import_service, ingest_service, page_service, raw_source_service,
)

router = APIRouter(prefix="/wiki", tags=["Wiki 知识库"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _require_wiki_enabled() -> None:
    if not settings.wiki_enabled:
        raise APIException(code=503, msg="Wiki 知识库未启用（wiki_enabled=False）", http_status=503)


def _require_wiki_diff_enabled() -> None:
    if not settings.wiki_diff_enabled:
        raise APIException(code=503, msg="知识差异对比未启用（wiki_diff_enabled=False）", http_status=503)


# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════

@router.get("/config", response_model=R[WikiConfigOut], summary="Wiki 能力开关")
def get_wiki_config(
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    return R.ok(WikiConfigOut(
        wiki_enabled=settings.wiki_enabled,
        wiki_auto_ingest_enabled=settings.wiki_auto_ingest_enabled,
        wiki_diff_enabled=settings.wiki_diff_enabled,
        wiki_auto_create_artifact=settings.wiki_auto_create_artifact,
        lanhu_mcp_enabled=settings.lanhu_mcp_enabled,
    ))


# ═══════════════════════════════════════════════════════
# 蓝湖导入 / Raw Source（VNext-1）
# ═══════════════════════════════════════════════════════

@router.post("/import/lanhu", response_model=R[LanhuImportResult], summary="导入蓝湖需求为 Raw Source")
async def import_lanhu(
    body: LanhuImportRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_wiki_enabled()
    result = await import_service.import_lanhu(
        db, project_id=current.project_id or 0,
        operator_id=current.user.id if current.user else 0,
        req=body, background_tasks=background_tasks,
    )
    _audit(req, current, db, action="wiki.import.lanhu", target=body.url,
           detail=f"status={result.extraction_status} raw={result.raw_source_id}")
    db.commit()
    return R.ok(result)


@router.get("/raw-sources", response_model=R[Page[WikiRawSourceBrief]], summary="Raw Source 列表")
def list_raw_sources(
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    rows, total = raw_source_service.list_raw_sources(
        db, pid, source_type=source_type, status=status, keyword=keyword,
        page=page, page_size=page_size,
    )
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiRawSourceBrief.model_validate(r) for r in rows]))


@router.get("/raw-sources/{raw_source_id}", response_model=R[WikiRawSourceOut], summary="Raw Source 详情")
def get_raw_source(
    raw_source_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    row = raw_source_service.get_raw_source(db, raw_source_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="Raw Source 不存在")
    return R.ok(WikiRawSourceOut.model_validate(row))


# ═══════════════════════════════════════════════════════
# Wiki 编译任务（VNext-2）
# ═══════════════════════════════════════════════════════

@router.post("/ingest-jobs", response_model=R[WikiIngestJobOut], summary="创建并触发 Wiki 编译任务")
def create_ingest_job(
    body: WikiIngestJobCreate,
    background_tasks: BackgroundTasks,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_wiki_enabled()
    pid = current.project_id or 0
    raw = raw_source_service.get_raw_source(db, body.raw_source_id, pid)
    if not raw:
        return R(code=404, msg="Raw Source 不存在")
    job = WikiIngestJob(project_id=pid, raw_source_id=raw.id, status="pending",
                        stage="analysis", operator_id=current.user.id if current.user else 0)
    db.add(job)
    db.flush()
    _audit(req, current, db, action="wiki.ingest.create", target=f"raw#{raw.id}", detail=f"job#{job.id}")
    db.commit()
    background_tasks.add_task(ingest_service.run_wiki_ingest_in_new_session, pid, job.id)
    return R.ok(WikiIngestJobOut.model_validate(job))


@router.get("/ingest-jobs/{job_id}", response_model=R[WikiIngestJobOut], summary="Wiki 编译任务详情")
def get_ingest_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    job = db.get(WikiIngestJob, job_id)
    if not job or job.project_id != (current.project_id or 0):
        return R(code=404, msg="任务不存在")
    return R.ok(WikiIngestJobOut.model_validate(job))


@router.post("/ingest-jobs/{job_id}/retry", response_model=R[WikiIngestJobOut], summary="重试 Wiki 编译任务")
def retry_ingest_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_wiki_enabled()
    job = db.get(WikiIngestJob, job_id)
    if not job or job.project_id != (current.project_id or 0):
        return R(code=404, msg="任务不存在")
    if job.status == "running":
        return R(code=400, msg="任务运行中，无法重试")
    job.status = "pending"; job.stage = "analysis"; job.error_message = ""
    job.retry_count = (job.retry_count or 0) + 1
    db.commit()
    background_tasks.add_task(ingest_service.run_wiki_ingest_in_new_session, job.project_id, job.id)
    return R.ok(WikiIngestJobOut.model_validate(job))


@router.post("/ingest-jobs/{job_id}/cancel", response_model=R[WikiIngestJobOut], summary="取消 Wiki 编译任务")
def cancel_ingest_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    job = db.get(WikiIngestJob, job_id)
    if not job or job.project_id != (current.project_id or 0):
        return R(code=404, msg="任务不存在")
    if job.status in ("success", "failed"):
        return R(code=400, msg="任务已结束，无法取消")
    job.status = "cancelled"
    db.commit()
    return R.ok(WikiIngestJobOut.model_validate(job))


# ═══════════════════════════════════════════════════════
# Wiki 页面（VNext-2）
# ═══════════════════════════════════════════════════════

@router.get("/pages", response_model=R[Page[WikiPageBrief]], summary="Wiki 页面列表")
def list_pages(
    page_type: str | None = Query(None),
    review_status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    rows, total = page_service.list_pages(
        db, current.project_id or 0, page_type=page_type, review_status=review_status,
        keyword=keyword, page=page, page_size=page_size)
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiPageBrief.model_validate(r) for r in rows]))


@router.get("/search", response_model=R[Page[WikiPageBrief]], summary="Wiki 页面关键词检索")
def search_pages(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    rows, total = page_service.list_pages(
        db, current.project_id or 0, keyword=keyword, page=page, page_size=page_size)
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiPageBrief.model_validate(r) for r in rows]))


@router.get("/pages/{page_id}", response_model=R[WikiPageOut], summary="Wiki 页面详情")
def get_page(
    page_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    row = page_service.get_page(db, page_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="页面不存在")
    return R.ok(WikiPageOut.model_validate(row))


@router.get("/pages/{page_id}/links", response_model=R[list[WikiLinkOut]], summary="Wiki 页面链接")
def get_page_links(
    page_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    links = page_service.get_page_links(db, page_id, current.project_id or 0)
    return R.ok([WikiLinkOut.model_validate(x) for x in links])


@router.post("/pages/{page_id}/approve", response_model=R[WikiPageOut], summary="通过 Wiki 页面")
def approve_page(
    page_id: int,
    body: WikiReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    row = page_service.review_page(db, page_id, current.project_id or 0, approve=True)
    if not row:
        return R(code=404, msg="页面不存在")
    _audit(req, current, db, action="wiki.page.approve", target=f"page#{page_id}", detail=body.comment)
    db.commit()
    return R.ok(WikiPageOut.model_validate(row))


@router.post("/pages/{page_id}/reject", response_model=R[WikiPageOut], summary="驳回 Wiki 页面")
def reject_page(
    page_id: int,
    body: WikiReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    row = page_service.review_page(db, page_id, current.project_id or 0, approve=False)
    if not row:
        return R(code=404, msg="页面不存在")
    _audit(req, current, db, action="wiki.page.reject", target=f"page#{page_id}", detail=body.comment)
    db.commit()
    return R.ok(WikiPageOut.model_validate(row))


# ═══════════════════════════════════════════════════════
# 知识库差异对比（VNext-3）
# ═══════════════════════════════════════════════════════

@router.post("/diff/tasks", response_model=R[WikiDiffTaskOut], summary="发起知识库差异对比")
def create_diff_task(
    body: WikiDiffCreateRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:diff")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    pid = current.project_id or 0
    task = WikiDiffTask(
        project_id=pid, title=body.title or f"{body.query} 差异对比",
        compare_type=body.compare_type, status="pending",
        left_ref_json=json.dumps({"kb_type": body.left_kb_type, "query": body.query}, ensure_ascii=False),
        right_ref_json=json.dumps({"kb_type": body.right_kb_type, "query": body.query}, ensure_ascii=False),
        created_by=current.user.id if current.user else 0,
    )
    db.add(task)
    db.flush()
    _audit(req, current, db, action="wiki.diff.create", target=body.query, detail=f"task#{task.id}")
    db.commit()
    background_tasks.add_task(compare_service.run_diff_in_new_session, pid, task.id)
    return R.ok(WikiDiffTaskOut.model_validate(task))


@router.get("/diff/tasks", response_model=R[Page[WikiDiffTaskBrief]], summary="差异任务列表")
def list_diff_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    q = db.query(WikiDiffTask).filter(WikiDiffTask.project_id == pid)
    if status:
        q = q.filter(WikiDiffTask.status == status)
    total = q.count()
    rows = q.order_by(WikiDiffTask.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiDiffTaskBrief.model_validate(r) for r in rows]))


@router.get("/diff/tasks/{task_id}", response_model=R[WikiDiffTaskOut], summary="差异任务详情（含差异项）")
def get_diff_task(
    task_id: int,
    dimension: str | None = Query(None),
    diff_type: str | None = Query(None),
    severity: str | None = Query(None),
    review_status: str | None = Query(None),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    task = db.get(WikiDiffTask, task_id)
    if not task or task.project_id != pid:
        return R(code=404, msg="任务不存在")
    q = db.query(WikiDiffItem).filter(WikiDiffItem.task_id == task_id)
    if dimension:
        q = q.filter(WikiDiffItem.dimension == dimension)
    if diff_type:
        q = q.filter(WikiDiffItem.diff_type == diff_type)
    if severity:
        q = q.filter(WikiDiffItem.severity == severity)
    if review_status:
        q = q.filter(WikiDiffItem.review_status == review_status)
    items = q.order_by(WikiDiffItem.severity, WikiDiffItem.id).all()
    out = WikiDiffTaskOut.model_validate(task)
    out.items = [WikiDiffItemOut.model_validate(x) for x in items]
    return R.ok(out)


def _get_diff_item(db: Session, item_id: int, pid: int) -> WikiDiffItem | None:
    item = db.get(WikiDiffItem, item_id)
    if not item or item.project_id != pid:
        return None
    return item


@router.post("/diff/items/{item_id}/accept", response_model=R[WikiDiffItemOut], summary="采纳差异项")
def accept_diff_item(
    item_id: int,
    body: WikiDiffItemReviewRequest,
    current: CurrentUser = Depends(require_permission("wiki:diff")),
    db: Session = Depends(get_db),
):
    item = _get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "accepted"
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/reject", response_model=R[WikiDiffItemOut], summary="忽略差异项")
def reject_diff_item(
    item_id: int,
    body: WikiDiffItemReviewRequest,
    current: CurrentUser = Depends(require_permission("wiki:diff")),
    db: Session = Depends(get_db),
):
    item = _get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "rejected"
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/create-artifact",
             response_model=R[WikiDiffCreateArtifactResult], summary="差异项转待审 AI 产物")
def create_artifact(
    item_id: int,
    body: WikiDiffCreateArtifactRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:diff")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    pid = current.project_id or 0
    item = _get_diff_item(db, item_id, pid)
    if not item:
        return R(code=404, msg="差异项不存在")
    if item.resolved_artifact_id:
        return R(code=400, msg="该差异项已生成产物")
    art = compare_service.create_artifact_from_item(
        db, pid, item, artifact_type=body.artifact_type,
        operator_id=current.user.id if current.user else 0)
    _audit(req, current, db, action="wiki.diff.create_artifact", target=f"item#{item_id}",
           detail=f"artifact#{art.id} type={art.artifact_type}")
    db.commit()
    return R.ok(WikiDiffCreateArtifactResult(artifact_id=art.id, artifact_type=art.artifact_type))
