"""AITDE V3.4 worker registry tests (V34-003 / V34-004)."""

from __future__ import annotations

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
