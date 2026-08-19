"""ai_provider 表（项目级 AI 提供方配置）"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260818_ai_provider"
down_revision = "20260817_b191_dsh_team_mode"  # 已核实：迁移链 head（af68b09103f3 是另一条旧链，非 head）
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 幂等守卫（仓库迁移惯例，对齐 b191/batch148）：stamp 回退后重跑 upgrade
    # 时表已存在则跳过，避免 "table ai_provider already exists"。
    conn = op.get_bind()
    if "ai_provider" in sa.inspect(conn).get_table_names():
        return
    op.create_table(
        "ai_provider",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(30), nullable=False, server_default="openai_compatible"),
        sa.Column("api_base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("models", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("default_model", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if "ai_provider" not in sa.inspect(conn).get_table_names():
        return
    op.drop_table("ai_provider")
