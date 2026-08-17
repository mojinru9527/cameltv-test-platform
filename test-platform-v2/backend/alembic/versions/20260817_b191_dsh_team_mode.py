"""batch-191 dsh_task team mode columns (mode / team_json)

/dsh-tasks 支持 AgentTeams 团队模式（B1 方案）：
- dsh_task.mode: single | team（任务形态标签，非状态值；存量行回填 "single"）
- dsh_task.team_json: 团队进度快照（插件 team.json 原文 JSON 字符串，全量幂等覆盖写；
  默认 "{}" 区分「团队模式尚无进度」与「single 模式恒无团队进度」）
- mode 建索引（ix_dsh_task_mode，与 SQLAlchemy index=True 默认命名一致）

SQLite/PG 双兼容：add_column 带 server_default（NOT NULL 列回填存量行）。

幂等守卫（仓库惯例，对齐 20260714_lanhu_evidence_quality_recovery.py）：
AUTO_CREATE_TABLES=true 环境下初始迁移按当前模型 create_all 建表，
dsh_task 可能已含 mode/team_json 列——列/索引存在则跳过，可安全补齐。

Revision ID: 20260817_b191_dsh_team_mode
Revises: 20260816_b182_status_unify
Create Date: 2026-08-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260817_b191_dsh_team_mode"
down_revision = "20260816_b182_status_unify"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]


def _index_exists(conn, table: str, index: str) -> bool:
    insp = sa.inspect(conn)
    return index in [i["name"] for i in insp.get_indexes(table)]


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "dsh_task", "mode"):
        op.add_column(
            "dsh_task",
            sa.Column("mode", sa.String(length=16), server_default="single", nullable=False),
        )
    if not _column_exists(conn, "dsh_task", "team_json"):
        op.add_column(
            "dsh_task",
            sa.Column("team_json", sa.Text(), server_default="{}", nullable=False),
        )
    if not _index_exists(conn, "dsh_task", "ix_dsh_task_mode"):
        op.create_index("ix_dsh_task_mode", "dsh_task", ["mode"])


def downgrade() -> None:
    conn = op.get_bind()
    if _index_exists(conn, "dsh_task", "ix_dsh_task_mode"):
        op.drop_index("ix_dsh_task_mode", table_name="dsh_task")
    if _column_exists(conn, "dsh_task", "team_json"):
        op.drop_column("dsh_task", "team_json")
    if _column_exists(conn, "dsh_task", "mode"):
        op.drop_column("dsh_task", "mode")
