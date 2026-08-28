"""Shared AITDE v2 FastAPI dependencies (V30-001/V30-002)."""
from __future__ import annotations

from fastapi import HTTPException

from app.core.config import settings


def require_aitde_v3() -> None:
    """Blocks AITDE v3 business endpoints until the feature flag is enabled."""
    if not settings.aitde_v3_enabled:
        raise HTTPException(
            status_code=404,
            detail="AITDE V3 is not enabled on this deployment.",
        )
