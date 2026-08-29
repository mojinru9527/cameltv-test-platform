"""aitde v3.1 M31-1: scenario_adapters + environment_snapshots

Revision ID: 20260829_aitde_v31_m31_1
Revises: 20260829_aitde_ai_ops
Create Date: 2026-08-29 00:30:00

AITDE V3.1 (V31-001): introduce ScenarioAdapter (bind a ScenarioVersion to an
existing API/UI asset or future Runtime Adapter) and EnvironmentSnapshot (the
environment fingerprint every ExecutionRun binds to).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v31_m31_1"
down_revision: Union[str, None] = "20260829_aitde_ai_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "scenario_adapters" not in inspector.get_table_names():
        op.create_table(
            "scenario_adapters",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("adapter_type", sa.String(16), nullable=False, server_default=sa.text("'API'"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DRAFT'"), index=True),
            sa.Column("source_asset_type", sa.String(64), nullable=True),
            sa.Column("source_asset_id", sa.Integer, nullable=True),
            sa.Column("config_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("adapter_version", sa.String(64), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("updated_at", sa.DateTime, nullable=True),
            # SQLite has no ALTER ADD CONSTRAINT: define UNIQUE inline at CREATE TABLE.
            sa.UniqueConstraint(
                "scenario_version_id", "adapter_type", "adapter_version",
                name="uq_scenario_adapter_version_type",
            ),
        )

    if "environment_snapshots" not in inspector.get_table_names():
        op.create_table(
            "environment_snapshots",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("build_label", sa.String(128), nullable=True),
            sa.Column("frontend_version", sa.String(64), nullable=True),
            sa.Column("service_versions_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("openapi_hash", sa.String(64), nullable=True),
            sa.Column("db_schema_version", sa.String(64), nullable=True),
            sa.Column("config_hash", sa.String(64), nullable=True),
            sa.Column("static_asset_hash", sa.String(64), nullable=True),
            sa.Column("manual_note", sa.Text, nullable=True),
            sa.Column("fingerprint_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("captured_at", sa.DateTime, nullable=True),
            sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'AUTO'")),
        )


def downgrade() -> None:
    op.drop_table("environment_snapshots")
    op.drop_table("scenario_adapters")
