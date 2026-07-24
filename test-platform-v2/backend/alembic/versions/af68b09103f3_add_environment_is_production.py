"""add_environment_is_production

Revision ID: af68b09103f3
Revises: 20260723_batch37_plan_assignee
Create Date: 2026-07-24 12:51:33.549562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af68b09103f3'
down_revision: Union[str, None] = '20260723_batch37_plan_assignee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('environment', sa.Column('is_production', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    op.drop_column('environment', 'is_production')
