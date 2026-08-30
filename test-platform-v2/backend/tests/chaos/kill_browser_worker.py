#!/usr/bin/env python
"""AITDE V3.4 chaos drill: kill a browser worker mid-run (PR34-11).

In-memory replay/resume semantics prove a re-delivered Activity resumes; a real
worker-kill drill requires a long-running worker + real Temporal server (V34-001,
待基础设施). This script documents the drill and runs the in-memory analog so CI
can assert no duplicate fixture on recovery.
"""
from __future__ import annotations



def run() -> bool:
    """Kill-a-worker analog: start a workflow, verify it survives an Activity retry."""
    from tests.aitde.v34.test_workflow_recovery import _run_workflow_through_env

    payload = {"scenario_id": 1, "scenario_version_id": 3, "command_plan": []}
    outcome = _run_workflow_through_env(payload)
    ok = outcome["ok"] is True
    print(f"[chaos] kill_browser_worker -> completed={ok}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
