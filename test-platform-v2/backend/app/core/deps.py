"""FastAPI 依赖 —— 当前用户 / 当前项目 / 权限校验。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import forbidden, not_found, unauthorized
from app.core.security import decode_token, password_token_version
from app.models.project import Project
from app.models.user import User
from app.services import project_service, rbac_service

logger = logging.getLogger("auth")
_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    permissions: list[str] = field(default_factory=list)
    project_id: int | None = None
    system_permissions: list[str] | None = None

    @property
    def is_super(self) -> bool:
        # Production authentication supplies system_permissions from global
        # (project_id=0) role assignments only. The None fallback preserves
        # explicitly constructed CurrentUser objects used by internal callers.
        permissions = self.permissions if self.system_permissions is None else self.system_permissions
        return "*" in permissions


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_project_id: int | None = Header(default=None, alias="X-Project-Id"),
    db: Session = Depends(get_db),
) -> CurrentUser:
    # P1-1: prefer httpOnly cookie; fall back to Authorization header (transition period).
    token = request.cookies.get(settings.cookie_name)
    used_fallback = False
    if not token and creds is not None:
        token = creds.credentials
        used_fallback = True
    if not token:
        raise unauthorized()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise unauthorized()
    if payload.get("type") not in (None, "access"):
        raise unauthorized("令牌类型无效")
    # S1b: log deprecation warning when Authorization header fallback is used
    if used_fallback:
        logger.warning(
            "User %s authenticated via Authorization header (deprecated fallback — migrate to httpOnly cookie)",
            payload.get("sub", "?"),
        )
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != 1:
        raise unauthorized("用户不存在或已禁用")
    token_password_version = payload.get("pwdv")
    if not token_password_version:
        raise unauthorized("会话版本过旧，请重新登录")
    if token_password_version != password_token_version(user.password):
        raise unauthorized("密码已变更，会话已失效，请重新登录")
    if user.must_change_password and request.url.path not in {
        "/api/v1/auth/change-password",
        "/api/v1/auth/logout",
    }:
        raise forbidden("必须先修改密码后才能访问业务功能")

    codes = rbac_service.permission_codes(db, user.id, x_project_id)
    system_codes = rbac_service.permission_codes(db, user.id)
    return CurrentUser(
        user=user,
        permissions=codes,
        project_id=x_project_id,
        system_permissions=system_codes,
    )


def require_project(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """要求请求头携带有效的 X-Project-Id，且用户是该项目成员（超管放行）。"""
    if not current.project_id:
        raise forbidden("缺少当前项目（请求头 X-Project-Id）")
    if not current.is_super and not project_service.is_member(db, current.user.id, current.project_id):
        raise forbidden("无权访问该项目")
    if not project_service.is_active_project(db, current.project_id):
        raise not_found("项目不存在")
    return current


def require_permission(code: str):
    """权限点校验依赖工厂。用法：Depends(require_permission('case:list'))

    P1-6/S3: 自动叠加 require_project，确保项目成员身份校验。
    """

    def _checker(
        proj: CurrentUser = Depends(require_project),
        perm: CurrentUser = Depends(_require_permission_only(code)),
    ) -> CurrentUser:
        return proj

    return _checker


def _require_permission_only(code: str):
    """仅校验权限码，不校验项目成员身份（供 require_permission 内部使用）。"""
    def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not rbac_service.has_permission(current.permissions, code):
            raise forbidden(f"缺少权限：{code}")
        return current
    return _checker


def require_system_permission(code: str):
    """Require a global RBAC grant without inventing a project scope for ops."""

    def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        system_permissions = current.system_permissions or []
        if not rbac_service.has_permission(system_permissions, code):
            raise forbidden(f"缺少全局权限：{code}")
        return current

    return _checker


def require_project_create(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """创建项目：超管 / project:create / project:self_create 三者任一（Batch 104）。"""
    perms = current.permissions or []
    if (
        current.is_super
        or rbac_service.has_permission(perms, "project:create")
        or rbac_service.has_permission(perms, "project:self_create")
    ):
        return current
    raise forbidden("缺少权限：project:create")


def require_project_owner_or(perm_code: str):
    """项目级操作放行：超管 / 项目负责人（owner_id） / 拥有全局权限且为项目成员。

    Batch 104 外放轻量模式：普通用户对自己的项目拥有管理能力，无需全局权限点。
    """

    def _checker(
        project_id: int,
        current: CurrentUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> CurrentUser:
        proj = db.get(Project, project_id)
        if not proj or proj.status == 0:
            raise not_found("项目不存在")
        if current.is_super or proj.owner_id == current.user.id:
            return current
        if not rbac_service.has_permission(current.permissions, perm_code):
            raise forbidden(f"缺少权限：{perm_code}")
        if not project_service.is_member(db, current.user.id, project_id):
            raise forbidden("无权访问该项目")
        return current

    return _checker
