"""canonical external AI jobs and local agents

Revision ID: 20260921_ai_job_agent
Revises: 20260920_execution_run_runner
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_ai_job_agent"
down_revision: Union[str, None] = "20260920_execution_run_runner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "ai_agents" not in tables:
        op.create_table(
            "ai_agents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("agent_id", sa.String(64), nullable=False, index=True),
            sa.Column("project_scope", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("capabilities_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'online'"), index=True),
            sa.Column("last_health_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("agent_id", name="uq_ai_agent_id"),
        )
    if "ai_jobs" not in tables:
        op.create_table(
            "ai_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("job_type", sa.String(64), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), index=True),
            sa.Column("input_ref", sa.String(512), nullable=False, server_default=sa.text("''")),
            sa.Column("capability", sa.String(128), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("model_hint", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default=sa.text("900")),
            sa.Column("agent_id", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("result_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("summary", sa.Text(), nullable=False, server_default=sa.text("''")),
            sa.Column("evidence_refs_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=sa.text("''")),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "ai_results" not in tables:
        op.create_table(
            "ai_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_id", sa.Integer(), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'completed'")),
            sa.Column("result_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("summary", sa.Text(), nullable=False, server_default=sa.text("''")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in ("ai_results", "ai_jobs", "ai_agents"):
        if table in tables:
            op.drop_table(table)
