from __future__ import annotations

import json

from cameltv_release.store import ReleaseStore


def test_deployment_export_never_includes_manifest_secret_references(tmp_path, manifest) -> None:
    store = ReleaseStore(tmp_path / "release-control.sqlite3")
    result = store.create_deployment(manifest, "test", "qa", "request-1")

    exported = store.export_deployment(result.deployment.id)

    assert json.loads(exported)["environment"] == "test"
    assert "secret://" not in exported
    assert "platform@v1" not in exported
