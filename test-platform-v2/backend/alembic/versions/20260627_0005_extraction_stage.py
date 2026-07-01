"""Add extraction stage columns to requirement_document

Revision ID: 20260627_0005
Revises: 20260626_0004
Create Date: 2026-06-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260627_0005"
down_revision = "20260626_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "requirement_document",
        sa.Column("extraction_raw", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "requirement_document",
        sa.Column("extraction_status", sa.String(30), nullable=False, server_default="not_started"),
    )


def downgrade() -> None:
    op.drop_column("requirement_document", "extraction_status")
    op.drop_column("requirement_document", "extraction_raw")
