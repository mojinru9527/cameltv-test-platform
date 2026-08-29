"""aitde v3.3 command_plans + command_plan_versions

Revision ID: 20260829_aitde_v33_command_plans
Revises: 20260829_aitde_v32_data_fixtures
Create Date: 2026-08-29 18:00:00

AITDE V3.3 (V33-002): versioned Command IR plans. ACTIVE versions are immutable;
a new version supersedes (staleness) the previous ACTIVE one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v33_command_plans"
down_revision: Union[str, None] = "20260829_aitde_v32_data_fixtures"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "command_plans" not in inspector.get_table_names():
        op.create_table(
            "command_plans",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("current_version_no", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )

    if "command_plan_versions" not in inspector.get_table_names():
        op.create_table(
            "command_plan_versions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("command_plan_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("version_no", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("contract_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("schema_version", sa.String(16), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("plan_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("plan_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DRAFT'"), index=True),
            sa.Column("generated_by_type", sa.String(16), nullable=False, server_default=sa.text("'AI'")),
            sa.Column("model_ref", sa.String(255), nullable=True),
            sa.Column("prompt_version", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("approved_by", sa.Integer, nullable=True),
            sa.Column("approved_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("command_plan_id", "version_no", name="uq_command_plan_version"),
        )


def downgrade() -> None:
    op.drop_table("command_plan_versions")
    op.drop_table("command_plans")
