"""V16-014-R2: case catalog for impact-to-scope mapping

Revision ID: 20261120_v16_014_catalog
Revises: 20261119_v16_016_platform
Create Date: 2026-11-20 00:20:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_v16_014_catalog"
down_revision: Union[str, None] = "20261119_v16_016_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_case_catalog" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_case_catalog",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("sys_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("node_key", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("workflow_id", sa.String(length=36), nullable=True),
        sa.Column("route", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("symbol", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("api_operation", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "case_id", name="uq_aiqe_case_catalog_case"),
    )
    op.create_index("ix_aiqe_case_catalog_project_id", "aiqe_case_catalog", ["project_id"])
    op.create_index("ix_aiqe_case_catalog_workflow_id", "aiqe_case_catalog", ["workflow_id"])
    op.create_index(
        "ix_aiqe_case_catalog_project_node", "aiqe_case_catalog", ["project_id", "node_key"]
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_case_catalog" not in inspector.get_table_names():
        return
    for name in (
        "ix_aiqe_case_catalog_project_node",
        "ix_aiqe_case_catalog_workflow_id",
        "ix_aiqe_case_catalog_project_id",
    ):
        op.drop_index(name, table_name="aiqe_case_catalog")
    op.drop_table("aiqe_case_catalog")
