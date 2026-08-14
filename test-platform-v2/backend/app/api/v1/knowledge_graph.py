"""知识中心 API 路由 —— 图谱（Batch 181 P2-10 拆分）。

从 knowledge.py 拆分：/graph/*（提取/实体/关系/可视化/审核/自演化/模块关联/
用例入图/层级图谱）与 /design-assets/*。

路由层不直连 ORM（Batch 181 强制）：图谱查询与写入收敛至
entity_service / chunk_service / source_service；commit 语义与拆分前一致
（保留在路由层）。
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R
from app.schemas.knowledge import (
    AutoBuildRequest,
    AutoBuildResult,
    EntityExtractRequest,
    EntityExtractResult,
    GraphEdge,
    GraphNode,
    GraphViewOut,
    KnowledgeEntityBrief,
    KnowledgeEntityOut,
    KnowledgeEntityStats,
    KnowledgeRelationOut,
    RelationApprovalRequest,
)
from app.schemas.release_bundle import ProjectSphereView
from app.services import audit_service
from app.services.knowledge import chunk_service, entity_service, source_service
from app.services.knowledge.entity_service import extract_and_build_graph_in_new_session

logger = logging.getLogger("knowledge")
router = APIRouter(prefix="/knowledge", tags=["知识中心-图谱"])


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
    if not settings.knowledge_graph_enabled:
        raise APIException(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）", http_status=503)

    available, unavailable_reason = chunk_service.has_active_chunks(
        db,
        current.project_id or 0,
        body.source_id,
    )
    if not available:
        raise APIException(code=409, msg=unavailable_reason, http_status=409)

    result = extract_and_build_graph_in_new_session(
        current.project_id or 0,
        source_id=body.source_id,
        max_chunks=body.max_chunks,
    )
    _audit(req, current, db, "knowledge:graph_extract", f"project#{current.project_id}", str(result))
    db.commit()
    return R.ok(EntityExtractResult(**result))


@router.get("/graph/entities/stats", response_model=R[KnowledgeEntityStats], summary="实体统计")
def entity_stats(
    entity_type: str | None = Query(None),
    keyword: str | None = Query(None),
    knowledge_domain: str | None = Query(None, description="知识域过滤: project | platform"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """Return project-wide totals without conflating them with the list limit."""
    stats = entity_service.get_entity_stats(
        db,
        current.project_id or 0,
        entity_type=entity_type,
        keyword=keyword,
        knowledge_domain=knowledge_domain,
    )
    return R.ok(KnowledgeEntityStats(**stats))


@router.get("/graph/entities", response_model=R[list[KnowledgeEntityBrief]], summary="实体列表")
def list_entities(
    entity_type: str | None = Query(None),
    keyword: str | None = Query(None),
    knowledge_domain: str | None = Query(None, description="知识域过滤: project | platform"),
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内知识图谱实体（支持按类型/关键词/知识域过滤）。"""
    rows, source_map = entity_service.get_entities(
        db,
        current.project_id or 0,
        entity_type=entity_type,
        keyword=keyword,
        knowledge_domain=knowledge_domain,
        limit=limit,
    )
    out = []
    for r in rows:
        item = KnowledgeEntityBrief.model_validate(r)
        if r.source_id and r.source_id in source_map:
            item.source_title, item.source_type = source_map[r.source_id]
        out.append(item)
    return R.ok(out)


@router.get("/graph/entities/{entity_id}", response_model=R[KnowledgeEntityOut], summary="实体详情")
def get_entity(
    entity_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    entity, src = entity_service.get_entity_with_source(db, entity_id, current.project_id or 0)
    if not entity:
        return R(code=404, msg="实体不存在")
    out = KnowledgeEntityOut.model_validate(entity)
    if src:
        out.source_title = src.title or ""
        out.source_type = src.source_type or ""
    return R.ok(out)


@router.get("/graph/relations", response_model=R[list[KnowledgeRelationOut]], summary="关系列表")
def list_relations(
    entity_id: int | None = Query(None, description="过滤以该实体为起点的关系"),
    relation_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内知识图谱关系。"""
    rows = entity_service.get_relations(
        db,
        current.project_id or 0,
        entity_id=entity_id,
        relation_type=relation_type,
        limit=limit,
    )
    return R.ok([KnowledgeRelationOut.model_validate(r) for r in rows])


@router.get("/graph/view", response_model=R[GraphViewOut], summary="图谱可视化数据")
def graph_view(
    limit: int = Query(200, ge=1, le=1000),
    knowledge_domain: str | None = Query(None, description="知识域过滤: project | platform"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """返回力导向图所需的 nodes + edges 数据。支持按 knowledge_domain 过滤。"""
    pid = current.project_id or 0
    if settings.knowledge_graph_enabled:
        extract_available, unavailable_reason = chunk_service.has_active_chunks(db, pid)
    else:
        extract_available = False
        unavailable_reason = "知识图谱功能未启用"

    entities, relations = entity_service.get_graph_view_data(
        db, pid, knowledge_domain=knowledge_domain, limit=limit,
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

    # 去重：重复 entity_key 会生成相同 node id（历史重复实体），vis-network add 会抛错导致整页崩溃
    seen: set[str] = set()
    unique_nodes = []
    for n in nodes:
        if n.id in seen:
            continue
        seen.add(n.id)
        unique_nodes.append(n)
    nodes = unique_nodes
    valid_ids = seen
    edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]

    return R.ok(GraphViewOut(
        nodes=nodes,
        edges=edges,
        extract_available=extract_available,
        unavailable_reason=unavailable_reason,
    ))


@router.post("/graph/relations/{relation_id}/approve", response_model=R[KnowledgeRelationOut], summary="采纳关系")
def approve_relation(
    relation_id: int,
    req: Request,
    body: RelationApprovalRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    rel = entity_service.review_relation(
        db, relation_id, current.project_id or 0, "approved", body.comment,
    )
    if not rel:
        return R(code=404, msg="关系不存在")
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
    rel = entity_service.review_relation(
        db, relation_id, current.project_id or 0, "rejected", body.comment,
    )
    if not rel:
        return R(code=404, msg="关系不存在")
    _audit(req, current, db, "knowledge:relation_reject", f"relation#{relation_id}", body.comment)
    db.commit()
    db.refresh(rel)
    return R.ok(KnowledgeRelationOut.model_validate(rel))


class GraphEvolveResult(BaseModel):
    merged: int = 0
    confidence_updates: int = 0
    new_relations: int = 0
    message: str = ""


@router.post("/graph/backfill-source", response_model=R[dict], summary="回填缺失来源的图谱实体（C147-9）")
def backfill_graph_source(
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """按名称匹配用例/需求，回填 source_id/source_ref；未匹配保持 None。"""
    from app.services.knowledge.entity_service import backfill_missing_source

    result = backfill_missing_source(db, current.project_id or 0)
    _audit(req, current, db, "knowledge:graph_backfill_source", f"project#{current.project_id or 0}", str(result))
    db.commit()
    return R.ok(result)


@router.post("/graph/evolve", response_model=R[GraphEvolveResult], summary="概念地图自演化")
def evolve_graph(
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """触发概念地图自演化：合并重复实体、更新置信度、发现隐含关系。"""
    if not settings.knowledge_graph_enabled:
        raise APIException(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）", http_status=503)

    from app.services.knowledge.entity_service import evolve_graph_in_new_session
    result = evolve_graph_in_new_session(current.project_id or 0)
    _audit(req, current, db, "knowledge:graph_evolve", f"project#{current.project_id}", str(result))
    db.commit()
    return R.ok(GraphEvolveResult(**result))


@router.post("/graph/auto-build", response_model=R[AutoBuildResult], summary="自动构建知识图谱（从 ReleaseBundle）")
def auto_build_graph(
    body: AutoBuildRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """从 ReleaseBundle + RequirementModule 树构建完整层级知识图谱。

    创建实体类型: project, release_bundle, platform, client_module, admin_module, page, changelog_entry
    创建关系类型: contains, has_platform, has_module, has_page, belongs_to_version,
                  navigates_to, links_to_admin, configures, evolves_from, described_by

    幂等：重复调用相同 release_bundle_id 不重复创建（返回 skipped > 0）。
    使用 force=true 强制重建。
    """
    if not settings.knowledge_graph_enabled:
        raise APIException(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）", http_status=503)

    from app.services.knowledge.graph_builder import auto_build_graph as do_auto_build
    try:
        result = do_auto_build(
            current.project_id or 0,
            body.release_bundle_id,
            force=body.force,
        )
    except Exception as e:
        logger.exception("auto_build_graph failed for bundle %d", body.release_bundle_id)
        raise APIException(code=500, msg=f"图谱构建失败: {str(e)}") from e

    _audit(req, current, db, "knowledge:graph_auto_build", f"bundle#{body.release_bundle_id}", result.message)
    db.commit()
    return R.ok(AutoBuildResult(
        created_entities=result.created_entities,
        created_relations=result.created_relations,
        skipped_entities=result.skipped_entities,
        skipped_relations=result.skipped_relations,
        message=result.message,
    ))


class ModuleAssociationEntity(BaseModel):
    entity_type: str
    entity_key: str
    name: str
    description: str = ""
    confidence: float = 1.0
    metadata: dict | None = None


class ModuleAssociationRelation(BaseModel):
    from_key: str
    relation_type: str
    to_key: str
    confidence: float = 1.0
    evidence: str = ""


class ModuleAssociationRequest(BaseModel):
    entities: list[ModuleAssociationEntity]
    relations: list[ModuleAssociationRelation]


class ModuleAssociationResult(BaseModel):
    created_entities: int = 0
    created_relations: int = 0
    skipped_entities: int = 0
    skipped_relations: int = 0
    total_entities: int = 0
    total_relations: int = 0


@router.post("/graph/module-associations", response_model=R[ModuleAssociationResult], summary="体育模块关联入库（Batch 122 用例结构）")
def import_module_associations(
    body: ModuleAssociationRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """从用例结构批量入库模块/用例/接口实体与业务关系（幂等）。

    实体：module / test_case / api；关系：contains / tested_by / navigates_to / links_to_admin / configures。
    幂等：按 entity_key 与 from+relation_type+to 去重，重复调用不重复创建。
    """
    if not settings.knowledge_graph_enabled:
        raise APIException(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）", http_status=503)

    pid = current.project_id or 0
    result = entity_service.import_module_associations(db, pid, body.entities, body.relations)
    _audit(req, current, db, "knowledge:graph_module_associations", f"project#{pid}",
           f"entities +{result['created_entities']} relations +{result['created_relations']}")
    db.commit()
    return R.ok(ModuleAssociationResult(**result))


@router.post("/graph/sync-test-cases", response_model=R[dict], summary="全量用例入图（Batch 132）")
def sync_test_cases_to_graph(
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """将项目全部 active 用例同步为图谱用例实体并回填来源（C125-3/C126-1），幂等。

    用例实体统一挂到"用例库全量"知识源（project 域）；能关联模块的用例建立
    tested_by 关联。返回 total_cases / test_case_entities / created /
    source_backfilled / linked_cases。
    """
    if not settings.knowledge_graph_enabled:
        raise APIException(code=503, msg="知识图谱未启用（knowledge_graph_enabled=False）", http_status=503)
    from app.services.knowledge.test_case_graph_sync import sync_all_test_cases_to_graph
    result = sync_all_test_cases_to_graph(db, current.project_id or 0)
    _audit(req, current, db, "knowledge:graph_sync_test_cases", f"project#{current.project_id or 0}",
           f"cases={result['total_cases']} entities={result['test_case_entities']}")
    return R.ok(result)


class DesignAssetImage(BaseModel):
    filename: str
    base64: str


class DesignAssetSource(BaseModel):
    title: str
    source_ref: str = ""
    text: str = ""
    metadata: dict | None = None
    images: list[DesignAssetImage] = []


class DesignAssetImportRequest(BaseModel):
    sources: list[DesignAssetSource]


class DesignAssetImportResult(BaseModel):
    created_sources: int = 0
    skipped_sources: int = 0
    created_chunks: int = 0
    saved_images: int = 0


@router.post("/design-assets/import", response_model=R[DesignAssetImportResult], summary="需求/设计稿入库（文本+图片）")
def import_design_assets(
    body: DesignAssetImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """把需求原型页（文本+设计稿图片）入库为知识源，幂等（按 content_hash 去重）。"""
    pid = current.project_id or 0
    result = source_service.import_design_assets(db, pid, body.sources)
    _audit(req, current, db, "knowledge:design_assets_import", f"project#{pid}",
           f"sources +{result['created_sources']} images {result['saved_images']}")
    db.commit()
    return R.ok(DesignAssetImportResult(**result))


@router.get("/design-assets/{source_id}/{filename}", summary="需求设计稿图片")
def get_design_asset(
    source_id: int,
    filename: str,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """服务需求设计稿图片（路径逃逸防护）。"""
    from fastapi.responses import FileResponse

    row = source_service.get_source(db, source_id, current.project_id or 0)
    if not row:
        raise APIException(code=404, msg="知识源不存在", http_status=404)
    safe = Path(filename).name
    base = (source_service._design_storage_base() / str(source_id)).resolve()
    target = (base / safe).resolve()
    if not target.is_relative_to(base) or not target.exists():
        raise APIException(code=404, msg="图片不存在", http_status=404)
    return FileResponse(str(target))


# ═══════════════════════════════════════════════════════
# M3 项目球层级图谱（Batch 27 Knowledge Sphere）
# ═══════════════════════════════════════════════════════

@router.get("/graph/hierarchy", response_model=R[ProjectSphereView], summary="项目球层级图谱")
def graph_hierarchy(
    release_bundle_id: int | None = Query(None, description="指定发布包，不传则返回最新 active"),
    max_depth: int = Query(4, ge=1, le=6, description="层级深度：1=项目, 2=版本, 3=平台, 4=模块, 5=页面"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """返回「项目球」层级图谱数据：project → version → platform → module → page
    （边：contains/configures/tested_by）。"""
    view = entity_service.get_hierarchy_view(
        db,
        current.project_id or 0,
        release_bundle_id,
        max_depth,
    )
    if view is None:
        return R(code=404, msg="发布包不存在")
    return R.ok(view)
