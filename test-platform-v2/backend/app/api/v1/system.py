"""系统管理路由 —— 用户 / 角色 / 权限 / 审计 + 动态菜单。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.schemas.common import R
from app.schemas.system import (
    AuditLogOut, PermissionGroup, PermissionOut, RoleCreate, RoleOut, RoleUpdate,
    UserCreate, UserOut, UserUpdate,
)
from app.services import audit_service, menu_service, role_service, user_service

router = APIRouter(prefix="/system", tags=["系统管理"])


def _audit(req: Request, current_user: CurrentUser, db, action, target, detail=""):
    audit_service.write_audit(
        db,
        user_id=current_user.user.id,
        username=current_user.user.username,
        project_id=current_user.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── 菜单 ──

@router.get("/menus", response_model=R[list], summary="当前用户可见菜单")
def menus(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return R.ok(menu_service.menu_tree(db, current.permissions))


# ── 用户 CRUD ──

@router.get("/users", response_model=R[list[UserOut]], summary="用户列表")
def list_users(
    current: CurrentUser = Depends(require_permission("system:user:list")),
    db: Session = Depends(get_db),
):
    users = user_service.list_users(db, current.project_id or 0)
    return R.ok([UserOut(**u) for u in users])


@router.get("/users/{user_id}", response_model=R[UserOut], summary="用户详情")
def get_user_api(
    user_id: int,
    current: CurrentUser = Depends(require_permission("system:user:list")),
    db: Session = Depends(get_db),
):
    u = user_service.get_user(db, user_id, current.project_id)
    if not u:
        from app.core.exceptions import not_found
        raise not_found("用户不存在")
    return R.ok(UserOut(**u))


@router.post("/users", response_model=R[UserOut], summary="新建用户")
def create_user(
    body: UserCreate, req: Request,
    current: CurrentUser = Depends(require_permission("system:user:create")),
    db: Session = Depends(get_db),
):
    u = user_service.create_user(db, body.model_dump())
    _audit(req, current, db, "user:create", f"用户 {body.username}", str(body.model_dump(exclude={"password"})))
    return R.ok(UserOut(**u))


@router.put("/users/{user_id}", response_model=R[UserOut], summary="更新用户")
def update_user_api(
    user_id: int, body: UserUpdate, req: Request,
    current: CurrentUser = Depends(require_permission("system:user:update")),
    db: Session = Depends(get_db),
):
    u = user_service.update_user(db, user_id, body.model_dump(exclude_none=True))
    if not u:
        from app.core.exceptions import not_found
        raise not_found("用户不存在")
    _audit(req, current, db, "user:update", f"用户 id={user_id}", str(body.model_dump(exclude={"password"})))
    return R.ok(UserOut(**u))


@router.delete("/users/{user_id}", response_model=R, summary="删除用户")
def delete_user_api(
    user_id: int, req: Request,
    current: CurrentUser = Depends(require_permission("system:user:delete")),
    db: Session = Depends(get_db),
):
    ok_ = user_service.delete_user(db, user_id)
    if not ok_:
        from app.core.exceptions import not_found
        raise not_found("用户不存在")
    _audit(req, current, db, "user:delete", f"用户 id={user_id}")
    return R.ok(msg="已删除")


# ── 角色 CRUD ──

@router.get("/roles", response_model=R[list[RoleOut]], summary="角色列表")
def list_roles(
    current: CurrentUser = Depends(require_permission("system:role:list")),
    db: Session = Depends(get_db),
):
    roles = role_service.list_roles(db)
    return R.ok([RoleOut(**r) for r in roles])


@router.get("/roles/{role_id}", response_model=R[RoleOut], summary="角色详情")
def get_role_api(
    role_id: int,
    current: CurrentUser = Depends(require_permission("system:role:list")),
    db: Session = Depends(get_db),
):
    r = role_service.get_role(db, role_id)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("角色不存在")
    return R.ok(RoleOut(**r))


@router.post("/roles", response_model=R[RoleOut], summary="新建角色")
def create_role(
    body: RoleCreate, req: Request,
    current: CurrentUser = Depends(require_permission("system:role:create")),
    db: Session = Depends(get_db),
):
    r = role_service.create_role(db, body.model_dump())
    _audit(req, current, db, "role:create", f"角色 {body.code}", str(body.model_dump()))
    return R.ok(RoleOut(**r))


@router.put("/roles/{role_id}", response_model=R[RoleOut], summary="更新角色")
def update_role_api(
    role_id: int, body: RoleUpdate, req: Request,
    current: CurrentUser = Depends(require_permission("system:role:update")),
    db: Session = Depends(get_db),
):
    r = role_service.update_role(db, role_id, body.model_dump(exclude_none=True))
    if not r:
        from app.core.exceptions import not_found
        raise not_found("角色不存在")
    _audit(req, current, db, "role:update", f"角色 id={role_id}", str(body.model_dump(exclude_none=True)))
    return R.ok(RoleOut(**r))


@router.delete("/roles/{role_id}", response_model=R, summary="删除角色")
def delete_role_api(
    role_id: int, req: Request,
    current: CurrentUser = Depends(require_permission("system:role:delete")),
    db: Session = Depends(get_db),
):
    ok_ = role_service.delete_role(db, role_id)
    if not ok_:
        from app.core.exceptions import not_found
        raise not_found("角色不存在")
    _audit(req, current, db, "role:delete", f"角色 id={role_id}")
    return R.ok(msg="已删除")


# ── 权限 ──

@router.get("/permissions", response_model=R[list[PermissionGroup]], summary="全量权限点（按分组）")
def list_permissions(
    current: CurrentUser = Depends(require_permission("system:role:list")),
    db: Session = Depends(get_db),
):
    """返回所有权限点，按类别分组（菜单/操作/接口），供角色分配表单用。"""
    perms = role_service.list_all_permissions(db)
    groups: dict[str, list[PermissionOut]] = {}
    for p in perms:
        prefix = p["type"]
        g_name = {"menu": "菜单权限", "button": "操作权限", "api": "接口权限"}.get(prefix, prefix)
        groups.setdefault(g_name, []).append(PermissionOut(**p))

    result = [PermissionGroup(group=k, items=v) for k, v in groups.items()]
    return R.ok(result)


# ── 审计 ──

@router.get("/audit-logs", response_model=R[dict], summary="审计日志分页")
def list_audit_logs(
    action: str = Query(""),
    keyword: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current: CurrentUser = Depends(require_permission("system:audit:list")),
    db: Session = Depends(get_db),
):
    rows, total = audit_service.list_audit(
        db, action=action, keyword=keyword,
        project_id=current.project_id,
        limit=limit, offset=offset,
    )
    return R.ok({
        "total": total,
        "list": [AuditLogOut.model_validate(r) for r in rows],
    })


@router.get("/audit-logs/export", summary="导出审计日志 CSV")
def export_audit_logs(
    action: str = Query(""),
    keyword: str = Query(""),
    current: CurrentUser = Depends(require_permission("system:audit:list")),
    db: Session = Depends(get_db),
):
    """导出审计日志为 CSV 文件。"""
    from fastapi.responses import PlainTextResponse
    csv_content = audit_service.export_audit_csv(
        db, action=action, keyword=keyword,
        project_id=current.project_id,
    )
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )
