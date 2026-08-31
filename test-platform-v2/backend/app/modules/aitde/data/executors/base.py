"""AITDE V3.9-R2 (DATA-002) — shared executor primitives.

Executors turn a validated DataPlanStep / EntitySpec into a *real* physical
effect (or a real SELECT) plus a physical VERIFY against the targeted DataSource.
They never fabricate a READY: a step only counts when its physical effect is
verifiably present.

This module carries the shared vocabulary so each executor reports the same
``physical_status`` / ``verification_status`` facts onto the FixtureEntity.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from app.modules.aitde.data.models import DataSource

# Physical-effect facts recorded onto FixtureEntity.physical_status.
PHYSICAL_FOUND = "PHYSICAL_FOUND"        # EXISTING located a real row
PHYSICAL_CREATED = "PHYSICAL_CREATED"    # DB_FIXTURE / API_BUILDER created a real effect
PHYSICAL_FAILED = "FAILED"

# Verification facts recorded onto FixtureEntity.verification_status.
VERIFIED = "VERIFIED"
VERIFY_FAILED = "FAILED"


@dataclass
class ExecutorOutcome:
    """Normalized result of executing one plan step (success path only).

    On failure an executor raises (``DatabaseQueryError`` / ``DataApiError``)
    rather than returning a ``ok=False`` — so a caller can never mistake a partial
    or fake payload for a successful physical effect.
    """

    created_by_fixture: bool
    physical: dict[str, Any]
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_data_driver(source: DataSource | None):
    """Resolve the right driver for a DataSource (DatabaseDriver / DataApiDriver).

    Returns ``None`` for a source that cannot be executed (STATIC / WORKFLOW /
    missing source). Never raises for an unsupported source — the caller decides.
    """
    if source is None:
        return None
    source_type = source.source_type
    config = json.loads(source.config_json or "{}")
    secret_ref = source.secret_ref
    if source_type in ("MYSQL", "POSTGRES"):
        from app.modules.aitde.drivers.database import get_driver

        return get_driver(source_type, config, secret_ref)
    if source_type == "API":
        from app.modules.aitde.drivers.http import DataApiDriver

        return DataApiDriver(config, secret_ref)
    return None
