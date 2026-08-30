"""AITDE V3.4 Execution Activities (V34-004).

Temporal Activity wrappers for the ScenarioExecutionWorkflow. Each Activity is
declared with a start/schedule timeout and retry policy in the workflow; the
``idempotency_key`` argument lets the IdempotencyService deduplicate a
re-delivered Activity so a crash/replay never repeats a business side effect.

PR34-01 keeps these as pass-through/lightweight adapters to the existing V3
runtime; later PRs wire the Data/API/Browser/Assertion/Evidence drivers into the
``fn`` hooks. Activities must remain deterministic (no `random`, no time-based
branching) so Temporal can replay them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from temporalio import activity


@dataclass
class StepResult:
    """A durable step result: status + summary + optional evidence refs."""

    status: str
    summary: str = ""
    evidence_refs: list[str] | None = None


# Pluggable executor hooks (default = pass-through echo). These are replaced by
# the real driver closures as the version grows — they must stay pure/deterministic.
_EXEC_HOOKS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def register_exec_hook(step_key: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """Register (or replace) the executor hook for a step key."""
    _EXEC_HOOKS[step_key] = fn


def _run_inner(step_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    hook = _EXEC_HOOKS.get(step_key)
    if hook is not None:
        return hook(payload)
    # Default: echo the payload so a skeleton workflow completes deterministically.
    return {"step": step_key, "echo": payload}


@activity.defn
async def capture_environment_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("capture_environment_snapshot", payload)


@activity.defn
async def plan_data(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("plan_data", payload)


@activity.defn
async def ensure_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("ensure_fixture", payload)


@activity.defn
async def resolve_command_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("resolve_command_plan", payload)


@activity.defn
async def policy_check(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("policy_check", payload)


@activity.defn
async def execute_commands(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("execute_commands", payload)


@activity.defn
async def evaluate_oracles(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("evaluate_oracles", payload)


@activity.defn
async def collect_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("collect_evidence", payload)


@activity.defn
async def classify_outcome(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("classify_outcome", payload)


@activity.defn
async def cleanup_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("cleanup_fixture", payload)


@activity.defn
async def build_replay(payload: dict[str, Any]) -> dict[str, Any]:
    return _run_inner("build_replay", payload)
