"""AITDE V3.4 ScenarioExecutionWorkflow (V34-003).

Deterministic Temporal orchestration following the V3.4 plan §2 activity chain.
Cleanup runs on the ``finally`` / compensation path, and every ``execute_activity``
declares timeouts + a retry policy so a crashed worker resumes without losing the
run.

The workflow module is deliberately import-light: it imports only ``temporalio``
and references its Activities by *name* (the worker binds the implementations).
This keeps the workflow deterministic and sandbox-clean — the Data/API/Browser/
Assertion/Evidence driver wiring lives entirely in the Activities module.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporalio.common import RetryPolicy

# Seconds. Long Browser/Data activities may override heartbeat per-call.
_START_SECONDS = 300
_SCHEDULE_SECONDS = 3600
_HEARTBEAT_SECONDS = 30

# The activity chain (plan §2). Names match the @activity.defn in activities.py.
_CHAIN: list[str] = [
    "capture_environment_snapshot",
    "plan_data",
    "ensure_fixture",
    "resolve_command_plan",
    "policy_check",
    "execute_commands",
    "evaluate_oracles",
    "collect_evidence",
    "classify_outcome",
]


@workflow.defn
class ScenarioExecutionWorkflow:
    """Durable execution of one frozen Scenario (V3.4 plan §2)."""

    @workflow.run
    async def run(self, scenario_input: dict[str, Any]) -> dict[str, Any]:
        """Create a chain of Activities with a shared retry policy.

        The workflow only orchestrates; it does not contain DB/UI detail.
        """
        retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        history: list[dict[str, Any]] = []
        try:
            for activity_name in _CHAIN:
                result = await workflow.execute_activity(
                    activity_name,
                    scenario_input,
                    start_to_close_timeout=timedelta(seconds=_START_SECONDS),
                    schedule_to_close_timeout=timedelta(seconds=_SCHEDULE_SECONDS),
                    heartbeat_timeout=timedelta(seconds=_HEARTBEAT_SECONDS),
                    retry_policy=retry,
                )
                history.append({"step": activity_name, "result": result})
        finally:
            # Compensation path: cleanup always runs, even on failure.
            await workflow.execute_activity(
                "cleanup_fixture",
                {"run": scenario_input, "history": history},
                start_to_close_timeout=timedelta(seconds=_START_SECONDS),
                schedule_to_close_timeout=timedelta(seconds=_SCHEDULE_SECONDS),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

        replay = await workflow.execute_activity(
            "build_replay",
            {"run": scenario_input, "history": history},
            start_to_close_timeout=timedelta(seconds=_START_SECONDS),
            schedule_to_close_timeout=timedelta(seconds=_SCHEDULE_SECONDS),
            retry_policy=retry,
        )
        return {"run": scenario_input, "history": history, "replay": replay}
