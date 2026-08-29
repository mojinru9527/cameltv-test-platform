"""V33-001 Command IR Schema Registry tests."""
from __future__ import annotations

from app.modules.aitde.command import DEFAULT_REGISTRY


def _ir(commands):
    return {"schema_version": "1.0", "commands": commands}


def test_valid_command_ir_passes():
    doc = _ir([
        {"id": "1", "driver": "data", "action": "ensure", "input": {"requirement_ref": "expired-member"}},
        {"id": "2", "driver": "browser", "action": "goto", "input": {"route": "/member"}},
        {"id": "3", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "立即续费"}}},
        {"id": "4", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-member-active"}},
    ])
    assert DEFAULT_REGISTRY.validate(doc) == []


def test_unknown_driver_rejected():
    doc = _ir([{"id": "1", "driver": "unknown", "action": "foo", "input": {}}])
    errors = DEFAULT_REGISTRY.validate(doc)
    assert any(e.get("code") == "unknown_driver" for e in errors)


def test_unknown_action_rejected():
    doc = _ir([{"id": "1", "driver": "browser", "action": "teleport", "input": {}}])
    errors = DEFAULT_REGISTRY.validate(doc)
    assert any(e.get("code") == "unknown_action" for e in errors)


def test_missing_required_input_rejected():
    # goto requires an input.route
    doc = _ir([{"id": "1", "driver": "browser", "action": "goto", "input": {}}])
    errors = DEFAULT_REGISTRY.validate(doc)
    assert any(e.get("code") == "missing_input" for e in errors)


def test_schema_version_mismatch_flagged():
    doc = {"schema_version": "9.9", "commands": [
        {"driver": "browser", "action": "goto", "input": {"route": "/"}},
    ]}
    errors = DEFAULT_REGISTRY.validate(doc)
    assert any(e.get("code") == "schema_version_mismatch" for e in errors)


def test_commands_required():
    assert any(e.get("code") == "commands_required" for e in DEFAULT_REGISTRY.validate({"schema_version": "1.0", "commands": []}))


def test_no_input_action_allowed():
    doc = _ir([{"id": "1", "driver": "browser", "action": "capture_screenshot", "input": {}}])
    assert DEFAULT_REGISTRY.validate(doc) == []
