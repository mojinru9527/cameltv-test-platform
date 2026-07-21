"""Add module_name to knowledge_source for traceability.

Revision ID: 20260721_knowledge_module_name
Revises: 20260721_knowledge_para_fields
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_knowledge_module_name"
down_revision: Union[str, None] = "20260721_knowledge_para_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("knowledge_source")}

    if "module_name" not in existing:
        op.add_column(
            "knowledge_source",
            sa.Column("module_name", sa.String(200), nullable=True),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("knowledge_source")}

    if "module_name" in existing:
        op.drop_column("knowledge_source", "module_name")
