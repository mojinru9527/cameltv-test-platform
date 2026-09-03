"""version_task_plan_item.exec_meta (Batch F-02 / B8)

Adds an ``exec_meta`` JSON Text column carrying optional executable metadata
(method / path / url / assertion) so adopted plan items can be *really* executed
instead of producing fabricated PASS/FAIL. NULL/{} = not executable yet.

Revision ID: 20260910_version_task_plan_exec_meta
Revises: 20260909_business_onboarding
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260910_version_task_plan_exec_meta"
down_revision: Union[str, None] = "20260909_business_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("version_task_plan_item")}
    if "exec_meta" not in cols and "version_task_plan_item" in inspector.get_table_names():
        op.add_column(
            "version_task_plan_item",
            sa.Column("exec_meta", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("version_task_plan_item")}
    if "exec_meta" in cols and "version_task_plan_item" in inspector.get_table_names():
        op.drop_column("version_task_plan_item", "exec_meta")
