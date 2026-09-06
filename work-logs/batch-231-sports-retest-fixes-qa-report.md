# Batch 231 - QA Report

> QA | Date: 2026-09-06 | Verdict: PASS for local code and isolated runtime; production success retest remains externally blocked

## Test Summary

| Area | Result |
|---|---|
| Backend | 2487 passed / 49 skipped / 1 xfailed / 0 failed; focused suites passed |
| Frontend | 153 files / 686 tests passed; focused responsive suite 6 passed |
| Static and build | Ruff F821, typecheck, lint, and production build passed |
| Migration | 11 migration/single-head checks passed; empty isolated DB upgraded through `20260913_b231_traceability_truth` |
| Repository gate | `PASS_WITH_WARN`: 0 HARD / 332 historical repository WARN; G1/G2 passed |
| Managed Worker | 11 focused tests passed; production profile guards, rendered Compose, and Bash syntax passed |
| Browser | Ten screenshots across 1440x900, 768x1024, 390x844; zero HTTP/console errors and zero `/change-sets/0` calls |
| Live failure closure | DSH submission and Worker-backed Run creation rejected before persistence |

This report uses Batch 231's newly executed tests and browser evidence. The production retest report is the defect baseline, not proof of a fixed production release.

## Executed Gates

| Command / check | Exit | Result |
|---|---:|---|
| Backend related-domain focused suites | 0 | 51 passed |
| Migration and single-head focused checks | 0 | 11 passed |
| Version-task focused suites | 0 | 63 passed |
| Managed Worker deploy + heartbeat suites | 0 | 11 passed |
| Production runtime profile PowerShell guards | 0 | Missing token, disabled Temporal, and invalid heartbeat interval fail closed |
| Production `docker compose ... config --quiet` | 0 | Worker profile renders without service, port, or container-name conflicts |
| Git Bash `bash -n .../start-worker.sh` | 0 | Launcher syntax passed |
| `python -m pytest -q` | 0 | 2487 passed, 49 skipped, 1 xfailed, 62 warnings |
| `python -m ruff check app --select F821` | 0 | All checks passed |
| `npm test` | 0 | 153 files, 686 tests passed |
| `npm run typecheck` | 0 | Passed |
| `npm run lint` | 0 | Passed with zero lint warnings |
| `npm run build` | 0 | Production build completed |
| `pwsh scripts/git/dev-gate.ps1 ...` | 1 | `PASS_WITH_WARN`; 0 HARD / 332 repository-baseline WARN; F821/typecheck/lint/4 route guards passed |
| Visible Chromium acceptance | 0 | 9 page/viewport checks plus mobile task-control check passed |

The first full-backend rerun displayed an all-green summary but was captured by the
tool wrapper with exit 1, so it was not accepted as evidence. The standalone rerun
explicitly printed `PYTEST_EXIT_CODE=0`; that rerun is the result recorded above.

Docker Compose configuration is validated, but the backend image could not be
built locally because the Docker Desktop daemon is not running. Image build and
container-level Worker health remain required CI/release evidence rather than a
local PASS claim.

The first frontend full-test attempt ran concurrently with the production build and lost one Vitest worker to resource contention (152/153 files completed, no assertion failure). It was discarded. The standalone rerun above is the accepted result.

## Acceptance Matrix

| Criteria | Result | Evidence |
|---|---|---|
| AC-01 execution truth | PASS | Non-zero exit, `No tests found`, and zero-test runs fail/block; executor and version-task regressions |
| AC-02 tenant isolation/history | PASS | Cross-project task/detail/nested reads and writes are not found; historical 0/0 rows reconcile to blocked |
| AC-03 Mission Gate | PASS | Build and Campaign are required and project/Mission matched; empty evidence is NOT_EVALUATED/BLOCKED |
| AC-04 scenario execution/errors | PASS | Route owns scenario ID, current persisted version is sent, structured 422 details render as text |
| AC-05 version task plan/run truth | PASS | Plan review remains reachable; blocked counts/reasons and action availability are truthful |
| AC-06 AI/DSH/Worker | PASS locally | Shared provider health fails closed; deterministic fallback exposes provenance/confidence; live local DSH/Worker probes persist nothing; Compose owns Worker restart and both managed processes |
| AC-07 schedule duplicate trigger | PASS | `already_running` states no new run and includes the existing Run ID |
| AC-08 SMART fallback | PASS | Unsafe SMART atomically persists effective FULL, all current scenario versions, and no exclusions |
| AC-09 review/source traceability | PASS | Canonical review statuses and positive persisted source refs flow through generated artifacts |
| AC-10 lineage | PASS | Contract-version nodes use `CONTRACT_VERSION`; migration repairs legacy labels |
| AC-11 changes/environment | PASS | No initial ChangeSet 0 request; Base URL/access/execution mode/Runner Key are visible |
| AC-12 mobile/accessibility | PASS | Service filters and task rows do not overlap; page does not shift; icon controls have accessible names |
| AC-13 deep regression | PASS locally | Full suites, build/static gates, migrations, three viewport browser run, and live fail-closed contracts passed |

## Browser Verification

- Environment details display `http://test5.internal.example`, `内网`, `专属 Runner`, and `test5-internal-01` at all three viewports.
- Mission changes renders without requesting `/api/v2/change-sets/0`.
- API service filters remain individually readable and non-overlapping at 390x844.
- The mobile API task row separates identity from metrics/actions; pairwise element-overlap list is empty, row `scrollWidth=356`, rendered width `356`.
- Clicking the rightmost task Tab leaves `main`, document, and body horizontal scroll at 0.
- Task detail button exposes `查看任务Batch 231 accessible detail详情`.
- `failedResponses=[]`, `consoleErrors=[]`, `zeroChangeSetRequests=[]`.

## QA Rework Finding

| ID | Severity | Finding | Resolution | Status |
|---|---|---|---|---|
| B231-QA-01 | P2 | Root-overflow checks missed task-row text/stat/action collision and page-level horizontal shift after selecting the rightmost Tab at 390px | Task rows now stack on narrow screens; the tab list owns hidden horizontal scrolling; unit and real geometry assertions added | Fixed |

## External Production Boundary

- DeepSeek account balance remains an operator-owned prerequisite; a real successful AI/DSH production call cannot be claimed until it is restored.
- The branch makes `aitde-worker` a Compose-managed `restart: unless-stopped` service, but production still needs a valid Worker Token, a reachable Temporal endpoint, deployment, and a successful post-release heartbeat/Run smoke test.
- No production deployment was authorized or performed. The latest production state therefore remains the original retest baseline until this branch is merged and released.
- Local code correctly fails closed for both unavailable states and cannot create misleading queued work.

## Release Recommendation

READY FOR DRAFT PR after the repository-required one-time confirmation. Required checks and final `audit-ai-pr.ps1 -RequireSuccessfulChecks` must pass before Leader approval and squash merge. A separate authorized production release and post-release retest are still required.

## 复盘卡

| Planned vs actual | Defects (P0/P1/P2/P3) | Rework | Root cause | Next prevention |
|---|---|---|---|---|
| Plan had no hour estimate / actual not reliably measured across handoff | 3/5/8/0 (production baseline plus QA finding) | 1 QA correction round | Technical debt + external dependencies + browser-test coverage gap | For every mobile tab workflow, assert descendant geometry and scroll-container position in addition to root `scrollWidth` |

**Skills used**: cameltv-agent-team governed artifacts and gates; cameltv-bug-guard governed API/error/test invariants; cameltv-ui-conventions governed responsive/accessibility correction; playwright-skill produced visible multi-viewport evidence.
