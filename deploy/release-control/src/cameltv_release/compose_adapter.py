"""Render immutable release Compose definitions without invoking Docker."""
from __future__ import annotations

from typing import Any

from cameltv_release.contracts import ReleaseManifest


def render_release_compose(manifest: ReleaseManifest) -> dict[str, Any]:
    """Return a test-release definition bound exclusively to manifest digests."""
    return {
        "name": f"cameltv-release-{manifest.release_id}",
        "x-cameltv-release": {
            "release_id": manifest.release_id,
            "manifest_sha256": manifest.manifest_sha256(),
            "secret_refs": manifest.secret_refs,
        },
        "services": {
            "backend": {
                "image": f"{manifest.backend.image}@{manifest.backend.digest}",
                "restart": "unless-stopped",
            },
            "frontend": {
                "image": f"{manifest.frontend.image}@{manifest.frontend.digest}",
                "restart": "unless-stopped",
            },
        },
    }
