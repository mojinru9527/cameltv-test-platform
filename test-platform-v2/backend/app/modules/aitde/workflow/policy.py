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

        # No bypass allowed: an "internal" driver takes the exact same path as a
        # user drive — Production stays read-only, dangerous DB writes still
        # require approval. V34-010 "internal driver 无绕过".
        if zone == "PROD_RO":
            if is_write:
                return PolicyDecision.DENY.value, "PROD_RO zone is read-only"
            return PolicyDecision.ALLOW.value, "read-only driver allowed"

        # Dangerous DB drivers require approval even in TEST (plan §6), and this
        # applies to internal drivers too (no bypass).
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

    def expire(self, db: Session, stale_seconds: int = 86400) -> int:
        """Mark stale PENDING idempotency keys as FAILED (V34-012 TTL).

        A key that has not been completed within its window is no longer a valid
        dedup guard, so a re-delivered activity may proceed rather than being
        silently swallowed.
        """
        from app.modules.aitde.common.enums import IdempotencyStatus
        from datetime import datetime, timedelta
        from sqlalchemy import select

        cutoff = (
            datetime.now().replace(tzinfo=None) - timedelta(seconds=max(1, stale_seconds))
        )
        rows = db.scalars(
            select(repository.RuntimeIdempotencyKey).where(
                repository.RuntimeIdempotencyKey.status == IdempotencyStatus.PENDING.value,
                repository.RuntimeIdempotencyKey.created_at < cutoff,
            )
        ).all()
        for r in rows:
            r.status = IdempotencyStatus.FAILED.value
        db.commit()
        return len(rows)


idempotency_service = IdempotencyService()
