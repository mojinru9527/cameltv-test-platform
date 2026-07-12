"""知识中心 API 路由 —— /api/v1/knowledge/*

本期（M0+M1）：知识源/切片只读 + 废弃；AI 产物列表/详情 + 采纳/驳回/导入（治理守卫）。
向量检索（/search）留 M2，知识图谱实体/关系留 M3。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.models.knowledge import (
    AgentRun, AiArtifact, KnowledgeChunk, KnowledgeEntity, KnowledgeIteration,
    KnowledgeRelation, KnowledgeSnapshot, KnowledgeSource,
)
from app.schemas.common import Page, R
from app.schemas.knowledge import (
    AiArtifactOut,
    ArtifactImportRequest,
    ArtifactReviewRequest,
    CompareSnapshotsOut,
    EntityExtractRequest,
    EntityExtractResult,
    GraphEdge,
    GraphNode,
    GraphViewOut,
    KnowledgeChunkOut,
    KnowledgeEntityBrief,
    KnowledgeEntityOut,
    KnowledgeHealth,
    KnowledgeIterationCreate,
    KnowledgeIterationOut,
    KnowledgeOverviewOut,
    KnowledgeRelationOut,
    KnowledgeSnapshotOut,
    KnowledgeSourceBrief,
    KnowledgeSourceOut,
    ReembedResult,
    RegressionPredictionItem,
    RegressionPredictionOut,
    RegressionPredictionRequest,
    RelationApprovalRequest,
    SearchQuery,
    SearchResultOut,
)
from app.services import audit_service
from app.services.knowledge import artifact_service, chunk_service, search_service, source_service
from app.services.knowledge.embedding_service import embedding_service
from app.services.knowledge.entity_service import extract_and_build_graph_in_new_session
from app.services.knowledge.vectorize import embed_pending_chunks_in_new_session

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

    # M3: 关系健康指标
    low_confidence_relations = _count(KnowledgeRelation, KnowledgeRelation.confidence < 0.5)
    unreviewed_relations = _count(KnowledgeRelation, KnowledgeRelation.review_status == "pending")

    # M4: Agent 执行指标
    agent_total_runs = _count(AgentRun)
    agent_avg_duration = db.scalar(
        select(func.avg(AgentRun.duration_ms)).where(
            AgentRun.project_id == pid,
            AgentRun.status == "success",
            AgentRun.duration_ms > 0,
        )
    ) or 0
    # 采纳率 = approved / (approved + rejected)
    approved_count = _count(AiArtifact, AiArtifact.review_status == "approved")
    rejected_count = _count(AiArtifact, AiArtifact.review_status == "rejected")
    total_reviewed = approved_count + rejected_count
    agent_approval_rate = approved_count / total_reviewed if total_reviewed > 0 else 0.0

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
            low_confidence_relations=low_confidence_relations,
            unreviewed_relations=unreviewed_relations,
            agent_approval_rate=round(agent_approval_rate, 2),
            agent_avg_duration_ms=int(agent_avg_duration),
            agent_total_runs=agent_total_runs,
        ),
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
    """关键词+向量 RRF 融合检索。仅 rag_enabled 时可用；模型不可用时自动降级为纯关键词。"""
    if not settings.rag_enabled:
        raise APIException(code=503, msg="RAG 检索未启用（rag_enabled=False）", http_status=503)
    hits = search_service.hybrid_search(
        db,
        project_id=current.project_id or 0,
        query=body.query,
        top_k=body.top_k,
        chunk_type=body.chunk_type,
        mode=body.mode,
    )
    return R.ok([SearchResultOut(**hit.__dict__) for hit in hits])


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
    pending = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.project_id == pid,
            KnowledgeChunk.status == "active",
            KnowledgeChunk.embedding_id == "",
        )
    ) or 0
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
    _audit(req, current, db, "ai_artifact:import", f"artifact#{artifact_id} → case#{result['case_id']}", body.comment)
    db.commit()
    return R.ok(result)


# ═══════════════════════════════════════════════════════
# M3 知识图谱
# ═══════════════════════════════════════════════════════

@router.post("/graph/extract", response_model=R[EntityExtractResult], summary="触发实体提取与关系建图")
def extract_graph(
    req: Request,
    body: EntityExtractRequest,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """对项目内 active 切片执行规则驱动的实体提取+关系构建（独立 Session，异步入库）。"""
    from app.core.config import settings
    if not settings.knowledge_graph_enabled:
        return R(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）")

    result = extract_and_build_graph_in_new_session(
        current.project_id or 0,
        source_id=body.source_id,
        max_chunks=body.max_chunks,
    )
    _audit(req, current, db, "knowledge:graph_extract", f"project#{current.project_id}", str(result))
    db.commit()
    return R.ok(EntityExtractResult(**result))


@router.get("/graph/entities", response_model=R[list[KnowledgeEntityBrief]], summary="实体列表")
def list_entities(
    entity_type: str | None = Query(None),
    keyword: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内知识图谱实体（支持按类型和关键词过滤）。"""
    pid = current.project_id or 0
    stmt = select(KnowledgeEntity).where(KnowledgeEntity.project_id == pid)
    if entity_type:
        stmt = stmt.where(KnowledgeEntity.entity_type == entity_type)
    if keyword:
        stmt = stmt.where(KnowledgeEntity.name.contains(keyword) | KnowledgeEntity.description.contains(keyword))
    rows = db.scalars(stmt.order_by(KnowledgeEntity.id.desc()).limit(limit)).all()
    return R.ok([KnowledgeEntityBrief.model_validate(r) for r in rows])


@router.get("/graph/entities/{entity_id}", response_model=R[KnowledgeEntityOut], summary="实体详情")
def get_entity(
    entity_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    entity = db.get(KnowledgeEntity, entity_id)
    if not entity or entity.project_id != (current.project_id or 0):
        return R(code=404, msg="实体不存在")
    return R.ok(KnowledgeEntityOut.model_validate(entity))


@router.get("/graph/relations", response_model=R[list[KnowledgeRelationOut]], summary="关系列表")
def list_relations(
    entity_id: int | None = Query(None, description="过滤以该实体为起点的关系"),
    relation_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内知识图谱关系。"""
    pid = current.project_id or 0
    stmt = select(KnowledgeRelation).where(KnowledgeRelation.project_id == pid)
    if entity_id:
        stmt = stmt.where(KnowledgeRelation.from_entity_id == entity_id)
    if relation_type:
        stmt = stmt.where(KnowledgeRelation.relation_type == relation_type)
    rows = db.scalars(stmt.order_by(KnowledgeRelation.id.desc()).limit(limit)).all()
    return R.ok([KnowledgeRelationOut.model_validate(r) for r in rows])


@router.get("/graph/view", response_model=R[GraphViewOut], summary="图谱可视化数据")
def graph_view(
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """返回力导向图所需的 nodes + edges 数据。"""
    pid = current.project_id or 0
    entities = list(
        db.scalars(
            select(KnowledgeEntity).where(KnowledgeEntity.project_id == pid).limit(limit)
        ).all()
    )
    relations = list(
        db.scalars(
            select(KnowledgeRelation).where(KnowledgeRelation.project_id == pid).limit(limit)
        ).all()
    )
    entity_ids = {e.id for e in entities}
    nodes = [
        GraphNode(
            id=f"{e.entity_type}:{e.entity_key}",
            entity_type=e.entity_type,
            name=e.name,
            group=e.entity_type,
            description=e.description[:120] if e.description else "",
            confidence=e.confidence,
            entity_id=e.id,
        )
        for e in entities
    ]
    edges = [
        GraphEdge(
            source=f"entity:{r.from_entity_id}",
            target=f"entity:{r.to_entity_id}",
            relation_type=r.relation_type,
            confidence=r.confidence,
        )
        for r in relations
        if r.from_entity_id in entity_ids and r.to_entity_id in entity_ids
    ]
    # Resolve source/target to entity:id format
    id_to_node_id: dict[int, str] = {e.id: f"{e.entity_type}:{e.entity_key}" for e in entities}
    for edge in edges:
        from_id = int(edge.source.split(":")[1])
        to_id = int(edge.target.split(":")[1])
        edge.source = id_to_node_id.get(from_id, edge.source)
        edge.target = id_to_node_id.get(to_id, edge.target)

    return R.ok(GraphViewOut(nodes=nodes, edges=edges))


@router.post("/graph/relations/{relation_id}/approve", response_model=R[KnowledgeRelationOut], summary="采纳关系")
def approve_relation(
    relation_id: int,
    req: Request,
    body: RelationApprovalRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    rel = db.get(KnowledgeRelation, relation_id)
    if not rel or rel.project_id != (current.project_id or 0):
        return R(code=404, msg="关系不存在")
    rel.review_status = "approved"
    rel.metadata_json = json.dumps({**json.loads(rel.metadata_json or "{}"), "comment": body.comment})
    _audit(req, current, db, "knowledge:relation_approve", f"relation#{relation_id}", body.comment)
    db.commit()
    db.refresh(rel)
    return R.ok(KnowledgeRelationOut.model_validate(rel))


@router.post("/graph/relations/{relation_id}/reject", response_model=R[KnowledgeRelationOut], summary="驳回关系")
def reject_relation(
    relation_id: int,
    req: Request,
    body: RelationApprovalRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    rel = db.get(KnowledgeRelation, relation_id)
    if not rel or rel.project_id != (current.project_id or 0):
        return R(code=404, msg="关系不存在")
    rel.review_status = "rejected"
    rel.metadata_json = json.dumps({**json.loads(rel.metadata_json or "{}"), "comment": body.comment})
    _audit(req, current, db, "knowledge:relation_reject", f"relation#{relation_id}", body.comment)
    db.commit()
    db.refresh(rel)
    return R.ok(KnowledgeRelationOut.model_validate(rel))


# ═══════════════════════════════════════════════════════
# M6 迭代知识包
# ═══════════════════════════════════════════════════════

from app.services.knowledge import snapshot_service
from app.services.knowledge.snapshot_service import compare_iterations, get_snapshots


@router.post("/iterations", response_model=R[KnowledgeIterationOut], summary="创建迭代")
def create_iteration(
    body: KnowledgeIterationCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    it = snapshot_service.create_iteration(
        db,
        current.project_id or 0,
        iteration_name=body.iteration_name,
        version=body.version,
        start_date=body.start_date,
        end_date=body.end_date,
        description=body.description,
    )
    _audit(req, current, db, "knowledge:iteration_create", f"iteration#{it.id}", body.iteration_name)
    db.commit()
    db.refresh(it)
    return R.ok(KnowledgeIterationOut.model_validate(it))


@router.get("/iterations", response_model=R[Page[KnowledgeIterationOut]], summary="迭代列表")
def list_iterations(
    status: str | None = Query(None, description="active/closed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = snapshot_service.list_iterations(
        db, current.project_id or 0,
        status=status, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[KnowledgeIterationOut.model_validate(r) for r in rows],
    ))


@router.get("/iterations/{iteration_id}", response_model=R[KnowledgeIterationOut], summary="迭代详情")
def get_iteration(
    iteration_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    it = snapshot_service.get_iteration(db, iteration_id, current.project_id or 0)
    if not it:
        return R(code=404, msg="迭代不存在")
    return R.ok(KnowledgeIterationOut.model_validate(it))


@router.post("/iterations/{iteration_id}/close", response_model=R[dict], summary="关闭迭代并生成快照")
def close_iteration(
    iteration_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """关闭迭代，自动创建 entity/relation/chunk/stats 四种快照。"""
    from app.services.knowledge.snapshot_service import close_iteration_in_new_session
    result = close_iteration_in_new_session(iteration_id, current.project_id or 0)
    _audit(req, current, db, "knowledge:iteration_close", f"iteration#{iteration_id}", str(result))
    db.commit()
    if result.get("success"):
        return R.ok(result)
    return R(code=400, msg=result.get("error", "关闭失败"))


@router.get("/iterations/{iteration_id}/snapshots", response_model=R[list[KnowledgeSnapshotOut]], summary="迭代快照列表")
def list_snapshots(
    iteration_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取某个迭代的所有快照（entity/relation/chunk/stats）。"""
    snaps = get_snapshots(db, iteration_id)
    return R.ok([KnowledgeSnapshotOut.model_validate(s) for s in snaps])


@router.get("/iterations/{iteration_id}/compare", response_model=R[CompareSnapshotsOut], summary="跨迭代对比")
def compare_iteration(
    iteration_id: int,
    base_iteration_id: int = Query(..., description="基准迭代 ID"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比两个迭代的快照数据，返回增量和趋势。"""
    result = compare_iterations(db, base_iteration_id, iteration_id, current.project_id or 0)
    if not result:
        return R(code=404, msg="迭代不存在")
    return R.ok(CompareSnapshotsOut(**result))


# ═══════════════════════════════════════════════════════
# M6 回归范围预测
# ═══════════════════════════════════════════════════════

@router.post("/predict/regression-scope", response_model=R[RegressionPredictionOut], summary="回归范围预测")
def predict_regression_scope(
    body: RegressionPredictionRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
):
    """输入变更的 API paths / modules，输出按风险排序的回归范围预测。"""
    from app.services.knowledge.regression_predictor import predict_regression_scope
    result = predict_regression_scope(
        current.project_id or 0,
        changed_paths=body.changed_paths,
        changed_modules=body.changed_modules,
    )
    return R.ok(RegressionPredictionOut(
        items=[RegressionPredictionItem(**i) for i in result["items"]],
        total_analyzed=result["total_analyzed"],
        high_risk_count=result["high_risk_count"],
    ))
