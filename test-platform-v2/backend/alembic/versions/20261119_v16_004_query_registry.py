"""V16-004: query registry hardening (allowed tables / env / hash / audit)

Revision ID: 20261119_v16_004_query_registry
Revises: 20261119_v16_003_secret_audit
Create Date: 2026-11-19 21:05:00

- `aiqe_registered_queries` 增加 environment_id / statement_hash /
  allowed_tables / allowed_columns / approval_status；
- 新增 `aiqe_query_execution_audits`（每次执行的服务端审计）。

可重复执行（inspect 守卫）；downgrade 幂等。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_004_query_registry"
down_revision: Union[str, None] = "20261119_v16_003_secret_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS: tuple[tuple[str, sa.types.TypeEngine, dict], ...] = (
    ("environment_id", sa.Integer(), {"nullable": True}),
    ("statement_hash", sa.String(length=80), {"nullable": False, "server_default": ""}),
    ("allowed_tables", sa.JSON(), {"nullable": False, "server_default": "[]"}),
    ("allowed_columns", sa.JSON(), {"nullable": False, "server_default": "[]"}),
    (
        "approval_status",
        sa.String(length=16),
        {"nullable": False, "server_default": "approved"},
    ),
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    columns = _columns("aiqe_registered_queries")
    if columns:
        for name, column_type, kwargs in COLUMNS:
            if name not in columns:
                op.add_column("aiqe_registered_queries", sa.Column(name, column_type, **kwargs))

    inspector = sa.inspect(op.get_bind())
    if "aiqe_query_execution_audits" not in inspector.get_table_names():
        op.create_table(
            "aiqe_query_execution_audits",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("environment_id", sa.Integer(), nullable=True),
            sa.Column("query_id", sa.String(length=36), nullable=False),
            sa.Column("query_key", sa.String(length=80), nullable=False),
            sa.Column("query_version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("query_hash", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("params_redacted_json", sa.JSON(), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "executor_identity",
                sa.String(length=120),
                nullable=False,
                server_default="worker",
            ),
            sa.Column(
                "policy_decision", sa.String(length=16), nullable=False, server_default="ALLOW"
            ),
            sa.Column("reason_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_aiqe_query_execution_audits_scope",
            "aiqe_query_execution_audits",
            ["project_id", "query_key", "created_at"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_query_execution_audits" in inspector.get_table_names():
        op.drop_index(
            "ix_aiqe_query_execution_audits_scope",
            table_name="aiqe_query_execution_audits",
        )
        op.drop_table("aiqe_query_execution_audits")
    if "aiqe_registered_queries" in inspector.get_table_names():
        # 初始迁移用 Base.metadata.create_all 建表，可能已带 environment_id 索引；
        # SQLite 无法在有索引时 DROP COLUMN，必须先删索引。
        indexes = {item["name"] for item in inspector.get_indexes("aiqe_registered_queries")}
        if "ix_aiqe_registered_queries_environment_id" in indexes:
            op.drop_index(
                "ix_aiqe_registered_queries_environment_id",
                table_name="aiqe_registered_queries",
            )
    columns = _columns("aiqe_registered_queries")
    for name, _type, _kwargs in COLUMNS:
        if name in columns:
            op.drop_column("aiqe_registered_queries", name)
