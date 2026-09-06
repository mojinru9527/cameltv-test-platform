# Batch 231 Acceptance Evidence

> Date: 2026-09-06 | Branch: `fix/batch-231-sports-retest-fixes` | Executor: Codex

## Evidence Index

| ID | Scope | Type | Baseline / Increment | Evidence | Result |
|---|---|---|---|---|---|
| E231-01 | Production sports-platform retest | External baseline | Baseline | `F:/CamelTv/_review_tools/sports-retest-20260906/复测结论-20260906.md` | 15 findings accepted into AC-01..AC-13 |
| E231-02 | Backend execution, tenancy, Gate, AI/DSH/Worker, SMART and lineage | Regression | Increment | QA report command matrix | PASS: 2483 passed, 49 skipped, 1 xfailed |
| E231-03 | Frontend workflows and responsive fixes | Regression / build | Increment | QA report command matrix | PASS: 153 files, 686 tests; typecheck/build/lint pass |
| E231-04 | Execution-truth and traceability migrations | Migration | Increment | QA report command matrix | PASS: 8 migration checks; empty DB upgraded to the new head |
| E231-05 | Repository development gate | Gate | Increment | QA report command matrix | PASS_WITH_WARN: 0 HARD, 332 reviewed repository-baseline WARN |
| E231-06 | Environment, Mission changes, API assets and task controls | Visible-browser screenshots / manifest | Increment | `browser/results.json`, ten PNG screenshots | PASS: 1440x900, 768x1024, 390x844; no HTTP/console error or root overflow |
| E231-07 | DSH and Durable Worker fail-closed behavior | Live local HTTP contract | Increment | `runtime-fail-closed.json` | PASS: rejected before task/Run persistence |

## Browser Manifest

- `desktop-*.png`: 1440x900.
- `tablet-*.png`: 768x1024.
- `mobile-*.png`: 390x844.
- `mobile-api-task.png`: icon accessibility plus responsive task-row layout.
- `results.json`: screenshot byte counts, overflow dimensions, task-item geometry, page scroll positions, HTTP failures, console errors, and `/change-sets/0` requests.

The browser run used a visible Chromium instance against the isolated Batch 231 database. AITDE and Temporal were enabled only in the local QA process. No production data or configuration was changed.

## Reuse Rule

These screenshots and runtime contracts may be reused only while the referenced API test, environment, Mission changes, DSH readiness, and execution-run modules are unchanged. Any production Worker/provider recovery invalidates the blocked production boundary and requires a new real production execution retest.
