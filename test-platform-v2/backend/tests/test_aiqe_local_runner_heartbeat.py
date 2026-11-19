"""Runner 能力心跳调用：平台 200 / 404 / 401 三种分支。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts" / "qa" / "aiqe_local_runner.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("aiqe_runner_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, headers=None, json=None):
        self.calls.append((url, headers, json))
        return self.response


def test_heartbeat_success_returns_data():
    module = load_runner()
    client = FakeClient(
        FakeResponse(200, {"code": 0, "data": {"node_id": "n1", "capability_status": "AVAILABLE"}})
    )
    result = module._capability_heartbeat(client, {"X-AI-Agent-Token": "t"}, "n1")
    assert result["capability_status"] == "AVAILABLE"
    assert client.calls[0][0] == "/api/v1/aiqe/nodes/n1/heartbeat"


def test_heartbeat_missing_manifest_is_non_fatal():
    module = load_runner()
    result = module._capability_heartbeat(
        FakeClient(FakeResponse(404)), {"X-AI-Agent-Token": "t"}, "n1"
    )
    assert result["status"] == "manifest_missing"
    assert "register_manifest" in result["hint"]


def test_heartbeat_unauthorized_is_non_fatal():
    module = load_runner()
    result = module._capability_heartbeat(
        FakeClient(FakeResponse(401)), {"X-AI-Agent-Token": "t"}, "n1"
    )
    assert result["status"] == "unauthorized"
