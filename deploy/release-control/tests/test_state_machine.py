from __future__ import annotations

from cameltv_release.state_machine import ReleaseControlService
from cameltv_release.store import ReleaseStore


def test_test_deployment_follows_legal_states_and_releases_lock(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    accepted = service.request_deploy(manifest, "test", "ops", "request-1")
    deployment_id = accepted.deployment.id
    assert accepted.code == "ACCEPTED"
    assert service.transition(deployment_id, "VALIDATED", "validate").code == "ACCEPTED"
    assert service.transition(deployment_id, "TEST_DEPLOYING", "deploy").code == "ACCEPTED"
    assert service.transition(deployment_id, "TEST_VERIFYING", "verify").code == "ACCEPTED"
    assert service.transition(deployment_id, "TEST_VERIFIED", "smoke").code == "ACCEPTED"
    assert store.get_deployment(deployment_id).state == "TEST_VERIFIED"

    next_request = service.request_deploy(manifest, "test", "ops", "request-2")
    assert next_request.code == "ACCEPTED"


def test_production_deployment_follows_legal_states_and_releases_lock(tmp_path, manifest) -> None:
    """腾讯云 production 发布状态链（release-platform batch）。"""
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)

    accepted = service.request_deploy(manifest, "production", "ops", "prod-1")
    deployment_id = accepted.deployment.id
    assert accepted.code == "ACCEPTED"
    assert service.transition(deployment_id, "VALIDATED", "validate").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_DEPLOYING", "deploy").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_OBSERVING", "observe").code == "ACCEPTED"
    assert service.transition(deployment_id, "PRODUCTION_VERIFIED", "smoke").code == "ACCEPTED"
    assert store.get_deployment(deployment_id).state == "PRODUCTION_VERIFIED"

    # 锁在终态释放，可登记下一条 production
    next_request = service.request_deploy(manifest, "production", "ops", "prod-2")
    assert next_request.code == "ACCEPTED"


def test_production_rollback_chain(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)
    deployment_id = service.request_deploy(manifest, "production", "ops", "prod-rl-1").deployment.id

    assert service.transition(deployment_id, "VALIDATED", "validate").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_DEPLOYING", "deploy").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_FAILED", "health").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_ROLLING_BACK", "rollback").code == "ACCEPTED"
    assert service.transition(deployment_id, "PROD_ROLLED_BACK", "rollback").code == "ACCEPTED"
    assert store.get_deployment(deployment_id).state == "PROD_ROLLED_BACK"


def test_illegal_transition_does_not_change_state_or_event_chain(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)
    deployment_id = service.request_deploy(manifest, "test", "ops", "request-1").deployment.id

    result = service.transition(deployment_id, "TEST_VERIFIED", "skip-validation")

    assert result.code == "INVALID_TRANSITION"
    assert store.get_deployment(deployment_id).state == "DRAFT"
    assert store.verify_event_chain(deployment_id) is True


def test_cancel_from_draft(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    service = ReleaseControlService(store)
    deployment_id = service.request_deploy(manifest, "production", "ops", "prod-cancelled").deployment.id

    assert service.transition(deployment_id, "CANCELLED", "cancel").code == "ACCEPTED"
    assert store.get_deployment(deployment_id).state == "CANCELLED"
