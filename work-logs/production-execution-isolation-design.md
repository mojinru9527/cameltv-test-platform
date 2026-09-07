# Execution Isolation - Migration Contract

Part of the authorized combined PR 415. Default behavior remains combined
until the complete isolated deployment is validated.

## Durable queue ownership

API processes set `WORKER_EXECUTION_ENABLED=false`. AI, API execution, DSH,
knowledge agent and UI submission continue committing existing task records,
but cannot lazily start local consumers. `python -m app.worker` starts the
existing consumers and scheduler in a separate process with the flag true.
Database claims, IDs and artifact paths remain the business sources of truth.

Manual schedules keep their existing running record and external response.
An unset heartbeat identifies an unclaimed dispatch. The worker claims it by
conditional update before executing; another worker cannot execute it again.
A worker restart before claim leaves the record available to the next worker.
Already claimed lost work retains the existing stale-failure policy.

Cron registry refresh reads committed schedules every 5 seconds. Disabled or
deleted schedules are removed; execution also rechecks enabled status. External
integration interval jobs refresh every 15 seconds. This removes dependence on
API-process memory for changes made after worker startup.

## Remaining before isolated rollout

- Exercise cross-process submission, claim, cancellation and restart recovery.
- Route synchronous heavy calls (DSH generation, local embeddings, compilation,
  media probes, playground and XHR capture/status) to their execution owner.
  Disabling queue consumers alone does not isolate these calls.
- Build and inspect separate API/runner images from pinned dependencies.
- Wire Temporal worker ownership and shared volumes, avoiding duplicated loops.
- Verify health checks detect failed consumers, not just a living supervisor.
- Measure idle/mixed peaks and then set memory/PID/CPU limits with host reserve.
- Build deployment and rollback support for the complete image set. Existing
  release tooling only loads backend/frontend; it must cover the runner too.

No production split or memory-saving claim follows from this first queue slice.

## Queue slice evidence

- Existing schedule/UI-schedule/AI/DSH/API-worker/task-worker regression:
  104 passed, 9 warnings, exit 0 (27.09s).
- Ownership and shared task-queue regression: 22 passed, exit 0 (52.14s).
- Final ownership regression including two actual fresh worker processes:
  6 passed, exit 0 (13.20s). Each worker starts and stops its real loops against
  the same temporary SQLite DB. The second worker does not repeat the completed
  manual trigger. The workload itself is stubbed to isolate dispatch semantics.
- Initial registry test used an unstarted APScheduler whose pending jobs do not
  replace until startup; corrected to a started, paused scheduler matching runtime
  registration behavior. A subprocess fixture import was also corrected.
- Worker heartbeat checks scheduler/consumer thread liveness and is removed on
  shutdown/startup failure. It does not claim that external providers are healthy
  or that a long-running job is making progress; task heartbeats remain separate.
