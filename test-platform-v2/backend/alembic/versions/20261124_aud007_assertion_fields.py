"""AUD-007：run_assertion_results 增加 Oracle / evaluator / 来源字段

Revision ID: 20261124_aud007_assertion_fields
Revises: 20261124_aud006_fencing_token
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud007_assertion_fields"
down_revision = "20261124_aud006_fencing_token"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("oracle_type", sa.String(length=40)),
    ("oracle_id", sa.String(length=80)),
    ("oracle_revision", sa.Integer()),
    ("evaluator_key", sa.String(length=80)),
    ("evaluator_version", sa.String(length=40)),
    ("source_ref", sa.String(length=255)),
    ("required", sa.Boolean()),
    ("duration_ms", sa.Integer()),
    ("evaluated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "run_assertion_results" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("run_assertion_results")}
    for name, type_ in _COLUMNS:
        if name in existing:
            continue
        op.add_column("run_assertion_results", sa.Column(name, type_, nullable=True))
    # PostgreSQL 的 boolean 不接受整数 1；SQLite 接受 TRUE。
    op.execute(
        "UPDATE run_assertion_results SET required = TRUE WHERE required IS NULL"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite 不支持 DROP COLUMN 于 FK 引用列；降级保留向后兼容的追加列。
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "run_assertion_results" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("run_assertion_results")}
    for name, _type in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("run_assertion_results", name)
