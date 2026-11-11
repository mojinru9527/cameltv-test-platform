"""M2 / TA-015：node_capability_manifests 迁移

Revision ID: 20261115_ta015_capability_manifests
Revises: 20261114_ta010_workflow_scheduler
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261115_ta015_capability_manifests"
down_revision = "20261114_ta010_workflow_scheduler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "node_capability_manifests" in inspector.get_table_names():
        return
    op.create_table(
        "node_capability_manifests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("driver_key", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("driver_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("capabilities_json", sa.JSON(), nullable=True),
        sa.Column("platforms_json", sa.JSON(), nullable=True),
        sa.Column(
            "max_parallel_sessions", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("artifact_types_json", sa.JSON(), nullable=True),
        sa.Column("last_evidence_ref", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", name="uq_node_capability_node"),
    )
    op.create_index(
        "ix_node_capability_manifests_node_id", "node_capability_manifests", ["node_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_node_capability_manifests_node_id", table_name="node_capability_manifests"
    )
    op.drop_table("node_capability_manifests")
