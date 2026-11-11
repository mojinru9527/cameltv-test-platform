"""M5 / TA-030：learning_candidates + bug_patterns 迁移

Revision ID: 20261122_ta030_learning
Revises: 20261121_ta0273_noise_rules
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261122_ta030_learning"
down_revision = "20261121_ta0273_noise_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "learning_candidates" not in tables:
        op.create_table(
            "learning_candidates",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("rule_json", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="bug"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
            sa.Column("benchmark_json", sa.JSON(), nullable=True),
            sa.Column("duplicate_of", sa.String(length=36), nullable=True),
            sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_learning_candidates_project_id", "learning_candidates", ["project_id"]
        )
    if "bug_patterns" not in tables:
        op.create_table(
            "bug_patterns",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("pattern_key", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("source_candidate_id", sa.String(length=36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("pattern_key", name="uq_bug_patterns_key"),
        )
        op.create_index("ix_bug_patterns_key", "bug_patterns", ["pattern_key"])


def downgrade() -> None:
    op.drop_index("ix_bug_patterns_key", table_name="bug_patterns")
    op.drop_table("bug_patterns")
    op.drop_index("ix_learning_candidates_project_id", table_name="learning_candidates")
    op.drop_table("learning_candidates")
