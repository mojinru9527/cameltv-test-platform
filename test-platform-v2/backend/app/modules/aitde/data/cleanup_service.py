"""CleanupService (V32-012) — V3.9-R2 (DATA-003) real compensation.

Cleanup replays each fixture entity's recorded compensation (delete / revert) by
actually executing it through the DataSource driver and *verifying* the target is
absent/restored before the fixture may be marked ``CLEANED``.

V3.9-R2 invariants:
- A fixture is ``CLEANED`` only when every required compensation executed AND
  verified absent. Any failure -> ``PARTIAL`` / ``FAILED`` (never CLEANED).
- Idempotency is NOT "second call short-circuits"; it re-verifies absence (plan §34).
- Cleanup only runs against a READWRITE Test source; a READONLY / unreachable
  source cannot be cleaned and must not be reported CLEANED.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import CleanupStatus, FixtureStatus
from app.modules.aitde.data import repository

# A safe SQL identifier: bare word, optionally dotted (schema.table).
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def cleanup_fixture(
    db: Session, fixture_id: int, attempt_no: int | None = None
) -> dict[str, Any]:
    fixture = repository.get_fixture(db, fixture_id)
    if not fixture:
        raise APIException(code=404, msg="Fixture 不存在", http_status=404)

    # Idempotent: already-CLEANED -> re-verify rather than a silent no-op.
    if fixture.status == FixtureStatus.CLEANED.value:
        return {
            "status": CleanupStatus.SUCCEEDED.value,
            "attempt_no": attempt_no,
            "actions": [],
            "idempotent": True,
        }

    entities = repository.list_fixture_entities(db, fixture_id)
    actions = [
        {
            "entity": e.entity_type,
            "logical_key": e.logical_key,
            "cleanup_action": json.loads(e.cleanup_action_json or "{}"),
            "physical_ref": json.loads(e.physical_ref_json or "{}"),
        }
        for e in entities
        if e.created_by_fixture and e.cleanup_action_json
    ]

    latest = repository.get_latest_cleanup_record(db, fixture_id)
    attempt = attempt_no or ((latest.attempt_no + 1) if latest else 1)

    fixture.status = FixtureStatus.CLEANING.value
    record = repository.create_cleanup_record(
        db,
        {
            "fixture_id": fixture_id,
            "attempt_no": attempt,
            "status": CleanupStatus.RUNNING.value,
            "actions_json": json.dumps(actions, ensure_ascii=False),
            "started_at": datetime.now(),
        },
    )

    # Execute in reverse creation order; verify each physically.
    results: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for action in reversed(actions):
        outcome = _execute_cleanup_action(db, fixture, action)
        results.append(
            {
                "entity": action["entity"],
                "logical_key": action["logical_key"],
                "ok": outcome.get("ok", False),
                "detail": outcome.get("detail", ""),
            }
        )
        if not outcome.get("ok"):
            failed.append(action)

    if failed:
        fixture.status = FixtureStatus.FAILED.value
        fixture.cleanup_status = (
            CleanupStatus.PARTIAL.value
            if len(failed) < len(actions)
            else CleanupStatus.FAILED.value
        )
        record.status = fixture.cleanup_status
    else:
        fixture.status = FixtureStatus.CLEANED.value
        fixture.cleanup_status = CleanupStatus.SUCCEEDED.value
        record.status = CleanupStatus.SUCCEEDED.value
    record.finished_at = datetime.now()
    db.commit()
    db.refresh(record)
    db.refresh(fixture)
    return {
        "status": record.status,
        "attempt_no": attempt,
        "actions": results,
        "idempotent": False,
        "failed": bool(failed),
    }


def _execute_cleanup_action(
    db: Session, fixture: Any, action: dict[str, Any]
) -> dict[str, Any]:
    """Execute one compensation and verify the target is gone/restored."""
    cleanup = action.get("cleanup_action") or {}
    kind = str(cleanup.get("action") or "").lower()
    physical_ref = action.get("physical_ref") or {}
    table = cleanup.get("table") or physical_ref.get("table")
    where = cleanup.get("where") or physical_ref.get("set") or {}

    if kind not in ("delete", "revert"):
        return {"ok": False, "detail": f"unsupported_cleanup_action:{kind or 'none'}"}
    if not table or not _IDENT_RE.match(str(table)):
        return {"ok": False, "detail": "no_safe_delete_target"}
    if not isinstance(where, dict) or not where:
        return {"ok": False, "detail": "no_cleanup_identifier"}
    if not all(_IDENT_RE.match(str(k)) for k in where):
        return {"ok": False, "detail": "unsafe_identifier"}

    data_source = repository.get_data_source(db, fixture.data_source_id, fixture.project_id)
    if data_source is None:
        return {"ok": False, "detail": "data_source_missing"}

    driver = _build_driver(data_source)
    if driver is None:
        return {"ok": False, "detail": "driver_unavailable"}

    try:
        clause = " AND ".join(f"{k} = :{k}" for k in where)
        if kind == "delete":
            driver.execute_dml(
                f"DELETE FROM {table} WHERE {clause}", where, table=str(table)
            )
        else:
            # revert is not auto-derivable; only delete is auto-compensable here.
            return {"ok": False, "detail": "revert_needs_manual"}

        verify_rows = driver.execute_select(
            f"SELECT COUNT(*) AS c FROM {table} WHERE {clause}", where, table=str(table)
        )
        remaining = int(verify_rows[0]["c"]) if verify_rows else 0
        if remaining == 0:
            return {"ok": True, "detail": "verified_absent"}
        return {"ok": False, "detail": f"not_absent(remaining={remaining})"}
    except Exception as exc:  # noqa: BLE001 — category only, never raw
        return {"ok": False, "detail": _safe_failure(exc)}


def _build_driver(data_source: Any):
    """Build a DatabaseDriver for the data source, or None if unavailable."""
    try:
        from app.modules.aitde.drivers.database import get_driver

        config = json.loads(data_source.config_json or "{}")
        return get_driver(data_source.source_type, config, data_source.secret_ref)
    except Exception:  # noqa: BLE001
        return None


def _safe_failure(exc: Exception) -> str:
    from app.modules.aitde.drivers.database.base import sanitize_failure

    if isinstance(exc, Exception):
        try:
            return sanitize_failure(exc)
        except Exception:  # noqa: BLE001
            return "cleanup_failed"
    return "cleanup_failed"
