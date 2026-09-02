"""version_knowledge_record tables (Batch 221 / B11)

Revision ID: 20260908_version_knowledge_record
Revises: 20260907_version_task_run
Create Date: 2026-09-08

B11 version knowledge record auto-sedimented on release.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260908_version_knowledge_record"
down_revision: Union[str, None] = "20260907_version_task_run"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "version_knowledge_record" in inspector.get_table_names():
        return
    op.create_table(
        "version_knowledge_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("version", sa.String(80), nullable=False, server_default="", index=True),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("coverage", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("verdict", sa.String(20), nullable=False, server_default="", index=True),
        sa.Column("risk", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("plan_summary", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("defect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "version_knowledge_record" in inspector.get_table_names():
        op.drop_table("version_knowledge_record")
