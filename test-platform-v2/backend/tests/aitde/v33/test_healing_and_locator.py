"""V33-011 Healing guard + V33-004 semantic locator tests."""
from __future__ import annotations

from app.modules.aitde.browser.healing import HealingGuard
from app.modules.aitde.browser.locator import SemanticLocatorResolver


def _ir(commands):
    return {"schema_version": "1.0", "commands": commands}


def test_action_only_change_allows_proposal():
    before = _ir([
        {"id": "1", "driver": "browser", "action": "goto", "input": {"route": "/member"}},
        {"id": "2", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "续费"}}},
    ])
    after = _ir([
        {"id": "1", "driver": "browser", "action": "goto", "input": {"route": "/member"}},
        {"id": "2", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "立即续费"}}},
    ])
    proposal = HealingGuard().create_proposal(before, after, "locator drift")
    assert proposal["approved"] is True
    assert proposal["status"] == "OPEN"
    assert proposal["proposal_type"] == "LOCATOR"
    assert proposal["audit"] is False


def test_oracle_mutation_rejected():
    before = _ir([
        {"id": "1", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "续费"}}},
        {"id": "2", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-active"}},
    ])
    after = _ir([
        {"id": "1", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "续费"}}},
        {"id": "2", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-active-NEW"}},  # changed oracle
    ])
    proposal = HealingGuard().create_proposal(before, after, "bad suggestion")
    assert proposal["approved"] is False
    assert proposal["status"] == "REJECTED"
    assert proposal["audit"] is True
    assert "oracle_contract_mutation" in proposal["reason"]


def test_detect_mutation_reports_oracle_change():
    before = _ir([{"id": "2", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-active"}}])
    after = _ir([{"id": "2", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "db-active"}}])
    result = HealingGuard().detect_mutation(before, after)
    assert result["oracle_mutation"] is True
    assert result["changed"] is True


# ── V33-004 locator ──
def test_locator_priority_data_testid():
    sel = SemanticLocatorResolver().resolve({"data-testid": "renew", "role": "button"})
    assert sel["strategy"] == "data-testid"
    assert sel["selector"] == "renew"


def test_locator_role_name():
    sel = SemanticLocatorResolver().resolve({"role": "button", "name": "立即续费"})
    assert sel["strategy"] == "role"
    assert sel["selector"] == 'role=button[name="立即续费"]'


def test_locator_text_fallback():
    sel = SemanticLocatorResolver().resolve({"text": "续费"})
    assert sel["strategy"] == "text"
    assert sel["selector"] == "续费"


def test_locator_direct_strategy_selector():
    sel = SemanticLocatorResolver().resolve({"strategy": "css", "selector": "#btn"})
    assert sel["selector"] == "#btn"
