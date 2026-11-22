"""V16-007: immutable workflow snapshots + Run snapshot binding

Revision ID: 20261119_v16_007_snapshot
Revises: 20261119_v16_005_job_idempotency
Create Date: 2026-11-19 21:55:00

- 新建 `aiqe_workflow_snapshots`（content-addressed 不可变快照，绑定策略/Registry/Driver 版本）；
- `test_runs` 增加 `workflow_snapshot_id` 与 `execution_kind`。

可重复执行；downgrade 先删索引再删列/表（SQLite 限制）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_007_snapshot"
down_revision: Union[str, None] = "20261119_v16_005_job_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_COLUMNS: tuple[tuple[str, sa.types.TypeEngine, dict], ...] = (
    ("workflow_snapshot_id", sa.String(length=36), {"nullable": True}),
    ("execution_kind", sa.String(length=32), {"nullable": False, "server_default": "NORMAL"}),
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
    inspector = sa.inspect(op.get_bind())
    if "aiqe_workflow_snapshots" not in inspector.get_table_names():
        op.create_table(
            "aiqe_workflow_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("workflow_id", sa.String(length=36), nullable=True),
            sa.Column("workflow_version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("schema_version", sa.String(length=20), nullable=False, server_default="1.0"),
            sa.Column("canonical_json", sa.JSON(), nullable=False),
            sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("parent_snapshot_id", sa.String(length=36), nullable=True),
            sa.Column("clone_diff_json", sa.JSON(), nullable=True),
            sa.Column(
                "execution_kind", sa.String(length=32), nullable=False, server_default="NORMAL"
            ),
            sa.Column("target_policy_id", sa.String(length=36), nullable=True),
            sa.Column(
                "target_policy_version", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "target_policy_hash", sa.String(length=64), nullable=False, server_default=""
            ),
            sa.Column(
                "query_registry_version",
                sa.String(length=120),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "driver_manifest_hash",
                sa.String(length=64),
                nullable=False,
                server_default="",
            ),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "uq_aiqe_workflow_snapshots_content",
            "aiqe_workflow_snapshots",
            ["project_id", "workflow_id", "checksum_sha256", "execution_kind"],
            unique=True,
        )
        op.create_index(
            "ix_aiqe_workflow_snapshots_workflow",
            "aiqe_workflow_snapshots",
            ["project_id", "workflow_id"],
        )
        op.create_index(
            "ix_aiqe_workflow_snapshots_project_id",
            "aiqe_workflow_snapshots",
            ["project_id"],
        )
        op.create_index(
            "ix_aiqe_workflow_snapshots_workflow_id",
            "aiqe_workflow_snapshots",
            ["workflow_id"],
        )
        op.create_index(
            "ix_aiqe_workflow_snapshots_checksum_sha256",
            "aiqe_workflow_snapshots",
            ["checksum_sha256"],
        )

    run_columns = _columns("test_runs")
    if run_columns:
        for name, column_type, kwargs in RUN_COLUMNS:
            if name not in run_columns:
                op.add_column("test_runs", sa.Column(name, column_type, **kwargs))
        run_indexes = _index_names("test_runs")
        if "ix_test_runs_workflow_snapshot_id" not in run_indexes:
            op.create_index(
                "ix_test_runs_workflow_snapshot_id", "test_runs", ["workflow_snapshot_id"]
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "test_runs" in inspector.get_table_names():
        new_columns = {name for name, _type, _kwargs in RUN_COLUMNS}
        for index in inspector.get_indexes("test_runs"):
            index_columns = {str(item) for item in (index.get("column_names") or [])}
            if index_columns & new_columns:
                op.drop_index(index["name"], table_name="test_runs")
        columns = _columns("test_runs")
        for name, _type, _kwargs in RUN_COLUMNS:
            if name in columns:
                op.drop_column("test_runs", name)
    if "aiqe_workflow_snapshots" in inspector.get_table_names():
        for name in (
            "ix_aiqe_workflow_snapshots_checksum_sha256",
            "ix_aiqe_workflow_snapshots_workflow_id",
            "ix_aiqe_workflow_snapshots_project_id",
            "ix_aiqe_workflow_snapshots_workflow",
            "uq_aiqe_workflow_snapshots_content",
        ):
            op.drop_index(name, table_name="aiqe_workflow_snapshots")
        op.drop_table("aiqe_workflow_snapshots")
