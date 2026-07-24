"""Generic CRUD helpers — pagination, batch lookups, soft-delete.

All functions are pure and session-explicit (no class state),
so they work with any SQLAlchemy model without inheritance coupling.
"""
from __future__ import annotations

from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User

T = TypeVar("T")


# ── Pagination ──────────────────────────────────────────

def paginate(
    db: Session,
    stmt,
    *,
    page: int = 1,
    page_size: int = 20,
    scalar: bool = True,
) -> tuple[list, int]:
    """Execute a paginated query, returning (rows, total_count).

    Args:
        db: SQLAlchemy session.
        stmt: A SELECT statement (with filters already applied).
              Do NOT include ORDER BY / OFFSET / LIMIT — they are added here.
        page: 1-indexed page number.
        page_size: Items per page (clamped 1-500).
        scalar: If True, call .scalars().all(); else .all() for multi-column results.

    Returns:
        (list of rows, total count matching the unfiltered query).
    """
    page_size = max(1, min(page_size, 500))
    offset = max(0, (page - 1) * page_size)

    # Count — strip any ORDER BY from the subquery
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0

    # Page
    paged = stmt.offset(offset).limit(page_size)
    rows = (db.scalars(paged).all() if scalar else db.execute(paged).all())  # type: ignore[union-attr]

    return rows, total


def resolve_order(stmt, order_by):
    """Apply a list of order criteria to a statement.

    Usage: stmt = resolve_order(base, [Model.created_at.desc(), Model.id])
    """
    if order_by:
        return stmt.order_by(*order_by)
    return stmt


# ── Batch name lookups (avoid N+1) ─────────────────────

def batch_user_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    """Return {user_id: display_name} for a set of user ids.

    Uses a single query; display_name = nickname or username.
    """
    if not user_ids:
        return {}
    # Exclude 0 (the "unassigned" sentinel)
    ids = {uid for uid in user_ids if uid and uid > 0}
    if not ids:
        return {}
    rows = db.execute(
        select(User.id, User.nickname, User.username).where(User.id.in_(ids))
    ).all()
    return {row.id: (row.nickname or row.username) for row in rows}


def batch_field_map(
    db: Session,
    model,
    ids: set[int],
    field: str = "title",
) -> dict[int, str]:
    """Return {id: field_value} for a set of model ids. Generic batch lookup.

    Example: batch_field_map(db, TestCase, case_ids, "title") → {case_id: title}
    """
    if not ids:
        return {}
    ids = {i for i in ids if i and i > 0}
    if not ids:
        return {}
    col_id = getattr(model, "id")
    col_field = getattr(model, field)
    rows = db.execute(select(col_id, col_field).where(col_id.in_(ids))).all()
    return {row[0]: row[1] for row in rows}


# ── Soft delete (status-based) ─────────────────────────

def soft_delete_status(db: Session, model, obj_id: int, *, project_id: int | None = None) -> bool:
    """Set status=0 on a model row (must have .status and .id attrs)."""
    filters = {model.id == obj_id}
    if project_id is not None:
        filters[model.project_id == project_id]  # type: ignore[index]
    obj = db.scalar(select(model).filter_by(**filters))
    if not obj:
        return False
    obj.status = 0
    db.flush()
    return True


# ── Transaction helpers ────────────────────────────────

from contextlib import contextmanager


@contextmanager
def transaction(db: Session):
    """Context manager: commit on success, rollback on exception.

    Usage:
        with transaction(db):
            create_case(db, ...)
            create_case(db, ...)
            # All or nothing.
    """
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
