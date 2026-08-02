from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from cameltv_release.contracts import ReleaseManifest


@pytest.fixture
def valid_manifest() -> dict[str, object]:
    return {
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


def test_manifest_hash_is_stable_across_input_key_order(valid_manifest: dict[str, object]) -> None:
    manifest = ReleaseManifest.model_validate(valid_manifest)
    reordered = ReleaseManifest.model_validate(dict(reversed(valid_manifest.items())))

    assert manifest.manifest_sha256() == reordered.manifest_sha256()
    assert len(manifest.manifest_sha256()) == 64


@pytest.mark.parametrize(
    ("mutate", "expected_path"),
    [
        (lambda value: value["frontend"].update({"digest": "latest"}), "frontend.digest"),
        (lambda value: value.update({"secret_key": "do-not-store"}), "secret_key"),
        (lambda value: value.update({"qa_evidence": []}), "qa_evidence"),
        (lambda value: value["database"].update({"alembic_heads": ["one", "two"]}), "database.alembic_heads"),
        (lambda value: value.update({"secret_refs": ["secret://production/cameltv/platform@v1"]}), "secret_refs"),
    ],
)
def test_manifest_rejects_unsafe_or_incomplete_input(
    valid_manifest: dict[str, object],
    mutate: object,
    expected_path: str,
) -> None:
    candidate = deepcopy(valid_manifest)
    mutate(candidate)  # type: ignore[operator]

    with pytest.raises(ValidationError) as error:
        ReleaseManifest.model_validate(candidate)

    assert expected_path in str(error.value)
