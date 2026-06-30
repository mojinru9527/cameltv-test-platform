"""鉴权路由 —— 登录 / 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.auth import LoginIn, LoginOut, MeOut, ProjectBrief, UserBrief
from app.schemas.common import R
from app.services import auth_service, project_service

router = APIRouter(prefix="/auth", tags=["鉴权"])


@router.post("/login", response_model=R[LoginOut], summary="账号密码登录")
def login(body: LoginIn, db: Session = Depends(get_db)):
    return R.ok(auth_service.login(db, body.username, body.password))


@router.get("/me", response_model=R[MeOut], summary="当前用户信息")
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = project_service.projects_for_user(db, current.user.id, is_superadmin=current.is_super)
    data = MeOut(
        user=UserBrief.model_validate(current.user),
        projects=[ProjectBrief.model_validate(p) for p in projects],
        permissions=current.permissions,
        current_project_id=current.project_id,
    )
    return R.ok(data)
