# DEV - Production Capacity Guard

Workflow: agent-team | Executor: codex | Start confirmed: user "Codex"
Worktree: F:/CamelTv-worktrees/codex-production-capacity-guard
Base: origin/main | Branch: feature/production-capacity-guard

- [x] Read production facts, repository gate and inherited conditions.
- [x] Create and verify clean isolated worktree (ports 25197/28197).
- [x] Product, PM and interface design.
- [x] S1: protected cleanup and capacity helpers + tests (21 unittest cases pass).
- [x] S2: upload/import integration (PowerShell success and rejection checks pass).
- [x] S3: local QA, dry-run evidence, review (production rollout not executed).
- [x] User batch push/PR/merge confirmation; user additionally authorized all roadmap phases and one final combined merge.
- [ ] Required checks, final audit, merge.
- [ ] Reviewed production application and post-checks.

Current position: authorized combined delivery in Draft PR 415. Added CI smoke
coverage under .github/workflows; worktree scope updated accordingly.
Initial capacity slice pushed; no production state changed. Production dry-run identifies
four image tags and four tar files; archive bytes 2851748352. Import/upload
reserve target is not yet attainable through the conservative preview alone.
Latest user instruction overrides the earlier per-batch merge ordering: finish
all four phases in this isolated branch and merge together after their gates.
Scope now also includes test-platform-v2/, docs/adr/ and CLAUDE.md.
Initial capacity commit 0f3138ff pushed; Draft PR 415 created. Initial checks
all passed and base audit passed; do not merge until all phases finish.

## Remaining roadmap (same final delivery)
- [ ] Phase 2: inventory all entry points and define cross-process resource ownership.
- [ ] Phase 2: shared capacity, cancellation/crash recovery, telemetry and regression.
- [ ] Phase 3: API/runner image split and migrated execution entry points.
- [ ] Phase 3: restart recovery, isolated execution smoke, measured image/runtime evidence.
- [ ] Phase 4: consolidate task/report entry points, preserve historical links/permissions.
- [ ] Phase 4: knowledge processing on-demand/off-peak, UI/functional validation.
- [ ] Complete scope-wide QA, update PR title/body and final audit.
- [ ] Squash merge, main CI and reviewed production optimization rollout.

Current Phase 2 slice: shared filelock primitive + UI/Lanhu polling admission
implemented, default disabled pending all entry-point coverage. 11 new tests
pass, Linux crash-recovery probe passes, selected existing tests pass (51).
Initial full backend regression passed: 2533 passed, 49 skipped, 1 xfailed.
DSH parent uses platform child
execution and must receive a separate orchestration budget to avoid deadlock;
see the evidence-led design refinement. No new production config was enabled.

DSH orchestration admission now implemented with pre-claim polling and direct
runner coverage. Direct Lanhu, native browser and embedding admission added.
Incremental DSH regression: 103 passed; mixed entry-point regression: 94 passed.
F821 and whitespace checks pass. Next: process-tree supervision and team-timeout
lease ownership, then actual execution ownership/image split. Native browser
currently reports capacity exhaustion as runtime_error; durable admission
deferral still needs integration before activating the feature.

Supervision follow-up: real Linux process-group tests pass; DSH team runtime
now retains its lease even if the monitor returns early. XHR capture reserves
capacity before spawning and returns retryable 429 when full. Release script
now reads fresh export metadata after build (real archive hash comparison
passed). Next focus is Phase 3 execution ownership and image split; all runtime
features remain default-disabled pending the complete rollout review.

Phase 3 queue ownership slice implemented: API can persist tasks without lazy
consumer startup; `app.worker` owns the durable consumers and scheduler. Manual
schedule triggers use an atomic heartbeat claim and survive API/worker handoff.
Cron/integration registries refresh committed changes. Independent real worker
processes consumed a test dispatch once across restart (6 ownership tests pass).
Existing queue/schedule regression: 104 passed; shared task queue plus ownership:
22 passed; additional schedule/wiki-sync/mainline regression: 22 passed.
Synchronous heavy calls, image targets, Temporal consolidation and production
limits are still outstanding. See production-execution-isolation-design.md.

Synchronous ownership slice: real aggregated routes forward to the HTTP runner;
API guards prohibit local models/browsers; HTTP and standalone consumers share
lifecycle/health checks. API target builds and imports as nonroot without system
Node/browser installation. Runner build is being verified. Off-peak knowledge
catch-up has filtering/idempotence/busy-deferral tests. Direct playground/plan UI
now use shared admission and supervised process groups; busy plan results are
blocked, not failed. Resource suite: 54 passed, 2 Linux-only skips; related browser
regression: 38 passed; catch-up/dispatch/RAG: 27 passed. F821 passes. These are
incremental results, not final full regression. No production changes or new push.

Runner build now passes import/nonroot/real Chromium smoke. Unpacked API is
980 MB; runner 5.35 GB; shared layers 972.9 MB. No complete-runtime size reduction
is claimed. Builds precede the final direct-browser edits and require refresh.
Current-source Linux process cleanup tests: 2 passed. Scan HARD fixed; compare
the unchanged 332 warnings with the existing main baseline before committing.

Synchronous/image slice committed as c2a36f2a. Baseline scan comparison passes:
332 -> 332 warnings; zero new files/categories and zero HARD findings.
Optional execution Compose overlay now has tested image ownership, shared
artifact/spec volumes, explicit memory values and ordered startup. Three actual
Compose merge tests pass. Real two-container HTTP/browser smoke passes including
auth/project scope and runner outage while API stays healthy. Post-task memory:
API 195.3 MiB / runner 325.2 MiB (no RAG/DSH; not peak). Smoke resources cleaned.
Production read-only refresh: 3723 MiB total, 2232 MiB available, swap 306 MiB;
disk still 94%, 2.6 GiB available. No production state changed. Next: finish
durable plan dispatch/compiler inventory, release image-set/rollback support,
mixed-workload sizing and product consolidation before full QA/one final merge.

Durable async plan slice: plan_execution_job additive migration and queue use
existing atomic claims. API keeps async submissions local even while runner is
down; sync request body is preserved for forwarding. Runner owns claim/heartbeat/
completion; stale running work is failed without automatic replay. Project-scoped
status route added and old in-memory background wrapper removed. Two actual
fresh processes execute a pending request once; real containers accept during
outage and complete after restart. Resource suite: 67 passed, 2 Linux-only skips,
24.45s; migration SQLite upgrade/downgrade and PostgreSQL offline DDL pass;
Alembic single head 20260915_plan_dispatch; F821 passes. All work remains local
pending final combined QA/push. Production has not changed.

Release integration preparation: native SCP failures now fail the background
upload and parent release flow, with job-handle cleanup; real local transfer
probe passes. ReleaseManifest now binds split runner/config artifacts while
preserving old two-image canonical digests. Release-control tests: 29 passed;
capacity/cleanup tests: 21 passed; PowerShell and workflow YAML parse checks pass.
CI covers transfer rejection and Compose merge contracts. Console deploy/import/
rollback and retention still need the complete image-set wiring. Production
override image mappings inspected read-only; no server state changed.

Release-set integration slice: producer exports api/backend, frontend and runner
with fresh config digests, binds the reviewed execution YAML checksum, and uploads
the complete set. Console validates immutable registration, rejects tag mismatch,
claims production state before SSH, blocks concurrent/observing releases and
records execution failures. Rollback resolves the target's registered topology;
executor checks retained images/config before retagging and stops old consumers
before recreation. SQLite request connections now close deterministically.
Cleanup recognizes runner images/archives and requires complete pinned split
sets; execution YAML is retained. Console tests: 36 passed; actual Compose merge:
3 passed; native transfer and build-metadata probes pass; F821 passes; scan HARD=0,
WARN=332 unchanged. Final bundle rebuild/real transition rehearsal, complete host
budget, product consolidation, final QA and production rollout remain pending.
