"""V16-005: execution job idempotency columns

Revision ID: 20261119_v16_005_job_idempotency
Revises: 20261119_v16_004_query_registry
Create Date: 2026-11-19 21:40:00

为 `execution_jobs` 增加 AIQE 幂等字段：
- run_id / node_run_id / execution_kind / idempotency_key；
- 唯一索引 (run_id, node_run_id, attempt, execution_kind)：
  重复投递/重复 dispatch 不得产生第二个副作用 Job；
- run/node 组合索引与 project+idempotency_key 索引。

旧的非 AIQE Job 这些列为 NULL，唯一索引允许多个 NULL（SQLite/PG 行为一致）。
可重复执行；downgrade 先删索引再删列（SQLite 限制）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_005_job_idempotency"
down_revision: Union[str, None] = "20261119_v16_004_query_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS: tuple[tuple[str, sa.types.TypeEngine, dict], ...] = (
    ("run_id", sa.String(length=36), {"nullable": True}),
    ("node_run_id", sa.String(length=36), {"nullable": True}),
    ("execution_kind", sa.String(length=32), {"nullable": False, "server_default": "NORMAL"}),
    ("idempotency_key", sa.String(length=160), {"nullable": True}),
)
INDEXES = (
    "uq_execution_jobs_idempotency_key",
    "ix_execution_jobs_attempt_kind",
    "ix_execution_jobs_run_node",
    "ix_execution_jobs_idempotency",
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def _index_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {item["name"] for item in inspector.get_indexes(table)}


def upgrade() -> None:
    columns = _columns("execution_jobs")
    if columns:
        for name, column_type, kwargs in COLUMNS:
            if name not in columns:
                op.add_column("execution_jobs", sa.Column(name, column_type, **kwargs))
    existing = _index_names("execution_jobs")
    # 早期实现曾用 (run,node,attempt,kind) 唯一索引；attempt 在 claim 时 +1 会与
    # 重试冲突，改为 idempotency_key 唯一（本迁移未发布，直接替换即可）。
    for legacy in ("uq_execution_jobs_attempt_kind",):
        if legacy in existing:
            op.drop_index(legacy, table_name="execution_jobs")
    if "uq_execution_jobs_idempotency_key" not in existing:
        op.create_index(
            "uq_execution_jobs_idempotency_key",
            "execution_jobs",
            ["idempotency_key"],
            unique=True,
        )
    if "ix_execution_jobs_attempt_kind" not in existing:
        op.create_index(
            "ix_execution_jobs_attempt_kind",
            "execution_jobs",
            ["run_id", "node_run_id", "attempt", "execution_kind"],
        )
    if "ix_execution_jobs_run_node" not in existing:
        op.create_index(
            "ix_execution_jobs_run_node", "execution_jobs", ["run_id", "node_run_id"]
        )
    if "ix_execution_jobs_idempotency" not in existing:
        op.create_index(
            "ix_execution_jobs_idempotency",
            "execution_jobs",
            ["project_id", "idempotency_key"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_jobs" in inspector.get_table_names():
        new_columns = {name for name, _type, _kwargs in COLUMNS}
        # 初始迁移用 Base.metadata.create_all 建表时可能已带列级索引；
        # SQLite 不允许在有索引时 DROP COLUMN，必须先删所有引用新列的索引。
        for index in inspector.get_indexes("execution_jobs"):
            index_columns = {str(item) for item in (index.get("column_names") or [])}
            if index_columns & new_columns:
                op.drop_index(index["name"], table_name="execution_jobs")
    columns = _columns("execution_jobs")
    for name, _type, _kwargs in COLUMNS:
        if name in columns:
            op.drop_column("execution_jobs", name)
