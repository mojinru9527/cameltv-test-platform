from __future__ import annotations

import pytest

from cameltv_release.contracts import ReleaseManifest


@pytest.fixture
def manifest() -> ReleaseManifest:
    return ReleaseManifest.model_validate(
        {
            "schema_version": "1.0",
            "release_id": "b62-test-20260802-0001",
            "git_sha": "1" * 40,
            "frontend": {
                "image": "registry.test.invalid/cameltv/frontend",
                "digest": "sha256:" + "a" * 64,
                "sbom_sha256": "b" * 64,
            },
            "backend": {
                "image": "registry.test.invalid/cameltv/backend",
                "digest": "sha256:" + "c" * 64,
                "sbom_sha256": "d" * 64,
                "openapi_sha256": "e" * 64,
            },
            "database": {
                "alembic_heads": ["batch62_release_core"],
                "target_revision": "batch62_release_core",
                "rollback_mode": "application-rollback-or-forward-fix",
            },
            "config_schema": "platform-runtime/v1",
            "secret_refs": ["secret://test/cameltv/platform@v1"],
            "qa_evidence": ["artifact://batch62/qa-report.json"],
        }
    )
