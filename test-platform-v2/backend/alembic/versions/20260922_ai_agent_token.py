"""ai_agent_token table + ai_jobs.model_name (Batch 248)

Revision ID: 20260922_ai_agent_token
Revises: 20260921_ai_job_agent
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_ai_agent_token"
down_revision: Union[str, None] = "20260921_ai_job_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "ai_agent_token" not in tables:
        op.create_table(
            "ai_agent_token",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("agent_id", sa.String(64), nullable=False, index=True),
            sa.Column("name", sa.String(100), nullable=False, server_default=sa.text("''")),
            sa.Column("token_hash", sa.String(64), nullable=False, index=True),
            sa.Column("token_prefix", sa.String(12), nullable=False, server_default=sa.text("''")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"), index=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("token_hash", name="uq_ai_agent_token_hash"),
        )
    columns = {c["name"] for c in inspector.get_columns("ai_jobs")}
    if "model_name" not in columns:
        op.add_column(
            "ai_jobs",
            sa.Column("model_name", sa.String(128), nullable=False, server_default=sa.text("''")),
        )
    if "imported_at" not in columns:
        op.add_column("ai_jobs", sa.Column("imported_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("ai_jobs")}
    if "imported_at" in columns:
        op.drop_column("ai_jobs", "imported_at")
    if "model_name" in columns:
        op.drop_column("ai_jobs", "model_name")
    if "ai_agent_token" in set(inspector.get_table_names()):
        op.drop_table("ai_agent_token")
