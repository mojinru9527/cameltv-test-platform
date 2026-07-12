"""Add version mission orchestration tables.

Revision ID: 20260705_0011
Revises: 20260703_0010
Create Date: 2026-07-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260705_0011"
down_revision: Union[str, None] = "20260703_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "version_mission",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mission_key", sa.String(), nullable=False, server_default=""),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("version", sa.String(), nullable=False, server_default=""),
        sa.Column("requirement_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("test_env_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("admin_env_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("environment_id", sa.Integer(), nullable=True),
        sa.Column("requirement_doc_id", sa.Integer(), nullable=True),
        sa.Column("test_plan_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("scope", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qa_owner_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "mission_key", name="uq_version_mission_key"),
    )
    op.create_index("ix_version_mission_project_id", "version_mission", ["project_id"])
    op.create_index("ix_version_mission_mission_key", "version_mission", ["mission_key"])
    op.create_index("ix_version_mission_version", "version_mission", ["version"])
    op.create_index("ix_version_mission_status", "version_mission", ["status"])
    op.create_index("ix_version_mission_environment_id", "version_mission", ["environment_id"])
    op.create_index("ix_version_mission_requirement_doc_id", "version_mission", ["requirement_doc_id"])
    op.create_index("ix_version_mission_test_plan_id", "version_mission", ["test_plan_id"])
    op.create_index("ix_version_mission_created_by", "version_mission", ["created_by"])
    op.create_index("ix_version_mission_qa_owner_id", "version_mission", ["qa_owner_id"])

    op.create_table(
        "agent_work_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(), nullable=False, server_default=""),
        sa.Column("agent_name", sa.String(), nullable=False, server_default=""),
        sa.Column("action", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="done"),
        sa.Column("input_ref", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_ref", sa.Text(), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_work_log_project_id", "agent_work_log", ["project_id"])
    op.create_index("ix_agent_work_log_mission_id", "agent_work_log", ["mission_id"])
    op.create_index("ix_agent_work_log_department", "agent_work_log", ["department"])
    op.create_index("ix_agent_work_log_action", "agent_work_log", ["action"])
    op.create_index("ix_agent_work_log_status", "agent_work_log", ["status"])

    op.create_table(
        "generated_artifact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False, server_default=""),
        sa.Column("source", sa.String(), nullable=False, server_default=""),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("ref_id", sa.String(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_generated_artifact_project_id", "generated_artifact", ["project_id"])
    op.create_index("ix_generated_artifact_mission_id", "generated_artifact", ["mission_id"])
    op.create_index("ix_generated_artifact_artifact_type", "generated_artifact", ["artifact_type"])
    op.create_index("ix_generated_artifact_source", "generated_artifact", ["source"])


def downgrade() -> None:
    op.drop_index("ix_generated_artifact_source", table_name="generated_artifact")
    op.drop_index("ix_generated_artifact_artifact_type", table_name="generated_artifact")
    op.drop_index("ix_generated_artifact_mission_id", table_name="generated_artifact")
    op.drop_index("ix_generated_artifact_project_id", table_name="generated_artifact")
    op.drop_table("generated_artifact")

    op.drop_index("ix_agent_work_log_status", table_name="agent_work_log")
    op.drop_index("ix_agent_work_log_action", table_name="agent_work_log")
    op.drop_index("ix_agent_work_log_department", table_name="agent_work_log")
    op.drop_index("ix_agent_work_log_mission_id", table_name="agent_work_log")
    op.drop_index("ix_agent_work_log_project_id", table_name="agent_work_log")
    op.drop_table("agent_work_log")

    op.drop_index("ix_version_mission_qa_owner_id", table_name="version_mission")
    op.drop_index("ix_version_mission_created_by", table_name="version_mission")
    op.drop_index("ix_version_mission_test_plan_id", table_name="version_mission")
    op.drop_index("ix_version_mission_requirement_doc_id", table_name="version_mission")
    op.drop_index("ix_version_mission_environment_id", table_name="version_mission")
    op.drop_index("ix_version_mission_status", table_name="version_mission")
    op.drop_index("ix_version_mission_version", table_name="version_mission")
    op.drop_index("ix_version_mission_mission_key", table_name="version_mission")
    op.drop_index("ix_version_mission_project_id", table_name="version_mission")
    op.drop_table("version_mission")
