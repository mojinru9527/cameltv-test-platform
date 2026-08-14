"""需求模块树 API 路由 —— /api/v1/requirement-modules（模块查询/树视图）

Batch 181（FIX-173-P2-10）拆分自 requirement_modules.py，端点逻辑逐字迁移。
（提取/用例关联在 requirement_modules_extract.py，交互在 requirement_modules_interactions.py）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import Page, R
from app.schemas.release_bundle import (
    ModuleTreeNode,
    ModuleTreeResponse,
    RequirementModuleBrief,
    RequirementModuleOut,
)
from app.services import audit_service, requirement_module_service

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
    total, rows = requirement_module_service.list_modules(
        db, pid,
        release_bundle_id=release_bundle_id,
        node_type=node_type,
        platform=platform,
        change_type=change_type,
        parent_module_id=parent_module_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

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
    mod = requirement_module_service.get_module(db, module_id)
    if not mod or mod.project_id != (current.project_id or 0):
        raise not_found("模块")
    return R.ok(RequirementModuleOut.model_validate(mod))


# ═══════════════════════════════════════════════════════
# 模块树视图
# ═══════════════════════════════════════════════════════

def _build_tree_nodes(
    modules,
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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    # Load all modules for this bundle
    all_modules = requirement_module_service.list_bundle_modules(db, pid, bundle_id)

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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    parent = requirement_module_service.get_bundle_module(db, pid, bundle_id, parent_id)
    if not parent:
        raise not_found("模块")

    children = requirement_module_service.list_child_modules(db, pid, bundle_id, parent_id)

    # Only load grandchildren (one level deeper), not all modules — P3 performance fix
    child_ids = [c.id for c in children]
    grandchildren = []
    if child_ids:
        grandchildren = requirement_module_service.list_modules_by_parent_ids(
            db, pid, bundle_id, child_ids,
        )

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
    modules,
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
