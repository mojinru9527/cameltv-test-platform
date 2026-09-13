"""Batch 236: persist local-model shadow comparisons.

Revision ID: 20260917_b236_ai_shadow_run
Revises: 20260916_b235_ai_gateway_cache
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260917_b236_ai_shadow_run"
down_revision: Union[str, None] = "20260916_b235_ai_gateway_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_shadow_run" in inspector.get_table_names():
        return
    op.create_table(
        "ai_shadow_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("namespace", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("input_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("json_mode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("primary_provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("primary_model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("shadow_provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("shadow_model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("primary_content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("shadow_content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("primary_json_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shadow_json_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exact_match", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("primary_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shadow_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("length_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_usage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("shadow_usage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        if_not_exists=True,
    )
    for column in ("project_id", "namespace", "status", "input_hash"):
        op.create_index(
            f"ix_ai_shadow_run_{column}",
            "ai_shadow_run",
            [column],
            if_not_exists=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_shadow_run" not in inspector.get_table_names():
        return
    for column in ("project_id", "namespace", "status", "input_hash"):
        op.drop_index(f"ix_ai_shadow_run_{column}", table_name="ai_shadow_run", if_exists=True)
    op.drop_table("ai_shadow_run")
