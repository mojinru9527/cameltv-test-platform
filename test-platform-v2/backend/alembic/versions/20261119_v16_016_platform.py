"""V16-016: platform binding environment/pool/runner fields

Revision ID: 20261119_v16_016_platform
Revises: 20261119_v16_015_capability
Create Date: 2026-11-20 00:05:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_016_platform"
down_revision: Union[str, None] = "20261119_v16_015_capability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    ("environment_id", sa.Integer(), {"nullable": True}),
    ("device_pool", sa.String(length=120), {"nullable": False, "server_default": ""}),
    ("runner_version", sa.String(length=80), {"nullable": False, "server_default": ""}),
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    existing = _columns("aiqe_platform_bindings")
    if not existing:
        return
    for name, column_type, kwargs in COLUMNS:
        if name not in existing:
            op.add_column("aiqe_platform_bindings", sa.Column(name, column_type, **kwargs))
    indexes = {
        item["name"] for item in sa.inspect(op.get_bind()).get_indexes("aiqe_platform_bindings")
    }
    if "ix_aiqe_platform_bindings_environment_id" not in indexes:
        op.create_index(
            "ix_aiqe_platform_bindings_environment_id",
            "aiqe_platform_bindings",
            ["environment_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_platform_bindings" not in inspector.get_table_names():
        return
    for index in inspector.get_indexes("aiqe_platform_bindings"):
        if str(index.get("name")) == "ix_aiqe_platform_bindings_environment_id":
            op.drop_index(index["name"], table_name="aiqe_platform_bindings")
    columns = _columns("aiqe_platform_bindings")
    for name, _type, _kwargs in COLUMNS:
        if name in columns:
            op.drop_column("aiqe_platform_bindings", name)
