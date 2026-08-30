"""AITDE V3.4 policy gateway + idempotency tests (V34-010 / V34-012)."""

from __future__ import annotations

from app.modules.aitde.common.enums import NetworkZone, PolicyDecision
from app.modules.aitde.workflow.policy import IdempotencyService, policy_gateway
from app.modules.aitde.workflow.schemas import PolicyDecisionIn


def test_prod_ro_rejects_write(db):
    req = PolicyDecisionIn(
        actor="user",
        project_id=1,
        environment_id=5,
        network_zone=NetworkZone.PROD_RO,
        driver="database",
        action="fixture_update",
        target={"schema": "prod", "table": "membership"},
    )
    decision, reason = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.DENY.value
    assert "read-only" in reason


def test_prod_ro_allows_read(db):
    req = PolicyDecisionIn(
        network_zone=NetworkZone.PROD_RO, driver="http", action="get", target={}
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.ALLOW.value


def test_database_write_requires_approval_in_test(db):
    req = PolicyDecisionIn(
        network_zone=NetworkZone.TEST,
        driver="database",
        action="fixture_update",
        target={"schema": "member_test"},
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.REQUIRE_APPROVAL.value


def test_office_write_denied(db):
    req = PolicyDecisionIn(
        network_zone=NetworkZone.OFFICE, driver="http", action="insert", target={}
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.DENY.value


def test_plain_http_read_allowed(db):
    req = PolicyDecisionIn(
        network_zone=NetworkZone.TEST, driver="http", action="get", target={}
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.ALLOW.value


def test_idempotency_first_delivery_only(db):
    svc = IdempotencyService()
    row, first = svc.acquire(db, "run", "workflow-123", "ACTIVITY")
    assert row is not None
    assert first is True

    row2, first2 = svc.acquire(db, "run", "workflow-123", "ACTIVITY")
    assert row2 is not None and row2.id == row.id
    assert first2 is False


def test_idempotency_unique_scope(db):
    svc = IdempotencyService()
    _, first_a = svc.acquire(db, "run", "key", "ACTIVITY")
    _, first_b = svc.acquire(db, "cleanup", "key", "CLEANUP")
    assert first_a is True
    assert first_b is True
