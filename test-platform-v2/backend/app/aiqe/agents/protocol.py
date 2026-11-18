"""AUD-013：Agent Protocol / AgentResult / ToolRegistry（v1.5 §03 AUD-013）。

每个 Agent 必须继承统一协议并返回 ``AgentResult``（含版本、模型、Prompt、输入输出
hash、tool calls、source refs、token 用量、warnings、needs_human）。

现有 ``BaseAgent``（同步 ``run(input_text)``）通过 ``BaseAgentAdapter`` 适配到协议，
保持既有 Agent 与测试兼容；新 Agent 直接实现 ``execute()``。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.aiqe.agents.base import AgentSchemaError, AgentUnavailable, BaseAgent

AGENT_STATUSES: tuple[str, ...] = (
    "QUEUED",
    "RUNNING",
    "WAITING_HUMAN",
    "PARTIAL",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
)
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"COMPLETED", "FAILED", "CANCELLED", "WAITING_HUMAN", "PARTIAL"}
)


class AgentContractError(ValueError):
    """AgentResult / 任务计划违反协议。"""


class ToolNotAllowed(PermissionError):
    """Agent 调用了未授权工具。"""

    def __init__(self, agent_key: str, tool_name: str) -> None:
        super().__init__(f"TOOL_NOT_ALLOWED: {agent_key} cannot use {tool_name}")
        self.code = "TOOL_NOT_ALLOWED"
        self.agent_key = agent_key
        self.tool_name = tool_name


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


class ToolRegistry:
    """按 Agent allowlist 授权工具；未授权/未注册一律 fail-closed。"""

    def __init__(
        self,
        allowlist: Mapping[str, tuple[str, ...]],
        tools: Mapping[str, Callable[..., Any]] | None = None,
    ) -> None:
        self._allowlist = {key: tuple(value) for key, value in allowlist.items()}
        self._tools = dict(tools or {})

    def allowed(self, agent_key: str) -> tuple[str, ...]:
        return self._allowlist.get(str(agent_key), ())

    def resolve(self, agent_key: str, tool_name: str) -> Callable[..., Any]:
        if tool_name not in self.allowed(agent_key):
            raise ToolNotAllowed(str(agent_key), tool_name)
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotAllowed(str(agent_key), f"{tool_name} (未注册实现)")
        return tool


@dataclass(frozen=True)
class AgentContext:
    project_id: int
    actor_id: int | None = None
    run_id: str | None = None
    idempotency_key: str | None = None
    tools: ToolRegistry | None = None
    evidence_resolver: Callable[[list[str]], list[Any]] | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_key: str
    agent_version: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model_provider: str = ""
    model_name: str = ""
    prompt_version: str = ""
    input_hash: str = ""
    output_hash: str = ""
    token_usage: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    warnings: list[str] = field(default_factory=list)
    needs_human: bool = False
    error_code: str = ""

    def validate(self) -> None:
        if self.status not in AGENT_STATUSES:
            raise AgentContractError(f"非法 Agent 状态: {self.status!r}")
        if not self.agent_key:
            raise AgentContractError("agent_key 不能为空")
        if not self.agent_version:
            raise AgentContractError("agent_version 不能为空")
        if self.status == "COMPLETED" and not self.output:
            raise AgentContractError("COMPLETED 必须有非空 output（空输出不能当成功）")
        if self.needs_human and self.status not in {"WAITING_HUMAN", "PARTIAL"}:
            raise AgentContractError("needs_human=true 时状态必须是 WAITING_HUMAN/PARTIAL")
        if self.status == "WAITING_HUMAN" and not self.needs_human:
            raise AgentContractError("WAITING_HUMAN 必须 needs_human=true")

    def payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "agent_key": self.agent_key,
            "agent_version": self.agent_version,
            "status": self.status,
            "output": self.output,
            "source_refs": list(self.source_refs),
            "tool_calls": list(self.tool_calls),
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "token_usage": dict(self.token_usage),
            "warnings": list(self.warnings),
            "needs_human": self.needs_human,
            "error_code": self.error_code,
        }


@runtime_checkable
class AgentProtocol(Protocol):
    key: str
    version: str

    @property
    def model(self) -> str: ...

    def execute(self, context: AgentContext, request: str) -> AgentResult: ...


class BaseAgentAdapter:
    """把既有同步 ``BaseAgent`` 适配成 ``AgentProtocol``。"""

    key: str
    version: str
    provider: str
    name: str

    def __init__(
        self,
        agent: BaseAgent,
        *,
        key: str | None = None,
        version: str = "1.0.0",
        provider: str = "",
        name: str | None = None,
    ) -> None:
        self._agent = agent
        self.key = key or str(agent.key)
        self.version = version
        self.provider = provider
        self.name = name or f"{self.key}-schema-agent"

    @property
    def model(self) -> str:
        return str(self._agent.model)

    def execute(self, context: AgentContext, request: str) -> AgentResult:
        input_hash = stable_hash(request)
        try:
            output = self._agent.run(request)
        except AgentUnavailable as exc:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                model_provider=self.provider,
                model_name=self.model,
                prompt_version=stable_hash(self._agent.system_prompt),
                input_hash=input_hash,
                error_code="MODEL_UNAVAILABLE",
                warnings=[str(exc)],
            )
        except AgentSchemaError as exc:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                model_provider=self.provider,
                model_name=self.model,
                prompt_version=stable_hash(self._agent.system_prompt),
                input_hash=input_hash,
                error_code="SCHEMA_INVALID",
                warnings=[str(exc)],
            )
        return AgentResult(
            agent_key=self.key,
            agent_version=self.version,
            status="COMPLETED",
            output=output,
            model_provider=self.provider,
            model_name=self.model,
            prompt_version=stable_hash(self._agent.system_prompt),
            input_hash=input_hash,
            output_hash=stable_hash(output),
        )


__all__ = [
    "AGENT_STATUSES",
    "TERMINAL_STATUSES",
    "AgentContext",
    "AgentContractError",
    "AgentProtocol",
    "AgentResult",
    "BaseAgentAdapter",
    "ToolNotAllowed",
    "ToolRegistry",
    "stable_hash",
]
