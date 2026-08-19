"""需求模块 API 路由 —— /api/v1/requirement-modules（页面交互/全局导航/配置关联/附件提取）

Batch 181（FIX-173-P2-10）拆分自 requirement_modules.py，端点逻辑逐字迁移。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import R
from app.schemas.release_bundle import (
    AttachmentExtractRequest,
    AttachmentExtractResultOut,
    ConfiguresLinkConfirmRequest,
    ConfiguresLinkRequest,
    GlobalNavClassifyRequest,
    GlobalNavItemOut,
    InteractionExtractRequest,
    InteractionSaveRequest,
)
from app.services import audit_service, requirement_module_service

router = APIRouter(prefix="/requirement-modules", tags=["需求模块-交互"])


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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    from app.services.knowledge.navigates_to_extractor import extract_all_pages

    report = await extract_all_pages(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
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
    mod = requirement_module_service.get_module(db, module_id)
    if not mod or mod.project_id != pid:
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
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
