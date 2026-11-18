"""AUD-001：aiqe_target_policies（服务端目标访问策略）

Revision ID: 20261124_aud001_target_policy
Revises: 20261123_ta033_mutation_ledger
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud001_target_policy"
down_revision = "20261123_ta033_mutation_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_target_policies" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_target_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("environment_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["environment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["sys_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "environment_id",
            "name",
            "version",
            name="uq_aiqe_target_policies_scope_version",
        ),
    )
    op.create_index(
        "ix_aiqe_target_policies_project_id", "aiqe_target_policies", ["project_id"]
    )
    op.create_index(
        "ix_aiqe_target_policies_environment_id", "aiqe_target_policies", ["environment_id"]
    )
    op.create_index(
        "ix_aiqe_target_policies_project_active",
        "aiqe_target_policies",
        ["project_id", "active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aiqe_target_policies_project_active", table_name="aiqe_target_policies"
    )
    op.drop_index(
        "ix_aiqe_target_policies_environment_id", table_name="aiqe_target_policies"
    )
    op.drop_index("ix_aiqe_target_policies_project_id", table_name="aiqe_target_policies")
    op.drop_table("aiqe_target_policies")
