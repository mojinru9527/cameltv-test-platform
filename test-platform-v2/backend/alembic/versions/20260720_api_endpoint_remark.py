"""Add remark column to api_endpoint

Revision ID: 20260720_remark
Revises: 20260719_requirement_review
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260720_remark'
down_revision = '20260719_requirement_review'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('api_endpoint', sa.Column('remark', sa.String(), nullable=True, server_default=''))


def downgrade():
    op.drop_column('api_endpoint', 'remark')
