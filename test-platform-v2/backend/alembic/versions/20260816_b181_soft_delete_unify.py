"""batch-181 soft-delete unification (FIX-173-P2-08)

知识域软删语义由 status=deprecated 统一为 is_deleted 布尔：
- knowledge_source / knowledge_chunk 新增 is_deleted 列（server_default=0）
- 存量 deprecated/superseded 数据幂等回填 is_deleted=1
- status 列保留（历史生命周期值展示），新代码不再产生 deprecated 值

Revision ID: 20260816_b181_soft_delete_unify
Revises: 20260816_b181_task_queue_locks
Create Date: 2026-08-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260816_b181_soft_delete_unify"
down_revision = "20260816_b181_task_queue_locks"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _has_col(bind, table: str, col: str) -> bool:
    if not _has_table(bind, table):
        return True
    try:
        columns = sa.inspect(bind).get_columns(table)
    except sa.exc.NoSuchTableError:
        return True
    return col in {c["name"] for c in columns}


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "knowledge_source") and not _has_col(bind, "knowledge_source", "is_deleted"):
        op.add_column(
            "knowledge_source",
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_table(bind, "knowledge_chunk") and not _has_col(bind, "knowledge_chunk", "is_deleted"):
        op.add_column(
            "knowledge_chunk",
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    # 幂等回填：历史 deprecated/superseded → is_deleted=1
    # 注意：PG 不隐式转换 integer→boolean（SET is_deleted = 1 会 DatatypeMismatch），
    # 必须用 TRUE/FALSE 字面量（SQLite 两者均可）
    if _has_table(bind, "knowledge_source") and _has_col(bind, "knowledge_source", "status"):
        op.execute(
            sa.text(
                "UPDATE knowledge_source SET is_deleted = TRUE "
                "WHERE status IN ('deprecated', 'superseded')"
            )
        )
    if _has_table(bind, "knowledge_chunk") and _has_col(bind, "knowledge_chunk", "status"):
        op.execute(
            sa.text("UPDATE knowledge_chunk SET is_deleted = TRUE WHERE status = 'deprecated'")
        )


def _is_deleted_indexes(bind, table: str) -> list[str]:
    """Indexes that reference the is_deleted column on ``table``."""
    if not _has_table(bind, table):
        return []
    names = []
    for idx in sa.inspect(bind).get_indexes(table):
        if not idx.get("name"):
            continue
        # column_names may be a list; SQLite/PostgreSQL both expose it.
        if "is_deleted" in (idx.get("column_names") or []):
            names.append(idx["name"])
    return names


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("knowledge_source", "knowledge_chunk"):
        if not (_has_table(bind, table) and _has_col(bind, table, "is_deleted")):
            continue
        # SQLite refuses ``DROP COLUMN`` while any index still references the
        # column, so drop the is_deleted index(es) first (see
        # knowledge_para_fields.downgrade for the established pattern).
        for index_name in _is_deleted_indexes(bind, table):
            op.drop_index(index_name, table_name=table)
        op.drop_column(table, "is_deleted")
