"""鉴权路由 —— 登录 / 当前用户 / 修改密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import APIException
from app.core.security import hash_password, verify_password
from app.schemas.auth import ChangePasswordIn, LoginIn, LoginOut, MeOut, ProjectBrief, UserBrief
from app.schemas.common import R
from app.services import auth_service, project_service

router = APIRouter(prefix="/auth", tags=["鉴权"])


def _set_auth_cookie(response: Response, token: str) -> None:
    """P1-1: 将 JWT 写入 httpOnly cookie，防止 XSS 脚本读取。"""
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        path=settings.cookie_path,
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        domain=settings.cookie_domain or None,
        path=settings.cookie_path,
    )


@router.post("/login", response_model=R[LoginOut], summary="账号密码登录")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    result = auth_service.login(db, body.username, body.password)
    # P1-1: 同时下发 httpOnly cookie；响应体仍返回 access_token 以兼容过渡期客户端。
    _set_auth_cookie(response, result.access_token)
    return R.ok(result)


@router.post("/logout", response_model=R[None], summary="登出（清除鉴权 cookie）")
def logout(response: Response):
    _clear_auth_cookie(response)
    return R.ok()


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
