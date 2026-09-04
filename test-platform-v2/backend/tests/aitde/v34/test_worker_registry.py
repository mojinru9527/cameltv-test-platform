"""AITDE V3.4 worker registry tests (V34-003 / V34-004)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import event

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


def test_register_worker_records_naive_utc_heartbeat(db, monkeypatch):
    fixed_utc = datetime(2026, 9, 3, 12, 0, 0)
    monkeypatch.setattr(service, "utcnow", lambda: fixed_utc)

    service.register_worker(db, _heartbeat())

    assert repository.get_worker(db, 1).last_heartbeat_at == fixed_utc


def test_worker_capabilities_attached(db):
    service.register_worker(db, _heartbeat())
    item = service.get_worker(db, 1)
    assert set(item["capabilities"]) == {Capability.HTTP.value, Capability.BROWSER.value}


def test_list_workers_includes_capabilities_with_one_bulk_query(db):
    service.register_worker(
        db,
        _heartbeat(key="worker-http", capabilities=[Capability.HTTP]),
    )
    service.register_worker(
        db,
        _heartbeat(key="worker-browser", capabilities=[Capability.BROWSER]),
    )

    statements: list[str] = []

    def capture_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        items = service.list_workers(db)
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)

    capabilities_by_key = {
        item["worker_key"]: set(item["capabilities"])
        for item in items
    }
    assert capabilities_by_key == {
        "worker-http": {Capability.HTTP.value},
        "worker-browser": {Capability.BROWSER.value},
    }
    capability_queries = [
        statement
        for statement in statements
        if "worker_capabilities" in statement.lower()
    ]
    assert len(capability_queries) == 1


def test_set_worker_status_disable(db):
    service.register_worker(db, _heartbeat())
    updated = service.set_worker_status(db, 1, "DISABLED")
    assert updated["status"] == "DISABLED"


def test_admin_worker_states_survive_later_heartbeats(db):
    service.register_worker(db, _heartbeat())

    for status in (WorkerStatus.DRAINING.value, WorkerStatus.DISABLED.value):
        service.set_worker_status(db, 1, status)
        heartbeat = service.register_worker(db, _heartbeat(version="2.0"))
        assert heartbeat["status"] == status


def test_offline_worker_returns_online_on_heartbeat(db):
    service.register_worker(db, _heartbeat())
    service.set_worker_status(db, 1, WorkerStatus.OFFLINE.value)

    heartbeat = service.register_worker(db, _heartbeat(version="2.0"))

    assert heartbeat["status"] == WorkerStatus.ONLINE.value


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


def test_list_workers_marks_stale_heartbeat_offline(db):
    from app.core.task_queue import utcnow

    service.register_worker(db, _heartbeat())
    row = repository.get_worker(db, 1)
    row.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    db.commit()

    items = service.list_workers(db)

    assert items[0]["status"] == WorkerStatus.OFFLINE.value


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


def test_capability_router_rejects_stale_online_worker(db):
    import pytest

    from app.core.exceptions import APIException
    from app.core.task_queue import utcnow
    from app.modules.aitde.workflow.router import task_queue_router

    service.register_worker(db, _heartbeat(capabilities=[Capability.HTTP]))
    row = repository.get_worker(db, 1)
    row.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    db.commit()

    with pytest.raises(APIException):
        task_queue_router.select_queue(
            db,
            network_zone=NetworkZone.TEST.value,
            required_capabilities=[Capability.HTTP.value],
        )
