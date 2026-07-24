"""add_environment_is_production

Revision ID: af68b09103f3
Revises: 20260722_batch27_merge_missing
Create Date: 2026-07-24 12:51:33.549562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af68b09103f3'
down_revision: Union[str, None] = '20260722_batch27_merge_missing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('environment')]
    if 'is_production' not in columns:
        op.add_column('environment', sa.Column('is_production', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('environment')]
    if 'is_production' in columns:
        op.drop_column('environment', 'is_production')
