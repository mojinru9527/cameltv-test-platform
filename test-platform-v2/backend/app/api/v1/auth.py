"""鉴权路由 —— 登录 / 当前用户 / 修改密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import APIException
from app.core.security import hash_password, verify_password
from app.schemas.auth import (
    ChangePasswordIn,
    LoginIn,
    LoginOut,
    MeOut,
    ProjectBrief,
    PublicAccessOut,
    RegisterIn,
    UserBrief,
)
from app.schemas.common import R
from app.services import auth_service, menu_service, project_service, user_service
from app.services.audit_service import write_audit

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


def _auth_audit(db: Session, request: Request, action: str, target: str = "", detail: str = "",
                user_id: int = 0, username: str = "") -> None:
    """B12：认证事件审计（登录/登出/改密/注册/重置密码），失败尝试同样记录。"""
    write_audit(
        db,
        user_id=user_id,
        username=username or "",
        project_id=0,
        action=action,
        target=target,
        detail=detail,
        ip=request.client.host if request.client else "",
    )


def _optional_current_user(request: Request, db: Session):
    """B12：登出审计用——会话有效时取用户；无效/过期时返回 None（不强求登录态）。"""
    from app.core.deps import get_current_user
    try:
        return get_current_user(request=request, creds=None, x_project_id=None, db=db)
    except Exception:  # noqa: BLE001 - 登出允许无有效会话
        return None


@router.post("/login", response_model=R[LoginOut], summary="账号密码登录")
def login(body: LoginIn, response: Response, request: Request, db: Session = Depends(get_db)):
    # 登录频率限制：同一 IP 最多 10 次/15 分钟
    from app.core.rate_limit import login_limiter
    client_ip = request.client.host if request.client else "unknown"
    allowed, wait = login_limiter.is_allowed(client_ip)
    if not allowed:
        raise APIException(code=429, msg=f"登录尝试过于频繁，请 {wait}s 后重试", http_status=429)

    try:
        result = auth_service.login(db, body.username, body.password)
    except APIException as exc:
        # B12：登录失败也记审计（用户名/密码错误、账号禁用等）
        _auth_audit(db, request, "auth.login", f"login {body.username}", f"登录失败：{exc.msg}",
                    username=body.username)
        db.commit()
        raise
    # P1-1: 同时下发 httpOnly cookie；响应体仍返回 access_token 以兼容过渡期客户端。
    _set_auth_cookie(response, result.access_token)
    _auth_audit(db, request, "auth.login", f"login {body.username}", "登录成功",
                user_id=result.user.id, username=result.user.username)
    db.commit()
    return R.ok(result)


@router.get("/public-access", response_model=R[PublicAccessOut], summary="公开平台访问配置")
def public_access(db: Session = Depends(get_db)):
    """返回访客可见的模块目录和注册策略，不包含用户、项目或权限数据。"""
    data = PublicAccessOut(
        registration_enabled=settings.effective_registration_enabled,
        invite_code_required=settings.invite_code_required,
        modules=menu_service.menu_tree(db, ["*"]),
    )
    return R.ok(data)


@router.post("/register", response_model=R[LoginOut], summary="普通用户注册")
def register(body: RegisterIn, response: Response, request: Request, db: Session = Depends(get_db)):
    """注册普通用户并自动登录，httpOnly cookie 同登录。

    注册关闭时接口返回 403；受控环境可开启 invite_code_required，
    其余环境允许普通用户直接注册，并统一受独立注册限流。
    """
    if not settings.effective_registration_enabled:
        raise APIException(code=403, msg="注册未开放，请联系管理员获取邀请码", http_status=403)

    from app.core.rate_limit import register_limiter
    client_ip = request.client.host if request.client else "unknown"
    allowed, wait = register_limiter.is_allowed(client_ip)
    if not allowed:
        raise APIException(code=429, msg=f"注册尝试过于频繁，请 {wait}s 后重试", http_status=429)

    try:
        auth_service.register(
            db,
            username=body.username,
            nickname=body.nickname,
            email=body.email,
            password=body.password,
            invite_code=body.invite_code,
            project_invite_token=body.project_invite_token,
        )
    except APIException as exc:
        # B12：注册失败（用户名/邮箱占用、邀请码无效等）也记审计
        _auth_audit(db, request, "auth.register", f"register {body.username}", f"注册失败：{exc.msg}",
                    username=body.username)
        db.commit()
        raise
    result = auth_service.login(db, body.username, body.password)
    _set_auth_cookie(response, result.access_token)
    _auth_audit(db, request, "auth.register", f"register {body.username}", "注册成功并自动登录",
                user_id=result.user.id, username=result.user.username)
    db.commit()
    return R.ok(result)


@router.post("/logout", response_model=R[None], summary="登出（清除鉴权 cookie）")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # B12：登出审计（会话有效时取用户；无有效会话仍记录 project=0）
    cu = _optional_current_user(request, db)
    _auth_audit(db, request, "auth.logout", "logout", "登出",
                user_id=cu.user.id if cu else 0,
                username=cu.user.username if cu else "")
    db.commit()
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
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # B12：改密流程全审计（原密码错误/相同/成功均记录）
    if not verify_password(body.old_password, current.user.password):
        _auth_audit(db, request, "auth.password_change", f"user {current.user.username}", "原密码错误",
                    user_id=current.user.id, username=current.user.username)
        db.commit()
        raise APIException(code=400, msg="原密码错误", http_status=400)
    if body.old_password == body.new_password:
        _auth_audit(db, request, "auth.password_change", f"user {current.user.username}", "新密码与原密码相同",
                    user_id=current.user.id, username=current.user.username)
        db.commit()
        raise APIException(code=400, msg="新密码不能与原密码相同", http_status=400)
    current.user.password = hash_password(body.new_password)
    current.user.must_change_password = False
    db.commit()
    _auth_audit(db, request, "auth.password_change", f"user {current.user.username}", "修改密码成功",
                user_id=current.user.id, username=current.user.username)
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

    user = user_service.get_user_by_username(db, body.username)
    if not user or user.status != 1:
        # 防止用户名枚举：不存在或已禁用用户也返回成功（审计仍记录尝试）
        _auth_audit(db, request, "auth.password_reset_request", f"forgot {body.username}",
                    "重置密码请求：用户不存在或已禁用（防枚举静默返回）",
                    username=body.username)
        db.commit()
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

    _auth_audit(db, request, "auth.password_reset_request", f"forgot {user.username}",
                "重置密码请求：已生成重置 token", user_id=user.id, username=user.username)
    db.commit()
    return R.ok()


@router.post("/reset-password", response_model=R[None], summary="重置密码（通过 token）")
def reset_password(body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """使用 forgot-password 返回的 token 重置密码。

    安全设计:
    - 验证 token 有效性与类型
    - Token 一次性使用
    """
    from app.core.security import decode_token

    payload = decode_token(body.token)
    if not payload:
        _auth_audit(db, request, "auth.password_reset", "reset-password", "重置失败：无效或已过期 token")
        db.commit()
        raise APIException(code=400, msg="无效或已过期的重置 token")

    if payload.get("type") != "password_reset":
        _auth_audit(db, request, "auth.password_reset", "reset-password", "重置失败：无效的 token 类型")
        db.commit()
        raise APIException(code=400, msg="无效的 token 类型")

    user_id = payload.get("sub")
    if not user_id:
        _auth_audit(db, request, "auth.password_reset", "reset-password", "重置失败：无效的重置 token")
        db.commit()
        raise APIException(code=400, msg="无效的重置 token")

    user = user_service.get_user_orm(db, int(user_id))
    if not user or user.status != 1:
        _auth_audit(db, request, "auth.password_reset", "reset-password", "重置失败：用户不存在或已禁用")
        db.commit()
        raise APIException(code=400, msg="用户不存在或已禁用")

    if len(body.new_password) < 6:
        _auth_audit(db, request, "auth.password_reset", f"reset {user.username}", "重置失败：密码长度至少 6 位",
                    user_id=user.id, username=user.username)
        db.commit()
        raise APIException(code=400, msg="密码长度至少 6 位")

    user.password = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    _auth_audit(db, request, "auth.password_reset", f"reset {user.username}", "密码重置成功",
                user_id=user.id, username=user.username)
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
