"""M1 / TA-005：Run 事实源四表（test_runs / node_runs / step_attempts / run_assertion_results）

Revision ID: 20261111_ta005_run_models
Revises: 20261110_b277b_ui_run_exec_job

设计偏差（D-279-1）：既有 `assertion_results` 表属于 AITDE execution_runtime
（7654 行、schema 不同），M1 新建 `run_assertion_results` 避免同名冲突。
`scenario_id` 按现有 `test_scenarios.id`（INT）使用 BIGINT 外键（ID 规则：旧表外键 BIGINT）。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261111_ta005_run_models"
down_revision = "20261110_b277b_ui_run_exec_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 旧 AITDE v40 governance 迁移在部分数据库（如 SQLite 全链）里创建过同名
    # test_runs / node_runs / step_attempts（schema 与本规格不同，生产已不存在）。
    # 先清理同名遗留表，避免 CREATE TABLE 冲突；生产为 no-op。
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if "test_runs" in existing:
        cols = {c["name"] for c in inspector.get_columns("test_runs")}
        if "run_key" in cols:
            # 初始迁移 20260616_0001 用 Base.metadata.create_all() 建全量表，
            # 在 SQLite/全新库上 M1 四表已被提前创建（含索引），此处无需重复建表。
            return
        # 旧 AITDE 遗留同名表（schema 不同）：先清理再新建。
        for legacy in ("run_assertion_results", "step_attempts", "node_runs", "test_runs"):
            if legacy not in existing:
                continue
            if bind.dialect.name == "postgresql":
                op.execute(f'DROP TABLE IF EXISTS "{legacy}" CASCADE')
            else:
                op.drop_table(legacy)
    op.create_table(
        "test_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_key", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("scenario_id", sa.Integer(), nullable=True),
        sa.Column("workflow_definition_id", sa.String(length=36), nullable=True),
        sa.Column("build_ref", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("commit_sha", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("environment_id", sa.Integer(), nullable=True),
        sa.Column("execution_profile_id", sa.String(length=36), nullable=True),
        sa.Column("environment_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("retest_of", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("trigger_user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["test_scenarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["environment_id"], ["environment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["retest_of"], ["test_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trigger_user_id"], ["sys_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "run_key", name="uq_test_runs_project_run_key"),
    )
    op.create_index("ix_test_runs_project_created", "test_runs", ["project_id", "created_at"])
    op.create_index("ix_test_runs_scenario_created", "test_runs", ["scenario_id", "created_at"])
    op.create_index("ix_test_runs_commit_sha", "test_runs", ["commit_sha"])
    op.create_index("ix_test_runs_retest_of", "test_runs", ["retest_of"])
    op.create_index("ix_test_runs_status", "test_runs", ["status"])

    op.create_table(
        "node_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("node_key", sa.String(length=100), nullable=False),
        sa.Column("driver_key", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("worker_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("input_ref", sa.JSON(), nullable=True),
        sa.Column("output_ref", sa.JSON(), nullable=True),
        sa.Column("error_class", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("resource_keys_json", sa.JSON(), nullable=True),
        sa.Column("execution_job_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_job_id"], ["execution_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "node_key", name="uq_node_runs_run_node"),
    )
    op.create_index("ix_node_runs_run_id", "node_runs", ["run_id"])
    op.create_index("ix_node_runs_status", "node_runs", ["status"])
    op.create_index("ix_node_runs_execution_job_id", "node_runs", ["execution_job_id"])

    op.create_table(
        "step_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("node_run_id", sa.String(length=36), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_summary_json", sa.JSON(), nullable=True),
        sa.Column("output_summary_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column(
            "external_execution_ref", sa.String(length=255), nullable=False, server_default=""
        ),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "node_run_id", "step_key", "attempt_no", name="uq_step_attempts_node_step_attempt"
        ),
    )
    op.create_index("ix_step_attempts_node_run_id", "step_attempts", ["node_run_id"])
    op.create_index("ix_step_attempts_status", "step_attempts", ["status"])

    op.create_table(
        "run_assertion_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("step_attempt_id", sa.String(length=36), nullable=False),
        sa.Column("assertion_key", sa.String(length=100), nullable=False),
        sa.Column("assertion_type", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=40), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="NOT_EVALUATED"
        ),
        sa.Column("expected_json", sa.JSON(), nullable=True),
        sa.Column("actual_json", sa.JSON(), nullable=True),
        sa.Column("diff_json", sa.JSON(), nullable=True),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=True),
        sa.Column(
            "evaluated_by", sa.String(length=20), nullable=False, server_default="deterministic"
        ),
        sa.ForeignKeyConstraint(["step_attempt_id"], ["step_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "step_attempt_id", "assertion_key", name="uq_run_assertion_attempt_assertion"
        ),
    )
    op.create_index(
        "ix_run_assertion_results_step_attempt_id", "run_assertion_results", ["step_attempt_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_run_assertion_results_step_attempt_id", table_name="run_assertion_results"
    )
    op.drop_table("run_assertion_results")
    op.drop_index("ix_step_attempts_status", table_name="step_attempts")
    op.drop_index("ix_step_attempts_node_run_id", table_name="step_attempts")
    op.drop_table("step_attempts")
    op.drop_index("ix_node_runs_execution_job_id", table_name="node_runs")
    op.drop_index("ix_node_runs_status", table_name="node_runs")
    op.drop_index("ix_node_runs_run_id", table_name="node_runs")
    op.drop_table("node_runs")
    op.drop_index("ix_test_runs_status", table_name="test_runs")
    op.drop_index("ix_test_runs_retest_of", table_name="test_runs")
    op.drop_index("ix_test_runs_commit_sha", table_name="test_runs")
    op.drop_index("ix_test_runs_scenario_created", table_name="test_runs")
    op.drop_index("ix_test_runs_project_created", table_name="test_runs")
    op.drop_table("test_runs")
