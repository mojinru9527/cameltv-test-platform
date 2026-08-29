"""V33-006/007 Observe session + observation→ActionPlan tests."""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.browser import service
from app.modules.aitde.command import DEFAULT_REGISTRY


def test_create_and_record_event_redacts_credentials(db):
    s = service.create_session(db, project_id=1, mission_id=1, environment_id=2, mode="OBSERVE", started_by=9)
    ev = service.record_event(
        db, s.id, "CLICK",
        semantic_target={"locator": {"strategy": "role", "role": "button", "name": "续费"}, "password": "supersecret"},
        payload_ref={"token": "abc", "url": "http://x"},
    )
    assert json.loads(ev.semantic_target_json)["password"] == "<REDACTED>"
    assert json.loads(ev.payload_ref_json)["token"] == "<REDACTED>"
    assert json.loads(ev.payload_ref_json)["url"] == "http://x"


def test_sequence_increments(db):
    s = service.create_session(db, project_id=1, mission_id=1, environment_id=2, mode="OBSERVE", started_by=9)
    e1 = service.record_event(db, s.id, "NAVIGATION", semantic_target={"route": "/member"}, payload_ref=None)
    e2 = service.record_event(db, s.id, "CLICK", semantic_target={"name": "续费"}, payload_ref=None)
    assert e1.sequence == 1
    assert e2.sequence == 2


def test_derive_action_plan_with_observation_ref(db):
    s = service.create_session(db, project_id=1, mission_id=1, environment_id=2, mode="OBSERVE", started_by=9)
    service.record_event(db, s.id, "NAVIGATION", {"route": "/member"}, None)
    service.record_event(db, s.id, "CLICK", {"name": "续费"}, None)
    plan = service.derive_action_plan(db, s.id)
    assert DEFAULT_REGISTRY.validate(plan) == []
    commands = plan["commands"]
    assert commands[0]["action"] == "goto"
    assert commands[1]["action"] == "click"
    # every key action carries an observation ref
    assert all("observation_ref" in c for c in commands)


def test_stop_session(db):
    s = service.create_session(db, project_id=1, mission_id=1, environment_id=2, mode="OBSERVE", started_by=9)
    stopped = service.stop_session(db, s.id)
    assert stopped.status == "FINISHED"
    assert stopped.finished_at is not None


def test_get_session_missing_404(db):
    with pytest.raises(APIException) as exc:
        service.get_session(db, 9999)
    assert exc.value.http_status == 404
