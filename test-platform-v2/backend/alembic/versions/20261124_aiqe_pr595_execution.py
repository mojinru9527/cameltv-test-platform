"""PR #595 后 v1.4：执行正确性字段与质量门禁快照。

Revision ID: 20261124_aiqe_pr595_execution
Revises: 20261123_ta033_mutation_ledger

新增内容全部是向后兼容的追加：
- test_runs：Workflow 快照/checksum、launch 幂等键、preflight/capability 快照；
- node_runs：结构化 outputs、脱敏后的 resolved input、断言/输出 schema 快照；
- run_assertion_results：oracle_layer/oracle_ref/actual_source/severity/timeout/duration；
- aiqe_quality_gate_snapshots：append-only 门禁快照。

迁移可重跑（upgrade/downgrade/upgrade）。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aiqe_pr595_execution"
down_revision = "20261123_ta033_mutation_ledger"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table)}


def upgrade() -> None:
    run_columns = _columns("test_runs")
    if "workflow_checksum" not in run_columns:
        op.add_column(
            "test_runs",
            sa.Column(
                "workflow_checksum",
                sa.String(length=64),
                nullable=False,
                server_default="",
            ),
        )
    if "workflow_snapshot_json" not in run_columns:
        op.add_column(
            "test_runs",
            sa.Column(
                "workflow_snapshot_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
    if "launch_key" not in run_columns:
        op.add_column(
            "test_runs", sa.Column("launch_key", sa.String(length=128), nullable=True)
        )
    if "preflight_json" not in run_columns:
        op.add_column(
            "test_runs",
            sa.Column(
                "preflight_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
    if "capability_snapshot_json" not in run_columns:
        op.add_column(
            "test_runs",
            sa.Column(
                "capability_snapshot_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
    if (
        op.get_bind().dialect.name != "sqlite"
        and "uq_test_runs_project_launch_key" not in _indexes("test_runs")
    ):
        # SQLite 的 DROP COLUMN 不能处理带 UNIQUE 约束的列（迁移演练会失败）；
        # 生产 PostgreSQL 保留 DB 级唯一约束，SQLite 由服务层 launch_key 查询兜底。
        op.create_index(
            "uq_test_runs_project_launch_key",
            "test_runs",
            ["project_id", "launch_key"],
            unique=True,
        )

    node_columns = _columns("node_runs")
    json_columns = {
        "outputs_json": "structured outputs declared by the node",
        "resolved_input_json": "resolved input, secrets redacted",
        "secret_keys_json": "secret keys only",
        "source_refs_json": "input provenance",
        "assertions_json": "frozen assertion snapshot",
        "outputs_spec_json": "declared output JSONPath mapping",
    }
    for name, _comment in json_columns.items():
        if name in node_columns:
            continue
        if name.endswith("_keys_json") or name.endswith("_refs_json"):
            default = sa.text("'[]'")
        else:
            default = sa.text("'{}'")
        op.add_column(
            "node_runs",
            sa.Column(name, sa.JSON(), nullable=False, server_default=default),
        )
    if "output_schema_json" not in node_columns:
        op.add_column("node_runs", sa.Column("output_schema_json", sa.JSON(), nullable=True))
    if "capability" not in node_columns:
        op.add_column(
            "node_runs",
            sa.Column(
                "capability", sa.String(length=64), nullable=False, server_default=""
            ),
        )
    if (
        op.get_bind().dialect.name != "sqlite"
        and "uq_node_runs_execution_job" not in _indexes("node_runs")
    ):
        op.create_index(
            "uq_node_runs_execution_job",
            "node_runs",
            ["execution_job_id"],
            unique=True,
        )

    assertion_columns = _columns("run_assertion_results")
    assertion_additions = {
        "schema_version": sa.Column(
            "schema_version", sa.String(length=20), nullable=False, server_default="1.0"
        ),
        "oracle_layer": sa.Column(
            "oracle_layer", sa.String(length=8), nullable=False, server_default="STD"
        ),
        "oracle_ref": sa.Column(
            "oracle_ref", sa.String(length=255), nullable=False, server_default=""
        ),
        "actual_source": sa.Column(
            "actual_source", sa.String(length=64), nullable=False, server_default=""
        ),
        "severity": sa.Column(
            "severity", sa.String(length=8), nullable=False, server_default="P1"
        ),
        "timeout_ms": sa.Column(
            "timeout_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        "duration_ms": sa.Column(
            "duration_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        "error_message": sa.Column(
            "error_message", sa.String(length=500), nullable=False, server_default=""
        ),
        "artifact_refs_json": sa.Column(
            "artifact_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
    }
    for name, column in assertion_additions.items():
        if name not in assertion_columns:
            op.add_column("run_assertion_results", column)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_quality_gate_snapshots" not in inspector.get_table_names():
        op.create_table(
            "aiqe_quality_gate_snapshots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("version_task_id", sa.Integer(), nullable=True),
            sa.Column("gate_status", sa.String(length=16), nullable=False),
            sa.Column("rule_version", sa.String(length=32), nullable=False, server_default="v1.4"),
            sa.Column("build_ref", sa.String(length=255), nullable=False, server_default=""),
            sa.Column(
                "environment_ref", sa.String(length=128), nullable=False, server_default=""
            ),
            sa.Column(
                "contract_checksum", sa.String(length=64), nullable=False, server_default=""
            ),
            sa.Column("p0_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("p0_passed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("p0_failed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("p0_blocked", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column(
                "computed_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("computed_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["version_task_id"], ["version_task.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_aiqe_gate_project_computed",
            "aiqe_quality_gate_snapshots",
            ["project_id", "computed_at"],
        )
        op.create_index(
            "ix_aiqe_gate_task_computed",
            "aiqe_quality_gate_snapshots",
            ["version_task_id", "computed_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "aiqe_quality_gate_snapshots" in inspector.get_table_names():
        op.drop_index(
            "ix_aiqe_gate_task_computed", table_name="aiqe_quality_gate_snapshots"
        )
        op.drop_index(
            "ix_aiqe_gate_project_computed", table_name="aiqe_quality_gate_snapshots"
        )
        op.drop_table("aiqe_quality_gate_snapshots")

    if op.get_bind().dialect.name == "sqlite":
        # 初始迁移 20260616_0001 用 Base.metadata.create_all() 建表，SQLite 上的
        # UNIQUE 约束属于表定义而非独立索引，DROP COLUMN 会失败。SQLite 仅用于
        # 本地/演练，保留追加列即可（upgrade 会按 inspector 跳过）；生产 PostgreSQL
        # 走下面的真实回滚。
        return

    assertion_columns = _columns("run_assertion_results")
    for name in (
        "error_message",
        "artifact_refs_json",
        "duration_ms",
        "timeout_ms",
        "severity",
        "actual_source",
        "oracle_ref",
        "oracle_layer",
        "schema_version",
    ):
        if name in assertion_columns:
            op.drop_column("run_assertion_results", name)

    if "uq_node_runs_execution_job" in _indexes("node_runs"):
        op.drop_index("uq_node_runs_execution_job", table_name="node_runs")
    node_columns = _columns("node_runs")
    for name in (
        "capability",
        "output_schema_json",
        "outputs_spec_json",
        "assertions_json",
        "source_refs_json",
        "secret_keys_json",
        "resolved_input_json",
        "outputs_json",
    ):
        if name in node_columns:
            op.drop_column("node_runs", name)

    if "uq_test_runs_project_launch_key" in _indexes("test_runs"):
        op.drop_index("uq_test_runs_project_launch_key", table_name="test_runs")
    run_columns = _columns("test_runs")
    for name in (
        "capability_snapshot_json",
        "preflight_json",
        "launch_key",
        "workflow_snapshot_json",
        "workflow_checksum",
    ):
        if name in run_columns:
            op.drop_column("test_runs", name)
