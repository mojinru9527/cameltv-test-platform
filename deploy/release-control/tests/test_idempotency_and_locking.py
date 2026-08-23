from __future__ import annotations

from cameltv_release.state_machine import ReleaseControlService
from cameltv_release.store import ReleaseStore


def test_unsupported_environment_is_rejected_before_persistence(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    result = service.request_deploy(manifest, "staging", "ops", "staging-1")

    assert result.code == "UNSUPPORTED_ENVIRONMENT"
    assert result.deployment is None
    assert store.count_deployments() == 0


def test_production_request_is_accepted_when_unlocked(tmp_path, manifest) -> None:
    """腾讯云 production 发布（release-platform batch）允许登记 production 部署。"""
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    result = service.request_deploy(manifest, "production", "ops", "production-1")

    assert result.code == "ACCEPTED"
    assert result.deployment.environment == "production"
    assert store.count_deployments() == 1


def test_production_lock_blocks_second_request(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    first = service.request_deploy(manifest, "production", "ops", "production-1")
    assert first.code == "ACCEPTED"
    second = service.request_deploy(manifest, "production", "ops", "production-2")
    assert second.code == "ENVIRONMENT_LOCKED"


def test_replay_returns_original_result_without_duplicate_transition(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    first = service.request_deploy(manifest, "test", "ops", "request-1")
    replay = service.request_deploy(manifest, "test", "ops", "request-1")

    assert replay.code == "IDEMPOTENT_REPLAY"
    assert replay.deployment.id == first.deployment.id
    assert store.count_deployments() == 1
