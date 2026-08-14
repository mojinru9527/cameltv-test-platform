"""batch-182 execution status vocabulary unification (FIX-173-P1-06)

统一词表：pending | running | passed | failed | skipped | cancelled | blocked

| 表.列 | 映射 |
|-------|------|
| test_execution.status | pass→passed, fail→failed, skip→skipped, block→blocked |
| test_plan_case.last_status | 同上 |
| api_execution_task.status | success→passed |
| ui_test_run.status | done→passed, fail→failed |
| ui_test_job.status | idle→pending, done→passed, fail→failed |
| test_schedule_run.status | completed→passed |

api_execution_task_item.status 已是规范词表（passed/failed/skipped），无需迁移。

Revision ID: 20260816_b182_status_unify
Revises: 20260816_b181_soft_delete_unify
Create Date: 2026-08-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260816_b182_status_unify"
down_revision = "20260816_b181_soft_delete_unify"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _has_col(bind, table: str, col: str) -> bool:
    if not _has_table(bind, table):
        return False
    try:
        columns = sa.inspect(bind).get_columns(table)
    except sa.exc.NoSuchTableError:
        return False
    return col in {c["name"] for c in columns}


def _remap(table: str, col: str, mapping: dict[str, str]) -> None:
    bind = op.get_bind()
    if not _has_table(bind, table) or not _has_col(bind, table, col):
        return
    for old, new in mapping.items():
        op.execute(
            sa.text(
                f"UPDATE {table} SET {col} = :new WHERE {col} = :old"
            ).bindparams(new=new, old=old)
        )


def upgrade() -> None:
    exec_map = {"pass": "passed", "fail": "failed", "skip": "skipped", "block": "blocked"}
    _remap("test_execution", "status", exec_map)
    _remap("test_plan_case", "last_status", exec_map)
    _remap("api_execution_task", "status", {"success": "passed"})
    _remap("ui_test_run", "status", {"done": "passed", "fail": "failed"})
    _remap("ui_test_job", "status", {"idle": "pending", "done": "passed", "fail": "failed"})
    _remap("test_schedule_run", "status", {"completed": "passed"})


def downgrade() -> None:
    exec_map = {"passed": "pass", "failed": "fail", "skipped": "skip", "blocked": "block"}
    _remap("test_execution", "status", exec_map)
    _remap("test_plan_case", "last_status", exec_map)
    _remap("api_execution_task", "status", {"passed": "success"})
    _remap("ui_test_run", "status", {"passed": "done", "failed": "fail"})
    _remap("ui_test_job", "status", {"pending": "idle", "passed": "done", "failed": "fail"})
    _remap("test_schedule_run", "status", {"passed": "completed"})
