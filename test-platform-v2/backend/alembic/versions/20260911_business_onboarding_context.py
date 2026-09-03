"""Add version and requirement context to business onboarding.

Revision ID: 20260911_business_onboarding_context
Revises: 20260910_version_task_plan_exec_meta
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260911_business_onboarding_context"
down_revision: Union[str, None] = "20260910_version_task_plan_exec_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "business_onboarding" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("business_onboarding")}
    if "version" not in columns:
        op.add_column(
            "business_onboarding",
            sa.Column("version", sa.String(64), nullable=False, server_default=""),
        )
    if "requirement_text" not in columns:
        op.add_column(
            "business_onboarding",
            sa.Column("requirement_text", sa.Text(), nullable=False, server_default=""),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "business_onboarding" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("business_onboarding")}
    if "requirement_text" in columns:
        op.drop_column("business_onboarding", "requirement_text")
    if "version" in columns:
        op.drop_column("business_onboarding", "version")
