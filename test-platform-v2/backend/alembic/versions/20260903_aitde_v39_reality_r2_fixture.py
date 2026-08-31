"""aitde v3.9-R2 reality gate: fixture physical execution facts

Revision ID: 20260903_aitde_v39_reality_r2_fixture
Revises: 20260903_aitde_v39_reality_r1
Create Date: 2026-09-03 01:30:00

V3.9 Reality Gate (R2 Data) migration: gives ``fixture_entities`` the physical
execution facts so an entity can answer "did the runtime really create/find it,
was it verified, and was cleanup executed + verified" — never a bare recipe→READY.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_aitde_v39_reality_r2_fixture"
down_revision: Union[str, None] = "20260903_aitde_v39_reality_r1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspector.get_columns(table)}


def _widen_version_table() -> None:
    """Widen ``alembic_version.version_num`` so the 37-41 char V3.9 revision ids fit.

    Alembic defaults the version column to ``VARCHAR(32)``; this V3.9 migration
    runs on PostgreSQL where the next revision id (37-41 chars) would otherwise be
    truncated. SQLite does not enforce varchar length (TEXT affinity), so it is
    left untouched there.
    """
    bind = op.get_bind()
    if getattr(bind.dialect, "name", "") == "sqlite":
        return
    op.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(128)"))


def upgrade() -> None:
    _widen_version_table()
    inspector = sa.inspect(op.get_bind())
    for col, ddl in (
        ("provision_step_id", sa.Column("provision_step_id", sa.Integer, nullable=True)),
        ("physical_status", sa.Column("physical_status", sa.String(16), nullable=True, server_default=sa.text("'PENDING'"), index=True)),
        ("verification_status", sa.Column("verification_status", sa.String(16), nullable=True, server_default=sa.text("'PENDING'"), index=True)),
        ("verified_at", sa.Column("verified_at", sa.DateTime, nullable=True)),
        ("cleanup_status", sa.Column("cleanup_status", sa.String(16), nullable=True, server_default=sa.text("''"), index=True)),
        ("cleanup_verified_at", sa.Column("cleanup_verified_at", sa.DateTime, nullable=True)),
    ):
        if _has_column(inspector, "fixture_entities", col) is False:
            op.add_column("fixture_entities", ddl)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for col in (
        "cleanup_verified_at", "cleanup_status", "verified_at", "verification_status",
        "physical_status", "provision_step_id",
    ):
        if _has_column(inspector, "fixture_entities", col):
            with op.batch_alter_table("fixture_entities") as batch_op:
                batch_op.drop_column(col)
