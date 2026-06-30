"""Defect service — list / get / create / update / delete / stats / transitions / comments."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_field_map, batch_user_names, paginate
from app.models.defect import Defect, DefectComment, DefectTransition
from app.models.test_case import TestCase
from app.models.user import User


def _generate_defect_id(db: Session, project_id: int) -> str:
    """Generate DEF-YYYYMMDD-NNN unique within project."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(Defect.id)).where(
            Defect.project_id == project_id,
            Defect.defect_id.like(f"DEF-{today}-%"),
        )
    ) or 0
    return f"DEF-{today}-{count + 1:03d}"


def _defect_to_dict(r: Defect, creator_name: str = "", assignee_name: str = "", case_title: str = "") -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "defect_id": r.defect_id,
        "title": r.title,
        "description": r.description,
        "severity": r.severity,
        "status": r.status,
        "case_id": r.case_id,
        "execution_id": r.execution_id,
        "assignee_id": r.assignee_id,
        "external_id": r.external_id,
        "external_url": r.external_url,
        "creator_id": r.creator_id,
        "resolved_at": r.resolved_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "creator_name": creator_name,
        "assignee_name": assignee_name,
        "case_title": case_title,
    }


def list_defects(
    db: Session,
    project_id: int,
    severity: str | None = None,
    status: str | None = None,
    assignee_id: int | None = None,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """Paginated defect list — batch-loaded names (no N+1)."""
    base = select(Defect).where(Defect.project_id == project_id)
    if severity:
        base = base.where(Defect.severity == severity)
    if status:
        base = base.where(Defect.status == status)
    if assignee_id is not None:
        base = base.where(Defect.assignee_id == assignee_id)
    if keyword:
        base = base.where(Defect.title.contains(keyword))

    rows, total = paginate(db, base.order_by(Defect.created_at.desc()), page=page, page_size=page_size)

    # Batch load all referenced users and cases in two queries (was N+1 per row)
    creator_ids = {r.creator_id for r in rows}
    assignee_ids = {r.assignee_id for r in rows}
    all_user_ids = creator_ids | assignee_ids
    case_ids = {r.case_id for r in rows if r.case_id}

    user_map = batch_user_names(db, all_user_ids)
    case_map = batch_field_map(db, TestCase, case_ids, "title")

    items = [
        _defect_to_dict(
            r,
            creator_name=user_map.get(r.creator_id, ""),
            assignee_name=user_map.get(r.assignee_id, ""),
            case_title=case_map.get(r.case_id, "") if r.case_id else "",
        )
        for r in rows
    ]
    return items, total


def get_defect(db: Session, defect_id: int, project_id: int) -> dict | None:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return None

    creator_name = ""
    assignee_name = ""
    case_title = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    if r.assignee_id:
        u = db.get(User, r.assignee_id)
        if u:
            assignee_name = u.nickname or u.username
    if r.case_id:
        tc = db.get(TestCase, r.case_id)
        if tc:
            case_title = tc.title
    return _defect_to_dict(r, creator_name, assignee_name, case_title)


def create_defect(db: Session, data, creator_id: int, project_id: int) -> dict:
    defect_id = _generate_defect_id(db, project_id)
    r = Defect(
        project_id=project_id,
        defect_id=defect_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        status="open",
        case_id=data.case_id,
        execution_id=data.execution_id,
        assignee_id=data.assignee_id,
        external_id=data.external_id,
        external_url=data.external_url,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    return _defect_to_dict(r)


def update_defect(db: Session, defect_id: int, data, project_id: int) -> dict | None:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return None

    update_fields = [
        "title", "description", "severity", "status",
        "case_id", "execution_id", "assignee_id",
        "external_id", "external_url", "resolved_at",
    ]
    update_data = data.model_dump(exclude_none=True)
    for k in update_fields:
        if k in update_data:
            setattr(r, k, update_data[k])

    # Auto-set resolved_at when transitioning to resolved/closed
    if "status" in update_data and update_data["status"] in ("resolved", "closed", "wontfix"):
        if not r.resolved_at:
            r.resolved_at = datetime.now(timezone.utc)

    db.flush()
    db.refresh(r)

    creator_name = ""
    assignee_name = ""
    case_title = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    if r.assignee_id:
        u = db.get(User, r.assignee_id)
        if u:
            assignee_name = u.nickname or u.username
    if r.case_id:
        tc = db.get(TestCase, r.case_id)
        if tc:
            case_title = tc.title
    return _defect_to_dict(r, creator_name, assignee_name, case_title)


def delete_defect(db: Session, defect_id: int, project_id: int) -> bool:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True


def get_defect_stats(db: Session, project_id: int) -> dict:
    rows = db.execute(
        select(Defect.severity, Defect.status)
        .where(Defect.project_id == project_id)
    ).all()

    total = len(rows)
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for sev, st in rows:
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1

    return {"total": total, "by_severity": by_severity, "by_status": by_status}


# ── State machine ─────────────────────────────────────

# Allowed transitions: from → {to}
_TRANSITIONS: dict[str, set[str]] = {
    "open":           {"confirmed", "rejected"},
    "confirmed":      {"fixing", "rejected"},
    "fixing":         {"pending_review", "rejected"},
    "pending_review": {"closed", "fixing"},
    "closed":         {"open"},          # reopen
    "rejected":       {"open"},          # reopen
}

# Human-readable labels
_STATUS_LABELS: dict[str, str] = {
    "open": "新建", "confirmed": "已确认", "fixing": "修复中",
    "pending_review": "待回归", "closed": "已关闭", "rejected": "已拒绝",
}

# Old status mapping for backward compatibility
_LEGACY_MAP: dict[str, str] = {
    "in_progress": "fixing",
    "resolved": "closed",
    "wontfix": "rejected",
}


def allowed_transitions(status: str) -> list[str]:
    """Return list of statuses that can be transitioned to from the given status."""
    # Normalize legacy statuses
    current = _LEGACY_MAP.get(status, status)
    return sorted(_TRANSITIONS.get(current, set()))


def transition_defect(
    db: Session,
    defect_id: int,
    to_status: str,
    *,
    project_id: int,
    operator_id: int = 0,
    operator_name: str = "",
    comment: str = "",
) -> dict | None:
    """Transition a defect to a new status, validating the state machine.

    Returns the updated defect dict or None if defect not found.
    Raises ValueError for invalid transitions.
    """
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return None

    current = _LEGACY_MAP.get(r.status, r.status)
    valid = _TRANSITIONS.get(current, set())

    if to_status not in valid:
        labels = ", ".join(f"{s}({_STATUS_LABELS.get(s, s)})" for s in sorted(valid))
        raise ValueError(
            f"不允许从「{_STATUS_LABELS.get(current, current)}」"
            f"转为「{_STATUS_LABELS.get(to_status, to_status)}」。"
            f"允许的流转: {labels}"
        )

    from_status = r.status
    r.status = to_status

    # Auto-set resolved_at on close, clear on reopen
    if to_status == "closed":
        r.resolved_at = datetime.now(timezone.utc)
    elif to_status == "open" and current in ("closed", "rejected"):
        r.resolved_at = None

    # Record transition
    t = DefectTransition(
        defect_id=defect_id,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        operator_id=operator_id,
        operator_name=operator_name,
    )
    db.add(t)
    db.flush()
    db.refresh(r)

    return _defect_to_dict(r)


def get_transitions(db: Session, defect_id: int, project_id: int) -> list[dict]:
    """Get transition history for a defect (ordered by time asc)."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return []
    return [
        {
            "id": t.id,
            "from_status": t.from_status,
            "from_label": _STATUS_LABELS.get(t.from_status, t.from_status),
            "to_status": t.to_status,
            "to_label": _STATUS_LABELS.get(t.to_status, t.to_status),
            "comment": t.comment,
            "operator_id": t.operator_id,
            "operator_name": t.operator_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in r.transitions
    ]


# ── Comments ──────────────────────────────────────────

def list_comments(db: Session, defect_id: int, project_id: int) -> list[dict]:
    """List comments for a defect."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return []
    rows = db.scalars(
        select(DefectComment).where(DefectComment.defect_id == defect_id)
        .order_by(DefectComment.created_at.asc())
    ).all()
    return [
        {
            "id": c.id, "defect_id": c.defect_id,
            "content": c.content, "author_id": c.author_id,
            "author_name": c.author_name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]


def create_comment(
    db: Session, defect_id: int, content: str,
    *, project_id: int, author_id: int = 0, author_name: str = "",
) -> dict | None:
    """Add a comment to a defect."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return None
    c = DefectComment(
        defect_id=defect_id, content=content,
        author_id=author_id, author_name=author_name,
    )
    db.add(c)
    db.flush()
    return {
        "id": c.id, "defect_id": c.defect_id,
        "content": c.content, "author_id": c.author_id,
        "author_name": c.author_name,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
