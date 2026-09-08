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

## Synchronous ownership slice

Explicit ExecutionRoute ownership forwards synchronous browser/compilation,
DSH generation and RAG calls to an internal HTTP runner. Durable queue submissions
stay in the API. FastAPI 0.139.2 lazily includes routers, so ownership is applied
through get_route_handler rather than patching APIRoute.app after inclusion.
Behavioral tests exercise the actual aggregated playground route. Authentication
and project checks run on the runner using the original caller's headers/cookies.
Streaming forwarding preserves duplicate Set-Cookie and strips hop headers;
unavailability returns 503 without automatic mutation retry or local fallback.

HTTP runner and standalone worker share a task_consumers lifecycle. The HTTP
health endpoint fails when a required consumer is no longer alive. API role
guards prevent local embedding/model loading and browser/DSH execution.

Playground and direct plan UI calls now take the same browser execution lease.
Busy playground calls return 429 with Retry-After; busy plan cases record blocked
and remain available for explicit re-execution instead of becoming false failed
tests. Their child process groups are supervised when the budget is enabled.
Compiler standalone validation and durable async plan dispatch remain to review.

API and runner Docker targets share Python layers. API excludes system Node,
browser installation and DSH; Python embedding dependencies remain for imports.
Application COPY occurs after large runtime layers, avoiding their invalidation
on application edits. The default target still produces the combined image.
The first API build passed import, UID 10001, role and no-browser smoke in a real
container. This is image structure evidence, not measured production RAM savings.

Optional 03:31 Asia/Shanghai catch-up processes active unembedded chunks using
the existing per-batch limit. Tests verify project filtering, repeat-run
idempotence, busy deferral, and no database work in API/disabled RAG roles.

## Opt-in Compose and container evidence

`test-platform-v2/deploy/docker-compose.execution.yml` overlays the base Compose.
Supply explicit API_IMAGE, RUNNER_IMAGE, API_MEMORY_LIMIT, RUNNER_MEMORY_LIMIT
and TEMPORAL_WORKER_MEMORY_LIMIT. Values in the smoke test are provisional local
ceilings, not production sizing. The base combined deployment is unchanged.

Runner uses the image's migration/start command; API waits for runner health and
starts HTTP directly. Temporal retains its gateway command and runner image,
and shares admission through the artifact volume. Both generated-script roots
are shared with API/runner/Temporal and initialized by volume-permissions.
Memory and PID limits apply to long-lived application processes. Database and
Temporal-server sizing still need the complete host budget.

Actual Compose config merge tests: 3 passed. Disposable API and runner containers
using current mounted application source passed login/auth/project context,
forwarded real Chromium execution, runner outage -> 503 + Retry-After, and API
health during that outage. Post-task memory: API 195.3 MiB, runner 325.2 MiB.
These are post-task snapshots with RAG/DSH disabled, not peaks or production
savings. All temporary containers, network and test-data volume were removed.
The first smoke omitted X-Project-Id and correctly received 403; the request was
corrected without weakening authorization. Repeat with final built images,
migrations and mixed workloads before rollout.

## Durable plan completion

Asynchronous execute-all now persists PlanExecutionJob before acknowledgment.
The mixed route keeps validated async requests in API even with no configured
runner; synchronous bodies (including absent/null bodies) are forwarded intact.
FastAPI's published OpenAPI marks the async submission owner separately. Invalid
requests retain normal framework validation and project/RBAC checks.

The runner's existing consumer lifecycle owns the plan queue. Atomic claim,
periodic owner-scoped heartbeats and conditional finalization prevent duplicate
claims and stale owners overwriting results. Lost running jobs become failed;
they are not replayed automatically because earlier case side effects may have
committed. GET execution-jobs exposes the latest 50 jobs scoped to project/plan.
The obsolete run_async_execute_all process-only wrapper has no callers and was
removed. Additive migration 20260915_plan_dispatch preserves older-image rollback
compatibility; dropping dispatch history is not part of operational rollback.

Two fresh processes executed one pending plan exactly once. Real API/runner
container smoke also accepted a pending plan during runner shutdown, then
completed it after runner restart. This uses current mounted source and an
isolated SQLite test database. Final-image and production database verification
remain required. Full resource slice: 67 passed, 2 Linux-only skips (24.45s).

## Release-set contract follow-up

ReleaseManifest now accepts explicit runtime_mode=split only with a runner
artifact and execution_config_sha256. Combined releases omit the new fields
from canonical hashing, preserving already registered immutable release IDs.
The generated JSON schema matches the model and digest-only Compose rendering
includes the runner artifact for split releases. Console execution and archive
handling still require complete-set integration before split publication.

Release archive transfers now check native scp exit status inside each background
job. The parent fails on any upload failure and removes the completed job handles
before leaving. A real local SCP probe verified successful content hashes and
failure propagation/cleanup without network access. CI runs this probe and the
actual execution Compose merge test.

Production read-only layout inspection confirms docker-compose.override.yml
binds backend/aitde-worker/volume-permissions to cameltv-tp-backend:main and
frontend to cameltv-tp-frontend:main. Split activation must preserve this layer,
use explicit release-mode metadata, and restore the old combined service topology
when rolling back. No production config was modified.

## Original queue evidence

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
