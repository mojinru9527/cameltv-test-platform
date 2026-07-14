"""FastAPI 依赖 —— 当前用户 / 当前项目 / 权限校验。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token
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
    # S1b: log deprecation warning when Authorization header fallback is used
    if used_fallback:
        logger.warning(
            "User %s authenticated via Authorization header (deprecated fallback — migrate to httpOnly cookie)",
            payload.get("sub", "?"),
        )
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != 1:
        raise unauthorized("用户不存在或已禁用")

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
