"""FastAPI 依赖 —— 当前用户 / 当前项目 / 权限校验。"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token
from app.models.user import User
from app.services import project_service, rbac_service

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    permissions: list[str] = field(default_factory=list)
    project_id: int | None = None

    @property
    def is_super(self) -> bool:
        return "*" in self.permissions


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_project_id: int | None = Header(default=None, alias="X-Project-Id"),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if creds is None:
        raise unauthorized()
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise unauthorized()
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != 1:
        raise unauthorized("用户不存在或已禁用")

    codes = rbac_service.permission_codes(db, user.id, x_project_id)
    return CurrentUser(user=user, permissions=codes, project_id=x_project_id)


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
    """权限点校验依赖工厂。用法：Depends(require_permission('case:list'))"""

    def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not rbac_service.has_permission(current.permissions, code):
            raise forbidden(f"缺少权限：{code}")
        return current

    return _checker
