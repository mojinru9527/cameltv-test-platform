"""M7 / TA-036：AIQE MCP stdio server 单测。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MCP_DIR = ROOT / "scripts" / "mcp-server" / "aiqe_mcp"


def load_server():
    sys.path.insert(0, str(MCP_DIR))
    spec = importlib.util.spec_from_file_location("aiqe_mcp_server_under_test", MCP_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def server_module():
    return load_server()


def gateway(server_module, *, reader=None, writer=None, verifier=None):
    return server_module.AiqeMcpGateway(
        reader=reader or (lambda tool, args: {"run_id": "run-1", "status": "PASS"}),
        writer=writer,
        approval_verifier=verifier,
    )


def test_initialize(server_module):
    response = server_module.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, gateway(server_module)
    )
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "cameltv-aiqe"


def test_tools_list(server_module):
    response = server_module.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, gateway(server_module)
    )
    tools = {tool["name"]: tool for tool in response["result"]["tools"]}
    assert tools["get_run"]["_meta"]["mode"] == "read"
    assert tools["create_run"]["_meta"]["requires_approval"] is True


def test_tools_call_read(server_module):
    response = server_module.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_run", "arguments": {"run_id": "run-1"}},
        },
        gateway(server_module),
    )
    assert response["result"]["isError"] is False
    assert json.loads(response["result"]["content"][0]["text"])["status"] == "PASS"


def test_write_without_token_returns_error(server_module):
    response = server_module.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "create_run", "arguments": {}},
        },
        gateway(server_module, writer=lambda *a: None),
    )
    assert response["result"]["isError"] is True
    assert "审批" in response["result"]["content"][0]["text"]


def test_unknown_method(server_module):
    response = server_module.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "resources/list"}, gateway(server_module)
    )
    assert response["error"]["code"] == -32601
