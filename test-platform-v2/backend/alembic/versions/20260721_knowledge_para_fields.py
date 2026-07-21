"""Add para_category, knowledge_domain, freshness_score, last_verified_at to knowledge_source.

Revision ID: 20260721_knowledge_para_fields
Revises: 20260719_requirement_review
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_knowledge_para_fields"
down_revision: Union[str, None] = "20260719_requirement_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns already exist (idempotent)
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("knowledge_source")}

    if "para_category" not in existing:
        op.add_column(
            "knowledge_source",
            sa.Column(
                "para_category", sa.String(), nullable=False, server_default="inbox"
            ),
        )
        op.create_index(
            op.f("ix_knowledge_source_para_category"),
            "knowledge_source",
            ["para_category"],
        )

    if "knowledge_domain" not in existing:
        op.add_column(
            "knowledge_source",
            sa.Column(
                "knowledge_domain", sa.String(), nullable=False, server_default="project"
            ),
        )
        op.create_index(
            op.f("ix_knowledge_source_knowledge_domain"),
            "knowledge_source",
            ["knowledge_domain"],
        )

    if "freshness_score" not in existing:
        op.add_column(
            "knowledge_source",
            sa.Column("freshness_score", sa.Float(), nullable=False, server_default="1.0"),
        )

    if "last_verified_at" not in existing:
        op.add_column(
            "knowledge_source",
            sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("knowledge_source")}

    if "last_verified_at" in existing:
        op.drop_column("knowledge_source", "last_verified_at")
    if "freshness_score" in existing:
        op.drop_column("knowledge_source", "freshness_score")
    if "knowledge_domain" in existing:
        op.drop_index(op.f("ix_knowledge_source_knowledge_domain"), table_name="knowledge_source")
        op.drop_column("knowledge_source", "knowledge_domain")
    if "para_category" in existing:
        op.drop_index(op.f("ix_knowledge_source_para_category"), table_name="knowledge_source")
        op.drop_column("knowledge_source", "para_category")
