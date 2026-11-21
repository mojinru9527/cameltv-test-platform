"""V16-003-R4 验收：外部 Secret Store（加密文件/KMS 抽象）与跨进程解析。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.aiqe.security.external_secret_store import (
    EncryptedFileStore,
    ExternalStoreUnavailable,
    build_external_store,
)
from app.aiqe.services.secret_vault import (
    SecretVaultUnavailable,
    clear_secret_vault_cache,
    get_secret_vault,
)
from app.core.config import settings


@pytest.fixture()
def store(tmp_path: Path) -> EncryptedFileStore:
    return EncryptedFileStore(path=tmp_path / "secrets.json", key=Fernet.generate_key().decode())


def _expires() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=10)


def test_encrypted_file_store_roundtrip_and_no_plaintext(store, tmp_path):
    store.put(
        handle_id="h1",
        value="CANARY-PLAINTEXT-VALUE",
        expires_at=_expires(),
        run_id="run-1",
        project_id=1,
    )
    entry = store.get("h1")
    assert entry is not None and entry.value == "CANARY-PLAINTEXT-VALUE"
    assert entry.run_id == "run-1" and entry.project_id == 1
    raw = (tmp_path / "secrets.json").read_text(encoding="utf-8")
    assert "CANARY-PLAINTEXT-VALUE" not in raw
    store.drop("h1")
    assert store.get("h1") is None
    assert store.purge_expired() == 0


def test_missing_or_invalid_key_fails_closed(tmp_path):
    with pytest.raises(ExternalStoreUnavailable):
        EncryptedFileStore(path=tmp_path / "x.json", key="")
    with pytest.raises(ExternalStoreUnavailable):
        EncryptedFileStore(path=tmp_path / "x.json", key="not-a-fernet-key")


def test_wrong_key_cannot_decrypt(tmp_path):
    path = tmp_path / "secrets.json"
    first = EncryptedFileStore(path=path, key=Fernet.generate_key().decode())
    first.put(handle_id="h1", value="v", expires_at=_expires(), run_id="r", project_id=1)
    other = EncryptedFileStore(path=path, key=Fernet.generate_key().decode())
    with pytest.raises(ExternalStoreUnavailable):
        other.get("h1")


def test_expired_entries_purged(store):
    past = datetime.now(UTC) - timedelta(seconds=5)
    store.put(handle_id="old", value="v", expires_at=past, run_id="r", project_id=1)
    store.put(handle_id="new", value="v", expires_at=_expires(), run_id="r", project_id=1)
    assert store.purge_expired() == 1
    assert store.get("old") is None
    assert store.get("new") is not None


def test_get_secret_vault_external_cross_instance(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode()
    path = tmp_path / "secrets.json"
    monkeypatch.setattr(settings, "use_external_secret_store", True)
    monkeypatch.setattr(settings, "aiqe_secret_store_provider", "file")
    monkeypatch.setattr(settings, "aiqe_secret_store_path", str(path))
    monkeypatch.setattr(settings, "aiqe_secret_store_key", key)
    clear_secret_vault_cache()
    try:
        vault = get_secret_vault()
        assert vault.backend == "file"
        vault.put(
            handle_id="h1",
            value="secret-value",
            expires_at=_expires(),
            run_id="run-1",
            project_id=1,
        )
        # 模拟新进程：清缓存后重新构造 vault，仍可解析同一 Handle
        clear_secret_vault_cache()
        again = get_secret_vault()
        entry = again.get("h1")
        assert entry is not None and entry.value == "secret-value"
        again.drop("h1")
        assert get_secret_vault().get("h1") is None
    finally:
        clear_secret_vault_cache()


def test_get_secret_vault_fails_closed_without_key(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "use_external_secret_store", True)
    monkeypatch.setattr(settings, "aiqe_secret_store_provider", "file")
    monkeypatch.setattr(settings, "aiqe_secret_store_path", str(tmp_path / "x.json"))
    monkeypatch.setattr(settings, "aiqe_secret_store_key", "")
    clear_secret_vault_cache()
    with pytest.raises(SecretVaultUnavailable):
        get_secret_vault()
    clear_secret_vault_cache()


def test_unknown_provider_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "aiqe_secret_store_provider", "unknown-cloud")
    with pytest.raises(ExternalStoreUnavailable):
        build_external_store()
