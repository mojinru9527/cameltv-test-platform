"""知识中心 API 路由 —— /api/v1/knowledge/*

本期（M0+M1）：知识源/切片只读 + 废弃；AI 产物列表/详情 + 采纳/驳回/导入（治理守卫）。
向量检索（/search）留 M2，知识图谱实体/关系留 M3。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.knowledge import AiArtifact, KnowledgeChunk, KnowledgeEntity, KnowledgeSource
from app.schemas.common import Page, R
from app.schemas.knowledge import (
    AiArtifactOut,
    ArtifactImportRequest,
    ArtifactReviewRequest,
    KnowledgeChunkOut,
    KnowledgeHealth,
    KnowledgeOverviewOut,
    KnowledgeSourceBrief,
    KnowledgeSourceOut,
)
from app.services import audit_service
from app.services.knowledge import artifact_service, chunk_service, source_service

router = APIRouter(prefix="/knowledge", tags=["知识中心"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ═══════════════════════════════════════════════════════
# 概览
# ═══════════════════════════════════════════════════════

@router.get("/overview", response_model=R[KnowledgeOverviewOut], summary="知识中心概览")
def overview(
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0

    def _count(model, *conds) -> int:
        stmt = select(func.count(model.id)).where(model.project_id == pid, *conds)
        return db.scalar(stmt) or 0

    source_count = _count(KnowledgeSource, KnowledgeSource.status.notin_(("deprecated", "superseded")))
    chunk_count = _count(KnowledgeChunk, KnowledgeChunk.status == "active")
    entity_count = _count(KnowledgeEntity)
    pending_artifacts = _count(AiArtifact, AiArtifact.review_status == "pending")
    deprecated_sources = _count(KnowledgeSource, KnowledgeSource.status == "deprecated")

    # 孤儿切片：引用了不存在知识源的切片
    sourceless = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.project_id == pid,
            KnowledgeChunk.source_id.notin_(select(KnowledgeSource.id)),
        )
    ) or 0

    recent = db.scalars(
        select(KnowledgeSource)
        .where(KnowledgeSource.project_id == pid)
        .order_by(KnowledgeSource.id.desc())
        .limit(5)
    ).all()

    out = KnowledgeOverviewOut(
        source_count=source_count,
        chunk_count=chunk_count,
        entity_count=entity_count,
        pending_artifact_count=pending_artifacts,
        recent_sources=[KnowledgeSourceBrief.model_validate(r) for r in recent],
        health=KnowledgeHealth(
            unreviewed_artifacts=pending_artifacts,
            deprecated_sources=deprecated_sources,
            sourceless_chunks=sourceless,
            low_confidence_relations=0,
        ),
    )
    return R.ok(out)


# ═══════════════════════════════════════════════════════
# 知识源
# ═══════════════════════════════════════════════════════

@router.get("/sources", response_model=R[Page[KnowledgeSourceBrief]], summary="知识源列表")
def list_sources(
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = source_service.list_sources(
        db, current.project_id or 0,
        source_type=source_type, status=status, keyword=keyword,
        page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[KnowledgeSourceBrief.model_validate(r) for r in rows],
    ))


@router.get("/sources/{source_id}", response_model=R[KnowledgeSourceOut], summary="知识源详情")
def get_source(
    source_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    row = source_service.get_source(db, source_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="知识源不存在")
    return R.ok(KnowledgeSourceOut.model_validate(row))


@router.get("/sources/{source_id}/chunks", response_model=R[list[KnowledgeChunkOut]], summary="知识源切片")
def get_source_chunks(
    source_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    src = source_service.get_source(db, source_id, current.project_id or 0)
    if not src:
        return R(code=404, msg="知识源不存在")
    rows = chunk_service.list_chunks_by_source(db, source_id)
    return R.ok([KnowledgeChunkOut.model_validate(r) for r in rows])


@router.get("/chunks/{chunk_id}", response_model=R[KnowledgeChunkOut], summary="切片详情")
def get_chunk(
    chunk_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    row = chunk_service.get_chunk(db, chunk_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="切片不存在")
    return R.ok(KnowledgeChunkOut.model_validate(row))


@router.post("/sources/{source_id}/deprecate", response_model=R[dict], summary="废弃知识源")
def deprecate_source(
    source_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    ok = source_service.deprecate_source(db, source_id, current.project_id or 0)
    if not ok:
        return R(code=404, msg="知识源不存在")
    db.commit()
    _audit(req, current, db, "knowledge:deprecate", f"source#{source_id}")
    db.commit()
    return R.ok({"id": source_id, "status": "deprecated"})


# ═══════════════════════════════════════════════════════
# AI 产物审核台
# ═══════════════════════════════════════════════════════

@router.get("/ai-artifacts", response_model=R[Page[AiArtifactOut]], summary="AI 产物列表")
def list_artifacts(
    review_status: str | None = Query(None),
    artifact_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = artifact_service.list_artifacts(
        db, current.project_id or 0,
        review_status=review_status, artifact_type=artifact_type,
        page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[AiArtifactOut.model_validate(r) for r in rows],
    ))


@router.get("/ai-artifacts/{artifact_id}", response_model=R[AiArtifactOut], summary="AI 产物详情")
def get_artifact(
    artifact_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    row = artifact_service.get_artifact(db, artifact_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    return R.ok(AiArtifactOut.model_validate(row))


@router.post("/ai-artifacts/{artifact_id}/approve", response_model=R[AiArtifactOut], summary="采纳 AI 产物")
def approve_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactReviewRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    row = artifact_service.approve(db, artifact_id, current.project_id or 0, current.user.id, body.comment)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    db.commit()
    _audit(req, current, db, "knowledge:approve", f"artifact#{artifact_id}", body.comment)
    db.commit()
    db.refresh(row)
    return R.ok(AiArtifactOut.model_validate(row))


@router.post("/ai-artifacts/{artifact_id}/reject", response_model=R[AiArtifactOut], summary="驳回 AI 产物")
def reject_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactReviewRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    row = artifact_service.reject(db, artifact_id, current.project_id or 0, current.user.id, body.comment)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    db.commit()
    _audit(req, current, db, "knowledge:reject", f"artifact#{artifact_id}", body.comment)
    db.commit()
    db.refresh(row)
    return R.ok(AiArtifactOut.model_validate(row))


@router.post("/ai-artifacts/{artifact_id}/import-to-test-cases", response_model=R[dict], summary="导入正式用例库")
def import_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactImportRequest,
    current: CurrentUser = Depends(require_permission("ai_artifact:import")),
    db: Session = Depends(get_db),
):
    """治理守卫：仅 review_status='approved' 的 AI 用例产物允许导入正式库。"""
    result = artifact_service.import_to_test_case(db, artifact_id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "ai_artifact:import", f"artifact#{artifact_id} → case#{result['case_id']}", body.comment)
    db.commit()
    return R.ok(result)
