from __future__ import annotations

import sqlite3

from cameltv_release.store import ReleaseStore


def test_event_chain_detects_payload_tampering(tmp_path, manifest) -> None:
    database_path = tmp_path / "release-control.sqlite3"
    store = ReleaseStore(database_path)
    result = store.create_deployment(manifest, "test", "qa", "request-1")
    deployment_id = result.deployment.id
    store.append_event(deployment_id, "DRAFT", "VALIDATED", "validate", "manifest accepted")

    assert store.verify_event_chain(deployment_id) is True

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE deployment_events SET reason = ? WHERE deployment_id = ? AND sequence = 1",
            ("edited", deployment_id),
        )

    assert store.verify_event_chain(deployment_id) is False
