"""M5 / TA-032：AIQE MCP Gateway 单测。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATEWAY_PATH = ROOT / "scripts" / "mcp-server" / "aiqe_mcp" / "gateway.py"


def load_gateway():
    spec = importlib.util.spec_from_file_location("aiqe_mcp_gateway_under_test", GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def gateway_module():
    return load_gateway()


def test_read_tool_delegates(gateway_module):
    calls = []

    def reader(tool, args):
        calls.append((tool, args))
        return {"run_id": "run-1", "status": "PASS"}

    gateway = gateway_module.AiqeMcpGateway(reader=reader)
    result = gateway.call("aiqe.run.get", {"run_id": "run-1"})
    assert result["status"] == "PASS"
    assert calls == [("aiqe.run.get", {"run_id": "run-1"})]


def test_write_requires_approval(gateway_module):
    written = []
    gateway = gateway_module.AiqeMcpGateway(writer=lambda *args: written.append(args))
    with pytest.raises(gateway_module.ApprovalRequired):
        gateway.call("aiqe.run.launch", {"scenario": "x"})
    assert written == []


def test_write_invalid_token_rejected(gateway_module):
    gateway = gateway_module.AiqeMcpGateway(
        writer=lambda *args: None,
        approval_verifier=lambda token, tool, args: False,
    )
    with pytest.raises(gateway_module.ApprovalRequired):
        gateway.call("aiqe.run.launch", {}, approval_token="bad")


def test_write_with_valid_token(gateway_module):
    captured = []

    def writer(tool, args, token):
        captured.append((tool, args, token))
        return {"ok": True}

    gateway = gateway_module.AiqeMcpGateway(
        writer=writer,
        approval_verifier=lambda token, tool, args: token == "approved-1",
    )
    result = gateway.call("aiqe.run.launch", {"run_id": "run-1"}, approval_token="approved-1")
    assert result == {"ok": True}
    assert captured == [("aiqe.run.launch", {"run_id": "run-1"}, "approved-1")]


def test_unknown_tool(gateway_module):
    with pytest.raises(gateway_module.UnknownTool):
        gateway_module.AiqeMcpGateway(reader=lambda *a: None).call("drop_database", {})


def test_tool_metadata_and_agents(gateway_module):
    tools = {tool["name"]: tool for tool in gateway_module.AiqeMcpGateway.list_tools()}
    assert tools["aiqe.run.get"]["mode"] == "read"
    assert tools["aiqe.run.launch"]["requires_approval"] is True
    assert gateway_module.AiqeMcpGateway.supported_agents() == ("claude-code", "codex", "cursor")


def test_missing_reader_adapter(gateway_module):
    with pytest.raises(gateway_module.McpError):
        gateway_module.AiqeMcpGateway().call("list_runs", {})


def test_spec_tool_names_and_scopes(gateway_module):
    tools = {tool["name"]: tool for tool in gateway_module.AiqeMcpGateway.list_tools()}
    for name in (
        "aiqe.project.get_context",
        "aiqe.requirement.analyze",
        "aiqe.requirement.get",
        "aiqe.testcase.generate",
        "aiqe.testcase.review",
        "aiqe.workflow.plan",
        "aiqe.workflow.validate",
        "aiqe.run.launch",
        "aiqe.run.get",
        "aiqe.run.events",
        "aiqe.triage.analyze",
        "aiqe.regression.plan",
        "aiqe.regression.launch",
        "aiqe.benchmark.run",
        "aiqe.learning.review",
        "aiqe.learning.activate",
    ):
        assert name in tools, name
    assert tools["aiqe.run.get"]["scope"] == "READ"
    assert tools["aiqe.run.events"]["mode"] == "read"
    assert tools["aiqe.run.launch"]["scope"] == "EXECUTE_TEST"
    assert tools["aiqe.learning.review"]["scope"] == "APPROVE"
    assert tools["aiqe.testcase.generate"]["requires_approval"] is True


def test_forbidden_tools_are_never_exposed(gateway_module):
    names = {tool["name"] for tool in gateway_module.AiqeMcpGateway.list_tools()}
    assert "close_defect" not in names
    gateway = gateway_module.AiqeMcpGateway(reader=lambda tool, args: 1)
    with pytest.raises(gateway_module.UnknownTool):
        gateway.call("close_defect", {})


def test_legacy_alias_maps_to_canonical_handler(gateway_module):
    calls: list[str] = []
    gateway = gateway_module.AiqeMcpGateway(reader=lambda tool, args: calls.append(tool))
    gateway.call("get_run", {"run_id": "r-1"})
    gateway.call("list_runs", {})
    assert calls == ["aiqe.run.get", "aiqe.project.get_context"]
