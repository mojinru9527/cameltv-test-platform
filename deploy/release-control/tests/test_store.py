from __future__ import annotations

from cameltv_release.store import ReleaseStore


def test_repeated_key_returns_original_deployment(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")

    first = store.create_deployment(manifest, "test", "qa", "request-1")
    replay = store.create_deployment(manifest, "test", "qa", "request-1")

    assert replay.replayed is True
    assert replay.deployment.id == first.deployment.id
    assert store.count_deployments() == 1


def test_competing_release_is_rejected_by_environment_lock(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    store.create_deployment(manifest, "test", "qa", "request-1")

    result = store.create_deployment(manifest, "test", "qa", "request-2")

    assert result.code == "ENVIRONMENT_LOCKED"
    assert store.count_deployments() == 1


def test_new_deployment_records_an_initial_hash_linked_audit_event(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")

    result = store.create_deployment(manifest, "test", "qa", "request-1")

    assert store.list_events(result.deployment.id) == [
        {
            "sequence": 1,
            "from_state": "",
            "to_state": "DRAFT",
            "phase": "register",
            "reason": "test deployment registered",
            "actor": "qa",
        }
    ]
    assert store.verify_event_chain(result.deployment.id) is True


def test_same_release_id_cannot_be_reused_with_changed_manifest(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    store.create_deployment(manifest, "test", "qa", "request-1")
    changed_manifest = manifest.model_copy(update={"config_schema": "platform-runtime/v2"})

    result = store.create_deployment(changed_manifest, "test", "qa", "request-2")

    assert result.code == "RELEASE_ID_CONFLICT"
    assert store.count_deployments() == 1
