"""execution_jobs table (Batch 258 / B1-4)

Revision ID: 20260923_batch258_execution_jobs
Revises: 20260922_ai_agent_token
Create Date: 2026-09-18

新增本地执行节点任务表。与 `ai_jobs` 并列、不合并；租约字段内联，
沿用 AiJob 的 claim/heartbeat/stale 语义（不另建 job_leases 表）。

写迁移前已确认（cameltv-bug-guard）：
  1. `execution_jobs` 表名与全部列名在 alembic/versions 下无既有定义；
  2. DDL 用独立临时 SQLite 走 from-base 与单步 upgrade 校验，未使用 dev 库。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_batch258_execution_jobs"
down_revision: Union[str, None] = "20260922_ai_agent_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_jobs" in set(inspector.get_table_names()):
        return
    op.create_table(
        "execution_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("kind", sa.String(16), nullable=False, server_default=sa.text("'api'"), index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), index=True),
        sa.Column("case_refs_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("env_ref", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default=sa.text("1800")),
        sa.Column("node_id", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("evidence_bundle_id", sa.Integer(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_jobs" in set(inspector.get_table_names()):
        op.drop_table("execution_jobs")
