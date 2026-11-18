"""AUD-013：Agent Registry + 调用关系 + 工具 allowlist。

规范编号（v1.5 §03 AUD-013）：

| A0 Orchestrator | A1 Requirement Assurance | A2 Test Design & Review | A3 Workflow Planner |
| A4 Failure & Noise Triage | A5 Change Impact & Regression | A6 Learning Curator |

- Agent 之间只能按 ``ALLOWED_CHILDREN`` 调用，子 Agent 不能任意调用未授权 Agent；
- 工具按 allowlist 授权（``DEFAULT_TOOL_ALLOWLIST``），Server 端权限层仍然生效。
"""
from __future__ import annotations

from collections.abc import Callable

from app.aiqe.agents.base import BaseAgent
from app.aiqe.agents.change_impact_agent import ChangeImpactAgent
from app.aiqe.agents.failure_triage_agent import FailureTriageAgent
from app.aiqe.agents.protocol import AgentProtocol, BaseAgentAdapter
from app.aiqe.agents.requirement_agent import RequirementAgent
from app.aiqe.agents.test_design_agent import TestDesignAgent
from app.aiqe.agents.workflow_planner_agent import WorkflowPlannerAgent

AGENT_NAMES: dict[str, str] = {
    "A0": "Orchestrator",
    "A1": "Requirement Assurance",
    "A2": "Test Design & Review",
    "A3": "Workflow Planner",
    "A4": "Failure & Noise Triage",
    "A5": "Change Impact & Regression",
    "A6": "Learning Curator",
}

#: 父 Agent 只能调度这些子 Agent（A0 为总编排）。
ALLOWED_CHILDREN: dict[str, tuple[str, ...]] = {
    "A0": ("A1", "A2", "A3", "A4", "A5", "A6"),
    "A1": ("A2",),
    "A2": ("A3",),
    "A3": (),
    "A4": ("A6",),
    "A5": (),
    "A6": (),
}

#: 工具 allowlist（名称 → 允许的 Agent）。未列出的工具任何 Agent 都不能用。
DEFAULT_TOOL_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "read_project_context": ("A0", "A1", "A2", "A3", "A4", "A5", "A6"),
    "read_requirements": ("A0", "A1", "A2", "A5"),
    "read_openapi": ("A1", "A2", "A3", "A5"),
    "read_run_evidence": ("A0", "A4", "A6"),
    "read_defects": ("A0", "A4", "A5", "A6"),
    "read_noise_rules": ("A4", "A6"),
    "read_git_diff": ("A5",),
    "read_benchmark_dataset": ("A6",),
    "create_draft": ("A0", "A1", "A2", "A3", "A4", "A6"),
    "create_regression_plan": ("A5",),
    "create_learning_candidate": ("A6",),
}

#: 写工具必须经过审批 token / 人工确认；Agent 永远不能获得这些能力。
FORBIDDEN_TOOLS: frozenset[str] = frozenset(
    {
        "close_defect",
        "approve_contract",
        "approve_workflow",
        "activate_rule",
        "run_production_write",
        "execute_sql",
        "launch_run",  # 只能通过 A0 Gateway + 人工审批
    }
)

_AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "A1": RequirementAgent,
    "A2": TestDesignAgent,
    "A3": WorkflowPlannerAgent,
    "A4": FailureTriageAgent,
    "A5": ChangeImpactAgent,
}


class AgentRegistryError(KeyError):
    pass


def tool_allowlist_for(agent_key: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            tool
            for tool, agents in DEFAULT_TOOL_ALLOWLIST.items()
            if agent_key in agents
        )
    )


def assert_child_allowed(parent: str, child: str) -> None:
    if parent not in ALLOWED_CHILDREN:
        raise AgentRegistryError(f"未知父 Agent: {parent!r}")
    if child not in ALLOWED_CHILDREN[parent]:
        raise AgentRegistryError(f"{parent} 不允许调用 {child}")
    if child in FORBIDDEN_TOOLS:
        raise AgentRegistryError(f"{child} 是受保护动作，不能作为子任务")


def build_tool_registry(tools: dict[str, Callable[..., object]] | None = None):
    from app.aiqe.agents.protocol import ToolRegistry

    allowlist = {
        agent_key: tool_allowlist_for(agent_key) for agent_key in AGENT_NAMES
    }
    return ToolRegistry(allowlist, tools or {})


def get_agent(
    key: str,
    llm: Callable[[str, str], str] | None = None,
    *,
    model: str | None = None,
) -> AgentProtocol:
    """按编号取 Agent（A0 由 orchestrator 提供，A6 由 learning curator 提供）。"""
    agent_key = str(key or "").strip().upper()
    if agent_key == "A0":
        from app.aiqe.agents.orchestrator_agent import OrchestratorAgent

        return OrchestratorAgent(llm, model=model)
    if agent_key == "A6":
        from app.aiqe.agents.learning_curator_agent import LearningCuratorAgent

        return LearningCuratorAgent(llm, model=model)
    agent_class = _AGENT_CLASSES.get(agent_key)
    if agent_class is None:
        raise AgentRegistryError(f"未注册的 Agent: {key!r}")
    adapter = BaseAgentAdapter(agent_class(llm, model=model), version="1.1.0")
    return adapter


def registered_keys() -> tuple[str, ...]:
    return tuple(sorted(AGENT_NAMES))


__all__ = [
    "AGENT_NAMES",
    "ALLOWED_CHILDREN",
    "DEFAULT_TOOL_ALLOWLIST",
    "FORBIDDEN_TOOLS",
    "AgentRegistryError",
    "assert_child_allowed",
    "build_tool_registry",
    "get_agent",
    "registered_keys",
    "tool_allowlist_for",
]
