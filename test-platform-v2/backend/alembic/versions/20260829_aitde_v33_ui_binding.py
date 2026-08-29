"""aitde v3.3 ui_asset_bindings

Revision ID: 20260829_aitde_v33_ui_binding
Revises: 20260829_aitde_v33_healing
Create Date: 2026-08-29 20:00:00

AITDE V3.3 (plan §2): bind a ScenarioAdapter to its legacy UI case / script so
the legacy-compiler adapter can keep pre-existing UI cases running while new
scenarios route through the deterministic Command IR path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v33_ui_binding"
down_revision: Union[str, None] = "20260829_aitde_v33_healing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ui_asset_bindings" not in inspector.get_table_names():
        op.create_table(
            "ui_asset_bindings",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("legacy_ui_case_id", sa.Integer, nullable=True),
            sa.Column("legacy_ui_script_id", sa.Integer, nullable=True),
            sa.Column("binding_status", sa.String(16), nullable=False, server_default=sa.text("'UNBOUND'"), index=True),
            sa.UniqueConstraint("scenario_adapter_id", "legacy_ui_case_id", name="uq_ui_asset_binding"),
        )


def downgrade() -> None:
    op.drop_table("ui_asset_bindings")
