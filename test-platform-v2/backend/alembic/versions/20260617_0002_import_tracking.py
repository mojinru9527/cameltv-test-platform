"""add import tracking columns per case type

Revision ID: 20260617_0002
Revises: 20260616_0001
Create Date: 2026-06-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260617_0002"
down_revision = "20260616_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip if columns already exist (e.g. created by ORM auto-create with AUTO_CREATE_TABLES)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing = [c["name"] for c in insp.get_columns("requirement_document")]
    if "imported_func_count" not in existing:
        op.add_column("requirement_document", sa.Column("imported_func_count", sa.Integer(), nullable=False, server_default="0"))
    if "imported_api_count" not in existing:
        op.add_column("requirement_document", sa.Column("imported_api_count", sa.Integer(), nullable=False, server_default="0"))
    if "imported_func_indices" not in existing:
        op.add_column("requirement_document", sa.Column("imported_func_indices", sa.String(), nullable=False, server_default="[]"))
    if "imported_api_indices" not in existing:
        op.add_column("requirement_document", sa.Column("imported_api_indices", sa.String(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("requirement_document", "imported_api_indices")
    op.drop_column("requirement_document", "imported_func_indices")
    op.drop_column("requirement_document", "imported_api_count")
    op.drop_column("requirement_document", "imported_func_count")
