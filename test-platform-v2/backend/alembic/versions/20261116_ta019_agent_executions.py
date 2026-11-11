"""M3 / TA-019：agent_executions 迁移

Revision ID: 20261116_ta019_agent_executions
Revises: 20261115_ta015_capability_manifests
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261116_ta019_agent_executions"
down_revision = "20261115_ta015_capability_manifests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_executions" in inspector.get_table_names():
        return
    op.create_table(
        "agent_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("agent_key", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("model", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("input_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_executions_project_id", "agent_executions", ["project_id"])
    op.create_index("ix_agent_executions_run_id", "agent_executions", ["run_id"])
    op.create_index("ix_agent_executions_agent_key", "agent_executions", ["agent_key"])


def downgrade() -> None:
    op.drop_index("ix_agent_executions_agent_key", table_name="agent_executions")
    op.drop_index("ix_agent_executions_run_id", table_name="agent_executions")
    op.drop_index("ix_agent_executions_project_id", table_name="agent_executions")
    op.drop_table("agent_executions")
