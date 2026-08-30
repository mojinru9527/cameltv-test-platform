#!/usr/bin/env python
"""AITDE V3.4 chaos drill: duplicate Activity delivery (PR34-11).

A Temporal worker can receive the same Activity more than once (crash + replay).
The IdempotencyStore must dedupe a re-delivered Activity so a business side
effect (e.g. a fixture) is never created twice.
"""
from __future__ import annotations


def run() -> bool:
    """Execute the duplicate-delivery drill against an in-memory store."""
    from app.core.db import SessionLocal
    from app.modules.aitde.workflow.policy import idempotency_service

    db = SessionLocal()
    try:
        row, first = idempotency_service.acquire(db, "activity", "dup-1", "ACTIVITY")
        _, duplicate = idempotency_service.acquire(db, "activity", "dup-1", "ACTIVITY")
        ok = first is True and duplicate is False
        print(f"[chaos] duplicate_activity_delivery -> first={first} duplicate={duplicate} ok={ok}")
        return ok
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
