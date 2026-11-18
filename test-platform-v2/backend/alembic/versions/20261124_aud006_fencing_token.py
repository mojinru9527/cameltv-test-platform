"""AUD-006：node_runs / step_attempts 增加 fencing token

Revision ID: 20261124_aud006_fencing_token
Revises: 20261124_aud005_capability_status
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud006_fencing_token"
down_revision = "20261124_aud005_capability_status"
branch_labels = None
depends_on = None

_TABLES = ("node_runs", "step_attempts")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table in _TABLES:
        if table not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "fencing_token" in columns:
            continue
        op.add_column(
            table,
            sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table in _TABLES:
        if table not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "fencing_token" in columns:
            op.drop_column(table, "fencing_token")
