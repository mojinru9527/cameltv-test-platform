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


def _column_names() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("test_case")}


def _index_names() -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("test_case")
        if index.get("name")
    }


def upgrade() -> None:
    # The initial migration intentionally calls current ``Base.metadata.create_all``.
    # On a fresh database that may already include these later model fields, so this
    # historical migration must be additive and idempotent.
    columns = _column_names()
    if "source_doc_id" not in columns:
        op.add_column("test_case", sa.Column("source_doc_id", sa.Integer(), nullable=True))
    if "review_status" not in columns:
        op.add_column("test_case", sa.Column("review_status", sa.String(), nullable=False, server_default="draft"))
    if "review_comment" not in columns:
        op.add_column("test_case", sa.Column("review_comment", sa.String(), nullable=False, server_default=""))
    if "reviewer_id" not in columns:
        op.add_column("test_case", sa.Column("reviewer_id", sa.Integer(), nullable=False, server_default="0"))

    index_name = op.f("ix_test_case_source_doc_id")
    if index_name not in _index_names():
        op.create_index(index_name, "test_case", ["source_doc_id"], unique=False)


def downgrade() -> None:
    op.drop_column("test_case", "reviewer_id")
    op.drop_column("test_case", "review_comment")
    op.drop_column("test_case", "review_status")
    op.drop_index(op.f("ix_test_case_source_doc_id"), table_name="test_case")
    op.drop_column("test_case", "source_doc_id")
