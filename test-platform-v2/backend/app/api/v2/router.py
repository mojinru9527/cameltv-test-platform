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
from app.api.v2.mission_sources import router as mission_sources_router  # noqa: E402
from app.api.v2.mission_sources import single_router as sources_router  # noqa: E402
from app.api.v2.mission_scope import router as mission_scope_router  # noqa: E402
from app.api.v2.mission_ambiguities import (  # noqa: E402
    router as ambiguity_router,
    intents_router,
    resolve_router,
    intent_review_router,
)
from app.api.v2.mission_contracts import (  # noqa: E402
    router as mission_contracts_router,
    contracts_router as contract_versions_router,
)
from app.api.v2.mission_scenarios import (  # noqa: E402
    generate_router as scenario_generate_router,
    list_router as scenario_list_router,
    scenario_router,
    oracle_router,
)
from app.api.v2.ai_operations import router as ai_operations_router  # noqa: E402
from app.api.v2.scenario_adapters import router as scenario_adapters_router  # noqa: E402
from app.api.v2.environment_snapshots import router as environment_snapshots_router  # noqa: E402
from app.api.v2.executions import router as executions_router  # noqa: E402
from app.api.v2.data_sources import router as data_sources_router  # noqa: E402
from app.api.v2.scenario_data_requirements import (  # noqa: E402
    data_requirement_router,
    scenario_data_router,
)
from app.api.v2.scenario_data_plans import (  # noqa: E402
    data_plan_router,
    scenario_plan_router,
)

router.include_router(missions_router)
router.include_router(mission_sources_router)
router.include_router(sources_router)
router.include_router(mission_scope_router)
router.include_router(ambiguity_router)
router.include_router(intents_router)
router.include_router(resolve_router)
router.include_router(intent_review_router)
router.include_router(mission_contracts_router)
router.include_router(contract_versions_router)
router.include_router(scenario_generate_router)
router.include_router(scenario_list_router)
router.include_router(scenario_router)
router.include_router(oracle_router)
router.include_router(ai_operations_router)
router.include_router(scenario_adapters_router)
router.include_router(environment_snapshots_router)
router.include_router(executions_router)
router.include_router(data_sources_router)
router.include_router(scenario_data_router)
router.include_router(data_requirement_router)
router.include_router(scenario_plan_router)
router.include_router(data_plan_router)

# Further domain routers are added with their epics:
# mission_contracts.py (EPIC-05), mission_scenarios.py (EPIC-06),
# ai_operations.py (EPIC-07).
