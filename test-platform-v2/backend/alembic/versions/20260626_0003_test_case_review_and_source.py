"""add review and source_doc_id columns to test_case

Revision ID: 20260626_0003
Revises: 20260617_0002
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260626_0003"
down_revision = "20260617_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_case", sa.Column("source_doc_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_test_case_source_doc_id"), "test_case", ["source_doc_id"], unique=False)
    op.add_column("test_case", sa.Column("review_status", sa.String(), nullable=False, server_default="draft"))
    op.add_column("test_case", sa.Column("review_comment", sa.String(), nullable=False, server_default=""))
    op.add_column("test_case", sa.Column("reviewer_id", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("test_case", "reviewer_id")
    op.drop_column("test_case", "review_comment")
    op.drop_column("test_case", "review_status")
    op.drop_index(op.f("ix_test_case_source_doc_id"), table_name="test_case")
    op.drop_column("test_case", "source_doc_id")
