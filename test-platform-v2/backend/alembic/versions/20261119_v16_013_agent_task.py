"""V16-013: agent_tasks table

Revision ID: 20261119_v16_013_agent_task
Revises: 20261119_v16_010_learning_gate
Create Date: 2026-11-19 23:25:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_013_agent_task"
down_revision: Union[str, None] = "20261119_v16_010_learning_gate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {item["name"] for item in inspector.get_indexes(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "agent_tasks" not in inspector.get_table_names():
        op.create_table(
        "agent_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=40), nullable=False, server_default="A0_PLAN"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("input_refs_json", sa.JSON(), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("plan_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column(
            "agent_registry_version", sa.String(length=40), nullable=False, server_default=""
        ),
        sa.Column("prompt_version", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("toolset_version", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reason", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("result_refs_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    existing = _index_names("agent_tasks")
    if "ix_agent_tasks_project_id" not in existing:
        op.create_index("ix_agent_tasks_project_id", "agent_tasks", ["project_id"])
    if "ix_agent_tasks_status" not in existing:
        op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])
    if "ix_agent_tasks_run_id" not in existing:
        op.create_index("ix_agent_tasks_run_id", "agent_tasks", ["run_id"])
    if "uq_agent_tasks_idempotency" not in existing:
        op.create_index(
            "uq_agent_tasks_idempotency",
            "agent_tasks",
            ["project_id", "idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "agent_tasks" not in inspector.get_table_names():
        return
    existing = {item["name"] for item in inspector.get_indexes("agent_tasks")}
    for name in (
        "uq_agent_tasks_idempotency",
        "ix_agent_tasks_run_id",
        "ix_agent_tasks_status",
        "ix_agent_tasks_project_id",
    ):
        if name in existing:
            op.drop_index(name, table_name="agent_tasks")
    op.drop_table("agent_tasks")
