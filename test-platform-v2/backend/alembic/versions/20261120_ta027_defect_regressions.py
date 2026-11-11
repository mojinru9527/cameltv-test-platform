"""M4 / TA-027：defect_regressions 迁移

Revision ID: 20261120_ta027_defect_regressions
Revises: 20261119_ta026_defect_aiqe_link
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261120_ta027_defect_regressions"
down_revision = "20261119_ta026_defect_aiqe_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "defect_regressions" in inspector.get_table_names():
        return
    op.create_table(
        "defect_regressions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defect_id", sa.Integer(), nullable=False),
        sa.Column("fixed_sha", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("previous_run_id", sa.String(length=36), nullable=True),
        sa.Column("verification_run_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["defect_id"], ["defect.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defect_regressions_defect_id", "defect_regressions", ["defect_id"])
    op.create_index(
        "ix_defect_regressions_verification_run", "defect_regressions", ["verification_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_defect_regressions_verification_run", table_name="defect_regressions")
    op.drop_index("ix_defect_regressions_defect_id", table_name="defect_regressions")
    op.drop_table("defect_regressions")
