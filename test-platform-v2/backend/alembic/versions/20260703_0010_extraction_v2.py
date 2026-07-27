"""Add extraction_state and extraction_progress columns for V2 changelog-driven extraction.

Revision ID: 20260703_0010
Revises: 20260702_0009
Create Date: 2026-07-03

Adds:
- extraction_state (TEXT): JSON continuation token + progress for V2 pipeline
- extraction_progress (REAL): 0.0-1.0 extraction completion percentage
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_0010"
down_revision: Union[str, None] = "20260702_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing = [c["name"] for c in insp.get_columns("requirement_document")]

    if "extraction_state" not in existing:
        op.add_column("requirement_document",
                      sa.Column("extraction_state", sa.Text(), nullable=False, server_default="{}"))
    if "extraction_progress" not in existing:
        op.add_column("requirement_document",
                      sa.Column("extraction_progress", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing = [c["name"] for c in insp.get_columns("requirement_document")]

    if "extraction_state" in existing:
        op.drop_column("requirement_document", "extraction_state")
    if "extraction_progress" in existing:
        op.drop_column("requirement_document", "extraction_progress")
