# Batch PRD — Canonical Runner protocol (PR-04)

## Goal
Expose one claim/heartbeat/report/cancel protocol backed by existing ExecutionRun.

## Scope
- Add runner_id/capabilities/locked_at/heartbeat_at to execution_runs.
- Canonical endpoints under /api/v1/execution/runs.
- Project-scoped claim, heartbeat, report and cancel.
- API/UI/External runners differ only by capability selection.

## Acceptance
1. Two runners cannot claim the same Run.
2. Project mismatch cannot claim/read/update.
3. Wrong runner cannot heartbeat/report.
4. Cancel prevents further report.
