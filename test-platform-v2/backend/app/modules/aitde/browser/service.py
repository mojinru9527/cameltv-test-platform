"""AITDE V3.3 BrowserObserverService (V33-006/007).

Standardizes observe events and compresses an Observation session into an
ActionPlan candidate. Credentials are redacted from event payload/semantic JSON.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.browser.models import BrowserObservationEvent, BrowserSession

_SENSITIVE_KEYS = {"password", "passwd", "token", "authorization", "cookie", "secret", "api_key", "apikey"}


def _redact(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: ("<REDACTED>" if str(k).lower() in _SENSITIVE_KEYS else _redact(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [_redact(v) for v in node]
    return node


def create_session(
    db: Session,
    project_id: int,
    mission_id: int,
    environment_id: int,
    mode: str,
    started_by: int,
    browser_type: str = "chromium",
    context_ref: str = "",
) -> BrowserSession:
    session = BrowserSession(
        project_id=project_id, mission_id=mission_id, environment_id=environment_id,
        mode=mode, started_by=started_by, browser_type=browser_type, context_ref=context_ref,
        status="ACTIVE",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> BrowserSession:
    s = db.get(BrowserSession, session_id)
    if not s:
        raise APIException(code=404, msg="浏览器会话不存在", http_status=404)
    return s


def stop_session(db: Session, session_id: int) -> BrowserSession:
    s = get_session(db, session_id)
    s.status = "FINISHED"
    s.finished_at = datetime.now()
    db.commit()
    db.refresh(s)
    return s


def record_event(
    db: Session,
    session_id: int,
    event_type: str,
    semantic_target: dict[str, Any] | None,
    payload_ref: dict[str, Any] | None,
) -> BrowserObservationEvent:
    s = get_session(db, session_id)
    max_seq = db.scalar(
        select(BrowserObservationEvent.sequence)
        .where(BrowserObservationEvent.browser_session_id == session_id)
        .order_by(BrowserObservationEvent.sequence.desc())
    )
    sequence = (max_seq or 0) + 1
    event = BrowserObservationEvent(
        browser_session_id=session_id,
        sequence=sequence,
        event_type=event_type,
        # credential redaction is a hard invariant for observe evidence
        semantic_target_json=json.dumps(_redact(semantic_target or {}), ensure_ascii=False),
        payload_ref_json=json.dumps(_redact(payload_ref or {}), ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, session_id: int) -> list[BrowserObservationEvent]:
    get_session(db, session_id)
    rows = db.scalars(
        select(BrowserObservationEvent)
        .where(BrowserObservationEvent.browser_session_id == session_id)
        .order_by(BrowserObservationEvent.sequence.asc())
    ).all()
    return list(rows)


def derive_action_plan(db: Session, session_id: int) -> dict[str, Any]:
    """Compress an Observe session into a Command IR candidate.

    Every click/input/goto event becomes a command carrying an ``observation_ref``
    (the event id) so each key action remains traceable to its observation.
    """
    events = list_events(db, session_id)
    commands: list[dict[str, Any]] = []
    seq = 1
    for ev in events:
        semantic = json.loads(ev.semantic_target_json or "{}")
        command = {"id": str(seq), "observation_ref": ev.sequence, "driver": "browser"}
        if ev.event_type == "NAVIGATION":
            command["action"] = "goto"
            command["input"] = {"route": semantic.get("route", "/")}
        elif ev.event_type == "CLICK":
            command["action"] = "click"
            command["input"] = {"locator": semantic.get("locator", {"strategy": "role", "role": "button", "name": semantic.get("name")})}
        elif ev.event_type == "INPUT":
            command["action"] = "fill"
            command["input"] = {"locator": semantic.get("locator", {}), "value": semantic.get("value", "")}
        else:
            continue
        commands.append(command)
        seq += 1
    return {"schema_version": "1.0", "commands": commands}
