"""AITDE V3.7 diff provider tests (V37-003..007)."""

from __future__ import annotations

from app.modules.aitde.common.enums import LineageNodeType, RiskHint
from app.modules.aitde.smart_regression import diff as diff_mod


def test_requirement_diff_added_changed_deleted():
    baseline = {"frag1": {"content_hash": "a"}, "frag2": {"content_hash": "b"}}
    current = {
        "frag1": {"content_hash": "a"},
        "frag2": {"content_hash": "c"},
        "frag3": {"content_hash": "d"},
    }
    items = diff_mod.diff_requirement(baseline, current)
    by_key = {i["entity_key"]: i for i in items}
    # frag1 unchanged (same content_hash) -> no diff item
    assert "frag1" not in by_key
    assert by_key["frag2"]["change_kind"] == "CHANGED"
    assert by_key["frag2"]["risk_hint"] == RiskHint.RECENT_CHANGE.value
    assert by_key["frag3"]["change_kind"] == "ADDED"


def test_openapi_diff_breaking_required_removed():
    baseline = {
        "GET /orders": {
            "request_required": [],
            "responses": {"200": {"required": ["id", "status"]}},
        }
    }
    current = {
        "GET /orders": {
            "request_required": [],
            "responses": {"200": {"required": ["id"]}},
        }
    }
    items = diff_mod.diff_openapi(baseline, current)
    assert len(items) == 1
    assert items[0]["risk_hint"] == RiskHint.CONTRACT_RULE.value
    import json

    refs = json.loads(items[0]["source_refs_json"] or "[]")
    assert any("response_200_required_removed" in s or "status" in s for s in refs)


def test_db_schema_diff_enum_value_removed_is_contract():
    baseline = {
        "users": {"columns": {"id": {"type": "int"}}, "enums": {"status": ["a", "b"]}}
    }
    current = {
        "users": {"columns": {"id": {"type": "int"}}, "enums": {"status": ["a"]}}
    }
    items = diff_mod.diff_db_schema(baseline, current)
    assert len(items) == 1
    assert items[0]["entity_type"] == LineageNodeType.DATA_ENTITY.value
    assert items[0]["risk_hint"] == RiskHint.CONTRACT_RULE.value


def test_db_schema_added_table_low_risk():
    items = diff_mod.diff_db_schema(
        {},
        {"new_table": {"columns": {"id": {"type": "int"}}, "enums": {}, "indexes": []}},
    )
    assert items[0]["change_kind"] == "ADDED"
    assert items[0]["risk_hint"] == RiskHint.NONE.value


def test_ui_cosmetic_locator_change_low_risk():
    baseline = {
        "page1": {
            "semantic_hash": "s1",
            "actions": {"btn": {"semantic_hash": "b1", "selector": "old"}},
        }
    }
    current = {
        "page1": {
            "semantic_hash": "s1",
            "actions": {"btn": {"semantic_hash": "b1", "selector": "new"}},
        }
    }
    items = diff_mod.diff_ui_discovery(baseline, current)
    # cosmetic locator change, semantics unchanged -> no item
    assert items == []


def test_ui_semantic_action_added_risk():
    baseline = {"page1": {"semantic_hash": "s1", "actions": {}}}
    current = {
        "page1": {
            "semantic_hash": "s1",
            "actions": {"new_btn": {"semantic_hash": "b2", "selector": "x"}},
        }
    }
    items = diff_mod.diff_ui_discovery(baseline, current)
    assert len(items) == 1
    assert items[0]["risk_hint"] == RiskHint.RECENT_CHANGE.value


def test_environment_value_change_risk():
    items = diff_mod.diff_environment(
        {"TOKEN": {"value": "a", "sensitivity": "secret"}},
        {"TOKEN": {"value": "b", "sensitivity": "secret"}},
    )
    assert len(items) == 1
    assert items[0]["risk_hint"] == RiskHint.RECENT_CHANGE.value


def test_historical_risk_keeps_highest_per_scenario():
    signals = [
        {"scenario_id": 1, "risk_hint": RiskHint.RECENT_CHANGE.value},
        {"scenario_id": 1, "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value},
        {"scenario_id": 2, "risk_hint": RiskHint.NONE.value},
    ]
    items = diff_mod.diff_historical_risk(signals)
    s1 = next(i for i in items if i["entity_key"] == "1")
    s2 = next(i for i in items if i["entity_key"] == "2")
    assert s1["risk_hint"] == RiskHint.LAST_BUSINESS_FAIL.value
    assert s2["risk_hint"] == RiskHint.NONE.value
