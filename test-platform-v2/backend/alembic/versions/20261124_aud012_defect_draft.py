"""AUD-012：缺陷草稿可复现字段

Revision ID: 20261124_aud012_defect_draft
Revises: 20261124_aud009_regression_hardening
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud012_defect_draft"
down_revision = "20261124_aud009_regression_hardening"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("reproduction_status", sa.String(length=32)),
    ("failing_assertion_refs_json", sa.JSON()),
    ("no_assertion_reason", sa.Text()),
    ("correlation_id", sa.String(length=128)),
    ("fixture_namespace", sa.String(length=128)),
    ("draft_id", sa.String(length=36)),
    ("approved_by", sa.Integer()),
    ("approved_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "defect" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("defect")}
    for name, type_ in _COLUMNS:
        if name in existing:
            continue
        op.add_column("defect", sa.Column(name, type_, nullable=True))
    op.execute(
        "UPDATE defect SET reproduction_status = 'COMPLETE' WHERE reproduction_status IS NULL"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite 不支持 DROP COLUMN 于 FK 引用列；降级保留向后兼容的追加列。
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "defect" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("defect")}
    for name, _type in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("defect", name)
