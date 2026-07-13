"""UI runner hardening — managed process + artifact isolation.

Revision ID: 20260713_ui_runner
Revises: 20260710_0017
Create Date: 2026-07-13

Changes:
- ui_test_run.process_id (Integer, nullable) — PID of running Playwright process
- ui_test_run.cancel_requested (Boolean, default False) — cancellation flag
- ui_test_run.report_json_path (String 500) — report.json path
- ui_test_run.html_report_path (String 500) — HTML report path
- ui_test_run.stdout (Text) — captured stdout
- ui_test_run.stderr (Text) — captured stderr
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_ui_runner"
down_revision: Union[str, None] = "20260710_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column already exists (safe for AUTO_CREATE_TABLES=true envs)."""
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "ui_test_run", "process_id"):
        op.add_column("ui_test_run",
            sa.Column("process_id", sa.Integer(), nullable=True))

    if not _column_exists(conn, "ui_test_run", "cancel_requested"):
        op.add_column("ui_test_run",
            sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not _column_exists(conn, "ui_test_run", "report_json_path"):
        op.add_column("ui_test_run",
            sa.Column("report_json_path", sa.String(500), nullable=False, server_default=""))

    if not _column_exists(conn, "ui_test_run", "html_report_path"):
        op.add_column("ui_test_run",
            sa.Column("html_report_path", sa.String(500), nullable=False, server_default=""))

    if not _column_exists(conn, "ui_test_run", "stdout"):
        op.add_column("ui_test_run",
            sa.Column("stdout", sa.Text(), nullable=False, server_default=""))

    if not _column_exists(conn, "ui_test_run", "stderr"):
        op.add_column("ui_test_run",
            sa.Column("stderr", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    conn = op.get_bind()
    with op.batch_alter_table("ui_test_run") as batch_op:
        if _column_exists(conn, "ui_test_run", "stderr"):
            batch_op.drop_column("stderr")
        if _column_exists(conn, "ui_test_run", "stdout"):
            batch_op.drop_column("stdout")
        if _column_exists(conn, "ui_test_run", "html_report_path"):
            batch_op.drop_column("html_report_path")
        if _column_exists(conn, "ui_test_run", "report_json_path"):
            batch_op.drop_column("report_json_path")
        if _column_exists(conn, "ui_test_run", "cancel_requested"):
            batch_op.drop_column("cancel_requested")
        if _column_exists(conn, "ui_test_run", "process_id"):
            batch_op.drop_column("process_id")
