"""鉴权服务 —— 登录校验、组装登录响应。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import unauthorized
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginOut, ProjectBrief, UserBrief
from app.services import project_service, rbac_service


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password):
        raise unauthorized("用户名或密码错误")
    if user.status != 1:
        raise unauthorized("账号已禁用")
    return user


def login(db: Session, username: str, password: str) -> LoginOut:
    user = authenticate(db, username, password)
    user.last_login_at = datetime.now()
    db.commit()

    codes = rbac_service.permission_codes(db, user.id)
    is_super = "*" in codes
    projects = project_service.projects_for_user(db, user.id, is_superadmin=is_super)

    token = create_access_token(user.id)
    return LoginOut(
        access_token=token,
        user=UserBrief.model_validate(user),
        projects=[ProjectBrief.model_validate(p) for p in projects],
        permissions=codes,
    )
