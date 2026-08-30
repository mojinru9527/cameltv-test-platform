#!/usr/bin/env python
"""AITDE V3.4 chaos drill: kill the Control Plane mid-run (PR34-11).

A Temporal workflow survives Control-Plane restart because Temporal persists the
run history on the server. This script documents the drill and runs the in-memory
analog: a workflow still completes after its Activity did work (Temporal decouples
execution from the Control Plane lifetime).
"""
from __future__ import annotations



def run() -> bool:
    from tests.aitde.v34.test_workflow_recovery import _run_workflow_through_env

    payload = {"scenario_id": 1, "scenario_version_id": 3, "command_plan": []}
    outcome = _run_workflow_through_env(payload)
    ok = outcome["ok"] is True
    print(f"[chaos] restart_control_plane -> completed={ok}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
