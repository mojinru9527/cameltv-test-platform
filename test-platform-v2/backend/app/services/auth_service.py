"""鉴权服务 —— 登录校验、组装登录响应。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException, unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    password_token_version,
    verify_password,
)
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.schemas.auth import LoginOut, ProjectBrief, UserBrief
from app.schemas.organization import OrganizationBrief
from app.services import project_service, rbac_service
from app.services import organization_service
from app.services.invite_service import consume_invite_code


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
    organizations = organization_service.organizations_for_user(
        db, user.id, is_superadmin=is_super
    )

    token = create_access_token(
        user.id,
        {
            "type": "access",
            "pwdv": password_token_version(user.password),
        },
    )
    return LoginOut(
        access_token=token,
        user=UserBrief.model_validate(user),
        projects=[ProjectBrief.model_validate(p) for p in projects],
        permissions=codes,
        must_change_password=user.must_change_password,
        organizations=[OrganizationBrief(**o) for o in organizations],
    )


def register(
    db: Session,
    *,
    username: str,
    nickname: str,
    email: str,
    password: str,
    invite_code: str,
) -> User:
    """注册新用户：校验邀请码与唯一性，创建用户并赋予默认全局角色。"""
    if db.scalar(select(User).where(User.username == username)):
        raise APIException(code=400, msg="用户名已存在", http_status=400)
    if email and db.scalar(select(User).where(User.email == email)):
        raise APIException(code=400, msg="邮箱已被使用", http_status=400)
    if settings.invite_code_required:
        consume_invite_code(db, invite_code)

    user = User(
        username=username,
        password=hash_password(password),
        nickname=nickname,
        email=email,
        status=1,
        must_change_password=False,
    )
    db.add(user)
    db.flush()

    role_code = settings.default_registration_role or "tester"
    role = db.scalar(select(Role).where(Role.code == role_code))
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id, project_id=0))
    # Batch 105：注册即拥有个人组织
    organization_service.ensure_personal_organization(db, user.id)
    db.commit()
    return user
