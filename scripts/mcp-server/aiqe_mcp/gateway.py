"""AIQE MCP Gateway（TA-032）。

只读工具供 Codex/Claude Code/Cursor 查询 Run；写动作必须携带审批 token。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: v1.5 §03 追加：A0 Gateway 必须与 REST 共用同一套 FastAPI Service，工具名使用规范命名。
#: scope 语义：READ/WRITE_DRAFT/EXECUTE_TEST/APPROVE/PROD_READONLY。
TOOL_SPECS: dict[str, dict[str, str]] = {
    "aiqe.project.get_context": {"scope": "READ", "description": "读取项目上下文与已批准对象"},
    "aiqe.requirement.analyze": {"scope": "WRITE_DRAFT", "description": "A1 生成 Contract Draft"},
    "aiqe.requirement.get": {"scope": "READ", "description": "读取 Requirement Contract"},
    "aiqe.testcase.generate": {"scope": "WRITE_DRAFT", "description": "A2 生成结构化 Case Draft"},
    "aiqe.testcase.review": {"scope": "APPROVE", "description": "测试设计审核（人工）"},
    "aiqe.workflow.plan": {"scope": "WRITE_DRAFT", "description": "A3 生成 Workflow Draft"},
    "aiqe.workflow.validate": {"scope": "READ", "description": "校验 Workflow 结构/能力"},
    "aiqe.run.launch": {"scope": "EXECUTE_TEST", "description": "启动 Run（需已批准 Workflow）"},
    "aiqe.run.get": {"scope": "READ", "description": "查询单个 Run"},
    "aiqe.run.events": {"scope": "READ", "description": "查询 Run 事件流"},
    "aiqe.triage.analyze": {"scope": "WRITE_DRAFT", "description": "A4 归因分析（draft）"},
    "aiqe.regression.plan": {"scope": "WRITE_DRAFT", "description": "A5 生成回归范围建议"},
    "aiqe.regression.launch": {"scope": "EXECUTE_TEST", "description": "发起回归（需部署证明）"},
    "aiqe.benchmark.run": {"scope": "EXECUTE_TEST", "description": "运行冻结 Benchmark"},
    "aiqe.learning.review": {"scope": "APPROVE", "description": "Learning Candidate 人工审核"},
    "aiqe.learning.activate": {"scope": "APPROVE", "description": "激活已批准规则"},
}
#: 旧名兼容（Codex/Claude 既有脚本仍可用），映射到同一 handler。
LEGACY_ALIASES: dict[str, str] = {
    "list_runs": "aiqe.project.get_context",
    "get_run": "aiqe.run.get",
    "get_run_events": "aiqe.run.events",
    "get_artifact_meta": "aiqe.run.get",
    "create_run": "aiqe.run.launch",
    "retry_run": "aiqe.run.launch",
}
#: Agent 永远不能通过 MCP 关闭缺陷/批准 Contract/激活规则。
FORBIDDEN_TOOLS: frozenset[str] = frozenset(
    {"close_defect", "approve_contract", "approve_workflow", "execute_sql"}
)
READ_SCOPES: frozenset[str] = frozenset({"READ", "PROD_READONLY"})
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
        return [
            {
                "name": name,
                "description": spec["description"],
                "mode": "read" if spec["scope"] in READ_SCOPES else "write",
                "scope": spec["scope"],
                "requires_approval": spec["scope"] not in READ_SCOPES,
            }
            for name, spec in TOOL_SPECS.items()
        ]

    @staticmethod
    def supported_agents() -> tuple[str, ...]:
        return SUPPORTED_AGENTS

    def call(
        self, tool: str, arguments: dict[str, Any], *, approval_token: str | None = None
    ) -> Any:
        if tool in FORBIDDEN_TOOLS:
            raise UnknownTool(f"工具禁止对 Agent 暴露: {tool}")
        canonical = tool if tool in TOOL_SPECS else LEGACY_ALIASES.get(tool)
        if canonical is None:
            raise UnknownTool(f"未知工具: {tool}")
        spec = TOOL_SPECS[canonical]
        if spec["scope"] in READ_SCOPES:
            if self.reader is None:
                raise McpError("read adapter 未配置")
            return self.reader(canonical, arguments)
        if not approval_token:
            raise ApprovalRequired(f"写操作 {canonical} 需要审批 token")
        if self.approval_verifier is None or not self.approval_verifier(
            approval_token, canonical, arguments
        ):
            raise ApprovalRequired("审批 token 无效")
        if self.writer is None:
            raise McpError("write adapter 未配置")
        return self.writer(canonical, arguments, approval_token)
