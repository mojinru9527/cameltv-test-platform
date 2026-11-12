"""M6 / TA-033：mutation_ledger 迁移

Revision ID: 20261123_ta033_mutation_ledger
Revises: 20261122_ta030_learning
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261123_ta033_mutation_ledger"
down_revision = "20261122_ta030_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "mutation_ledger" in inspector.get_table_names():
        return
    op.create_table(
        "mutation_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_mutation_ledger_key"),
    )
    op.create_index("ix_mutation_ledger_key", "mutation_ledger", ["key"])


def downgrade() -> None:
    op.drop_index("ix_mutation_ledger_key", table_name="mutation_ledger")
    op.drop_table("mutation_ledger")
