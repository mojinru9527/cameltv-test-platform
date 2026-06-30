"""鉴权路由 —— 登录 / 当前用户 / 修改密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import APIException
from app.core.security import hash_password, verify_password
from app.schemas.auth import ChangePasswordIn, LoginIn, LoginOut, MeOut, ProjectBrief, UserBrief
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


@router.post("/change-password", response_model=R[None], summary="修改当前用户密码")
def change_password(
    body: ChangePasswordIn,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current.user.password):
        raise APIException(code=400, message="原密码错误")
    if body.old_password == body.new_password:
        raise APIException(code=400, message="新密码不能与原密码相同")
    current.user.password = hash_password(body.new_password)
    current.user.must_change_password = False
    db.commit()
    return R.ok()
