"""M2 / TA-010：workflow_definitions + resource_locks 迁移

Revision ID: 20261114_ta010_workflow_scheduler
Revises: 20261113_ta007_run_artifacts
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261114_ta010_workflow_scheduler"
down_revision = "20261113_ta007_run_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "workflow_definitions" not in tables:
        op.create_table(
            "workflow_definitions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("scenario_id", sa.Integer(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("graph_json", sa.JSON(), nullable=True),
            sa.Column("schema_version", sa.String(length=20), nullable=False, server_default="1.0"),
            sa.Column("checksum", sa.String(length=128), nullable=False, server_default=""),
            sa.Column(
                "validation_status", sa.String(length=16), nullable=False, server_default="draft"
            ),
            sa.Column(
                "approval_status", sa.String(length=16), nullable=False, server_default="pending"
            ),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["scenario_id"], ["test_scenarios.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approved_by"], ["sys_user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scenario_id", "version", name="uq_workflow_scenario_version"),
        )

    if "resource_locks" not in tables:
        op.create_table(
            "resource_locks",
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("owner_id", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("fencing_token", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("key"),
        )


def downgrade() -> None:
    op.drop_table("resource_locks")
    op.drop_table("workflow_definitions")
