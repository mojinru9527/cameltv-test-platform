"""PG compatibility — ensure all columns use PostgreSQL-safe types.

Revision ID: 20260702_0006
Revises: 20260627_0005
Create Date: 2026-07-02

Existing schema uses SQLAlchemy abstract types (String, Text, Integer, Boolean,
DateTime) which auto-map correctly to PG native types. This migration is a
placeholder that ensures the revision chain includes PG-awareness.

If any SQLite-specific column types (BLOB, etc.) are discovered during review,
they should be ALTERed here.
"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = "20260702_0006"
down_revision: Union[str, None] = "20260627_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """All existing columns are already PG-compatible via SQLAlchemy abstract types.
    No structural changes needed at this time.
    """
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
