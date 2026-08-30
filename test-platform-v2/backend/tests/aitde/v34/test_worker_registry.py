"""AITDE V3.4 worker registry tests (V34-003 / V34-004)."""

from __future__ import annotations

from datetime import timedelta

from app.modules.aitde.common.enums import Capability, NetworkZone, WorkerStatus
from app.modules.aitde.workflow import repository, service
from app.modules.aitde.workflow.schemas import WorkerHeartbeatIn


def _heartbeat(key="worker-1", **overrides):
    defaults = {
        "worker_key": key,
        "name": "test-worker",
        "network_zone": NetworkZone.TEST,
        "version": "1.0",
        "machine_identity": "m==",
        "tags": {"team": "qa"},
        "capabilities": [Capability.HTTP, Capability.BROWSER],
    }
    defaults.update(overrides)
    return WorkerHeartbeatIn(**defaults)


def test_register_worker_upsert(db):
    data = service.register_worker(db, _heartbeat())
    assert data["status"] == WorkerStatus.ONLINE.value
    assert data["worker_key"] == "worker-1"

    # Re-heartbeat with a second version should not create a duplicate row.
    data2 = service.register_worker(db, _heartbeat(version="2.0"))
    assert data2["id"] == data["id"]
    workers = repository.list_workers(db)
    assert len(workers) == 1


def test_worker_capabilities_attached(db):
    service.register_worker(db, _heartbeat())
    item = service.get_worker(db, 1)
    assert set(item["capabilities"]) == {Capability.HTTP.value, Capability.BROWSER.value}


def test_set_worker_status_disable(db):
    service.register_worker(db, _heartbeat())
    updated = service.set_worker_status(db, 1, "DISABLED")
    assert updated["status"] == "DISABLED"


def test_get_worker_404(db):
    import pytest

    from app.core.exceptions import APIException

    with pytest.raises(APIException):
        service.get_worker(db, 9999)


def test_offline_detection(db):
    """An ONLINE worker with a stale heartbeat flips to OFFLINE (V34-005)."""
    from app.core.task_queue import utcnow

    service.register_worker(db, _heartbeat())
    row = repository.get_worker(db, 1)
    # Backdate the heartbeat beyond the stale window (naive UTC, matching utcnow).
    row.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    db.commit()

    reaped = repository.mark_offline_workers(db, stale_seconds=180)
    assert reaped == 1
    assert repository.get_worker(db, 1).status == WorkerStatus.OFFLINE.value


def test_fresh_heartbeat_stays_online(db):
    service.register_worker(db, _heartbeat())
    # last_heartbeat_at is set at registration (now), so nothing goes offline.
    reaped = repository.mark_offline_workers(db, stale_seconds=180)
    assert reaped == 0


def test_capability_router_browser_requires_browser_worker(db):
    import pytest

    from app.core.exceptions import APIException
    from app.modules.aitde.workflow.router import task_queue_router

    # HTTP-only worker in TEST zone.
    service.register_worker(db, _heartbeat(capabilities=[Capability.HTTP]))
    # Routeless BROWSER requirement must be refused (V34-006).
    with pytest.raises(APIException):
        task_queue_router.select_queue(
            db,
            network_zone=NetworkZone.TEST.value,
            required_capabilities=[Capability.BROWSER.value],
        )


def test_capability_router_zone_queue(db):
    from app.modules.aitde.workflow.router import task_queue_router

    service.register_worker(
        db,
        _heartbeat(key="worker-http", capabilities=[Capability.HTTP]),
    )
    queue = task_queue_router.select_queue(
        db,
        network_zone=NetworkZone.TEST.value,
        required_capabilities=[Capability.HTTP.value],
    )
    assert queue == "worker-test"


def test_capability_router_ignores_offline(db):
    import pytest

    from app.core.exceptions import APIException
    from app.modules.aitde.workflow.router import task_queue_router

    service.register_worker(db, _heartbeat(capabilities=[Capability.HTTP]))
    service.set_worker_status(db, 1, "OFFLINE")
    with pytest.raises(APIException):
        task_queue_router.select_queue(
            db,
            network_zone=NetworkZone.TEST.value,
            required_capabilities=[Capability.HTTP.value],
        )
