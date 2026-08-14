"""需求模块 API 路由 —— /api/v1/requirement-modules（跨系统关联 admin-links）

Batch 181（FIX-173-P2-10）拆分自 requirement_modules.py，端点逻辑逐字迁移。
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException, not_found
from app.schemas.common import R
from app.schemas.release_bundle import (
    ModuleAdminLinkCreate,
    ModuleAdminLinkOut,
)
from app.services import audit_service, requirement_module_service

router = APIRouter(prefix="/requirement-modules", tags=["需求模块-跨系统关联"])


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
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    # Get all client/admin module IDs in this bundle
    module_ids = requirement_module_service.list_bundle_module_ids(db, pid, bundle_id)

    rows = requirement_module_service.list_admin_links(
        db, pid, module_ids, relation_type=relation_type,
    )
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

    client_mod = requirement_module_service.get_module_in_project(db, body.client_module_id, pid)
    admin_mod = requirement_module_service.get_module_in_project(db, body.admin_module_id, pid)
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
    existing = requirement_module_service.find_admin_link_id(
        db,
        project_id=pid,
        client_module_id=body.client_module_id,
        admin_module_id=body.admin_module_id,
        relation_type=body.relation_type,
    )
    if existing:
        raise APIException(code=409, msg="该关联已存在", http_status=409)

    link = requirement_module_service.create_admin_link(
        db,
        project_id=pid,
        client_module_id=body.client_module_id,
        admin_module_id=body.admin_module_id,
        relation_type=body.relation_type,
        confidence=1.0,
        evidence="手动创建",
    )
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
    link = requirement_module_service.get_admin_link(db, link_id)
    if not link or link.project_id != pid:
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
