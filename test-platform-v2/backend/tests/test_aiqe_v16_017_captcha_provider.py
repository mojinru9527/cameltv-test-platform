"""V16-017 产品 TC：Playwright fill_http 验证码 Provider 单测。"""
from __future__ import annotations

import importlib.util
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py"


def _load():
    spec = importlib.util.spec_from_file_location("playwright_driver", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        body = b'{"code":"8421"}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_captcha_provider_reads_local_value():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert MODULE._captcha_provider_value(f"http://127.0.0.1:{port}/captcha") == "8421"
    finally:
        server.shutdown()
        server.server_close()


def test_captcha_provider_rejects_external_host():
    with pytest.raises(ValueError):
        MODULE._captcha_provider_value("http://example.com/captcha")


def test_captcha_provider_rejects_credentials_and_scheme():
    with pytest.raises(ValueError):
        MODULE._captcha_provider_value("http://user:pass@127.0.0.1/captcha")
    with pytest.raises(ValueError):
        MODULE._captcha_provider_value("file:///etc/passwd")


def test_fill_http_action_parsed():
    action = MODULE.PlaywrightAction.from_dict(
        {
            "type": "fill_http",
            "selector": "#code",
            "provider_url": "http://127.0.0.1:18080/captcha",
            "json_path": "$.code",
        }
    )
    assert action.type == "fill_http"
    assert action.provider_url.endswith("/captcha")
    assert action.json_path == "$.code"
