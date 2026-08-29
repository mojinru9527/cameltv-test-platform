"""aitde v3.2 data_sources

Revision ID: 20260829_aitde_v32_data_sources
Revises: 20260829_aitde_v31_m31_4
Create Date: 2026-08-29 02:00:00

AITDE V3.2 (V32-001): introduce data_sources — a typed, policy-constrained
connection (static / mysql / postgres / api / workflow) that the V3.2 data
runtime provisions data through. Only secret_ref (the reference) is stored;
the secret value is never persisted here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v32_data_sources"
down_revision: Union[str, None] = "20260829_aitde_v31_m31_4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent for fresh (create_all) + incremental upgrades.
    inspector = sa.inspect(op.get_bind())
    if "data_sources" in inspector.get_table_names():
        return

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("environment_id", sa.Integer, nullable=True, index=True),
        sa.Column("source_type", sa.String(32), nullable=False, server_default=sa.text("'STATIC'"), index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("network_zone", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("secret_ref", sa.String(255), nullable=True),
        sa.Column("access_mode", sa.String(32), nullable=False, server_default=sa.text("'READONLY'"), index=True),
        sa.Column("config_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("policy_ref", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("data_sources")
