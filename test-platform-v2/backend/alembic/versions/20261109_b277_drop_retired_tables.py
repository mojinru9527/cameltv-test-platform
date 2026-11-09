"""Batch 277 P0-5: drop retired AI cache/shadow tables (ai_response_cache / ai_shadow_run).

ai-gateway 服务已删除，控制面直连项目级 provider；两张表不再有任何读写方。
DROP 带存在性守卫（inspector + ``if_exists``），downgrade 可完整重建表结构，
满足 13 号 §0 P0-2「可升可降」。

Revision ID: 20261109_b277_drop_retired_tables
Revises: 20261007_platform_simplification_drop_tables
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261109_b277_drop_retired_tables"
down_revision: Union[str, None] = "20261007_platform_simplification_drop_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CACHE_INDEXES = ("project_id", "namespace", "cache_key", "provider_id", "expires_at")
SHADOW_INDEXES = ("project_id", "namespace", "status", "input_hash")


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    names = _table_names()
    if "ai_response_cache" in names:
        for column in CACHE_INDEXES:
            op.execute(f"DROP INDEX IF EXISTS ix_ai_response_cache_{column}")
        op.execute("DROP TABLE IF EXISTS ai_response_cache")
    if "ai_shadow_run" in names:
        for column in SHADOW_INDEXES:
            op.execute(f"DROP INDEX IF EXISTS ix_ai_shadow_run_{column}")
        op.execute("DROP TABLE IF EXISTS ai_shadow_run")


def downgrade() -> None:
    names = _table_names()
    if "ai_response_cache" not in names:
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
        for column in CACHE_INDEXES:
            op.create_index(
                f"ix_ai_response_cache_{column}",
                "ai_response_cache",
                [column],
                if_not_exists=True,
            )
    if "ai_shadow_run" not in names:
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
        for column in SHADOW_INDEXES:
            op.create_index(
                f"ix_ai_shadow_run_{column}",
                "ai_shadow_run",
                [column],
                if_not_exists=True,
            )
