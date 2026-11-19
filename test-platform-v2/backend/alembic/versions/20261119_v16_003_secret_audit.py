"""V16-003: secret handle metadata + access audit

Revision ID: 20261119_v16_003_secret_audit
Revises: 20261119_v16_001_policy_status
Create Date: 2026-11-19 20:35:00

- `aiqe_secret_handles` 增加 V16-003 元信息：
  secret_type / key_version / rotation_version / consumer_scope_json /
  last_accessed_at / access_count / access_audit_id；
- 新增 `aiqe_secret_access_audits`：Handle 解析成功/拒绝审计。

迁移可重复执行（inspect 守卫）；downgrade 幂等。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_003_secret_audit"
down_revision: Union[str, None] = "20261119_v16_001_policy_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HANDLE_COLUMNS: tuple[tuple[str, sa.types.TypeEngine, dict], ...] = (
    ("secret_type", sa.String(length=32), {"nullable": False, "server_default": "generic"}),
    ("key_version", sa.Integer(), {"nullable": False, "server_default": "1"}),
    ("rotation_version", sa.Integer(), {"nullable": False, "server_default": "1"}),
    ("consumer_scope_json", sa.JSON(), {"nullable": True}),
    ("last_accessed_at", sa.DateTime(timezone=True), {"nullable": True}),
    ("access_count", sa.Integer(), {"nullable": False, "server_default": "0"}),
    ("access_audit_id", sa.String(length=36), {"nullable": True}),
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    columns = _columns("aiqe_secret_handles")
    if columns:
        for name, column_type, kwargs in HANDLE_COLUMNS:
            if name not in columns:
                op.add_column("aiqe_secret_handles", sa.Column(name, column_type, **kwargs))

    inspector = sa.inspect(op.get_bind())
    if "aiqe_secret_access_audits" not in inspector.get_table_names():
        op.create_table(
            "aiqe_secret_access_audits",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("handle_id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=36), nullable=False),
            sa.Column("consumer_node_key", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("decision", sa.String(length=16), nullable=False),
            sa.Column("reason_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column(
                "requested_by_actor",
                sa.String(length=120),
                nullable=False,
                server_default="worker",
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_aiqe_secret_access_audits_handle",
            "aiqe_secret_access_audits",
            ["handle_id", "created_at"],
        )
        op.create_index(
            "ix_aiqe_secret_access_audits_scope",
            "aiqe_secret_access_audits",
            ["project_id", "run_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_secret_access_audits" in inspector.get_table_names():
        op.drop_index(
            "ix_aiqe_secret_access_audits_scope", table_name="aiqe_secret_access_audits"
        )
        op.drop_index(
            "ix_aiqe_secret_access_audits_handle", table_name="aiqe_secret_access_audits"
        )
        op.drop_table("aiqe_secret_access_audits")
    columns = _columns("aiqe_secret_handles")
    for name, _type, _kwargs in HANDLE_COLUMNS:
        if name in columns:
            op.drop_column("aiqe_secret_handles", name)
