"""API Token for CI/CD and external integrations."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApiToken(Base):
    """Per-project API token for CI/CD webhook authentication."""

    __tablename__ = "api_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    token_hash: Mapped[str] = mapped_column(String(128), default="")    # SHA256 of the plain token
    token_prefix: Mapped[str] = mapped_column(String(12), default="")  # First 8 chars for display
    scopes: Mapped[str] = mapped_column(String(200), default="[]")     # JSON: ["trigger","read"]
    enabled: Mapped[bool] = mapped_column(default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def generate() -> tuple[str, str]:
        """Generate a new token. Returns (plain_token, sha256_hash)."""
        plain = "tpat_" + secrets.token_urlsafe(32)
        import hashlib
        h = hashlib.sha256(plain.encode()).hexdigest()
        return plain, h
