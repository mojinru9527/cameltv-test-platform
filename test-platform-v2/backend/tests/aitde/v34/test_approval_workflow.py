"""AITDE V3.4 approval workflow integration test (V34-011).

Runs the real ScenarioExecutionWorkflow against the in-memory Temporal server and
proves the approval gate: a ``REQUIRE_APPROVAL`` policy decision holds the
workflow until an ``approve`` Signal; ``approved`` resumes and ``rejected``
aborts before the dangerous step (never runs it).
"""
from __future__ import annotations

from app.modules.aitde.workflow import gateway as gw


def _run_approval_workflow(payload, *, decision, wait_until_signal=False):
    import asyncio

    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    async def main():
        env = await WorkflowEnvironment.start_local()
        client = env.client
        async with Worker(
            client,
            task_queue="worker-test",
            workflows=[gw.ScenarioExecutionWorkflow],
            activities=gw.get_activities(),
        ):
            handle = await client.start_workflow(
                gw.ScenarioExecutionWorkflow.run,
                payload,
                id="wf-approval-1",
                task_queue="worker-test",
            )
            if wait_until_signal:
                await asyncio.sleep(1)
            await handle.signal("approve", {"approved": decision, "reason": "review"})
            try:
                result = await asyncio.wait_for(handle.result(), timeout=10)
                return {"ok": True, "result": result}
            except asyncio.TimeoutError:
                return {"ok": False, "error": "TIMEOUT"}
            except Exception as exc:  # noqa: BLE001 — workflow failure surfaces here
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            finally:
                await env.shutdown()

    return asyncio.run(main())


def _policy_payload(**overrides):
    # A unique run_id keeps the activity idempotency keys fresh per execution; a hard
    # coded run_id would let a prior run's keys make the activities return a
    # ``duplicate`` skip, so policy_check never reports REQUIRE_APPROVAL on re-runs.
    import uuid

    data = {
        "run_id": int(uuid.uuid4().int % 10_000_000_000),
        "project_id": 1,
        "scenario_id": 1,
        "network_zone": "TEST",
        "driver": "database",
        "action": "fixture_update",
        "target": {"schema": "member_test"},
    }
    data.update(overrides)
    return data


def test_approval_gate_approve_resumes():
    # A database fixture_update in TEST requires approval (REQUIRE_APPROVAL).
    payload = _policy_payload()
    outcome = _run_approval_workflow(payload, decision=True, wait_until_signal=True)
    assert outcome["ok"] is True
    steps = [h["step"] for h in outcome["result"]["history"]]
    # The workflow continued past the gate and completed the chain.
    assert "execute_commands" in steps
    assert steps[-1] == "classify_outcome"


def test_approval_gate_reject_aborts_before_dangerous_step():
    # Reject aborts before the dangerous step; the workflow completes with a
    # BLOCKED marker and never runs execute_commands.
    payload = _policy_payload()
    outcome = _run_approval_workflow(payload, decision=False, wait_until_signal=True)
    assert outcome["ok"] is True
    steps = [h["step"] for h in outcome["result"]["history"]]
    assert "execute_commands" not in steps
    assert "approval_gate" in steps
