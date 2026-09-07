# Production Capacity Guard - QA Report

Date: 2026-09-07 | Executor: codex
Verdict: PASS for local implementation; production rollout NOT EXECUTED.
Base: 8f6599bb (origin/main at worktree creation, Batch 232 / PR 414).

Scope note (2026-09-08): this report covers initial capacity commit 0f3138ff.
The user expanded PR 415 to include all roadmap phases before one combined
merge. It is no longer an operations-only PR. Resource-phase progress and
validation are recorded in production-resource-budget-design.md and the kanban;
final full-scope QA must replace this initial delivery conclusion before merge.

## Executed checks

| Check | Exit | Result |
|---|---:|---|
| `python -m unittest discover -s deploy/release-console/tests -v` | 0 | 21 passed; evidence/unittest.txt |
| `pwsh -NoProfile -File scripts/ops/test-capacity.ps1` | 0 | Structured argument transport, shell isolation, successful admission, four fail-closed rejection paths |
| `ruff check deploy/release-console/capacity.py deploy/release-console/release_cleanup.py deploy/release-console/tencent_executor.py deploy/release-console/tests --select F` | 0 | No undefined/unused Python symbols |
| `python -m compileall -q deploy/release-console` | 0 | Python syntax passes |
| PowerShell `Parser.ParseFile` for scripts/ops/release.ps1 | 0 | No parse errors |
| PyYAML safe_load of ai-delivery-policy.yml | 0 | Parsed |
| `python -m pytest deploy/release-control/tests -q` with PYTHONPATH=deploy/release-control/src | 0 | Entire adjacent deployment-domain suite: 27 passed |
| `python scripts/ci/test_classify_ci_changes.py` | 0 | 10 passed |
| `git diff --cached --check` | 0 | No whitespace errors |
| `pwsh scripts/git/dev-gate.ps1 -SkipBackend -SkipFrontend` | 1 | Output PASS_WITH_WARN; HARD=0 / WARN=332; do not describe wrapper as exit 0 |
| `scan-common-bugs.ps1 -BaselinePath .../scan-main.json` | 0 | 332 -> 332, delta 0; no new warning files/categories or hard findings |

Initial red phase: test modules failed to import absent capacity/cleanup helpers
(exit 1), then implementation and additional behavioral tests passed. Apply
tests include an actual temporary-file removal while retaining a backup file;
Docker actions are mocked, and no test deletes production objects.

## Baseline and scope

The clean detached checkout F:/CamelTv-release-20260907-b232 is at the same
8f6599bb revision and has no dirty files. Scan baseline and branch inventories
are saved in evidence/production-capacity-guard/scan-{main,branch}.json.
Their warning file/count maps are identical; full-platform tests are not
claimed to pass. This batch changes only deploy/, scripts/ops/,
.github/workflows/ and work-logs/; these are neutral operations paths in the
current CI classifier (backend=false, frontend=false). No platform app,
frontend, schema, dependency lock or test-platform-v2/deploy file is changed.
Thus platform pytest/Vitest/typecheck/build are not applicable to this diff.
New release-console Python and PowerShell tests are explicitly added to the
delivery-policy workflow; existing CI did not run this separate console suite.
Remote required checks and PR audit have not run because push is not yet authorized.

## Production evidence (read-only)

- Preview JSON: evidence/production-capacity-guard/production-preview.json.
- Current/rollback pairs retained: release-20260907-0001 and release-20260906-0001.
- Candidates: backend/frontend tags release-20260905-0001 and release-20260905-0002.
- Archive candidates: backend/frontend tar pairs release-20260903-0001 and
  release-20260905-0001, total 2851748352 bytes (2.656 GiB).
- Upload admission invoked with 1425670656 archive bytes: exit 1 as expected;
  free=2745151488 and required=8589934592 bytes. No upload/load/restart followed.
- At 23:44 CST, disk remained 94% used / about 2.6 GiB available; RAM available
  2222 MiB, swap used 306 MiB. No production cleanup or runtime config applied.
- Six running container IDs unchanged from initial inventory. Backend, frontend,
  postgres, AITDE worker and Temporal report healthy. The API health endpoint
  `/api/v1/open/health` returns code=0, data.status=ok, version=2.3.0.
  `/health` at the public frontend returns SPA HTML and is not backend evidence.
- `flock` exists at /usr/bin/flock. Existing production release-console does
  not yet contain this patch; until upgraded, preview only.

## Findings and operational limits

1. P1: Free-disk objective of 8 GiB remains unmet. Shared image layers mean the
   four eligible tags have little unique space. Stopped legacy worker retains
   an approximately 5.319 GB unique old image; it is deliberately protected.
   Retirement needs its own explicit recovery evidence, or expand the disk.
2. P2: Current main's release.ps1 still reads digests before fresh buildx export.
   This pre-existing first-release issue is outside the capacity patch; the
   tests validate upload admission directly and do not claim a clean full
   production release has been executed.
3. Approximation: admission uses archive-size factors and a reserve, not an
   exact expansion bound. Custom containerd roots require matching inspection.
4. No rollback drill, image build, authenticated UI regression or production
   deletion was executed. Preserved image-pair presence is not a rollback drill.
5. The cleanup tool does not read pending deployments from the console DB;
   operators must pin those tags and pause out-of-band deployment before apply.

## Phase 2 incremental evidence (2026-09-08)

- Initial resource primitive/UI/Lanhu snapshot: `python -m pytest -q --tb=short`
  in backend, exit 0; 2533 passed, 49 skipped, 1 xfailed, 62 warnings, 589.89s.
  Actual failures: empty set. Later DSH/native-browser/inference edits are not
  covered by this full-suite result.
- DSH admission + existing runner/sandbox/tasks/attachment/agent execution:
  103 passed in 8.09s, exit 0. Separate parent and browser child lanes exercised.
- All resource-budget tests + Lanhu import/worker + knowledge RAG + browser
  driver/hybrid cleanup: 94 passed in 17.96s, exit 0. Direct Lanhu busy admission,
  lease handoff, inference deferral, browser startup/close errors covered.
- `python -m ruff check app/ --select F821`: exit 0. `git diff --check`: exit 0.
- No production feature switch enabled. Remaining before activation: actual
  child-process-tree supervision, DSH team timeout lease ownership, queue
  deferral for native browser admission, API/runner entry-point migration,
  mixed workload memory measurement and cross-container integration.
- Test-generated tracked baseline JSON has only line-ending churn and is
  excluded from task commits; no user changes reverted.

## Supervision and release-build incremental evidence (2026-09-08)

- Disposable local Linux stdlib process-tree suite: 2 passed, exit 0 (1.056s).
  Actual child processes were checked after timeout and normal parent exit.
- Playwright/environment/artifact/DSH/OCR plus budget tests: 99 passed, exit 0.
- DSH team ownership refinement plus budget/tasks/runner/sandbox: 98 passed,
  2 Linux-only skipped on Windows, exit 0. No running test sessions remain.
- XHR capacity admission/API/route-layer regression: 37 passed, 2 skipped,
  exit 0. Final XHR/API run including the OpenAPI header assertion: 7 passed
  in 5.10s, exit 0. F821, diff whitespace, PowerShell parser and YAML checks pass.
- Release digest ordering debt above is now fixed locally: build/export first,
  then read `containerimage.config.digest` from fresh build metadata. Existing
  local image tags are no longer the digest source. Missing/malformed metadata
  is rejected before deployment registration. PowerShell tests pass, exit 0.
- Real scratch-image buildx export passed. Parsing its Docker archive and
  hashing the referenced config produced exactly the fresh metadata digest:
  `sha256:cdf7d1bdf6a1e397aafdb0c8be05280a3a75881b6bde378d71d1e345a3497332`.
  This verifies export metadata behavior, not a full production image build.
- No production cleanup, deployment, container restart or feature activation.

## Phase 3 queue ownership evidence (2026-09-08)

- Existing schedule/UI-schedule/AI/DSH/API-worker/task-worker: 104 passed,
  9 warnings, exit 0, 27.09s.
- Ownership plus shared task queue: 22 passed, exit 0, 52.14s.
- Two real sequential worker processes against a temporary SQLite database,
  with workload execution stubbed: 6 ownership tests passed, exit 0, 13.20s.
  A durable manual trigger executes once and remains completed on restart.
- Schedule/environment/async/stale/wiki-sync/mainline: 22 passed, 4 warnings,
  exit 0, 11.73s. F821 and whitespace checks pass.
- Follow-up shutdown ordering stops scheduler admission before consumer drain;
  final process startup/exit regression: 6 passed, exit 0, 15.89s. F821 passes.
- This is durable queue isolation, not full API/runtime isolation. Synchronous
  heavy endpoints, image builds, final full regression and production remain pending.

## Synchronous ownership incremental evidence

- `python -m pytest tests/resource_budget -q`: 54 passed, 2 Linux-only skips,
  20.89s, exit 0. Includes fresh worker-process lifecycle tests.
- Direct browser admission + existing playground/plan/auth regression: 38 passed,
  6 existing collection warnings, 3.43s, exit 0. Expanded admission-only follow-up:
  7 passed, 0.47s, exit 0 (adds blocked plan persistence and missing npx cleanup).
- Catch-up, HTTP dispatch and RAG regression: 27 passed, 4.61s, exit 0.
- F821: passed, exit 0.
- Real API Docker target built successfully. Container smoke passed app import,
  effective UID 10001, worker execution disabled, no system Node and no installed
  browser directory. Python Playwright/model packages remain for import stability.
- Runner image/build, cross-container workflow, final full regression and
  production limits/rollout remain outstanding. No production savings claimed.

Image follow-up: runner target built successfully and a real Chromium launched,
rendered a local HTML page and closed as UID 10001. Docker system df reports API
980 MB, runner 5.35 GB, shared 972.9 MB, API unique 6.963 MB. Inspect Size reports
compressed content (228936319 / 1397292433 bytes), which must not be confused with
the unpacked figures. The complete runtime is not materially smaller yet; the
split isolates execution and shares layers. Both builds precede the latest direct
browser admission edits, so final image builds still need refresh. The Linux
process cleanup tests ran against mounted current source: 2 passed, exit 0.
Scan follow-up eliminated the ProcessLookupError silent-pass HARD finding;
remaining warning count is 332, matching the initial main snapshot.

## Compose and real HTTP execution evidence

- `python scripts/ops/test_execution_compose.py -v`: 3 passed, exit 0. Uses
  actual Docker Compose merge output, including the optional Temporal profile.
  Checks role/image targets, acyclic startup, shared volumes, memory/PID limits.
- `python scripts/ops/smoke_execution_containers.py`: exit 0. Disposable local
  SQLite and containers with current source mounted into built runtime images.
  Auth and login pass; authenticated project-scoped request executes a real
  Chromium test through API -> runner; stopping runner produces 503 with
  Retry-After while API /health remains 200. Temporary resources removed.
- Post-task snapshot: API 195.3 MiB / 512 MiB ceiling; runner 325.2 MiB / 1.5 GiB.
  RAG/DSH disabled and no peak sampling: not a sizing verdict or production gain.
- Initial smoke failed because the test omitted mandatory X-Project-Id. Corrected
  the test request; authorization remains enforced. Compose test assumptions
  were also corrected for inactive profiles, nullable command and string limits.
- Main-warning comparison: exit 0, 332 -> 332, no new files/categories, HARD=0.
- Read-only production refresh: total 3723 MiB, available 2232 MiB, swap 306 MiB;
  root filesystem 94% used and 2.6 GiB free. No cleanup/deployment was performed.

## Durable plan evidence

Durable plan follow-up evidence (before final full regression):

- Entire resource-budget suite: 67 passed, 2 Linux-only skips, 24.45s, exit 0.
- Plan/dispatch/legacy async regression: 20 passed, 2 existing collection warnings,
  14.29s, exit 0. Null/absent synchronous-body follow-up: 9 passed, 3.11s, exit 0.
- Additive migration: SQLite upgrade/downgrade + PostgreSQL offline DDL, 2 passed,
  0.29s, exit 0. Alembic reports one head, 20260915_plan_dispatch. Actual PostgreSQL
  migration execution remains part of final verification.
- Fresh-process test consumes one persisted plan once across two invocations.
- Extended real-container smoke exits 0: async plan accepted while runner is
  stopped, visible as pending, completes after restart; synchronous 503 and API
  health checks still pass. Post-task memory 195.9 MiB API / 208.4 MiB runner;
  snapshots vary and must not be interpreted as measured peak savings.
- F821 passed. No production schema or runtime was changed.

## Initial slice retro card

Planned: 2 hours implementation/QA, excluding gated rollout.
Actual: approximately 0.3 hours to local QA.
Defects: new-code P0=0, P1=0; operational P1=1 and known baseline P2=1 above.
Rework: 2 review rounds (apply-path tests and recent rebuild protection).
Root causes: capacity management debt, independent deployment tools.
Next prevention: always compare actual unique/shared image storage and measure
post-cleanup free space; never promise summed virtual image sizes as savings.
