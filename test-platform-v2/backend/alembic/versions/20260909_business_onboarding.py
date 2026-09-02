# business_onboarding tables (Batch 225 / B15)
# Revision ID: 20260909_business_onboarding
# Revises: 20260908_version_knowledge_record
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260909_business_onboarding"
down_revision: Union[str, None] = "20260908_version_knowledge_record"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "business_onboarding" in inspector.get_table_names():
        return
    op.create_table(
        "business_onboarding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("service_key", sa.String(120), nullable=False, server_default="", index=True),
        sa.Column("api_spec_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version_task_id", sa.Integer(), nullable=True, index=True),
        sa.Column("baseline", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "business_onboarding" in inspector.get_table_names():
        op.drop_table("business_onboarding")
