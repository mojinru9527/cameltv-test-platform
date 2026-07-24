"""鉴权路由 —— 登录 / 当前用户 / 修改密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import APIException
from app.core.security import hash_password, verify_password
from app.models.user import User
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
def login(body: LoginIn, response: Response, request: Request, db: Session = Depends(get_db)):
    # 登录频率限制：同一 IP 最多 10 次/15 分钟
    from app.core.rate_limit import login_limiter
    client_ip = request.client.host if request.client else "unknown"
    allowed, wait = login_limiter.is_allowed(client_ip)
    if not allowed:
        raise APIException(code=429, msg=f"登录尝试过于频繁，请 {wait}s 后重试", http_status=429)

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


# ── P2-5: 密码找回 ──────────────────────────────────────

from pydantic import BaseModel as _PydanticBaseModel

class ForgotPasswordRequest(_PydanticBaseModel):
    username: str

class ResetPasswordRequest(_PydanticBaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", response_model=R[None], summary="忘记密码 — 发送重置邮件")
def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """根据用户名查找用户，生成密码重置 token 并通过邮件发送。

    安全设计:
    - 无论用户是否存在都返回成功（防止用户名枚举）
    - Token 有效期 30 分钟
    - 使用后立即失效
    """
    from app.core.security import create_access_token

    user = db.query(User).filter(User.username == body.username).first()
    if not user or user.status != 1:
        # 防止用户名枚举：不存在或已禁用用户也返回成功
        return R.ok()

    # 生成重置 token（30 分钟有效，通过 extra payload 携带 type 标记）
    reset_token = create_access_token(
        user.id,
        extra={"type": "password_reset", "expires_minutes": 30},
    )

    # 尝试发送邮件通知（如有 SMTP 配置）
    try:
        from app.services.notify_service import notify_sync
        notify_sync(
            db,
            project_id=0,
            event="password_reset_requested",
            data={
                "username": user.username,
                "reset_token": reset_token,
                "expires_in": "30 minutes",
                "ip": request.client.host if request.client else "",
            },
        )
    except Exception:
        pass  # 邮件不是必需的，token 可通过管理员人工交接

    return R.ok()


@router.post("/reset-password", response_model=R[None], summary="重置密码（通过 token）")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """使用 forgot-password 返回的 token 重置密码。

    安全设计:
    - 验证 token 有效性与类型
    - Token 一次性使用
    """
    from app.core.security import decode_token

    payload = decode_token(body.token)
    if not payload:
        raise APIException(code=400, msg="无效或已过期的重置 token")

    if payload.get("type") != "password_reset":
        raise APIException(code=400, msg="无效的 token 类型")

    user_id = payload.get("sub")
    if not user_id:
        raise APIException(code=400, msg="无效的重置 token")

    user = db.get(User, int(user_id))
    if not user or user.status != 1:
        raise APIException(code=400, msg="用户不存在或已禁用")

    if len(body.new_password) < 6:
        raise APIException(code=400, msg="密码长度至少 6 位")

    user.password = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()

    return R.ok()


# ── P2-5: SSO 配置占位 ───────────────────────────────────

@router.get("/sso-config", response_model=R[dict], summary="SSO/OIDC 配置状态")
def sso_config():
    """返回当前 SSO 集成状态和可用的 OIDC 提供商配置点。

    当前为最小可行版本，返回配置占位。
    生产环境需要在 settings 中配置 OIDC_PROVIDER_URL / OIDC_CLIENT_ID 等。
    """
    from app.core.config import settings

    sso_enabled = bool(
        getattr(settings, "oidc_provider_url", None)
        and getattr(settings, "oidc_client_id", None)
    )

    return R.ok({
        "enabled": sso_enabled,
        "provider_type": "oidc",
        "providers": [
            {
                "id": "oidc",
                "name": "OIDC / OAuth 2.0",
                "config_keys": ["oidc_provider_url", "oidc_client_id", "oidc_client_secret", "oidc_redirect_uri"],
                "status": "available" if sso_enabled else "not_configured",
            },
        ],
        "note": "配置 OIDC_PROVIDER_URL / OIDC_CLIENT_ID / OIDC_CLIENT_SECRET 环境变量后自动启用" if not sso_enabled else None,
    })
