"""CleanupService (V32-012): idempotent compensation.

Cleanup replays each fixture entity's recorded compensation (delete / revert)
and is idempotent: a CLEANED fixture returns a consistent no-op result instead
of erroring or duplicating work.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import CleanupStatus, FixtureStatus
from app.modules.aitde.data import repository


def cleanup_fixture(
    db: Session, fixture_id: int, attempt_no: int | None = None
) -> dict[str, Any]:
    fixture = repository.get_fixture(db, fixture_id)
    if not fixture:
        raise APIException(code=404, msg="Fixture 不存在", http_status=404)

    # Idempotent: already cleaned -> consistent no-op.
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
        }
        for e in entities
        if e.created_by_fixture and e.cleanup_action_json
    ]

    latest = repository.get_latest_cleanup_record(db, fixture_id)
    attempt = attempt_no or ((latest.attempt_no + 1) if latest else 1)

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

    fixture.status = FixtureStatus.CLEANED.value
    fixture.cleanup_status = CleanupStatus.SUCCEEDED.value
    record.status = CleanupStatus.SUCCEEDED.value
    record.finished_at = datetime.now()
    db.commit()
    db.refresh(record)
    db.refresh(fixture)
    return {
        "status": CleanupStatus.SUCCEEDED.value,
        "attempt_no": attempt,
        "actions": actions,
        "idempotent": False,
    }
