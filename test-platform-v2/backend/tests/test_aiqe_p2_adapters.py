"""P2：MCP HTTP adapter + 真实执行探针单测。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.aiqe.adapters.probes import command_available, collect_probes, module_available, probe_appium

ROOT = Path(__file__).resolve().parents[3]
MCP_DIR = ROOT / "scripts" / "mcp-server" / "aiqe_mcp"


def load_adapter():
    sys.path.insert(0, str(MCP_DIR))
    spec = importlib.util.spec_from_file_location("aiqe_http_adapter_under_test", MCP_DIR / "http_adapter.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or FakeResponse()

    def get(self, url, params=None, headers=None):
        self.calls.append(("GET", url, params, headers))
        return self.response

    def post(self, url, json=None, headers=None):
        self.calls.append(("POST", url, json, headers))
        return self.response


def test_reader_get_run():
    module = load_adapter()
    client = FakeClient(FakeResponse(200, {"id": "run-1"}))
    adapter = module.HttpMcpAdapter("http://x", token="t", client=client)
    assert adapter.reader("get_run", {"run_id": "run-1"})["id"] == "run-1"
    assert client.calls[0][3]["Authorization"] == "Bearer t"


def test_writer_passes_approval_header():
    module = load_adapter()
    client = FakeClient(FakeResponse(200, {"ok": True}))
    adapter = module.HttpMcpAdapter("http://x", client=client)
    adapter.writer("create_run", {"scenario": "s"}, "approve-1")
    assert client.calls[0][3]["X-Approval-Token"] == "approve-1"


def test_http_error_raises():
    module = load_adapter()
    client = FakeClient(FakeResponse(500, {"error": "boom"}))
    adapter = module.HttpMcpAdapter("http://x", client=client)
    with pytest.raises(module.HttpMcpAdapterError):
        adapter.reader("list_runs", {})


def test_probes(monkeypatch):
    class Client:
        def get(self, url):
            return FakeResponse(200)

    assert probe_appium("http://appium:4723", client=Client()) is True
    assert probe_appium("", client=Client()) is False
    monkeypatch.setattr("app.aiqe.adapters.probes.command_available", lambda name: name == "minium")
    monkeypatch.setattr("app.aiqe.adapters.probes.module_available", lambda name: name == "paho")
    result = collect_probes({"AIQE_APPIUM_URL": ""})
    assert result["minium_cli"] is True
    assert result["paho_mqtt"] is True
    assert result["appium_reachable"] is False
