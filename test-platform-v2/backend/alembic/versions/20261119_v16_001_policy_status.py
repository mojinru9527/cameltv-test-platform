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
    columns = _columns("aiqe_workflow_definitions")
    if columns and "policy_status" not in columns:
        op.add_column(
            "aiqe_workflow_definitions",
            sa.Column(
                "policy_status",
                sa.String(length=24),
                nullable=False,
                server_default="UNREVIEWED",
            ),
        )
        op.create_index(
            "ix_aiqe_workflow_definitions_policy_status",
            "aiqe_workflow_definitions",
            ["policy_status"],
            unique=False,
        )


def downgrade() -> None:
    columns = _columns("aiqe_workflow_definitions")
    if "policy_status" in columns:
        op.drop_index(
            "ix_aiqe_workflow_definitions_policy_status",
            table_name="aiqe_workflow_definitions",
        )
        op.drop_column("aiqe_workflow_definitions", "policy_status")
