"""V16-019: tool execution audits

Revision ID: 20261119_v16_019_tool_audit
Revises: 20261119_v16_013_agent_task
Create Date: 2026-11-19 23:55:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_019_tool_audit"
down_revision: Union[str, None] = "20261119_v16_013_agent_task"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_tool_execution_audits" not in inspector.get_table_names():
        op.create_table(
            "aiqe_tool_execution_audits",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("agent_key", sa.String(length=16), nullable=False, server_default=""),
            sa.Column("task_id", sa.String(length=80), nullable=True),
            sa.Column("tool_name", sa.String(length=80), nullable=False),
            sa.Column("tool_version", sa.String(length=40), nullable=False, server_default=""),
            sa.Column(
                "side_effect_level", sa.String(length=16), nullable=False, server_default="READ"
            ),
            sa.Column("decision", sa.String(length=16), nullable=False, server_default="ALLOW"),
            sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("args_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("args_summary_json", sa.JSON(), nullable=False),
            sa.Column("result_summary_json", sa.JSON(), nullable=False),
            sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    existing = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(
        "aiqe_tool_execution_audits"
    )}
    if "ix_aiqe_tool_execution_audits_project_id" not in existing:
        op.create_index(
            "ix_aiqe_tool_execution_audits_project_id",
            "aiqe_tool_execution_audits",
            ["project_id"],
        )
    if "ix_aiqe_tool_execution_audits_agent_key" not in existing:
        op.create_index(
            "ix_aiqe_tool_execution_audits_agent_key",
            "aiqe_tool_execution_audits",
            ["agent_key"],
        )
    if "ix_aiqe_tool_execution_audits_task_id" not in existing:
        op.create_index(
            "ix_aiqe_tool_execution_audits_task_id",
            "aiqe_tool_execution_audits",
            ["task_id"],
        )
    if "ix_aiqe_tool_execution_audits_tool_name" not in existing:
        op.create_index(
            "ix_aiqe_tool_execution_audits_tool_name",
            "aiqe_tool_execution_audits",
            ["tool_name"],
        )
    if "ix_aiqe_tool_audits_project_tool" not in existing:
        op.create_index(
            "ix_aiqe_tool_audits_project_tool",
            "aiqe_tool_execution_audits",
            ["project_id", "tool_name"],
        )
    if "ix_aiqe_tool_audits_task" not in existing:
        op.create_index(
            "ix_aiqe_tool_audits_task",
            "aiqe_tool_execution_audits",
            ["project_id", "task_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_tool_execution_audits" not in inspector.get_table_names():
        return
    existing = {item["name"] for item in inspector.get_indexes("aiqe_tool_execution_audits")}
    for name in (
        "ix_aiqe_tool_audits_task",
        "ix_aiqe_tool_audits_project_tool",
        "ix_aiqe_tool_execution_audits_tool_name",
        "ix_aiqe_tool_execution_audits_task_id",
        "ix_aiqe_tool_execution_audits_agent_key",
        "ix_aiqe_tool_execution_audits_project_id",
    ):
        if name in existing:
            op.drop_index(name, table_name="aiqe_tool_execution_audits")
    op.drop_table("aiqe_tool_execution_audits")
