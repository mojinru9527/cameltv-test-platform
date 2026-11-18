"""AUD-020：Platform Binding 表

Revision ID: 20261124_aud020_platform_binding
Revises: 20261124_aud018_benchmark
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud020_platform_binding"
down_revision = "20261124_aud018_benchmark"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_platform_bindings" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_platform_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=8), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("platform_id", sa.String(length=40), nullable=False),
        sa.Column("os_version", sa.String(length=80), nullable=False),
        sa.Column("browser_or_app_version", sa.String(length=80), nullable=False),
        sa.Column("device_model", sa.String(length=80), nullable=False),
        sa.Column("driver_name", sa.String(length=80), nullable=False),
        sa.Column("driver_version", sa.String(length=40), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("capability_status", sa.String(length=20), nullable=False),
        sa.Column("test_profile", sa.String(length=80), nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "target_type",
            "target_id",
            "platform_id",
            name="uq_aiqe_platform_binding_target",
        ),
    )
    op.create_index(
        "ix_aiqe_platform_bindings_project_id", "aiqe_platform_bindings", ["project_id"]
    )
    op.create_index(
        "ix_aiqe_platform_bindings_target_id", "aiqe_platform_bindings", ["target_id"]
    )
    op.create_index(
        "ix_aiqe_platform_bindings_platform_id", "aiqe_platform_bindings", ["platform_id"]
    )
    op.create_index(
        "ix_aiqe_platform_bindings_capability_status",
        "aiqe_platform_bindings",
        ["capability_status"],
    )
    op.create_index(
        "ix_aiqe_platform_bindings_project_platform",
        "aiqe_platform_bindings",
        ["project_id", "platform_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_platform_bindings" in inspector.get_table_names():
        op.drop_table("aiqe_platform_bindings")
