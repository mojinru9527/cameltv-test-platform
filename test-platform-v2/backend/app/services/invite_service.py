"""邀请码服务 —— 生成 / 消耗 / 管理（Batch 104 外放轻量模式）。"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.invite_code import InviteCode
from app.models.user import User


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_code() -> str:
    """生成 10 位大写字母数字邀请码（secrets，免字典攻击）。"""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混淆字符
    return "".join(secrets.choice(alphabet) for _ in range(10))


def consume_invite_code(db: Session, code: str) -> InviteCode:
    """校验并消耗一个邀请码；失败抛 400 业务异常。"""
    if not code or not code.strip():
        raise APIException(code=400, msg="请填写邀请码", http_status=400)
    normalized = code.strip().upper()
    invite = db.scalar(select(InviteCode).where(InviteCode.code == normalized))
    if not invite or invite.status != 1:
        raise APIException(code=400, msg="邀请码无效", http_status=400)
    if invite.expires_at and invite.expires_at < _now_utc_naive():
        raise APIException(code=400, msg="邀请码已过期", http_status=400)
    if invite.used_count >= invite.usage_limit:
        raise APIException(code=400, msg="邀请码已用尽", http_status=400)
    invite.used_count += 1
    return invite


def create_invite_code(
    db: Session,
    created_by: int,
    usage_limit: int = 1,
    expires_at: datetime | None = None,
) -> InviteCode:
    invite = InviteCode(
        code=generate_code(),
        created_by=created_by,
        usage_limit=usage_limit,
        used_count=0,
        expires_at=expires_at,
        status=1,
    )
    db.add(invite)
    db.flush()
    return invite


def list_invite_codes(db: Session) -> list[dict]:
    rows = db.execute(
        select(InviteCode, User)
        .join(User, User.id == InviteCode.created_by, isouter=True)
        .order_by(InviteCode.id.desc())
    ).all()
    return [
        {
            "id": inv.id,
            "code": inv.code,
            "created_by": inv.created_by,
            "created_by_name": u.nickname or u.username if u else "",
            "usage_limit": inv.usage_limit,
            "used_count": inv.used_count,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv, u in rows
    ]


def disable_invite_code(db: Session, invite_id: int) -> InviteCode | None:
    invite = db.get(InviteCode, invite_id)
    if not invite:
        return None
    invite.status = 0
    db.flush()
    return invite
