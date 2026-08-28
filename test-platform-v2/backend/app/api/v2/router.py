"""AITDE v2 router aggregation (V30-002).

Aggregates the V3 domain routers under the ``/api/v2`` prefix. Business routers
are feature-gated behind ``settings.aitde_v3_enabled``; the health probe stays
always available so operators can confirm the v2 surface is mounted.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v2.deps import require_aitde_v3  # noqa: F401  (re-export convenience)
from app.core.config import settings

router = APIRouter(prefix="/api/v2")

# ── Health probe (always available, feature-gate independent) ──
@router.get("/health", tags=["aitde"], summary="AITDE v2 health check")
def health() -> dict:
    return {"status": "ok", "aitde_v3_enabled": settings.aitde_v3_enabled}


# ── Business routers (feature-gated) ──
from app.api.v2.missions import router as missions_router  # noqa: E402

router.include_router(missions_router)

# Further domain routers are added with their epics:
# mission_sources.py (EPIC-02), mission_scope.py (EPIC-03),
# mission_contracts.py (EPIC-05), mission_scenarios.py (EPIC-06),
# ai_operations.py (EPIC-07).
