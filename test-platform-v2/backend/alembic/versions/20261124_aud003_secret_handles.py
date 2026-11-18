"""AUD-003：aiqe_secret_handles（Secret Handle 元信息）

Revision ID: 20261124_aud003_secret_handles
Revises: 20261124_aud004_experiment_run_binding
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud003_secret_handles"
down_revision = "20261124_aud004_experiment_run_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_secret_handles" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_secret_handles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("producer_node_run_id", sa.String(length=36), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=False),
        sa.Column("key_name", sa.String(length=120), nullable=False),
        sa.Column("allowed_consumer_nodes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["producer_node_run_id"], ["node_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aiqe_secret_handles_project_id", "aiqe_secret_handles", ["project_id"])
    op.create_index("ix_aiqe_secret_handles_run_id", "aiqe_secret_handles", ["run_id"])
    op.create_index(
        "ix_aiqe_secret_handles_producer_node_run_id",
        "aiqe_secret_handles",
        ["producer_node_run_id"],
    )
    op.create_index(
        "ix_aiqe_secret_handles_scope",
        "aiqe_secret_handles",
        ["project_id", "run_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_aiqe_secret_handles_scope", table_name="aiqe_secret_handles")
    op.drop_index(
        "ix_aiqe_secret_handles_producer_node_run_id", table_name="aiqe_secret_handles"
    )
    op.drop_index("ix_aiqe_secret_handles_run_id", table_name="aiqe_secret_handles")
    op.drop_index("ix_aiqe_secret_handles_project_id", table_name="aiqe_secret_handles")
    op.drop_table("aiqe_secret_handles")
