from __future__ import annotations

from cameltv_release.state_machine import ReleaseControlService
from cameltv_release.store import ReleaseStore


def test_production_request_is_rejected_before_persistence(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    result = service.request_test_deploy(manifest, "production", "ops", "production-1")

    assert result.code == "PRODUCTION_NOT_CONFIGURED"
    assert result.deployment is None
    assert store.count_deployments() == 0


def test_replay_returns_original_result_without_duplicate_transition(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    first = service.request_test_deploy(manifest, "test", "ops", "request-1")
    replay = service.request_test_deploy(manifest, "test", "ops", "request-1")

    assert replay.code == "IDEMPOTENT_REPLAY"
    assert replay.deployment.id == first.deployment.id
    assert store.count_deployments() == 1
