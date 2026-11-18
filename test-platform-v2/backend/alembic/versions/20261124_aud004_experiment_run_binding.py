"""AUD-004：triage_experiments 绑定真实验证 Run + 单变量快照字段

Revision ID: 20261124_aud004_experiment_run_binding
Revises: 20261124_aud001_target_policy
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud004_experiment_run_binding"
down_revision = "20261124_aud001_target_policy"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("project_id", sa.Integer()),
    ("changed_dimension", sa.String(length=64)),
    ("baseline_run_id", sa.String(length=36)),
    ("baseline_snapshot_hash", sa.String(length=128)),
    ("verification_snapshot_hash", sa.String(length=128)),
    ("snapshot_diff_json", sa.JSON()),
    ("experiment_result", sa.String(length=24)),
    ("error_code", sa.String(length=64)),
    ("started_at", sa.DateTime(timezone=True)),
    ("completed_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "triage_experiments" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("triage_experiments")}
    for name, type_ in _COLUMNS:
        if name in existing:
            continue
        op.add_column("triage_experiments", sa.Column(name, type_, nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("triage_experiments")}
    if "ix_triage_experiments_project_id" not in indexes:
        op.create_index(
            "ix_triage_experiments_project_id", "triage_experiments", ["project_id"]
        )
    if "ix_triage_experiments_baseline_run_id" not in indexes:
        op.create_index(
            "ix_triage_experiments_baseline_run_id",
            "triage_experiments",
            ["baseline_run_id"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite 不支持 DROP COLUMN 于 FK 引用列；降级保留向后兼容的追加列。
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "triage_experiments" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("triage_experiments")}
    for index in (
        "ix_triage_experiments_baseline_run_id",
        "ix_triage_experiments_project_id",
    ):
        if index in indexes:
            op.drop_index(index, table_name="triage_experiments")
    existing = {column["name"] for column in inspector.get_columns("triage_experiments")}
    for name, _type in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("triage_experiments", name)
