"""M4 / TA-027.3：noise_rules 迁移

Revision ID: 20261121_ta0273_noise_rules
Revises: 20261120_ta027_defect_regressions
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261121_ta0273_noise_rules"
down_revision = "20261120_ta027_defect_regressions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "noise_rules" in inspector.get_table_names():
        return
    op.create_table(
        "noise_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False, server_default="suppress"),
        sa.Column("scope", sa.String(length=20), nullable=False, server_default="run"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("ix_noise_rules_project_id", "noise_rules", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_noise_rules_project_id", table_name="noise_rules")
    op.drop_table("noise_rules")
