"""AIQE MCP stdio server（JSON-RPC 2.0，供 Codex CLI/Claude Code/Cursor 注册）。

启动：python scripts/mcp-server/aiqe_mcp/server.py
注册（示例）：codex mcp add cameltv-aiqe -- python /path/to/server.py
"""
from __future__ import annotations

import json
import sys
from typing import Any

try:  # 包内导入 / 脚本直跑
    from .gateway import AiqeMcpGateway, McpError
except ImportError:  # pragma: no cover - 脚本直跑
    from gateway import AiqeMcpGateway, McpError

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "cameltv-aiqe", "version": "1.0.0"}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message: dict[str, Any], gateway: AiqeMcpGateway) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid Request")
    request_id = message.get("id")
    method = message.get("method")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {"type": "object", "properties": {}},
                "_meta": {
                    "mode": tool["mode"],
                    "requires_approval": tool.get("requires_approval", False),
                },
            }
            for tool in gateway.list_tools()
        ]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = dict(params.get("arguments") or {})
        approval_token = arguments.pop("approval_token", None)
        try:
            result = gateway.call(name, arguments, approval_token=approval_token)
        except McpError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": False,
            },
        }
    return _error(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    gateway = AiqeMcpGateway(reader=lambda tool, args: {"tool": tool, "arguments": args})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_message(message, gateway)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
