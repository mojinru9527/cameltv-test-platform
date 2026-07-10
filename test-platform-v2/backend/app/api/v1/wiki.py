"""LLM-Wiki 知识库 API 路由 —— /api/v1/wiki/*

VNext-1..3：蓝湖导入 → Raw Source → Wiki 编译 → RAG vs Wiki 差异对比 → 待审产物。
所有能力受配置开关门禁（默认 OFF，raise APIException(503)）与 RBAC（wiki:*）保护。

已落地：切片 0 GET /config；切片 1 蓝湖导入 + Raw Source 列表/详情。
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.wiki import (
    LanhuImportRequest,
    LanhuImportResult,
    WikiConfigOut,
    WikiRawSourceBrief,
    WikiRawSourceOut,
)
from app.services import audit_service
from app.services.wiki import import_service, raw_source_service

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
