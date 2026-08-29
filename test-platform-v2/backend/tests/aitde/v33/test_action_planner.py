"""V33-003 ActionPlanner tests."""
from __future__ import annotations

from app.modules.aitde.command import DEFAULT_REGISTRY
from app.modules.aitde.command.planner import ActionPlanner

ORACLES = [
    {"oracle_key": "ui-member-active", "oracle_type": "UI"},
    {"oracle_key": "db-member-active", "oracle_type": "DB"},
]


def test_plan_builds_navigate_act_assert():
    planner = ActionPlanner()
    ir = planner.plan({"action": "renew_membership", "package": "monthly"}, ORACLES, route="/member")
    drivers = [c["driver"] for c in ir["commands"]]
    assert drivers[0] == "browser"
    assert "goto" in [c["action"] for c in ir["commands"]]
    assert "click" in [c["action"] for c in ir["commands"]]
    assert sum(1 for c in ir["commands"] if c["driver"] == "assertion") == 2
    # validate against registry
    assert DEFAULT_REGISTRY.validate(ir) == []


def test_plan_and_validate_ok():
    ir = ActionPlanner().plan_and_validate({"action": "renew"}, ORACLES, route="/x")
    assert ir["schema_version"] == "1.0"


def test_reject_oracle_mutation_false_for_frozen_oracles():
    ir = ActionPlanner().plan({"action": "renew"}, ORACLES, route="/x")
    assert ActionPlanner.reject_oracle_mutation(ir, ORACLES) is False


def test_reject_oracle_mutation_true_for_new_oracle():
    # candidate references a foreign oracle (not in the scenario's frozen set)
    ir = {
        "schema_version": "1.0",
        "commands": [{"driver": "assertion", "action": "evaluate", "input": {"oracle_key": "db-member-active"}}],
    }
    assert ActionPlanner.reject_oracle_mutation(ir, ORACLES) is False  # db-member-active IS frozen
    ir2 = {
        "schema_version": "1.0",
        "commands": [{"driver": "assertion", "action": "evaluate", "input": {"oracle_key": "NEW-oracle"}}],
    }
    assert ActionPlanner.reject_oracle_mutation(ir2, ORACLES) is True
