"""M3 / TA-022：execution_profiles 迁移

Revision ID: 20261117_ta022_execution_profiles
Revises: 20261116_ta019_agent_executions
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261117_ta022_execution_profiles"
down_revision = "20261116_ta019_agent_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "execution_profiles" in inspector.get_table_names():
        return
    op.create_table(
        "execution_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checksum", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(
            "approval_status", sa.String(length=16), nullable=False, server_default="pending"
        ),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["sys_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_profiles_project_id", "execution_profiles", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_execution_profiles_project_id", table_name="execution_profiles")
    op.drop_table("execution_profiles")
