"""aitde v3 ai_operation_records

Revision ID: 20260829_aitde_ai_ops
Revises: 20260829_aitde_scenario
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-07 / V30-080): introduce ai_operation_records for structured AI
operation auditing (never chain-of-thought).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_ai_ops"
down_revision: Union[str, None] = "20260829_aitde_scenario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_operation_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("operation_type", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'QUEUED'"), index=True),
        sa.Column("model_provider", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("model_name", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("model_config_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("prompt_version", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("input_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("output_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
        sa.Column("result_ref_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_code", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("error_message", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("token_usage_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ai_operation_records")
