# Production Optimization Implementation Plan

Date: 2026-09-07 | Executor: Codex | Branch: feature/production-capacity-guard

## Roadmap and sequencing

1. Capacity guard (this full batch): inventory, protected cleanup preview and
   application, upload/import admission checks, regression and operational runbook.
2. Resource budget (after batch 1 merges): inventory every heavy-task entry;
   implement a shared durable lease with global heavy-task capacity one,
   cancellation/expiry recovery and workload attribution. Test UI, Lanhu,
   DSH and Temporal concurrency together before setting measured container limits.
3. Execution isolation (after batch 2 merges): separate API and runner images;
   move browser/OCR/DSH execution out of API, preserving claims, task IDs,
   heartbeats, artifacts and restart recovery. Compare image size and task results.
4. Product consolidation (after batch 3 merges): freeze unused experimental
   entry expansion; design one task/report navigation with historical deep links;
   retain populated knowledge/Wiki/graph features and move optional processing
   to explicit or off-peak jobs. Validate permissions and old/new task mapping.

Each subsequent batch starts from the merged latest main. The current batch
does not promise later-batch functionality or treat planning as implementation.

## Current implementation slices

- [x] S1 (45 min): stdlib capacity and cleanup helpers under
  deploy/release-console/, tests in deploy/release-console/tests/.
  Reproduce protected aliases, missing rollback, symlinks, stale approval,
  reserve/inode boundary and error behavior before implementation.
- [x] S2 (45 min): integrate capacity guard into tencent_executor.py,
  Dockerfile and scripts/ops/release.ps1. CI workflow runs the new Python and
  PowerShell tests. Check before transfer and before
  import, without adding capacity restrictions to emergency rollback.
- [x] S3 (30 min): run unittest discovery, Python compile/Ruff, PowerShell
  parser and deployment-domain regression; inspect current production with
  preview only. Write command/exit/result evidence in QA and update kanban.
- [ ] S4: publish exact cleanup objects and code diff. Obtain required batch
  push/PR/merge confirmation; apply only the reviewed operations, capture
  disk delta, container IDs/health and retained image-pair checks.

## Validation commands

From this worktree:

```powershell
python -m unittest discover -s deploy/release-console/tests -v
python -m compileall -q deploy/release-console
ruff check deploy/release-console/capacity.py deploy/release-console/tests --select F821
pwsh scripts/git/dev-gate.ps1 -SkipBackend -SkipFrontend
python scripts/ci/test_classify_ci_changes.py
```

Operations-only classification must be recorded from the complete changed
file list. Platform frontend/backend suites are not substitutes for executing
the changed release tests. No platform application code is changed in S1-S3.

## Production and rollback

Retain the inspected current pair and at least one explicitly verified rollback
pair; keep recent releases and every container reference. Preview names and
digest, then apply that exact digest during a release maintenance window.
For removed historical tags, recovery requires original release artifacts;
database volumes/backups are never candidates. If cleanup cannot reach 8 GiB
without protected assets, stop and recommend storage expansion; do not widen
deletion scope automatically. No claim of a successful rollback drill is made
without actually running one in an isolated environment.
