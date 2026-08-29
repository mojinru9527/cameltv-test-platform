"""ReplayService (V31-004/V31-014).

Builds or returns the append-only proof replay for a Run. A successful Run is
replayable too; Replay is a view over steps + assertions + evidence, not a
re-execution.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.evidence.service import list_evidence
from app.modules.aitde.evidence.manifest import build_manifest, manifest_hash
from app.modules.aitde.execution import repository, service
from app.modules.aitde.execution.models import ReplayManifest


def get_manifest(db: Session, run_id: int, project_id: int) -> ReplayManifest:
    """Return the stored manifest or build+persist a fresh one."""
    run = service.get_run(db, run_id, project_id)
    existing = repository.get_replay_manifest(db, run_id, project_id)
    if existing is not None:
        return existing

    steps = repository.list_steps(db, run_id, project_id)
    assertions = repository.list_assertions(db, run_id, project_id)
    evidence = list_evidence(db, run_id, project_id)

    manifest = build_manifest(run, steps, assertions, evidence)
    h = manifest_hash(manifest)
    return repository.create_replay_manifest(
        db,
        {
            "run_id": run_id,
            "schema_version": manifest["schema_version"],
            "manifest_json": json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            "manifest_hash": h,
        },
    )


def manifest_dict(row: ReplayManifest) -> dict[str, Any]:
    try:
        return json.loads(row.manifest_json)
    except (ValueError, json.JSONDecodeError):
        return {}


def build_replay_view(m: dict[str, Any]) -> dict[str, Any]:
    """Shape the manifest into the 3-column Replay response (timeline/context/detail)."""
    return {
        "outcome": m.get("outcome"),
        "runtime_status": m.get("runtime_status"),
        "environment_snapshot_id": m.get("environment_snapshot_id"),
        "timeline": m.get("timeline", []),
        "assertions": m.get("assertions", []),
        "evidence": m.get("evidence", []),
    }
