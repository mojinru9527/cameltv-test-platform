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


def export_audit_csv(
    db: Session,
    action: str = "", keyword: str = "",
    project_id: int | None = None,
    max_rows: int = 10000,
) -> str:
    """导出审计日志为 CSV 字符串。"""
    import csv
    import io

    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if keyword:
        kw = f"%{keyword}%"
        q = q.where(AuditLog.target.like(kw) | AuditLog.username.like(kw))
    if project_id is not None:
        q = q.where(AuditLog.project_id == project_id)

    rows = list(db.scalars(q.order_by(AuditLog.id.desc()).limit(max_rows)).all())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "用户ID", "用户名", "项目ID", "操作", "目标", "详情", "IP", "时间"])
    for r in rows:
        writer.writerow([
            r.id, r.user_id, r.username, r.project_id,
            r.action, r.target, r.detail, r.ip,
            r.created_at.isoformat() if r.created_at else "",
        ])
    return buf.getvalue()
