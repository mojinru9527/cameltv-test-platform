"""aitde v3.2 data_plans + data_plan_steps

Revision ID: 20260829_aitde_v32_data_plans
Revises: 20260829_aitde_v32_data_requirements
Create Date: 2026-08-29 02:40:00

AITDE V3.2 (V32-003): a data plan declares a strategy (EXISTING / API_BUILDER /
DB_FIXTURE / WORKFLOW) and ordered steps with compensation. The planner never
executes; execute lives with the fixture/runtime (V32-009..V32-014).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v32_data_plans"
down_revision: Union[str, None] = "20260829_aitde_v32_data_requirements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "data_plans" not in inspector.get_table_names():
        op.create_table(
            "data_plans",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=True, index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("environment_id", sa.Integer, nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DRAFT'"), index=True),
            sa.Column("strategy", sa.String(32), nullable=False, server_default=sa.text("'EXISTING'"), index=True),
            sa.Column("plan_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
            sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'USER'")),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("approved_by", sa.Integer, nullable=True),
            sa.Column("approved_at", sa.DateTime, nullable=True),
        )

    if "data_plan_steps" not in inspector.get_table_names():
        op.create_table(
            "data_plan_steps",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("data_plan_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("step_type", sa.String(16), nullable=False, server_default=sa.text("'CREATE'")),
            sa.Column("driver", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("command_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("compensation_json", sa.Text, nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'")),
            sa.UniqueConstraint("data_plan_id", "sequence", name="uq_data_plan_step_seq"),
        )


def downgrade() -> None:
    op.drop_table("data_plan_steps")
    op.drop_table("data_plans")
