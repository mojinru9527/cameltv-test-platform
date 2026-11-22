"""V16-001: workflow policy migration marker (policy_status)

Revision ID: 20261119_v16_001_policy_status
Revises: 20261125_merge_aud_v15_pr595
Create Date: 2026-11-19 19:10:00

为 `aiqe_workflow_definitions` 增加 `policy_status`：
- UNREVIEWED：尚未核对旧字段（allowed_hosts / allow_private / allowed_tables / query_registry）；
- MIGRATED：旧字段已迁入服务端 TargetPolicy，Workflow 不再参与授权决策；
- NEEDS_POLICY_REVIEW：无法自动映射，禁止调度，必须管理员人工配置策略。

迁移本身只加列，可重复执行；downgrade 幂等。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_001_policy_status"
down_revision: Union[str, None] = "20261125_merge_aud_v15_pr595"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    # 兼容历史表名 aiqe_workflow_definitions 与当前 ORM 表 workflow_definitions。
    for table, index_name in (
        ("aiqe_workflow_definitions", "ix_aiqe_workflow_definitions_policy_status"),
        ("workflow_definitions", "ix_workflow_definitions_policy_status"),
    ):
        columns = _columns(table)
        if columns and "policy_status" not in columns:
            op.add_column(
                table,
                sa.Column(
                    "policy_status",
                    sa.String(length=24),
                    nullable=False,
                    server_default="UNREVIEWED",
                ),
            )
            op.create_index(index_name, table, ["policy_status"], unique=False)


def downgrade() -> None:
    for table, index_name in (
        ("aiqe_workflow_definitions", "ix_aiqe_workflow_definitions_policy_status"),
        ("workflow_definitions", "ix_workflow_definitions_policy_status"),
    ):
        columns = _columns(table)
        if "policy_status" in columns:
            op.drop_index(index_name, table_name=table)
            op.drop_column(table, "policy_status")
