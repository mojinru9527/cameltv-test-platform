"""AIQE MCP Gateway（TA-032）。

只读工具供 Codex/Claude Code/Cursor 查询 Run；写动作必须携带审批 token。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

READ_TOOLS = {
    "list_runs": "按项目/状态分页查询 Run",
    "get_run": "查询单个 Run 详情与状态",
    "get_run_events": "查询 Run 事件流",
    "get_artifact_meta": "查询证据元数据",
}
WRITE_TOOLS = {
    "create_run": "创建 Run（需审批）",
    "retry_run": "重试 Run（需审批）",
    "close_defect": "关闭缺陷（需审批）",
}
SUPPORTED_AGENTS = ("claude-code", "codex", "cursor")


class McpError(RuntimeError):
    pass


class UnknownTool(McpError):
    pass


class ApprovalRequired(McpError):
    pass


class AiqeMcpGateway:
    def __init__(
        self,
        *,
        reader: Callable[[str, dict], Any] | None = None,
        writer: Callable[[str, dict, str], Any] | None = None,
        approval_verifier: Callable[[str, str, dict], bool] | None = None,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.approval_verifier = approval_verifier

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        tools = [
            {"name": name, "description": desc, "mode": "read"}
            for name, desc in READ_TOOLS.items()
        ]
        tools += [
            {"name": name, "description": desc, "mode": "write", "requires_approval": True}
            for name, desc in WRITE_TOOLS.items()
        ]
        return tools

    @staticmethod
    def supported_agents() -> tuple[str, ...]:
        return SUPPORTED_AGENTS

    def call(
        self, tool: str, arguments: dict[str, Any], *, approval_token: str | None = None
    ) -> Any:
        if tool in READ_TOOLS:
            if self.reader is None:
                raise McpError("read adapter 未配置")
            return self.reader(tool, arguments)
        if tool in WRITE_TOOLS:
            if not approval_token:
                raise ApprovalRequired(f"写操作 {tool} 需要审批 token")
            if self.approval_verifier is None or not self.approval_verifier(
                approval_token, tool, arguments
            ):
                raise ApprovalRequired("审批 token 无效")
            if self.writer is None:
                raise McpError("write adapter 未配置")
            return self.writer(tool, arguments, approval_token)
        raise UnknownTool(f"未知工具: {tool}")
