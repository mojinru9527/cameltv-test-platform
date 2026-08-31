"""aitde v3.9-R3 reality gate: fingerprint / snapshot confidence

Revision ID: 20260903_aitde_v39_reality_r3_fingerprint
Revises: 20260903_aitde_v39_reality_r2_fixture
Create Date: 2026-09-03 02:30:00

V3.9 Reality Gate (R3 FINGER-001) migration: gives `environment_fingerprints` and
`environment_snapshots` a `confidence` (LOW/MEDIUM/HIGH) so a P0 release gate can
require MEDIUM/HIGH — a fingerprint/snapshot assembled only from a manual build
label (LOW confidence) can never satisfy a release gate (plan §57).

The column index is managed explicitly (add_index / drop_index) rather than being
bundled into ``op.add_column(..., index=True)``. That keeps the migration
reversible for the §77-78 PostgreSQL previous-head <-> current-head drill, where a
batched ``drop_column`` otherwise leaves an orphan index that breaks the re-upgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_aitde_v39_reality_r3_fingerprint"
down_revision: Union[str, None] = "20260903_aitde_v39_reality_r2_fixture"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("environment_fingerprints", "environment_snapshots")


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspector.get_columns(table)}


def _has_index(inspector, table: str, index: str) -> bool:
    return any(i["name"] == index for i in inspector.get_indexes(table))


def _index_name(table: str) -> str:
    return f"ix_{table}_confidence"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in _TABLES:
        if _has_column(inspector, table, "confidence") is False:
            op.add_column(
                table,
                sa.Column("confidence", sa.String(16), nullable=True, server_default=sa.text("'LOW'")),
            )
        if _has_index(inspector, table, _index_name(table)) is False:
            op.create_index(_index_name(table), table, ["confidence"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in _TABLES:
        if _has_index(inspector, table, _index_name(table)):
            op.drop_index(_index_name(table), table_name=table)
        if _has_column(inspector, table, "confidence"):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_column("confidence")
