#!/usr/bin/env python
"""AITDE V3.4 worker-join drill (part of the live E2E validation).

Proves against the LIVE Temporal server (127.0.0.1:7233) that the backend worker:
  1. connects, registers a Worker on a TaskQueue, and starts polling ('worker joins');
  2. Temporal delivers a ScenarioExecutionWorkflow to that worker ('pullable');
  3. the worker executes the activity chain (deterministic echo, no real drivers)
     and the workflow COMPLETES.

Run from the backend directory:
    python exploit/drill_worker_join.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure the backend package is importable regardless of cwd.
BACKEND = Path(__file__).resolve().parents[1] if __file__.endswith(".py") else None
sys.path.insert(0, os.environ.get("AITDE_BACKEND", str(Path(__file__).resolve().parents[1])))

os.environ.setdefault("TEMPORAL_ENABLED", "true")
os.environ.setdefault("TEMPORAL_GRPC_ENDPOINT", "127.0.0.1:7233")
os.environ.setdefault("TEMPORAL_NAMESPACE", "default")
os.environ.setdefault("TEMPORAL_TASK_QUEUE", "worker-test")

from temporalio.client import Client
from temporalio.worker import Worker  # noqa: E402

from app.modules.aitde.workflow.gateway import get_activities  # noqa: E402
from app.temporal.workflows import ScenarioExecutionWorkflow  # noqa: E402

QUEUE = os.environ["TEMPORAL_TASK_QUEUE"]
ENDPOINT = os.environ["TEMPORAL_GRPC_ENDPOINT"]
NS = os.environ["TEMPORAL_NAMESPACE"]


async def main() -> int:
    client = await Client.connect(ENDPOINT, namespace=NS)
    print(f"[drill] connected client to {ENDPOINT} ns={NS}")

    payload = {"scenario_id": 1, "scenario_version_id": 3, "command_plan": []}
    workflow_id = "drill-worker-join-0001"

    # Start the worker (registers on the queue + polls).
    worker = Worker(
        client,
        task_queue=QUEUE,
        workflows=[ScenarioExecutionWorkflow],
        activities=list(get_activities()),
    )
    print(f"[drill] starting Worker on task_queue={QUEUE} (join + poll)")

    async with worker:
        # Give the worker a moment to register/poll, then start a workflow.
        await asyncio.sleep(2)
        handle = await client.start_workflow(
            ScenarioExecutionWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=QUEUE,
        )
        print(f"[drill] started workflow id={workflow_id} run_id={handle.first_execution_run_id}")

        # Wait for the workflow to complete (echo activities -> prompt result).
        result = await handle.result()
        print("[drill] workflow COMPLETED")
        history = result.get("history", [])
        steps = [h.get("step") for h in history]
        print(f"[drill] step count = {len(steps)}")
        for s in steps:
            print(f"    - {s}")

        ok = (
            len(steps) == 9
            and steps == [
                "capture_environment_snapshot", "plan_data", "ensure_fixture",
                "resolve_command_plan", "policy_check", "execute_commands",
                "evaluate_oracles", "collect_evidence", "classify_outcome",
            ]
        )
        print(f"\nRESULT: {'PASS' if ok else 'FAIL'} (worker joined queue + Temporal pulled + 9-step chain exec)")
        return 0 if ok else 1

    # Worker stopped (not reached while using context manager exit).
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
