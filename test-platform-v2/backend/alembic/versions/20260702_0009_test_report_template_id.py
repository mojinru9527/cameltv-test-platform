"""Add template_id column to test_report table for R4 report template feature.

Revision ID: 20260702_0009
Revises: 20260702_0008
Create Date: 2026-07-02

Adds an optional template_id foreign key on test_report to link reports to the
template they were generated with.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260702_0009"
down_revision: Union[str, None] = "20260702_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip if column already exists (e.g. created by ORM auto-create)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing = [c["name"] for c in insp.get_columns("test_report")]
    if "template_id" in existing:
        return
    op.add_column(
        "test_report",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN directly via Alembic in batch mode,
    # but for PG compatibility we keep the drop statement.
    op.drop_column("test_report", "template_id")
