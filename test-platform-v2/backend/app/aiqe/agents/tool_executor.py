"""V16-019：Agent 工具调用执行器。

职责
----
- 统一由 Agent 侧调用 ``ToolExecutor.call()``，内部走 ``BoundToolRegistry.resolve()``
  完成授权/审批/审计，禁止 Agent 直接访问数据库或 HTTP；
- 记录**真实发生**的工具调用（名称 + 参数摘要），供 ``AgentResult.tool_calls`` 与
  ToolExecutionAudit 对账；
- 工具不可用/越权/异常一律 fail-closed：抛给调用方，由 Agent 决定 BLOCKED。

红线
----
``create_tool_calls`` 只从本执行器产生；Agent 不得自行伪造 tool_calls。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

MAX_SUMMARY_CHARS = 200


def _digest(arguments: dict[str, Any]) -> dict[str, Any]:
    """参数摘要：只保留长度受限的可读值，避免把 Secret/大对象落库。"""
    summary: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str):
            summary[key] = value[:MAX_SUMMARY_CHARS]
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[key] = value
        elif isinstance(value, (list, tuple)):
            summary[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            summary[key] = f"dict[{len(value)}]"
        else:
            summary[key] = type(value).__name__
    return summary


@dataclass
class ToolInvocation:
    agent_key: str
    tool_name: str
    arguments: dict[str, Any]
    ok: bool = True
    error: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "tool": self.tool_name,
            "agent": self.agent_key,
            "arguments": dict(self.arguments),
            "ok": self.ok,
        }
        if self.error:
            payload["error"] = self.error[:MAX_SUMMARY_CHARS]
        return payload


@dataclass
class ToolExecutor:
    """绑定到单个 Agent 任务/Agent 的工具执行器。"""

    registry: Any
    agent_key: str
    task_id: str | None = None
    #: Agent 证据参数（run_id / base_sha / head_sha 等），来自 AgentContext。
    references: Mapping[str, Any] = field(default_factory=dict)
    invocations: list[ToolInvocation] = field(default_factory=list)

    def available(self) -> tuple[str, ...]:
        allowed = getattr(self.registry, "allowed", None)
        if callable(allowed):
            try:
                return tuple(allowed(self.agent_key))
            except Exception:  # pragma: no cover - 授权表异常按不可用处理
                return ()
        return ()

    def call(self, tool_name: str, **arguments: Any) -> Any:
        if tool_name not in self.available():
            raise PermissionError(f"{self.agent_key} 未被授权调用工具 {tool_name}")
        tool = self.registry.resolve(self.agent_key, tool_name)
        invocation = ToolInvocation(
            agent_key=self.agent_key,
            tool_name=tool_name,
            arguments=_digest(arguments),
        )
        try:
            result = tool(**arguments)
        except Exception as exc:
            invocation.ok = False
            invocation.error = f"{type(exc).__name__}: {exc}"
            self.invocations.append(invocation)
            raise
        self.invocations.append(invocation)
        return result

    def safe_call(self, tool_name: str, **arguments: Any) -> dict[str, Any]:
        """收集证据用：失败不抛出，返回显式 error，Agent 必须把 error 带入结论。"""
        try:
            return {"ok": True, "data": self.call(tool_name, **arguments)}
        except PermissionError as exc:
            return {"ok": False, "error": f"TOOL_NOT_ALLOWED: {exc}"}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def tool_calls(self) -> list[dict[str, Any]]:
        return [invocation.to_payload() for invocation in self.invocations]


__all__ = ["ToolExecutor", "ToolInvocation"]
