"""V16-003-R4: Vault Transit external KMS adapter (live HTTP, no mock fallback)."""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.aiqe.security.external_secret_store import (
    ExternalStoreUnavailable,
    VaultTransitStore,
)


class _Vault(BaseHTTPRequestHandler):
    fail = False

    def log_message(self, *_args):
        return

    def do_POST(self):
        if _Vault.fail:
            self.send_response(500)
            self.end_headers()
            return
        length = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/encrypt/aiqe-secrets"):
            raw = base64.b64decode(body.get("plaintext") or "")
            data = {"ciphertext": "vault:v1:" + base64.b64encode(raw).decode()}
        elif self.path.endswith("/decrypt/aiqe-secrets"):
            raw = base64.b64decode(str(body.get("ciphertext") or "").split(":", 2)[-1])
            data = {"plaintext": base64.b64encode(raw).decode()}
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps({"data": data}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def vault_server():
    _Vault.fail = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Vault)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_vault_roundtrip_and_ciphertext_only(vault_server, tmp_path):
    from datetime import UTC, datetime, timedelta

    path = tmp_path / "secrets.json"
    store = VaultTransitStore(
        path=path,
        addr=vault_server,
        token="test-token",
        mount="transit",
        key="aiqe-secrets",
    )
    store.put(
        handle_id="h1",
        value="plain-secret-value",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        run_id="run-1",
        project_id=1,
    )
    raw = path.read_text(encoding="utf-8")
    assert "plain-secret-value" not in raw
    entry = store.get("h1")
    assert entry is not None
    assert entry.value == "plain-secret-value"
    assert entry.run_id == "run-1"
    assert entry.project_id == 1


def test_vault_missing_config_fails_closed(tmp_path):
    with pytest.raises(ExternalStoreUnavailable):
        VaultTransitStore(path=tmp_path / "x.json", addr="", token="", key="")
    with pytest.raises(ExternalStoreUnavailable):
        VaultTransitStore(
            path=tmp_path / "x.json",
            addr="http://127.0.0.1:1",
            token="",
            key="aiqe-secrets",
        )


def test_vault_http_failure_fails_closed(vault_server, tmp_path):
    from datetime import UTC, datetime, timedelta

    store = VaultTransitStore(
        path=tmp_path / "secrets.json",
        addr=vault_server,
        token="test-token",
        key="aiqe-secrets",
    )
    _Vault.fail = True
    with pytest.raises(ExternalStoreUnavailable):
        store.put(
            handle_id="h1",
            value="x",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            run_id="r",
            project_id=1,
        )
