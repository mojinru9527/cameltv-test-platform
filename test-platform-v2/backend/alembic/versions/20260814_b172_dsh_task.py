"""batch-172 dsh task execution module

Revision ID: 20260814_b172_dsh_task
Revises: 20260813_b167_version_coverage
Create Date: 2026-08-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260814_b172_dsh_task"
down_revision = "20260813_b167_version_coverage"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "dsh_task"):
        return
    op.create_table(
        "dsh_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("task", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("params_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("session_dir", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("operator_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dsh_task_project_id", "dsh_task", ["project_id"])
    op.create_index("ix_dsh_task_status", "dsh_task", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "dsh_task"):
        return
    op.drop_index("ix_dsh_task_status", table_name="dsh_task")
    op.drop_index("ix_dsh_task_project_id", table_name="dsh_task")
    op.drop_table("dsh_task")
