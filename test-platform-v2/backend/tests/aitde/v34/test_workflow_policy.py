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


def test_internal_driver_no_bypass_prod_ro(db):
    """An internal driver still cannot write to PROD_RO (V34-010)."""
    req = PolicyDecisionIn(
        actor="worker",
        network_zone=NetworkZone.PROD_RO,
        driver="database",
        action="db_exec",
        target={"schema": "prod"},
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.DENY.value


def test_internal_driver_no_bypass_requires_approval(db):
    """An internal database write in TEST still requires approval (no bypass)."""
    req = PolicyDecisionIn(
        actor="worker",
        network_zone=NetworkZone.TEST,
        driver="database",
        action="fixture_update",
        target={"schema": "member_test"},
    )
    decision, _ = policy_gateway.evaluate(db, req)
    assert decision == PolicyDecision.REQUIRE_APPROVAL.value


def test_idempotency_expiry_marks_stale_pending(db):
    from app.modules.aitde.workflow import repository
    from datetime import datetime, timedelta

    svc = IdempotencyService()
    row, _ = svc.acquire(db, "run", "expired-key", "ACTIVITY")
    # Backdate the key so it's stale.
    row.created_at = datetime.now().replace(tzinfo=None) - timedelta(days=2)
    db.commit()

    expired = svc.expire(db, stale_seconds=86400)
    assert expired == 1
    assert repository.RuntimeIdempotencyKey.__table__ is not None  # model registered
    refreshed = db.get(type(row), row.id)
    assert refreshed.status == "FAILED"
