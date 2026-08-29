"""FixtureLeaseService (V32-010): concurrency isolation via leases + TTL.

A fixture may be leased exclusively to one run at a time. A second exclusive
lease from a different run is rejected (destructive runs never share).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import FixtureLeaseStatus, FixtureStatus
from app.modules.aitde.data import repository
from app.modules.aitde.data.models import FixtureLease


def lease_fixture(
    db: Session, fixture_id: int, run_id: int, ttl_seconds: int = 3600
) -> FixtureLease:
    fixture = repository.get_fixture(db, fixture_id)
    if not fixture:
        raise APIException(code=404, msg="Fixture 不存在", http_status=404)
    if fixture.status not in (FixtureStatus.READY.value, FixtureStatus.LEASED.value):
        raise APIException(
            code=400, msg=f"Fixture 状态 {fixture.status} 不可租约", http_status=400
        )

    now = datetime.now()
    active = repository.get_active_lease_for_fixture(db, fixture_id)
    if active:
        if active.run_id != run_id:
            raise APIException(
                code=409, msg="Fixture 已被其他 Run 独占", http_status=409
            )
        # Same run re-request: refresh TTL, idempotent (no duplicate row).
        active.expires_at = now + timedelta(seconds=ttl_seconds)
        db.commit()
        db.refresh(active)
        return active

    lease = repository.create_fixture_lease(
        db,
        {
            "fixture_id": fixture_id,
            "run_id": run_id,
            "lease_token": secrets.token_urlsafe(24),
            "status": FixtureLeaseStatus.ACTIVE.value,
            "leased_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
        },
    )
    if fixture.status != FixtureStatus.LEASED.value:
        fixture.status = FixtureStatus.LEASED.value
    db.commit()
    db.refresh(lease)
    db.refresh(fixture)
    return lease


def release_lease(db: Session, lease_id: int) -> FixtureLease:
    lease = db.get(FixtureLease, lease_id)
    if not lease:
        raise APIException(code=404, msg="租约不存在", http_status=404)
    lease.status = FixtureLeaseStatus.RELEASED.value
    lease.released_at = datetime.now()
    fixture = repository.get_fixture(db, lease.fixture_id)
    if fixture and fixture.status == FixtureStatus.LEASED.value:
        fixture.status = FixtureStatus.READY.value
    db.commit()
    db.refresh(lease)
    return lease
