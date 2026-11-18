"""AUD-002：aiqe_registered_queries（登记式只读查询模板）

Revision ID: 20261124_aud002_query_registry
Revises: 20261124_aud003_secret_handles
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud002_query_registry"
down_revision = "20261124_aud003_secret_handles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_registered_queries" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_registered_queries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("query_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("project_scope", sa.String(length=32), nullable=False),
        sa.Column("connection_ref", sa.String(length=80), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("allowed_params", sa.JSON(), nullable=False),
        sa.Column("max_rows", sa.Integer(), nullable=False),
        sa.Column("max_execution_ms", sa.Integer(), nullable=False),
        sa.Column("result_schema", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["sys_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["sys_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "query_key", "version", name="uq_aiqe_registered_queries_key_version"
        ),
    )
    op.create_index(
        "ix_aiqe_registered_queries_project_id", "aiqe_registered_queries", ["project_id"]
    )
    op.create_index(
        "ix_aiqe_registered_queries_query_key", "aiqe_registered_queries", ["query_key"]
    )
    op.create_index(
        "ix_aiqe_registered_queries_project_key",
        "aiqe_registered_queries",
        ["project_id", "query_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aiqe_registered_queries_project_key", table_name="aiqe_registered_queries"
    )
    op.drop_index("ix_aiqe_registered_queries_query_key", table_name="aiqe_registered_queries")
    op.drop_index(
        "ix_aiqe_registered_queries_project_id", table_name="aiqe_registered_queries"
    )
    op.drop_table("aiqe_registered_queries")
