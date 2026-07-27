"""审计日志 —— 写入 + 分页查询。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session, *,
    user_id: int = 0, username: str = "",
    project_id: int = 0, action: str = "",
    target: str = "", detail: str = "", ip: str = "",
) -> None:
    db.add(AuditLog(
        user_id=user_id, username=username, project_id=project_id,
        action=action, target=target, detail=detail, ip=ip,
        created_at=datetime.now(),
    ))
    db.flush()


def list_audit(
    db: Session,
    action: str = "", keyword: str = "",
    project_id: int | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[AuditLog], int]:
    q = select(AuditLog)
    cnt_q = select(func.count(AuditLog.id))

    if action:
        q = q.where(AuditLog.action == action)
        cnt_q = cnt_q.where(AuditLog.action == action)
    if keyword:
        kw = f"%{keyword}%"
        f_kw = AuditLog.target.like(kw) | AuditLog.username.like(kw)
        q = q.where(f_kw)
        cnt_q = cnt_q.where(f_kw)
    if project_id is not None:
        q = q.where(AuditLog.project_id == project_id)
        cnt_q = cnt_q.where(AuditLog.project_id == project_id)

    total = db.scalar(cnt_q) or 0
    rows = list(
        db.scalars(
            q.order_by(AuditLog.id.desc()).limit(limit).offset(offset),
        ).all()
    )
    return rows, total
