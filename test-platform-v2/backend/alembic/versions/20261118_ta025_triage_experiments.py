"""M3 / TA-025：triage_experiments 迁移

Revision ID: 20261118_ta025_triage_experiments
Revises: 20261117_ta022_execution_profiles
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261118_ta025_triage_experiments"
down_revision = "20261117_ta022_execution_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "triage_experiments" in inspector.get_table_names():
        return
    op.create_table(
        "triage_experiments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("triage_case_id", sa.String(length=36), nullable=True),
        sa.Column("hypothesis_id", sa.String(length=36), nullable=True),
        sa.Column("experiment_key", sa.String(length=8), nullable=False),
        sa.Column("changed_variable", sa.String(length=128), nullable=False),
        sa.Column("changed_value", sa.String(length=255), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("verification_run_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="completed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["execution_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_triage_experiments_idempotency"),
    )
    op.create_index("ix_triage_experiments_experiment_key", "triage_experiments", ["experiment_key"])
    op.create_index("ix_triage_experiments_triage_case_id", "triage_experiments", ["triage_case_id"])
    op.create_index("ix_triage_experiments_verification_run", "triage_experiments", ["verification_run_id"])


def downgrade() -> None:
    op.drop_index("ix_triage_experiments_verification_run", table_name="triage_experiments")
    op.drop_index("ix_triage_experiments_triage_case_id", table_name="triage_experiments")
    op.drop_index("ix_triage_experiments_experiment_key", table_name="triage_experiments")
    op.drop_table("triage_experiments")
