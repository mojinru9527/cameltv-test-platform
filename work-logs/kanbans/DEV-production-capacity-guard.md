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
