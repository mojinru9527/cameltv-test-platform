"""未来娃屿生产只读探测（futurewayu_production_readonly.py）离线测试。"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/per_tc/futurewayu_production_readonly.py"


def _load():
    spec = importlib.util.spec_from_file_location("futurewayu_readonly", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


class _Handler(BaseHTTPRequestHandler):
    hits: list[str] = []

    def log_message(self, *_args):
        return

    def do_GET(self):
        _Handler.hits.append(self.path)
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        _Handler.hits.append("POST:" + self.path)
        self.send_response(500)
        self.end_headers()


def _server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_no_urls_is_not_proven():
    env = {"PATH": "", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        env={**env, "FUTUREWAYU_BASE_URL": "", "FUTUREWAYU_ADMIN_URL": ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NOT_PROVEN" in result.stdout


def test_get_only_guard():
    try:
        MODULE._request("POST", "https://example.invalid/api")
    except PermissionError as exc:
        assert "只读" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("POST 必须被只读守卫拒绝")


def test_probes_against_local_fake_server(tmp_path):
    _Handler.hits = []
    server = _server()
    try:
        port = server.server_address[1]
        output = tmp_path / "prod.json"
        env = {
            **os.environ,
            "FUTUREWAYU_BASE_URL": f"http://127.0.0.1:{port}",
            "FUTUREWAYU_ADMIN_URL": "",
            "FUTUREWAYU_ADMIN_TOKEN": "",
            "FUTUREWAYU_DB_READONLY_DSN": "",
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(output)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["status"] == "PROBED"
        assert payload["readonly_only"] is True
        assert payload["probes"] and all(item["method"] == "GET" for item in payload["probes"])
        assert not any(hit.startswith("POST:") for hit in _Handler.hits)
    finally:
        server.shutdown()
        server.server_close()


def test_parse_mysql_dsn():
    parsed = MODULE._parse_mysql_dsn("mysql://ro_user:secret@db.example:3307/futurewayu")
    assert parsed["host"] == "db.example"
    assert parsed["port"] == 3307
    assert parsed["user"] == "ro_user"
    assert parsed["password"] == "secret"
    assert parsed["database"] == "futurewayu"
