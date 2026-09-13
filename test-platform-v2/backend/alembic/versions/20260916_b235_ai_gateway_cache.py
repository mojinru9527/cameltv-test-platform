"""Batch 235: persistent exact-response cache for AI gateway.

Revision ID: 20260916_b235_ai_gateway_cache
Revises: 20260915_plan_dispatch
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_b235_ai_gateway_cache"
down_revision: Union[str, None] = "20260915_plan_dispatch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_response_cache" in inspector.get_table_names():
        return
    op.create_table(
        "ai_response_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("namespace", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("cache_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("provider_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("input_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("response_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("usage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("finish_reason", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("cache_key", name="uq_ai_response_cache_cache_key"),
        if_not_exists=True,
    )
    for column in ("project_id", "namespace", "cache_key", "provider_id", "expires_at"):
        op.create_index(
            f"ix_ai_response_cache_{column}",
            "ai_response_cache",
            [column],
            if_not_exists=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_response_cache" not in inspector.get_table_names():
        return
    for column in ("project_id", "namespace", "cache_key", "provider_id", "expires_at"):
        op.drop_index(
            f"ix_ai_response_cache_{column}",
            table_name="ai_response_cache",
            if_exists=True,
        )
    op.drop_table("ai_response_cache")
