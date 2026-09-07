# Shared Heavy-Task Budget - Design and Acceptance

Date: 2026-09-07 | Workflow: agent-team | Executor: codex
Part of PR 415; user requested one combined final merge for all roadmap phases.

## Product and PM

The UI executor's process-local limit is effective but does not coordinate
with Lanhu, DSH, embedding or other containers. Shared admission must happen
before durable task claim where possible, leaving excess work pending and
cancellable. Core API reads/login must not need a heavy-task slot.

Implementation slices:
- [x] Shared kernel-backed lease primitive and real multi-process tests.
- [ ] Wire UI, Lanhu, DSH, local inference and Temporal browser execution.
- [ ] Ensure pending/cancelled semantics, retries and parent-child task behavior.
- [ ] Attribute memory observations and terminate full child process groups.
- [ ] Validate mixed workloads, crash recovery and define measured runtime limits.

## Design

Use filelock (already pinned to 3.32.0 in requirements.lock) on the same-host
shared artifact volume. Explicitly declare the dependency; no extra daemon or
new database schema is needed. This is a single-host deployment design, not a
distributed lock for NFS/multi-host workers. A future distributed worker pool
must replace the admission backend rather than sharing these files over NFS.

One persistent lock file per slot, and one bounded JSON status file per slot.
Kernel locks enforce ownership and release after process exit; stale JSON is
diagnostic only and never determines slot ownership. The filelock instance
uses thread_local=False so poller-to-worker handoff releases the same lease.
Lease FDs must not be inherited by exec'ed subprocesses. Mixed configured
limits fail closed until an operator quiesces workers and resets the policy.

Retain existing database task records/claims and cancellation fields. This
primitive controls resources, not business task ownership. No business task
is moved to success merely because it acquired or released a resource slot.

Memory telemetry explicitly names its scope: cgroup current memory (whole
container) on Linux when available, otherwise process RSS, otherwise unknown.
An observed peak during a lease is not presented as isolated per-task memory.
Fixed status slots bound disk usage; completed history belongs in existing
application/audit logs, not an ever-growing new resource-history directory.

## Mandatory acceptance

- Separate processes and FileBudget instances sharing the directory cannot
  exceed the same configured capacity; distinct slots work when capacity >1.
- Killing a holder releases admission without a TTL delay. State files alone
  must not prevent recovery or authorize a second running task.
- Cancellation and timeout while queued start no task and leak no lock.
- Exception and explicit cross-thread release free admission exactly once.
- Different limits using the same directory fail closed.
- Repeated executions do not create unbounded status/history files.
- Parent orchestration must not hold the only slot while waiting for a child
  that needs it; entry-point integration must test this explicitly before rollout.
- API/worker containers must mount the same budget volume; integration is not
  complete merely because unit tests for this primitive pass.

## Evidence-led refinement (2026-09-08)

tester_team_persona.py explicitly requires the DSH parent to use
knowledge-mcp trigger_test_execution and wait until platform-runner tasks
finish. Holding a single execution slot for the whole DSH parent lifetime
would deadlock this supported workflow. Therefore use two centrally configured
resource classes: one orchestration lease (DSH parent) and one heavy-execution
lease (browser/OCR/local-model work). Both are shared across local containers;
the runner cgroup enforces their combined measured memory ceiling. This is
not a claim that two concurrent tasks cost the same memory as one. Mixed-flow
peak measurement and parent/child completion remain mandatory before enabling.

## Current evidence

- Shared primitive, UI and Lanhu admission tests: 11 passed on Windows.
- Existing UI/environment/worker selected regression: 43 passed; UI/Lanhu/worker
  selected regression: 51 passed.
- Linux probe inside existing backend container: separate helper process held
  the kernel lock, another process was denied, killing the helper released it;
  next holder admitted successfully. Temporary files were removed. Container
  scoped observed memory was 238821376 bytes; this is not per-task usage.
- Backend F821 passes; Alembic remains single-headed at 20260914_b232_ai_test_lifecycle.
- Initial UI/Lanhu slice complete backend regression: 2533 passed, 49 skipped,
  1 xfailed, 62 warnings in 589.89s, exit 0 (2583 collected). DSH and subsequent
  slices are outside this tested snapshot and require additional verification.
- Feature default remains disabled. DSH/local-inference/direct-Lanhu entry-point
  coverage and process-tree cleanup are not yet implemented; no rollout claimed.

## Entry-point inventory

| Workload | Current owner | Required integration |
| --- | --- | --- |
| Legacy UI | ui_runner_queue, task_worker, Temporal legacy activity | Common run_playwright_test admission before claim; runner owns polling |
| Lanhu evidence | worker poller; direct run_job_in_new_session | Transfer poller lease to job runner; direct callers need admission |
| DSH | Lazy dsh_task_service poller; direct run_dsh_task | Separate orchestration lane; bound queued claims and runtime admission |
| AITDE browser | PlaywrightPageAdapter open/close | Hold execution lease for actual browser lifetime, including startup failure |
| Embedding | EmbeddingService available/embed, API and ingestion | Budget model load and inference; avoid nested lease deadlock; API profile must avoid loading local model |
| XHR capture | In-process thread from UI capture route | Reserve before thread creation; retryable 429 while busy; move route and status ownership together |
| Scheduled maintenance | API lifespan / APScheduler | Explicit owner; preserve schedule updates and startup recovery |
| AI/background tasks | Lazy ensure_worker_running calls | Submission persists work; API must not start execution threads |

The initial backend full regression is being allowed to finish before changing
its source snapshot. New slices require their own affected regression evidence.

## Supervision slice evidence

- Linux process-group helper tested in a disposable local `python:3.12-slim`
  container with no network and a read-only source mount. Two real process
  tests pass: timeout and normally exited parent both leave no live child.
- DSH team dispatch transfers lease ownership to its execution thread. Tests
  simulate the monitor returning before the runtime finishes and a late thread
  dispatch after owner close. Neither may release capacity early or start late.
- DSH/resource regression: 98 passed, 2 Linux-only skips on Windows, exit 0.
  Playwright/DSH/OCR regression before the team ownership refinement: 99 passed.
- XHR admission and route regression: 37 passed, 2 Linux-only skips, exit 0.
  OpenAPI now declares the retryable 429 and Retry-After header.
- Supervision is tied to the disabled resource-budget flag. Linux groups cover
  descendants in the owned group, not deliberately detached sessions. Windows
  uses taskkill for active parents and has no equivalent successful-parent
  guarantee. Production remains Linux; container limits remain required.
- Native BrowserRuntimeDriver has no production callers found in app/; its
  busy outcome is runtime_error, not a durable queue retry. Keep this distinction
  in the rollout review, rather than claiming a native Temporal execution path.
