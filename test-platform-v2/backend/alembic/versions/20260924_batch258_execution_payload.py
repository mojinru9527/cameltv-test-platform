"""execution_jobs.payload_json (Batch 258 / B1-5)

Revision ID: 20260924_batch258_execution_payload
Revises: 20260923_batch258_execution_jobs
Create Date: 2026-09-18

节点认领任务后需要拿到**可执行载荷**（用例列表）。载荷在登记任务时随 body 写入，
由节点用节点令牌拉取（`GET /execution-jobs/{id}/payload`）。

为什么单列一条迁移而不是改上一条：上一条迁移对已存在的表直接 return，
若把新列塞进去，任何已升级到 `20260923_batch258_execution_jobs` 的库都会漏列。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_batch258_execution_payload"
down_revision: Union[str, None] = "20260923_batch258_execution_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_jobs" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("execution_jobs")}
    if "payload_json" not in columns:
        op.add_column(
            "execution_jobs",
            sa.Column("payload_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_jobs" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("execution_jobs")}
    if "payload_json" in columns:
        op.drop_column("execution_jobs", "payload_json")
