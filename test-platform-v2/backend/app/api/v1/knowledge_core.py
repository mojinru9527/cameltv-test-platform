"""知识中心 API 路由 —— 概览/检索（Batch 181 P2-10 拆分）。

从 knowledge.py 拆分：/overview、/search、/search/health、/reembed、
/sources、/chunks、/capture。

路由层不直连 ORM（Batch 181 强制）：概览统计、切片计数全部收敛至
source_service / chunk_service；commit 语义与拆分前一致（保留在路由层）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.knowledge import (
    KnowledgeChunkOut,
    KnowledgeHealth,
    KnowledgeOverviewOut,
    KnowledgeSourceBrief,
    KnowledgeSourceOut,
    ReembedResult,
    SearchHealthOut,
    SearchQuery,
    SearchResultOut,
)

from app.services import audit_service
from app.services.knowledge import chunk_service, search_service, source_service
from app.services.knowledge.embedding_service import embedding_service
from app.services.knowledge.vectorize import embed_pending_chunks_in_new_session

logger = logging.getLogger("knowledge")
router = APIRouter(prefix="/knowledge", tags=["知识中心-概览/检索"])


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
    data = source_service.get_knowledge_overview(db, pid)

    # M2 RAG: embedding 覆盖率
    rag_enabled = settings.rag_enabled
    active_chunks = data["chunk_count"]
    embedded_chunks = data["embedded_chunks"]
    embedding_coverage = embedded_chunks / active_chunks if active_chunks > 0 and rag_enabled else None
    embedding_model = settings.embedding_model if rag_enabled else ""

    out = KnowledgeOverviewOut(
        source_count=data["source_count"],
        chunk_count=data["chunk_count"],
        entity_count=data["entity_count"],
        pending_artifact_count=data["pending_artifacts"],
        recent_sources=[KnowledgeSourceBrief.model_validate(r) for r in data["recent_sources"]],
        health=KnowledgeHealth(
            unreviewed_artifacts=data["pending_artifacts"],
            deprecated_sources=data["deprecated_sources"],
            sourceless_chunks=data["sourceless"],
            low_confidence_relations=data["low_confidence_relations"],
            unreviewed_relations=data["unreviewed_relations"],
            agent_approval_rate=round(data["agent_approval_rate"], 2),
            agent_avg_duration_ms=int(data["agent_avg_duration"]),
            agent_total_runs=data["agent_total_runs"],
        ),
        rag_enabled=rag_enabled,
        embedding_model=embedding_model,
        active_chunks=active_chunks,
        embedded_chunks=embedded_chunks,
        embedding_coverage=embedding_coverage,
    )
    return R.ok(out)


# ═══════════════════════════════════════════════════════
# 混合检索（M2 RAG）
# ═══════════════════════════════════════════════════════

@router.post("/search", response_model=R[list[SearchResultOut]], summary="知识混合检索（RAG）")
def search_knowledge(
    body: SearchQuery,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """关键词+向量 RRF 融合检索。rag_enabled=False 或模型不可用时自动降级为纯关键词。"""
    pid = current.project_id or 0

    # Determine effective mode: if RAG disabled or model unavailable, force keyword-only
    effective_mode = body.mode
    if not settings.rag_enabled:
        effective_mode = "keyword"
    elif not embedding_service.available():
        effective_mode = "keyword"

    hits = search_service.hybrid_search(
        db,
        project_id=pid,
        query=body.query,
        top_k=body.top_k,
        chunk_type=body.chunk_type,
        mode=effective_mode,
    )
    return R.ok([SearchResultOut.model_validate(hit) for hit in hits])


@router.get("/search/health", response_model=R[SearchHealthOut], summary="搜索健康检查（RAG）")
def search_health(
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """报告 RAG 启用状态、模型可用性、向量检索功能与覆盖率。"""
    pid = current.project_id or 0
    rag_enabled = settings.rag_enabled
    model_name = settings.embedding_model if rag_enabled else ""
    embedding_available = embedding_service.available() if rag_enabled else False

    # 向量检索功能验证：有 rag 开关 + 模型就绪 + 库中有向量记录
    vector_functional = False
    active_total = 0
    embedded_total = 0
    if rag_enabled and embedding_available:
        active_total = chunk_service.count_chunks(db, pid)
        embedded_total = chunk_service.count_chunks(db, pid, embedded_only=True)
        # 向量检索功能可用：至少有一条已嵌入切片（说明向量库和嵌入管线可工作）
        vector_functional = embedded_total > 0

    fallback_mode = "hybrid" if (rag_enabled and embedding_available and vector_functional) else "keyword-only"
    coverage = embedded_total / active_total if active_total > 0 and rag_enabled else None

    return R.ok(SearchHealthOut(
        rag_enabled=rag_enabled,
        embedding_model=model_name,
        embedding_available=embedding_available,
        vector_search_functional=vector_functional,
        fallback_mode=fallback_mode,
        active_chunks=active_total,
        embedded_chunks=embedded_total,
        embedding_coverage=coverage,
    ))


@router.post("/reembed", response_model=R[ReembedResult], summary="存量切片向量回填（RAG）")
def reembed(
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """分批回填本项目 active 且未嵌入的切片（幂等）。需 rag_enabled 且嵌入模型就绪。"""
    if not settings.rag_enabled:
        raise APIException(code=503, msg="RAG 检索未启用（rag_enabled=False）", http_status=503)
    if not embedding_service.available():
        raise APIException(code=503, msg="嵌入模型不可用（fastembed 未安装或模型未就绪）", http_status=503)
    pid = current.project_id or 0
    pending = chunk_service.count_pending_embedding_chunks(db, pid)
    result = embed_pending_chunks_in_new_session(pid)  # 独立 Session、分批、幂等
    _audit(req, current, db, "knowledge:reembed", f"project#{pid}", str(result))
    db.commit()
    return R.ok(ReembedResult(
        total=pending,
        embedded=result.get("embedded", 0),
        skipped=result.get("skipped", 0),
    ))


# ═══════════════════════════════════════════════════════
# 知识源
# ═══════════════════════════════════════════════════════

@router.get("/sources", response_model=R[Page[KnowledgeSourceBrief]], summary="知识源列表")
def list_sources(
    source_type: str | None = Query(None),
    para_category: str | None = Query(None),
    knowledge_domain: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = source_service.list_sources(
        db, current.project_id or 0,
        source_type=source_type, para_category=para_category,
        knowledge_domain=knowledge_domain, status=status, keyword=keyword,
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
    _audit(req, current, db, "knowledge:deprecate", f"source#{source_id}")
    db.commit()
    return R.ok({"id": source_id, "status": "deprecated"})


@router.post("/sources/{source_id}/verify", response_model=R[KnowledgeSourceBrief], summary="验证知识源保鲜度")
def verify_source(
    source_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """标记知识源为已验证：设置 last_verified_at = now()，freshness_score = 1.0。"""
    row = source_service.verify_source(db, source_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="知识源不存在")
    _audit(req, current, db, "knowledge:verify", f"source#{source_id}")
    db.commit()
    db.refresh(row)
    return R.ok(KnowledgeSourceBrief.model_validate(row))


class ClassifySourceRequest(BaseModel):
    para_category: str | None = None
    knowledge_domain: str | None = None


@router.patch("/sources/{source_id}/classify", response_model=R[KnowledgeSourceBrief], summary="更新知识源 PARA 分类")
def classify_source(
    source_id: int,
    body: ClassifySourceRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """更新知识源的 para_category / knowledge_domain。"""
    valid_cats = {"inbox", "project", "area", "resource", "archive", "wiki", "skill"}
    valid_domains = {"project", "platform"}
    if body.para_category is not None and body.para_category not in valid_cats:
        return R(code=400, msg=f"无效的 para_category，有效值: {valid_cats}")
    if body.knowledge_domain is not None and body.knowledge_domain not in valid_domains:
        return R(code=400, msg=f"无效的 knowledge_domain，有效值: {valid_domains}")

    row = source_service.classify_source(
        db, source_id, current.project_id or 0,
        para_category=body.para_category, knowledge_domain=body.knowledge_domain,
    )
    if not row:
        return R(code=404, msg="知识源不存在")
    _audit(req, current, db, "knowledge:classify", f"source#{source_id}",
           f"para={body.para_category} domain={body.knowledge_domain}")
    db.commit()
    db.refresh(row)
    return R.ok(KnowledgeSourceBrief.model_validate(row))


# ── 灵感捕获 ──

class CaptureRequest(BaseModel):
    title: str
    content: str
    source_url: str | None = None
    tags: list[str] | None = None


@router.post("/capture", response_model=R[dict], summary="灵感快速捕获")
def capture_insight(
    body: CaptureRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """快速捕获灵感/想法/片段，自动入库为 inbox 分类，后续 AI 自动加工。"""
    from app.services.knowledge.ingest_service import ingest_capture_in_new_session

    result = ingest_capture_in_new_session(
        current.project_id or 0,
        title=body.title,
        content=body.content,
        source_url=body.source_url or "",
        tags=body.tags,
    )
    if result.reason == "disabled":
        raise APIException(
            code=503,
            msg="知识入库未启用（KNOWLEDGE_INGEST_ENABLED=false），请联系管理员",
            http_status=503,
        )
    if result.reason == "duplicate":
        return R(code=409, msg="内容重复，已存在相同知识源")
    if result.reason == "error" or result.source_id is None:
        raise APIException(code=500, msg="知识入库失败，请查看服务日志", http_status=500)
    _audit(req, current, db, "knowledge:capture", f"source#{result.source_id}", body.title)
    db.commit()
    return R.ok({"id": result.source_id, "title": body.title, "status": "captured"})
