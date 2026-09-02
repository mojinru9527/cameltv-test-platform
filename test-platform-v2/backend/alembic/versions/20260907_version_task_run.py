"""version_task_run tables (Batch 218 / B8)

Revision ID: 20260907_version_task_run
Revises: 20260906_version_task_plan_item
Create Date: 2026-09-07

B8 execution run record with progress / coverage / evidence / failure classification.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260907_version_task_run"
down_revision: Union[str, None] = "20260906_version_task_plan_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "version_task_run" in inspector.get_table_names():
        return
    op.create_table(
        "version_task_run",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("failures", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_version_task_run_task_status", "version_task_run", ["task_id", "status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "version_task_run" in inspector.get_table_names():
        op.drop_table("version_task_run")
