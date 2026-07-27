"""UI 自动化真实化改造 — 模型增强。

Revision ID: 20260710_0016
Revises: 20260709_0015
Create Date: 2026-07-10

Changes:
- ui_test_run.error_message (Text) — 失败路径落库
- ui_test_job.environment_id (Integer, nullable) — 执行环境
- ui_test_run.base_url (String 500) — 执行时 BASE_URL 快照
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_0016"
down_revision: Union[str, None] = "20260709_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column already exists (safe for AUTO_CREATE_TABLES=true envs)."""
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()

    # 1) ui_test_run.error_message
    if not _column_exists(conn, "ui_test_run", "error_message"):
        op.add_column("ui_test_run",
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""))

    # 2) ui_test_job.environment_id
    if not _column_exists(conn, "ui_test_job", "environment_id"):
        op.add_column("ui_test_job",
            sa.Column("environment_id", sa.Integer(), nullable=True))
        op.create_index("ix_ui_test_job_environment_id", "ui_test_job", ["environment_id"])

    # 3) ui_test_run.base_url
    if not _column_exists(conn, "ui_test_run", "base_url"):
        op.add_column("ui_test_run",
            sa.Column("base_url", sa.String(500), nullable=False, server_default=""))

    # 4) ui_test_run.artifact_dir
    if not _column_exists(conn, "ui_test_run", "artifact_dir"):
        op.add_column("ui_test_run",
            sa.Column("artifact_dir", sa.String(500), nullable=False, server_default=""))

    # 5) ui_test_script table
    if "ui_test_script" not in sa.inspect(conn).get_table_names():
        op.create_table("ui_test_script",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("name", sa.String(200), nullable=False, server_default=""),
            sa.Column("script_key", sa.String(200), nullable=False, server_default=""),
            sa.Column("spec_path", sa.String(500), nullable=False, server_default=""),
            sa.Column("module", sa.String(100), nullable=False, server_default=""),
            sa.Column("owner", sa.String(100), nullable=False, server_default=""),
            sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ui_test_script_project_id", "ui_test_script", ["project_id"])
        op.create_index("ix_ui_test_script_script_key", "ui_test_script", ["script_key"])


def downgrade() -> None:
    conn = op.get_bind()
    with op.batch_alter_table("ui_test_run") as batch_op:
        if _column_exists(conn, "ui_test_run", "artifact_dir"):
            batch_op.drop_column("artifact_dir")
        if _column_exists(conn, "ui_test_run", "base_url"):
            batch_op.drop_column("base_url")
        if _column_exists(conn, "ui_test_run", "error_message"):
            batch_op.drop_column("error_message")
    with op.batch_alter_table("ui_test_job") as batch_op:
        if _column_exists(conn, "ui_test_job", "environment_id"):
            batch_op.drop_index("ix_ui_test_job_environment_id")
            batch_op.drop_column("environment_id")
