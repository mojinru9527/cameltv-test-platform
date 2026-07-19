"""Add requirement_review table for persistent AI-generated test case review queue.

Revision ID: 20260719_requirement_review
Revises: 20260716_case_cleanup
Create Date: 2026-07-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_requirement_review"
down_revision: Union[str, None] = "20260716_case_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())

    if "requirement_review" in existing:
        return

    op.create_table(
        "requirement_review",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "requirement_id",
            sa.Integer(),
            sa.ForeignKey("requirement_document.id"),
            index=True,
        ),
        sa.Column("case_index", sa.Integer(), server_default="0"),
        sa.Column("case_type", sa.String(10), server_default="func"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("edited_data", sa.Text(), server_default="{}"),
        sa.Column("reviewer_id", sa.Integer(), server_default="0"),
        sa.Column("reviewed_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("requirement_review")
