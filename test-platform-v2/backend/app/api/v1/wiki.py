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
from app.models.wiki import WikiDiffItem, WikiDiffTask, WikiIngestJob, ExternalWikiConnection
from app.models.wiki import WikiLintIssue, WikiLintReport
from app.schemas.common import Page, R
from app.schemas.wiki import (
    ExternalWikiConnectionCreate,
    ExternalWikiConnectionOut,
    ExternalWikiConnectionUpdate,
    ExternalWikiGraphRequest,
    ExternalWikiGraphResult,
    ExternalWikiHealthResult,
    ExternalWikiPageRequest,
    ExternalWikiPageResult,
    ExternalWikiSearchRequest,
    ExternalWikiSearchResult,
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
    WikiLintConvertRequest,
    WikiLintIssueOut,
    WikiLintReportBrief,
    WikiLintReportOut,
    WikiLintRunRequest,
)
from app.services import audit_service
from app.services.wiki import (
    compare_service, import_service, ingest_service, lint_service, page_service,
    raw_source_service,
)
from app.services.wiki.external_llm_wiki import (
    graph as ext_graph,
    health_check as ext_health_check,
    read_page as ext_read_page,
    search as ext_search,
)
from app.core.cipher import encrypt_value

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


def _require_external_llm_wiki_enabled() -> None:
    if not settings.external_llm_wiki_enabled:
        raise APIException(code=503, msg="外部 LLM-Wiki 连接器未启用（external_llm_wiki_enabled=False）", http_status=503)


def _enrich_raw_source_meta(raw) -> dict:
    """Parse metadata_json to extract Lanhu-specific doc_id/version_id/page_id."""
    meta = json.loads(raw.metadata_json or "{}")
    return {
        "doc_id": meta.get("doc_id", ""),
        "version_id": meta.get("version_id", ""),
        "page_id": meta.get("page_id", ""),
    }


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
    raise APIException(
        code=409,
        msg="蓝湖链接必须先通过证据包质量门禁，再导入需求/RAG/Wiki",
        http_status=409,
    )


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
                     items=[WikiRawSourceBrief.model_validate(r).model_copy(update=_enrich_raw_source_meta(r)) for r in rows]))


@router.get("/raw-sources/{raw_source_id}", response_model=R[WikiRawSourceOut], summary="Raw Source 详情")
def get_raw_source(
    raw_source_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    row = raw_source_service.get_raw_source(db, raw_source_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="Raw Source 不存在")
    return R.ok(WikiRawSourceOut.model_validate(row).model_copy(update=_enrich_raw_source_meta(row)))


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
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    item = _get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "accepted"
    _audit(req, current, db, action="wiki.diff.accept", target=f"item#{item_id}",
           detail=f"{item.dimension}/{item.diff_type}")
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/reject", response_model=R[WikiDiffItemOut], summary="忽略差异项")
def reject_diff_item(
    item_id: int,
    body: WikiDiffItemReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_diff_enabled()
    item = _get_diff_item(db, item_id, current.project_id or 0)
    if not item:
        return R(code=404, msg="差异项不存在")
    item.review_status = "rejected"
    _audit(req, current, db, action="wiki.diff.reject", target=f"item#{item_id}",
           detail=f"{item.dimension}/{item.diff_type}")
    db.commit()
    return R.ok(WikiDiffItemOut.model_validate(item))


@router.post("/diff/items/{item_id}/create-artifact",
             response_model=R[WikiDiffCreateArtifactResult], summary="差异项转待审 AI 产物")
def create_artifact(
    item_id: int,
    body: WikiDiffCreateArtifactRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
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


# ═══════════════════════════════════════════════════════
# 外部 LLM-Wiki 连接器（VNext-5）
# ═══════════════════════════════════════════════════════

@router.post("/external-connections", response_model=R[ExternalWikiConnectionOut],
             summary="创建外部 Wiki 连接")
def create_external_connection(
    body: ExternalWikiConnectionCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    pid = current.project_id or 0
    token_encrypted = None
    if body.token:
        token_encrypted = encrypt_value(body.token)
    conn = ExternalWikiConnection(
        project_id=pid,
        name=body.name,
        provider=body.provider,
        base_url=body.base_url.rstrip("/"),
        token_encrypted=token_encrypted,
        external_project_id=body.external_project_id,
        enabled=body.enabled,
    )
    db.add(conn)
    db.flush()
    _audit(req, current, db, action="wiki.external.create", target=body.name,
           detail=f"conn#{conn.id} provider={body.provider}")
    db.commit()
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.get("/external-connections", response_model=R[list[ExternalWikiConnectionOut]],
            summary="外部 Wiki 连接列表")
def list_external_connections(
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    pid = current.project_id or 0
    rows = db.query(ExternalWikiConnection).filter(
        ExternalWikiConnection.project_id == pid,
    ).order_by(ExternalWikiConnection.id.desc()).all()
    return R.ok([ExternalWikiConnectionOut.model_validate(r) for r in rows])


@router.get("/external-connections/{conn_id}", response_model=R[ExternalWikiConnectionOut],
            summary="外部 Wiki 连接详情")
def get_external_connection(
    conn_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.put("/external-connections/{conn_id}", response_model=R[ExternalWikiConnectionOut],
            summary="更新外部 Wiki 连接")
def update_external_connection(
    conn_id: int,
    body: ExternalWikiConnectionUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")

    if body.name is not None:
        conn.name = body.name
    if body.provider is not None:
        conn.provider = body.provider
    if body.base_url is not None:
        conn.base_url = body.base_url.rstrip("/")
    if body.token is not None and body.token != "":
        conn.token_encrypted = encrypt_value(body.token)
    if body.external_project_id is not None:
        conn.external_project_id = body.external_project_id
    if body.enabled is not None:
        conn.enabled = body.enabled

    _audit(req, current, db, action="wiki.external.update", target=f"conn#{conn_id}",
           detail=f"name={conn.name}")
    db.commit()
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.delete("/external-connections/{conn_id}", response_model=R[None],
               summary="删除外部 Wiki 连接")
def delete_external_connection(
    conn_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    _audit(req, current, db, action="wiki.external.delete", target=f"conn#{conn_id}",
           detail=f"name={conn.name}")
    db.delete(conn)
    db.commit()
    return R.ok(msg="已删除")


@router.post("/external-connections/{conn_id}/health-check",
             response_model=R[ExternalWikiHealthResult], summary="测试外部 Wiki 连接")
def check_external_connection_health(
    conn_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_health_check(conn)
    _audit(req, current, db, action="wiki.external.health_check", target=f"conn#{conn_id}",
           detail=f"ok={result.get('ok')} provider={conn.provider}")
    return R.ok(ExternalWikiHealthResult(
        ok=result["ok"],
        version=result.get("version", ""),
        message=result.get("message", ""),
    ))


@router.post("/external-connections/{conn_id}/search",
             response_model=R[ExternalWikiSearchResult], summary="搜索外部 Wiki")
def search_external_wiki(
    conn_id: int,
    body: ExternalWikiSearchRequest,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    items = ext_search(conn, body.query, body.limit)
    return R.ok(ExternalWikiSearchResult(items=items, total=len(items)))


@router.get("/external-connections/{conn_id}/files/content",
            response_model=R[ExternalWikiPageResult], summary="读取外部 Wiki 页面")
def read_external_page(
    conn_id: int,
    path: str = Query(..., min_length=1, max_length=500),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_read_page(conn, path)
    return R.ok(ExternalWikiPageResult(
        ok=result["ok"],
        title=result.get("title", ""),
        content_md=result.get("content_md", ""),
        meta=result.get("meta", {}),
        error=result.get("error", ""),
    ))


@router.get("/external-connections/{conn_id}/graph",
            response_model=R[ExternalWikiGraphResult], summary="获取外部 Wiki 图谱")
def get_external_graph(
    conn_id: int,
    node: str = Query(..., min_length=1, max_length=500),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_graph(conn, node)
    return R.ok(ExternalWikiGraphResult(
        ok=result["ok"],
        node=result.get("node", node),
        edges=result.get("edges", []),
        nodes=result.get("nodes", []),
        error=result.get("error", ""),
    ))


def _require_wiki_lint_enabled() -> None:
    if not settings.wiki_lint_enabled:
        raise APIException(code=503, msg="Wiki 健康体检未启用（wiki_lint_enabled=False）", http_status=503)


# ═══════════════════════════════════════════════════════
# Wiki 健康体检 / Lint（VNext-6）
# ═══════════════════════════════════════════════════════

@router.post("/lint", response_model=R[WikiLintReportOut], summary="运行 Wiki 健康体检")
def run_wiki_lint(
    body: WikiLintRunRequest = WikiLintRunRequest(),
    req: Request = None,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_wiki_lint_enabled()
    if (
        body.project_id_override
        and body.project_id_override != (current.project_id or 0)
        and not current.is_super
    ):
        raise APIException(
            code=403,
            msg="Only a super administrator may override project scope",
            http_status=403,
        )
    pid = body.project_id_override if body.project_id_override else (current.project_id or 0)
    if not pid:
        raise APIException(code=400, msg="缺少项目上下文")
    report = lint_service.run_lint(db, project_id=pid,
                                   operator_id=current.user.id if current.user else 0)
    issues = lint_service.get_issues(db, report.id)
    _audit(req, current, db, action="wiki.lint.run", target=f"project#{pid}",
           detail=f"report#{report.id} status={report.status}")
    db.commit()
    out = WikiLintReportOut.model_validate(report)
    out.issues = [WikiLintIssueOut.model_validate(i) for i in issues]
    return R.ok(out)


@router.get("/lint/reports", response_model=R[Page[WikiLintReportBrief]], summary="Lint 报告列表")
def list_lint_reports(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    rows, total = lint_service.list_reports(db, pid, status=status, page=page, page_size=page_size)
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiLintReportBrief.model_validate(r) for r in rows]))


@router.get("/lint/reports/{report_id}", response_model=R[WikiLintReportOut], summary="Lint 报告详情（含问题列表）")
def get_lint_report(
    report_id: int,
    rule: str | None = Query(None),
    severity: str | None = Query(None),
    review_status: str | None = Query(None),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    report = lint_service.get_report(db, report_id, pid)
    if not report:
        return R(code=404, msg="报告不存在")
    issues = lint_service.get_issues(db, report_id, rule=rule, severity=severity, review_status=review_status)
    out = WikiLintReportOut.model_validate(report)
    out.issues = [WikiLintIssueOut.model_validate(i) for i in issues]
    return R.ok(out)


@router.post("/lint/reports/{report_id}/convert", response_model=R[dict], summary="Lint 问题转待审 AI 产物")
def convert_lint_issues(
    report_id: int,
    body: WikiLintConvertRequest = WikiLintConvertRequest(),
    req: Request = None,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_lint_enabled()
    pid = current.project_id or 0
    report = lint_service.get_report(db, report_id, pid)
    if not report:
        return R(code=404, msg="报告不存在")
    artifacts = lint_service.convert_issues_to_artifacts(
        db, report,
        issue_ids=body.issue_ids if body.issue_ids else None,
        artifact_type=body.artifact_type,
        operator_id=current.user.id if current.user else 0,
    )
    _audit(req, current, db, action="wiki.lint.convert", target=f"report#{report_id}",
           detail=f"converted {len(artifacts)} issues")
    db.commit()
    return R.ok({"converted": len(artifacts), "artifact_ids": [a.id for a in artifacts]})


def _get_external_connection(db: Session, conn_id: int, project_id: int) -> ExternalWikiConnection | None:
    conn = db.get(ExternalWikiConnection, conn_id)
    if not conn or conn.project_id != project_id:
        return None
    return conn
