"""batch-181 task queue lock columns (FIX-173-P2-06)

Revision ID: 20260816_b181_task_queue_locks
Revises: 20260814_b172_dsh_task
Create Date: 2026-08-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260816_b181_task_queue_locks"
down_revision = "20260814_b172_dsh_task"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _has_col(bind, table: str, col: str) -> bool:
    if not _has_table(bind, table):
        return True  # 表不存在按「列已存在」处理，跳过该表
    try:
        columns = sa.inspect(bind).get_columns(table)
    except sa.exc.NoSuchTableError:
        return True
    return col in {c["name"] for c in columns}


def _add_col(table: str, col, *, drop_first: bool = False) -> None:
    """仅当表存在且列缺失时添加列（stamped 增量链场景安全）。"""
    bind = op.get_bind()
    if not _has_table(bind, table):
        return
    if _has_col(bind, table, col.name):
        return
    op.add_column(table, col)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "ai_task"):
        _add_col("ai_task", sa.Column("locked_by", sa.String(length=64), nullable=False, server_default=""))
    if _has_table(bind, "dsh_task"):
        _add_col("dsh_task", sa.Column("locked_at", sa.DateTime(), nullable=True))
        _add_col("dsh_task", sa.Column("locked_by", sa.String(length=64), nullable=False, server_default=""))
    if _has_table(bind, "agent_queue_item"):
        _add_col("agent_queue_item", sa.Column("locked_at", sa.DateTime(), nullable=True))
        _add_col("agent_queue_item", sa.Column("locked_by", sa.String(length=64), nullable=False, server_default=""))
    if _has_table(bind, "ui_test_run"):
        _add_col("ui_test_run", sa.Column("locked_at", sa.DateTime(), nullable=True))
        _add_col("ui_test_run", sa.Column("locked_by", sa.String(length=64), nullable=False, server_default=""))
    if _has_table(bind, "lanhu_evidence_job"):
        _add_col("lanhu_evidence_job", sa.Column("locked_by", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    bind = op.get_bind()
    for table, cols in (
        ("ai_task", ("locked_by",)),
        ("dsh_task", ("locked_at", "locked_by")),
        ("agent_queue_item", ("locked_at", "locked_by")),
        ("ui_test_run", ("locked_at", "locked_by")),
        ("lanhu_evidence_job", ("locked_by",)),
    ):
        if not _has_table(bind, table):
            continue
        for col in cols:
            if _has_col(bind, table, col):
                op.drop_column(table, col)
