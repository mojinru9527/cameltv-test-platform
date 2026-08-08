"""需求模块树 API 路由 —— /api/v1/requirement-modules

提供模块树查询（层级/平台/版本/变化类型）+ M2 服务集成入口。
M3 API 层：对接 M2 ModuleExtractor / TestCaseLinker / NavigatesToExtractor /
              GlobalNavClassifier / ConfiguresLinker / AttachmentExtractor。
"""
from __future__ import annotations

import json

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException, not_found
from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.release_bundle import ReleaseBundle
from app.schemas.common import Page, R
from app.schemas.release_bundle import (
    AttachmentExtractRequest,
    AttachmentExtractResultOut,
    ConfiguresLinkConfirmRequest,
    ConfiguresLinkRequest,
    GlobalNavClassifyRequest,
    GlobalNavItemOut,
    InteractionExtractRequest,
    InteractionSaveRequest,
    ModuleAdminLinkCreate,
    ModuleAdminLinkOut,
    BuildFromDocumentRequest,
    ModuleExtractRequest,
    ProductionDiffRequest,
    ModuleExtractResult,
    ModuleTestSummaryOut,
    ModuleTreeNode,
    ModuleTreeResponse,
    RequirementModuleBrief,
    RequirementModuleOut,
    TestLinkingResult,
)
from app.services import audit_service

router = APIRouter(prefix="/requirement-modules", tags=["需求模块"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _commit_with_audit(
    req: Request,
    current: CurrentUser,
    db: Session,
    action: str,
    target: str,
    detail: str = "",
) -> None:
    """Persist one business operation and its audit row atomically."""
    try:
        _audit(req, current, db, action, target, detail)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ═══════════════════════════════════════════════════════
# 模块查询
# ═══════════════════════════════════════════════════════

@router.get("", response_model=R[Page[RequirementModuleBrief]], summary="模块列表")
def list_modules(
    release_bundle_id: int | None = Query(None, description="按发布包过滤"),
    node_type: str | None = Query(None, description="module / page / function_point / attachment"),
    platform: str | None = Query(None, description="APP / PC / WEB / ADMIN"),
    change_type: str | None = Query(None, description="new / modified / deleted / unchanged"),
    parent_module_id: int | None = Query(None, description="按父模块过滤（0=仅顶层）"),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内的需求模块节点，支持多维度过滤和关键词搜索。"""
    pid = current.project_id or 0
    stmt = select(RequirementModule).where(RequirementModule.project_id == pid)

    if release_bundle_id:
        stmt = stmt.where(RequirementModule.release_bundle_id == release_bundle_id)
    if node_type:
        stmt = stmt.where(RequirementModule.node_type == node_type)
    if platform:
        stmt = stmt.where(RequirementModule.platform == platform)
    if change_type:
        stmt = stmt.where(RequirementModule.change_type == change_type)
    if parent_module_id is not None:
        if parent_module_id == 0:
            stmt = stmt.where(RequirementModule.parent_module_id.is_(None))
        else:
            stmt = stmt.where(RequirementModule.parent_module_id == parent_module_id)
    if keyword:
        stmt = stmt.where(
            RequirementModule.name.contains(keyword)
            | RequirementModule.description.contains(keyword)
        )

    # P0-5: Use a separate count query instead of subquerying the ORM select
    # to avoid errors with complex ORM expressions
    count_stmt = select(func.count()).select_from(RequirementModule).where(
        RequirementModule.project_id == pid
    )
    if release_bundle_id:
        count_stmt = count_stmt.where(RequirementModule.release_bundle_id == release_bundle_id)
    if node_type:
        count_stmt = count_stmt.where(RequirementModule.node_type == node_type)
    if platform:
        count_stmt = count_stmt.where(RequirementModule.platform == platform)
    if change_type:
        count_stmt = count_stmt.where(RequirementModule.change_type == change_type)
    if parent_module_id is not None:
        if parent_module_id == 0:
            count_stmt = count_stmt.where(RequirementModule.parent_module_id.is_(None))
        else:
            count_stmt = count_stmt.where(RequirementModule.parent_module_id == parent_module_id)
    if keyword:
        count_stmt = count_stmt.where(
            RequirementModule.name.contains(keyword)
            | RequirementModule.description.contains(keyword)
        )
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(
        stmt.order_by(RequirementModule.sort_order, RequirementModule.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all())

    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[RequirementModuleBrief.model_validate(r) for r in rows],
    ))


@router.get("/{module_id}", response_model=R[RequirementModuleOut], summary="模块详情")
def get_module(
    module_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取单个需求模块的完整信息（含 page_interactions JSON）。"""
    mod = db.get(RequirementModule, module_id)
    if not mod or mod.project_id != (current.project_id or 0):
        from app.core.exceptions import not_found
        raise not_found("模块")
    return R.ok(RequirementModuleOut.model_validate(mod))


# ═══════════════════════════════════════════════════════
# 模块树视图
# ═══════════════════════════════════════════════════════

def _build_tree_nodes(
    modules: list[RequirementModule],
    parent_id: int | None = None,
) -> list[ModuleTreeNode]:
    """递归构建模块树节点列表。"""
    children = [m for m in modules if m.parent_module_id == parent_id]
    nodes: list[ModuleTreeNode] = []
    for child in sorted(children, key=lambda m: (m.sort_order or 0, m.id)):
        sub_nodes = _build_tree_nodes(modules, child.id)
        node = ModuleTreeNode(
            id=child.id,
            name=child.name,
            node_type=child.node_type,
            platform=child.platform,
            change_type=child.change_type,
            description=child.description or "",
            lanhu_page_id=child.lanhu_page_id or "",
            page_interactions=child.page_interactions or "[]",
            children=sub_nodes,
            child_count=len(sub_nodes),
        )
        nodes.append(node)
    return nodes


@router.get("/bundle/{bundle_id}/tree", response_model=R[ModuleTreeResponse], summary="发布包模块树")
def get_module_tree(
    bundle_id: int,
    platform: str | None = Query(None, description="按平台过滤子树：APP / PC / WEB / ADMIN"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取发布包的完整模块层级树（project → platform → module → page → function_point）。

    用于前端树形组件和版本全景视图。
    """
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    # Load all modules for this bundle
    stmt = select(RequirementModule).where(
        RequirementModule.project_id == pid,
        RequirementModule.release_bundle_id == bundle_id,
    ).order_by(RequirementModule.sort_order, RequirementModule.id)

    all_modules = list(db.scalars(stmt).all())

    # Begin building from top-level modules (no parent)
    top_modules = [m for m in all_modules if m.parent_module_id is None]

    if platform:
        top_modules = [m for m in top_modules if m.platform == platform or m.node_type != "module"]

    roots = _build_tree_nodes(all_modules, parent_id=None)
    # Filter by platform if requested
    if platform:
        roots = [r for r in roots if r.platform == platform or r.node_type != "module"]

    total_modules = sum(1 for m in all_modules if m.node_type == "module")
    total_pages = sum(1 for m in all_modules if m.node_type == "page")
    total_attachments = sum(1 for m in all_modules if m.node_type == "attachment")

    return R.ok(ModuleTreeResponse(
        bundle_id=bundle.id,
        bundle_name=bundle.name,
        client_version=bundle.client_version,
        admin_version=bundle.admin_version,
        roots=roots,
        total_modules=total_modules,
        total_pages=total_pages,
        total_attachments=total_attachments,
    ))


@router.get("/bundle/{bundle_id}/children/{parent_id}", response_model=R[list[ModuleTreeNode]], summary="子节点列表")
def get_child_modules(
    bundle_id: int,
    parent_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取指定模块的直接子节点（懒加载子节点，适用于大型模块树）。P3: 只加载两层而非全部模块。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    parent = db.scalar(
        select(RequirementModule).where(
            RequirementModule.id == parent_id,
            RequirementModule.project_id == pid,
            RequirementModule.release_bundle_id == bundle_id,
        )
    )
    if not parent:
        raise not_found("模块")

    children = list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.project_id == pid,
            RequirementModule.release_bundle_id == bundle_id,
            RequirementModule.parent_module_id == parent_id,
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())

    # Only load grandchildren (one level deeper), not all modules — P3 performance fix
    child_ids = [c.id for c in children]
    grandchildren: list[RequirementModule] = []
    if child_ids:
        grandchildren = list(db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == pid,
                RequirementModule.release_bundle_id == bundle_id,
                RequirementModule.parent_module_id.in_(child_ids),
            ).order_by(RequirementModule.sort_order, RequirementModule.id)
        ).all())

    # Build nodes with two-level depth
    nodes: list[ModuleTreeNode] = []
    for child in sorted(children, key=lambda m: (m.sort_order or 0, m.id)):
        gchildren = [gc for gc in grandchildren if gc.parent_module_id == child.id]
        sub_nodes = _build_tree_nodes_from_list(gchildren, parent_id=child.id)
        nodes.append(ModuleTreeNode(
            id=child.id,
            name=child.name,
            node_type=child.node_type,
            platform=child.platform,
            change_type=child.change_type,
            description=child.description or "",
            lanhu_page_id=child.lanhu_page_id or "",
            page_interactions=child.page_interactions or "[]",
            children=sub_nodes,
            child_count=len(sub_nodes),
        ))
    return R.ok(nodes)


def _build_tree_nodes_from_list(
    modules: list[RequirementModule],
    parent_id: int | None = None,
) -> list[ModuleTreeNode]:
    """Build tree nodes from a flat list (without recursive DB query — P3 performance fix)."""
    children = [m for m in modules if m.parent_module_id == parent_id]
    nodes: list[ModuleTreeNode] = []
    for child in sorted(children, key=lambda m: (m.sort_order or 0, m.id)):
        sub_nodes = _build_tree_nodes_from_list(modules, child.id)
        nodes.append(ModuleTreeNode(
            id=child.id,
            name=child.name,
            node_type=child.node_type,
            platform=child.platform,
            change_type=child.change_type,
            description=child.description or "",
            lanhu_page_id=child.lanhu_page_id or "",
            page_interactions=child.page_interactions or "[]",
            children=sub_nodes,
            child_count=len(sub_nodes),
        ))
    return nodes


# ═══════════════════════════════════════════════════════
# 模块提取（对接 M2 ModuleExtractor）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/extract", response_model=R[ModuleExtractResult], summary="从证据包提取模块树")
def extract_modules(
    bundle_id: int,
    body: ModuleExtractRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """从 LanhuEvidenceJob 提取模块→页面→功能点层级树。

    自动识别平台（APP/PC/WEB/ADMIN）、更新日志条目和说明附件。
    提取结果写入 RequirementModule 表，关联到指定发布包。
    """
    pid = current.project_id or 0
    bundle = db.scalar(
        select(ReleaseBundle)
        .where(
            ReleaseBundle.id == bundle_id,
            ReleaseBundle.project_id == pid,
        )
        .with_for_update()
    )
    if not bundle:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.module_extractor import extract_module_tree, persist_module_tree

    # Phase 1: Extract
    extraction = extract_module_tree(
        db,
        evidence_job_id=body.evidence_job_id,
        project_id=pid,
        document_id=body.document_id,
    )

    # Phase 2: Persist
    module_ids = persist_module_tree(
        db,
        extraction=extraction,
        release_bundle_id=bundle_id,
        project_id=pid,
        source_version=body.source_version or bundle.client_version,
    )

    _commit_with_audit(
        req,
        current,
        db,
        "module:extract",
        f"bundle#{bundle_id}",
        f"{len(module_ids)} modules, {extraction.stats}",
    )

    return R.ok(ModuleExtractResult(
        module_ids=module_ids,
        module_count=len(extraction.modules),
        page_count=sum(len(m.pages) for m in extraction.modules),
        attachment_count=len(extraction.attachments),
        changelog_entries=len(extraction.changelog_entries),
        warnings=extraction.warnings,
    ))


@router.post("/build-from-document", response_model=R[ModuleExtractResult], summary="从需求文档直建模块树（C102-3）")
def build_modules_from_document(
    body: BuildFromDocumentRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """C102-3：不依赖蓝湖证据包，从需求文档（extraction_raw/content）直接构建模块树。

    发布包解析顺序：请求体 release_bundle_id → 文档关联 release_bundle_id →
    自动创建（名称=文档标题，client_version=文档版本或 source_version）。
    """
    pid = current.project_id or 0
    document = db.get(RequirementDocument, body.document_id)
    if not document or document.project_id != pid:
        raise not_found("需求文档")

    # Resolve release bundle context
    bundle_id = body.release_bundle_id
    if bundle_id is not None:
        bundle = db.get(ReleaseBundle, bundle_id)
        if not bundle or bundle.project_id != pid:
            raise not_found("发布包")
    elif document.release_bundle_id:
        bundle_id = document.release_bundle_id
    else:
        bundle = ReleaseBundle(
            project_id=pid,
            name=document.title or "需求文档直建模块树",
            description="Batch 118 C102-3 需求文档直建模块树",
            client_version=document.version or body.source_version or "draft",
            status="draft",
        )
        db.add(bundle)
        db.flush()
        bundle_id = bundle.id

    from app.services.knowledge.module_extractor import (
        build_module_tree_from_document,
        persist_module_tree,
    )

    extraction = build_module_tree_from_document(
        db,
        document_id=body.document_id,
        project_id=pid,
        source_version=body.source_version,
    )
    if not extraction.modules and not extraction.warnings:
        extraction.warnings.append("文档中未解析到模块")

    module_ids = persist_module_tree(
        db,
        extraction=extraction,
        release_bundle_id=bundle_id,
        project_id=pid,
        source_version=body.source_version or document.version or "draft",
    )

    _commit_with_audit(
        req,
        current,
        db,
        "module:build_from_document",
        f"doc#{body.document_id}",
        f"{len(module_ids)} modules, {extraction.stats}",
    )

    return R.ok(ModuleExtractResult(
        module_ids=module_ids,
        module_count=len(extraction.modules),
        page_count=sum(len(m.pages) for m in extraction.modules),
        attachment_count=len(extraction.attachments),
        changelog_entries=len(extraction.changelog_entries),
        warnings=extraction.warnings,
    ))


# ═══════════════════════════════════════════════════════
# 测试用例关联（对接 M2 TestCaseLinker）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/link-test-cases", response_model=R[dict], summary="批量关联测试用例到模块")
def link_test_cases(
    bundle_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """对发布包内所有模块执行三级匹配策略（精确名→功能点→API），自动创建 tested_by 关联。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.test_case_linker import link_all_modules

    results = link_all_modules(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        version=bundle.client_version,
    )
    total_linked = sum(r.linked_count for r in results.values())
    total_relations = sum(r.relations_created for r in results.values())

    _commit_with_audit(
        req,
        current,
        db,
        "module:link_tests",
        f"bundle#{bundle_id}",
        f"{len(results)} modules, {total_linked} cases linked",
    )

    return R.ok({
        "modules_processed": len(results),
        "total_linked": total_linked,
        "total_relations": total_relations,
        "results": {
            str(mod_id): {
                "linked_count": r.linked_count,
                "relations_created": r.relations_created,
                "by_strategy": r.by_strategy,
            }
            for mod_id, r in results.items()
        },
    })


@router.get("/{module_id}/test-summary", response_model=R[ModuleTestSummaryOut], summary="模块测试覆盖摘要")
def get_module_test_summary(
    module_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取单个模块的测试覆盖摘要（按用例类型和自动化程度分类）。"""
    pid = current.project_id or 0
    mod = db.get(RequirementModule, module_id)
    if not mod or mod.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("模块")

    from app.services.knowledge.test_case_linker import get_module_test_summary as get_summary

    summary = get_summary(db, module_id=module_id, project_id=pid)
    return R.ok(ModuleTestSummaryOut(
        module_id=summary.module_id,
        module_name=summary.module_name,
        total_test_cases=summary.total_test_cases,
        functional=summary.functional,
        api=summary.api,
        automation=summary.automation,
        coverage_rate=summary.coverage_rate,
        last_run_status=summary.last_run_status,
        linked_case_ids=summary.linked_case_ids,
    ))


# ═══════════════════════════════════════════════════════
# 页面交互提取（对接 M2 NavigatesToExtractor）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/extract-interactions", response_model=R[dict], summary="提取页面交互跳转关系")
async def extract_interactions(
    bundle_id: int,
    body: InteractionExtractRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """对发布包内所有页面执行四层降级提取（DOM→AI→CV→Manual），结果写入 page_interactions 字段。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.navigates_to_extractor import extract_all_pages

    report = await extract_all_pages(
        db,
        release_bundle_id=bundle_id,
        preferred_layers=body.preferred_layers,
        save=True,
    )
    _commit_with_audit(
        req,
        current,
        db,
        "module:extract_interactions",
        f"bundle#{bundle_id}",
        f"{report.pages_with_interactions}/{report.total_pages_processed} pages",
    )

    return R.ok({
        "total_pages_processed": report.total_pages_processed,
        "pages_with_interactions": report.pages_with_interactions,
        "pages_without_interactions": report.pages_without_interactions,
        "interactions_found": report.interactions_found,
        "by_layer": report.by_layer,
        "by_type": report.by_type,
        "failed_pages": report.failed_pages,
        "warnings": report.warnings,
    })


@router.put("/{module_id}/interactions", response_model=R[dict], summary="手动编辑页面交互（P4）")
def save_interactions(
    module_id: int,
    body: InteractionSaveRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """手动标注或合并页面交互跳转关系。merge=true 时与现有交互去重合并。"""
    pid = current.project_id or 0
    mod = db.get(RequirementModule, module_id)
    if not mod or mod.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("模块")
    if mod.node_type != "page":
        return R(code=400, msg="仅页面节点支持交互编辑")

    from app.services.knowledge.navigates_to_extractor import save_manual_interactions

    merged = save_manual_interactions(
        db,
        page_module_id=module_id,
        interactions=body.interactions,
        merge=body.merge,
    )
    _commit_with_audit(
        req,
        current,
        db,
        "module:save_interactions",
        f"page#{module_id}",
        f"{len(merged)} interactions (merge={body.merge})",
    )

    return R.ok({"interaction_count": len(merged), "merge": body.merge})


# ═══════════════════════════════════════════════════════
# 全局导航分类（对接 M2 GlobalNavClassifier）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/classify-global-nav", response_model=R[dict], summary="分类全局导航")
def classify_global_nav(
    bundle_id: int,
    body: GlobalNavClassifyRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """分析发布包内所有页面交互，将出现在 >threshold 页面的交互提升为全局导航。

    结果写入 ReleaseBundle.global_navigation 并清理每个页面中的重复条目。
    """
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.global_nav_classifier import classify_global_navigation

    result = classify_global_navigation(
        db,
        release_bundle_id=bundle_id,
        threshold=body.threshold,
        save=True,
    )
    _commit_with_audit(
        req,
        current,
        db,
        "module:classify_global_nav",
        f"bundle#{bundle_id}",
        f"{len(result.global_nav_items)} items, removed {result.removed_from_pages} from pages",
    )

    return R.ok({
        "total_pages": result.total_pages,
        "pages_with_interactions": result.pages_with_interactions,
        "global_nav_items": [
            {
                "trigger": i.trigger,
                "target_page": i.target_page,
                "coverage": i.coverage,
                "source_element": i.source_element,
                "description": i.description,
            }
            for i in result.global_nav_items
        ],
        "removed_from_pages": result.removed_from_pages,
        "warnings": result.warnings,
    })


@router.get("/bundle/{bundle_id}/global-nav", response_model=R[list[GlobalNavItemOut]], summary="获取全局导航项")
def get_global_nav(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """读取发布包已分类的全局导航项列表。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.global_nav_classifier import get_global_navigation

    items = get_global_navigation(db, release_bundle_id=bundle_id)
    return R.ok([
        GlobalNavItemOut(
            trigger=i.trigger,
            target_page=i.target_page,
            interaction_type=i.interaction_type,
            coverage=i.coverage,
            source_element=i.source_element,
            description=i.description,
        )
        for i in items
    ])


# ═══════════════════════════════════════════════════════
# 跨系统配置关联（对接 M2 ConfiguresLinker）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/suggest-configures", response_model=R[dict], summary="分析配置关联建议")
def suggest_configures(
    bundle_id: int,
    body: ConfiguresLinkRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """分析发布包内 client↔admin 模块的配置关联建议。

    P1 级：从 dynamic_filter 交互提取 admin_config_source。
    P2 级：模块名相似度模糊匹配。
    返回按置信度排序的建议列表供人工审核。
    """
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.configures_linker import suggest_configures_links

    result = suggest_configures_links(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        client_version=body.client_version or bundle.client_version,
        admin_version=body.admin_version or bundle.admin_version,
    )

    return R.ok({
        "suggestions": [
            {
                "index": i,
                "client_module_id": s.client_module_id,
                "client_module_name": s.client_module_name,
                "admin_module_id": s.admin_module_id,
                "admin_module_name": s.admin_module_name,
                "config_items": s.config_items,
                "impact": s.impact,
                "confidence": s.confidence,
                "source": s.source,
                "evidence": s.evidence,
            }
            for i, s in enumerate(result.suggestions)
        ],
        "total_suggestions": len(result.suggestions),
        "by_strategy": result.by_strategy,
        "unmatched_admin_sources": result.unmatched_admin_sources,
        "warnings": result.warnings,
    })


@router.post("/bundle/{bundle_id}/confirm-configures", response_model=R[dict], summary="确认配置关联并入库")
def confirm_configures(
    bundle_id: int,
    body: ConfiguresLinkConfirmRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """确认配置关联建议，创建 ModuleAdminLink 和 KnowledgeRelation（configures 类型）。

    支持按索引选择或按置信度阈值批量确认。
    """
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.configures_linker import suggest_configures_links, confirm_configures_links

    # Re-generate suggestions
    suggest_result = suggest_configures_links(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        client_version=bundle.client_version,
        admin_version=bundle.admin_version,
    )

    # Filter by indices or confidence
    if body.suggestion_indices:
        selected = [suggest_result.suggestions[i] for i in body.suggestion_indices
                    if 0 <= i < len(suggest_result.suggestions)]
    else:
        selected = [s for s in suggest_result.suggestions if s.confidence >= body.min_confidence]

    if not selected:
        return R.ok({"links_created": 0, "message": "无符合条件的配置关联建议"})

    confirm_result = confirm_configures_links(
        db,
        suggestions=selected,
        project_id=pid,
        client_version=bundle.client_version,
        admin_version=bundle.admin_version,
    )
    _commit_with_audit(
        req,
        current,
        db,
        "module:confirm_configures",
        f"bundle#{bundle_id}",
        f"{confirm_result.links_created} links",
    )

    return R.ok({
        "links_created": confirm_result.links_created,
        "confirmed_count": len(selected),
    })


@router.get("/bundle/{bundle_id}/admin-links", response_model=R[list[ModuleAdminLinkOut]], summary="跨系统关联列表")
def list_admin_links(
    bundle_id: int,
    relation_type: Literal["configures", "links_to_admin"] | None = Query(
        None,
        description="configures / links_to_admin",
    ),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取发布包内所有 client↔admin 模块关联。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    # Get all client/admin module IDs in this bundle
    module_ids = list(db.scalars(
        select(RequirementModule.id).where(
            RequirementModule.project_id == pid,
            RequirementModule.release_bundle_id == bundle_id,
        )
    ).all())

    stmt = select(ModuleAdminLink).where(
        ModuleAdminLink.project_id == pid,
        ModuleAdminLink.client_module_id.in_(module_ids),
    )
    if relation_type:
        stmt = stmt.where(ModuleAdminLink.relation_type == relation_type)

    rows = list(db.scalars(stmt.order_by(ModuleAdminLink.id.desc())).all())
    return R.ok([ModuleAdminLinkOut.model_validate(r) for r in rows])


@router.post("/admin-links", response_model=R[ModuleAdminLinkOut], summary="手动创建跨系统关联")
def create_admin_link(
    body: ModuleAdminLinkCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """手动创建 client↔admin 模块关联。"""
    pid = current.project_id or 0

    client_mod = db.scalar(
        select(RequirementModule).where(
            RequirementModule.id == body.client_module_id,
            RequirementModule.project_id == pid,
        )
    )
    admin_mod = db.scalar(
        select(RequirementModule).where(
            RequirementModule.id == body.admin_module_id,
            RequirementModule.project_id == pid,
        )
    )
    if not client_mod:
        raise not_found("用户端模块")
    if not admin_mod:
        raise not_found("运营后台模块")
    if client_mod.id == admin_mod.id:
        raise APIException(code=400, msg="用户端与运营后台模块不能相同", http_status=400)
    if client_mod.node_type != "module" or client_mod.platform not in {"APP", "PC", "WEB"}:
        raise APIException(code=400, msg="用户端必须是 APP、PC 或 WEB 的模块节点", http_status=400)
    if admin_mod.node_type != "module" or admin_mod.platform != "ADMIN":
        raise APIException(code=400, msg="运营后台必须是 ADMIN 模块节点", http_status=400)
    if client_mod.release_bundle_id != admin_mod.release_bundle_id:
        raise APIException(code=400, msg="关联模块必须属于同一发布包", http_status=400)

    # Check duplicate
    existing = db.scalar(
        select(ModuleAdminLink.id).where(
            ModuleAdminLink.project_id == pid,
            ModuleAdminLink.client_module_id == body.client_module_id,
            ModuleAdminLink.admin_module_id == body.admin_module_id,
            ModuleAdminLink.relation_type == body.relation_type,
        )
    )
    if existing:
        raise APIException(code=409, msg="该关联已存在", http_status=409)

    link = ModuleAdminLink(
        project_id=pid,
        client_module_id=body.client_module_id,
        admin_module_id=body.admin_module_id,
        relation_type=body.relation_type,
        confidence=1.0,
        evidence="手动创建",
    )
    db.add(link)
    try:
        db.flush()
        _commit_with_audit(
            req,
            current,
            db,
            "module:admin_link_create",
            f"client#{body.client_module_id}→admin#{body.admin_module_id}",
        )
    except IntegrityError as exc:
        db.rollback()
        raise APIException(code=409, msg="该关联已存在", http_status=409) from exc
    db.refresh(link)
    return R.ok(ModuleAdminLinkOut.model_validate(link))


@router.delete("/admin-links/{link_id}", response_model=R[dict], summary="删除跨系统关联")
def delete_admin_link(
    link_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """删除指定的跨系统模块关联。"""
    pid = current.project_id or 0
    link = db.get(ModuleAdminLink, link_id)
    if not link or link.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("关联")
    detail = f"link#{link_id} client#{link.client_module_id}→admin#{link.admin_module_id}"
    db.delete(link)
    _commit_with_audit(
        req,
        current,
        db,
        "module:admin_link_delete",
        detail,
    )
    return R.ok({"deleted": True})


# ═══════════════════════════════════════════════════════
# 附件内容提取（对接 M2 AttachmentExtractor）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/extract-attachments", response_model=R[AttachmentExtractResultOut], summary="提取附件内容")
async def extract_attachments(
    bundle_id: int,
    body: AttachmentExtractRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """提取发布包内所有 attachment 类型模块的结构化内容。

    过程：下载附件→OCR/文本提取→AI 分析→存储为功能点+业务规则 KnowledgeEntity。
    """
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    from app.services.knowledge.attachment_extractor import extract_all_attachments

    result = await extract_all_attachments(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        version=body.version or bundle.client_version,
    )
    _commit_with_audit(
        req,
        current,
        db,
        "module:extract_attachments",
        f"bundle#{bundle_id}",
        f"{result.processed}/{result.total_attachments} processed",
    )

    return R.ok(AttachmentExtractResultOut(
        total_attachments=result.total_attachments,
        processed=result.processed,
        failed=result.failed,
        business_rules_created=result.business_rules_created,
        function_points_extracted=result.function_points_extracted,
        errors=result.errors,
    ))


@router.post("/production-diff", response_model=R[dict], summary="生产页面 vs 需求原型差异标注（C102-4）")
def production_diff_annotate(
    body: ProductionDiffRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比发布包模块树与生产页面清单，输出 new / matched / missing 差异标注。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, body.release_bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    from app.services.knowledge.production_diff_service import compute_production_diff

    result = compute_production_diff(
        db,
        release_bundle_id=body.release_bundle_id,
        project_id=pid,
        production_pages=[p.model_dump() for p in body.production_pages],
    )
    return R.ok(result)


class ModuleTreeImportNode(BaseModel):
    path: str
    type: str = "page"
    lanhu_page_id: str = ""
    screenshots: list[str] = []


class ModuleTreeImportRequest(BaseModel):
    release_bundle_id: int | None = None
    bundle_name: str = "蓝湖需求模块树"
    source_version: str = "e6b5ce1e"
    tree: list[ModuleTreeImportNode]


class ModuleTreeImportResult(BaseModel):
    created: int = 0
    skipped: int = 0
    total: int = 0


@router.post("/import-tree", response_model=R[ModuleTreeImportResult], summary="导入需求模块树（蓝湖 sitemap 层级）")
def import_module_tree(
    body: ModuleTreeImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """把蓝湖导出 sitemap 的层级树导入 requirement_module（幂等）。

    按 path 层级建 parent_module_id（path 即 平台/模块/页）；node_type=module|page；
    lanhu_page_id=html 文件；screenshot_urls=设计稿截图清单。
    """
    pid = current.project_id or 0
    bundle_id = body.release_bundle_id
    if bundle_id is None:
        bundle = ReleaseBundle(
            project_id=pid,
            name=body.bundle_name,
            description="Batch 124 蓝湖需求模块树导入",
            client_version=body.source_version,
            status="draft",
        )
        db.add(bundle)
        db.flush()
        bundle_id = bundle.id

    nodes = sorted(body.tree, key=lambda n: n.path.count("/"))
    path_to_id: dict[str, int] = {}
    created = skipped = 0
    for n in nodes:
        segs = [s for s in n.path.split("/") if s]
        if not segs:
            continue
        name = segs[-1]
        platform = segs[0]
        parent_key = "/".join(segs[:-1])
        parent_id = path_to_id.get(parent_key)

        q = select(RequirementModule.id).where(
            RequirementModule.project_id == pid,
            RequirementModule.name == name,
            RequirementModule.lanhu_page_id == n.lanhu_page_id,
        )
        q = q.where(RequirementModule.parent_module_id.is_(None) if parent_id is None else RequirementModule.parent_module_id == parent_id)
        exists = db.scalar(q)
        if exists:
            path_to_id[n.path] = exists
            skipped += 1
            continue
        row = RequirementModule(
            project_id=pid,
            release_bundle_id=bundle_id,
            name=name,
            node_type=n.type,
            platform=platform,
            lanhu_page_id=n.lanhu_page_id,
            change_type="added",
            parent_module_id=parent_id,
            source_version=body.source_version,
            screenshot_urls=json.dumps(n.screenshots, ensure_ascii=False),
            sort_order=0,
        )
        db.add(row)
        db.flush()
        path_to_id[n.path] = row.id
        created += 1

    db.commit()
    _commit_with_audit(req, current, db, "module:import_tree", f"bundle#{bundle_id}", f"created {created} skipped {skipped}")
    return R.ok(ModuleTreeImportResult(created=created, skipped=skipped, total=len(body.tree)))
