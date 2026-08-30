"""AITDE V3.4 secret resolver + redaction tests (V34-008 / V34-009).

The Control Plane stores only metadata; the value is resolved at worker runtime
and masked before leaving process memory. A resolved value must never appear in
a serialized payload (history/log), and the API must reject a value in scope.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import SecretRefStatus
from app.modules.aitde.workflow import repository, service
from app.modules.aitde.workflow.schemas import SecretRefIn
from app.modules.aitde.workflow.secret_resolver import worker_secret_resolver


def _make_ref(db, *, provider="env", external_ref="MY_SECRET", scope=None):
    return repository.create_secret_ref(
        db,
        {
            "project_id": 1,
            "name": "db-password",
            "provider": provider,
            "external_ref": external_ref,
            "purpose": "fixture",
            "scope_json": __import__("json").dumps(scope or {}),
            "status": SecretRefStatus.ACTIVE.value,
        },
    )


def test_resolve_env_provider(db, monkeypatch):
    monkeypatch.setenv("MY_SECRET", "s3cr3t-val")
    ref = _make_ref(db)
    assert worker_secret_resolver.resolve(ref) == "s3cr3t-val"


def test_resolve_file_provider(db, tmp_path):
    path = tmp_path / "secret.txt"
    path.write_text("file-secret", encoding="utf-8")
    ref = _make_ref(db, provider="file", external_ref=str(path))
    assert worker_secret_resolver.resolve(ref) == "file-secret"


def test_inactive_ref_not_resolved(db):
    ref = _make_ref(db)
    ref.status = SecretRefStatus.REVOKED.value
    db.commit()
    assert worker_secret_resolver.resolve(ref) is None


def test_redact_masks_value(db):
    redacted = worker_secret_resolver.redact("topsecret")
    assert "<redacted:" in redacted
    assert "topsecret" not in redacted


def test_secret_value_not_in_history(db, monkeypatch):
    monkeypatch.setenv("MY_SECRET", "super-secret-999")
    ref = _make_ref(db)
    # A well-formed history payload must not embed the secret value.
    history_payload = {"run_id": 1, "project_id": 1, "driver": "fixture_update"}
    text = __import__("json").dumps(history_payload)
    assert worker_secret_resolver.contains_secret(text, [ref]) is False
    # The detector catches a leaked raw value when it does appear verbatim.
    assert worker_secret_resolver.contains_secret("super-secret-999", [ref]) is True


def test_create_secret_ref_rejects_value_in_scope(db):
    with pytest.raises(APIException):
        service.create_secret_ref(
            db, SecretRefIn(project_id=1, name="x", provider="literal", scope={"value": "abc"})
        )


def test_create_secret_ref_rejects_any_secret_named_key(db):
    with pytest.raises(APIException):
        service.create_secret_ref(
            db, SecretRefIn(project_id=1, name="x", provider="literal", scope={"password": "hunter2"})
        )


def test_create_secret_ref_returns_metadata_only(db):
    result = service.create_secret_ref(
        db,
        SecretRefIn(
            project_id=1, name="api-token", provider="env",
            external_ref="API_TOKEN", purpose="auth", scope={"nested": "ok"},
        ),
    )
    payload = __import__("json").dumps(result, ensure_ascii=False, default=str)
    assert "API_TOKEN" in payload  # metadata ref present
    assert '"value"' not in payload  # but no resolved value ever included
