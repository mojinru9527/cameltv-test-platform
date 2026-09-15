"""add canonical runner lock state to execution runs

Revision ID: 20260920_execution_run_runner
Revises: 20260919_execution_run_campaign
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_execution_run_runner"
down_revision: Union[str, None] = "20260919_execution_run_campaign"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_runs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("execution_runs")}
    additions = {
        "runner_id": sa.Column("runner_id", sa.String(128), nullable=False, server_default=sa.text("''")),
        "runner_capabilities_json": sa.Column(
            "runner_capabilities_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")
        ),
        "locked_at": sa.Column("locked_at", sa.DateTime(), nullable=True),
        "heartbeat_at": sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("execution_runs", column)
    indexes = {index["name"] for index in inspector.get_indexes("execution_runs")}
    if "ix_execution_runs_runner_id" not in indexes:
        op.create_index("ix_execution_runs_runner_id", "execution_runs", ["runner_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_runs" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("execution_runs")}
    if "ix_execution_runs_runner_id" in indexes:
        op.drop_index("ix_execution_runs_runner_id", table_name="execution_runs")
    columns = {column["name"] for column in inspector.get_columns("execution_runs")}
    for name in ("heartbeat_at", "locked_at", "runner_capabilities_json", "runner_id"):
        if name in columns:
            op.drop_column("execution_runs", name)
