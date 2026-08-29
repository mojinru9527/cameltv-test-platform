"""aitde v3.2 data_requirements

Revision ID: 20260829_aitde_v32_data_requirements
Revises: 20260829_aitde_v32_data_sources
Create Date: 2026-08-29 02:20:00

AITDE V3.2 (V32-002): data_requirements captures a scenario's declared business
data needs (entity_type + constraints_json) bound to a frozen ScenarioVersion.
Requirement is business only — never SQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v32_data_requirements"
down_revision: Union[str, None] = "20260829_aitde_v32_data_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "data_requirements" in inspector.get_table_names():
        return

    op.create_table(
        "data_requirements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("requirement_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("entity_type", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("constraints_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("required", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("sharing_policy", sa.String(32), nullable=False, server_default=sa.text("'EXCLUSIVE'")),
        sa.Column("cleanup_policy", sa.String(32), nullable=False, server_default=sa.text("'ALWAYS'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("scenario_version_id", "requirement_key", name="uq_data_req_scenario_key"),
    )


def downgrade() -> None:
    op.drop_table("data_requirements")
