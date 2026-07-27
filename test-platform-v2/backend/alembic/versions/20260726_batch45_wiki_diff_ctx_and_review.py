"""batch-45: WikiDiffItem 补 left/right ref+scope + WikiReviewItem/Contradiction 表

Revision ID: 20260726_batch45
Revises: af68b09103f3
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260726_batch45'
down_revision: Union[str, None] = 'af68b09103f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── WikiDiffItem: add left/right ref + scope columns ──
    inspector = sa.inspect(op.get_bind())
    existing_cols = {c["name"] for c in inspector.get_columns("wiki_diff_item")}
    for col_name in ("left_ref", "right_ref", "left_scope", "right_scope"):
        if col_name not in existing_cols:
            op.add_column("wiki_diff_item", sa.Column(col_name, sa.Text(), nullable=False, server_default=""))

    # ── WikiReviewItem ──
    op.create_table(
        "wiki_review_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), index=True, nullable=False),
        sa.Column("item_id", sa.Integer(), index=True, nullable=False),
        sa.Column("project_id", sa.Integer(), index=True, nullable=False),
        sa.Column("reviewer", sa.String(100), nullable=False, server_default=""),
        sa.Column("decision", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── WikiReviewContradiction ──
    op.create_table(
        "wiki_review_contradiction",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), index=True, nullable=False),
        sa.Column("item_a_id", sa.Integer(), nullable=False),
        sa.Column("item_b_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), index=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved_by", sa.String(100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # ── Drop new tables first (FK-safe order) ──
    op.drop_table("wiki_review_contradiction")
    op.drop_table("wiki_review_item")

    # ── Drop added columns ──
    for col_name in ("right_scope", "left_scope", "right_ref", "left_ref"):
        op.drop_column("wiki_diff_item", col_name)
