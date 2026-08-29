"""V33-011 Healing Proposal persistence + service tests.

Covers the durable Action Healing Proposal path: guard-driven creation (OPEN for
action-only diffs, REJECTED+audit for oracle/contract mutations), list filtering,
and open-only approve/reject with immutable REJECTED proposals.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.browser import healing_service
from app.modules.aitde.browser.models import HealingProposal
from app.modules.aitde.common.enums import HealingProposalStatus


def _ir(commands):
    return {"schema_version": "1.0", "commands": commands}


def _action_only_before():
    return _ir([
        {"id": "1", "driver": "browser", "action": "goto", "input": {"route": "/member"}},
        {"id": "2", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "续费"}}},
    ])


def _action_only_after():
    return _ir([
        {"id": "1", "driver": "browser", "action": "goto", "input": {"route": "/member"}},
        {"id": "2", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "立即续费"}}},
    ])


def _oracle_mutated():
    return _ir([
        {"id": "1", "driver": "browser", "action": "click", "input": {"locator": {"strategy": "role", "role": "button", "name": "续费"}}},
        {"id": "2", "driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-active-NEW"}},
    ])


# ── create_proposal ──
def test_action_only_diff_persists_as_open(db):
    p = healing_service.create_proposal(
        db, scenario_adapter_id=7, command_plan_version_id=11,
        before_ir=_action_only_before(), after_ir=_action_only_after(), reason="locator drift",
    )
    assert p.id is not None
    assert p.status == HealingProposalStatus.OPEN.value
    assert p.proposal_type == "LOCATOR"
    assert p.reason == "locator drift"
    # JSON-string columns round-trip to objects via to_dict
    d = healing_service.to_dict(p)
    assert d["before_json"]["commands"][0]["action"] == "goto"
    assert d["after_json"]["commands"][1]["input"]["locator"]["name"] == "立即续费"


def test_oracle_mutation_persists_as_rejected(db):
    p = healing_service.create_proposal(
        db, scenario_adapter_id=7, command_plan_version_id=11,
        before_ir=_action_only_before(), after_ir=_oracle_mutated(), reason="bad suggestion",
        created_by_type="AI",
    )
    assert p.status == HealingProposalStatus.REJECTED.value
    assert "oracle_contract_mutation" in p.reason
    d = healing_service.to_dict(p)
    assert d["created_by_type"] == "AI"


# ── list_proposals ──
def test_list_filters_by_scenario_and_status(db):
    healing_service.create_proposal(db, 7, 11, _action_only_before(), _action_only_after(), "a")
    healing_service.create_proposal(db, 7, 12, _action_only_before(), _oracle_mutated(), "b")
    healing_service.create_proposal(db, 9, 20, _action_only_before(), _action_only_after(), "c")

    all_rows = healing_service.list_proposals(db)
    assert len(all_rows) == 3

    scoped = healing_service.list_proposals(db, scenario_adapter_id=7)
    assert len(scoped) == 2

    open_scoped = healing_service.list_proposals(db, scenario_adapter_id=7, status=HealingProposalStatus.OPEN.value)
    assert len(open_scoped) == 1
    assert open_scoped[0].status == HealingProposalStatus.OPEN.value


# ── approve / reject ──
def test_approve_open_proposal(db):
    p = healing_service.create_proposal(db, 7, 11, _action_only_before(), _action_only_after(), "a")
    approved = healing_service.approve_proposal(db, p.id, reviewed_by=42)
    assert approved.status == HealingProposalStatus.APPROVED.value
    assert approved.reviewed_by == 42
    assert approved.reviewed_at is not None


def test_reject_open_proposal(db):
    p = healing_service.create_proposal(db, 7, 11, _action_only_before(), _action_only_after(), "a")
    rejected = healing_service.reject_proposal(db, p.id, reviewed_by=42)
    assert rejected.status == HealingProposalStatus.REJECTED.value


def test_cannot_approve_oracle_mutation(db):
    p = healing_service.create_proposal(db, 7, 11, _action_only_before(), _oracle_mutated(), "bad")
    # An oracle/contract mutation is created REJECTED and immutable at OPEN — no
    # approve path exists.
    assert p.status == HealingProposalStatus.REJECTED.value
    with pytest.raises(APIException) as exc:
        healing_service.approve_proposal(db, p.id, reviewed_by=42)
    assert exc.value.http_status == 409


def test_cannot_approve_a_closed_proposal(db):
    p = healing_service.create_proposal(db, 7, 11, _action_only_before(), _action_only_after(), "a")
    healing_service.reject_proposal(db, p.id, reviewed_by=42)
    with pytest.raises(APIException) as exc:
        healing_service.approve_proposal(db, p.id, reviewed_by=42)
    assert exc.value.http_status == 409


def test_missing_proposal_raises_404(db):
    with pytest.raises(APIException) as exc:
        healing_service.get_proposal(db, 999)
    assert exc.value.http_status == 404


# ── routes registered ──
def test_healing_routes_registered():
    """Smoke-check the healing-proposals routes are mounted under /api/v2."""
    from app.main import app

    paths = set(app.openapi()["paths"].keys())
    assert "/api/v2/healing-proposals" in paths
    assert "/api/v2/healing-proposals/{proposal_id}/approve" in paths
    assert "/api/v2/healing-proposals/{proposal_id}/reject" in paths
