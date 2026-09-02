"""version_task_plan_item tables (Batch 217 / B7)

Revision ID: 20260906_version_task_plan_item
Revises: 20260905_version_task_model
Create Date: 2026-09-06

B7 AI acceptance plan items for VersionTask review panel.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260906_version_task_plan_item"
down_revision: Union[str, None] = "20260905_version_task_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    if "version_task_plan_item" in existing:
        return
    op.create_table(
        "version_task_plan_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("item_type", sa.String(30), nullable=False, server_default="functional", index=True),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_vt_plan_task_status", "version_task_plan_item", ["task_id", "status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "version_task_plan_item" in inspector.get_table_names():
        op.drop_table("version_task_plan_item")
