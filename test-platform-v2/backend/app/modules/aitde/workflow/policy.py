"""AITDE V3.4 PolicyGateway + IdempotencyService (V34-010 / V34-012).

PolicyGateway returns ALLOW | DENY | REQUIRE_APPROVAL for dangerous drivers. It
is a self-built provider adapter (OPA can be dropped in later). The security
invariant: dangerous drivers MUST be enforced here, never by hiding a button.

IdempotencyService protects Run/Data/Cleanup/Activity from duplicate delivery,
scoped by a ``(scope, key_hash)`` pair.
"""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import PolicyDecision
from app.modules.aitde.workflow import repository
from app.modules.aitde.workflow.schemas import PolicyDecisionIn


class PolicyGateway:
    """Evaluate a driver action against policy bindings for the target scope.

    Production zone is read-only (ALLOW only read drivers); TEST zone allows
    fixture writes; anything targeting a non-TEST zone with a write driver is
    DENY, and known risky writes (fixture_update, db_exec) require approval.
    """

    def evaluate(self, db: Session, request: PolicyDecisionIn) -> tuple[str, str]:
        driver = (request.driver or "").lower()
        action = (request.action or "").lower()
        zone = request.network_zone.value

        is_write = action in {
            "fixture_update",
            "db_exec",
            "create",
            "update",
            "delete",
            "insert",
            "grant",
        }

        # Production is strictly read-only (plan invariant "Production 默认只读").
        if zone == "PROD_RO":
            if is_write:
                return PolicyDecision.DENY.value, "PROD_RO zone is read-only"
            return PolicyDecision.ALLOW.value, "read-only driver allowed"

        # Dangerous DB drivers require approval even in TEST (plan §6).
        if driver == "database" and action in {"fixture_update", "db_exec"}:
            return (
                PolicyDecision.REQUIRE_APPROVAL.value,
                "database write driver requires approval",
            )

        if driver == "database" and is_write:
            return (
                PolicyDecision.REQUIRE_APPROVAL.value,
                "database write requires approval",
            )

        if is_write and zone == "OFFICE":
            return PolicyDecision.DENY.value, "OFFICE zone does not write test data"

        return PolicyDecision.ALLOW.value, "allowed by policy"


policy_gateway = PolicyGateway()


class IdempotencyService:
    """Dedup a runtime side effect by (scope, key_hash)."""

    def acquire(
        self, db: Session, scope: str, key: str, resource_type: str
    ) -> tuple[Any, bool]:
        """Return ``(row, first)`` — ``first`` True when this is the first delivery."""
        key_hash = hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()
        return repository.acquire_idempotency_key(db, scope, key_hash, resource_type)


idempotency_service = IdempotencyService()
