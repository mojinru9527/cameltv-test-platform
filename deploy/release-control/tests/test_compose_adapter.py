from __future__ import annotations

from cameltv_release.compose_adapter import render_release_compose


def test_release_compose_binds_images_to_manifest_digests(manifest) -> None:
    compose = render_release_compose(manifest)

    assert compose["services"]["backend"]["image"] == f"{manifest.backend.image}@{manifest.backend.digest}"
    assert compose["services"]["frontend"]["image"] == f"{manifest.frontend.image}@{manifest.frontend.digest}"
    assert "build" not in compose["services"]["backend"]
    assert "build" not in compose["services"]["frontend"]
    assert "latest" not in str(compose)


def test_release_compose_uses_only_secret_references(manifest) -> None:
    compose = render_release_compose(manifest)

    assert compose["x-cameltv-release"]["secret_refs"] == manifest.secret_refs
    assert "environment" not in compose["services"]["backend"]
