"""AUD-005：node_capability_manifests 增加 6 态能力状态

Revision ID: 20261124_aud005_capability_status
Revises: 20261124_aud002_query_registry
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud005_capability_status"
down_revision = "20261124_aud002_query_registry"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("runner_version", sa.String(length=80), ""),
    ("manifest_version", sa.String(length=40), ""),
    ("manifest_signature", sa.String(length=255), ""),
    ("verified_platforms_json", sa.JSON(), None),
    ("capability_status", sa.String(length=16), "REGISTERED"),
    ("status_reason", sa.String(length=255), ""),
    ("verified_at", sa.DateTime(timezone=True), None),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "node_capability_manifests" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("node_capability_manifests")}
    for name, type_, default in _COLUMNS:
        if name in existing:
            continue
        kwargs = {"nullable": True}
        if default is not None:
            kwargs["server_default"] = sa.text("''") if isinstance(default, str) else default
        op.add_column("node_capability_manifests", sa.Column(name, type_, **kwargs))
    indexes = {index["name"] for index in inspector.get_indexes("node_capability_manifests")}
    if "ix_node_capability_manifests_capability_status" not in indexes:
        op.create_index(
            "ix_node_capability_manifests_capability_status",
            "node_capability_manifests",
            ["capability_status"],
        )
    # 既有行按 available 回填状态，避免全部显示 REGISTERED。
    op.execute(
        "UPDATE node_capability_manifests SET capability_status = "
        "CASE WHEN available THEN 'AVAILABLE' ELSE 'REGISTERED' END "
        "WHERE capability_status IS NULL"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite 不支持 DROP COLUMN 于 FK 引用列；降级保留向后兼容的追加列。
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "node_capability_manifests" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("node_capability_manifests")}
    if "ix_node_capability_manifests_capability_status" in indexes:
        op.drop_index(
            "ix_node_capability_manifests_capability_status",
            table_name="node_capability_manifests",
        )
    existing = {column["name"] for column in inspector.get_columns("node_capability_manifests")}
    for name, _type, _default in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("node_capability_manifests", name)
