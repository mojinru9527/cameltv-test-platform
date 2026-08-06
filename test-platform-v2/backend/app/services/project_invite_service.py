"""项目邀请链接服务（Batch 106：注册即入项目）。"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.project_invite import ProjectInvite


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def create_project_invite(
    db: Session,
    project_id: int,
    created_by: int,
    usage_limit: int = 1,
    expires_at: datetime | None = None,
) -> ProjectInvite:
    invite = ProjectInvite(
        project_id=project_id,
        token=generate_token(),
        created_by=created_by,
        usage_limit=usage_limit,
        used_count=0,
        expires_at=expires_at,
        status=1,
    )
    db.add(invite)
    db.flush()
    return invite


def consume_project_invite(db: Session, token: str) -> ProjectInvite:
    """校验并消耗项目邀请链接；失败抛 400。"""
    if not token or not token.strip():
        raise APIException(code=400, msg="项目邀请链接无效", http_status=400)
    invite = db.scalar(
        select(ProjectInvite).where(ProjectInvite.token == token.strip())
    )
    if not invite or invite.status != 1:
        raise APIException(code=400, msg="项目邀请链接无效", http_status=400)
    if invite.expires_at and invite.expires_at < _now_utc_naive():
        raise APIException(code=400, msg="项目邀请链接已过期", http_status=400)
    if invite.used_count >= invite.usage_limit:
        raise APIException(code=400, msg="项目邀请链接已用尽", http_status=400)
    invite.used_count += 1
    return invite


def list_project_invites(db: Session, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(ProjectInvite)
        .where(ProjectInvite.project_id == project_id)
        .order_by(ProjectInvite.id.desc())
    ).all()
    return [
        {
            "id": inv.id,
            "project_id": inv.project_id,
            "token": inv.token[:4] + "****" + inv.token[-4:],
            "usage_limit": inv.usage_limit,
            "used_count": inv.used_count,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in rows
    ]


def disable_project_invite(db: Session, invite_id: int) -> ProjectInvite | None:
    invite = db.get(ProjectInvite, invite_id)
    if not invite:
        return None
    invite.status = 0
    db.flush()
    return invite
