# Batch 232 - QA Report

> QA | Date: 2026-09-07 | Verdict: PASS for implementation, isolated runtime, and browser acceptance

## Test Summary

| Area | Result |
|---|---|
| Backend | 2504 passed / 49 skipped / 1 xfailed / 0 failed |
| Frontend | 154 files / 688 tests passed; Mission focused suite 25 passed |
| Static and build | Ruff F821, typecheck, lint, and production build passed |
| Migration | Single head `20260914_b232_ai_test_lifecycle`; fresh, previous-head, and stamped-old-schema upgrade paths passed |
| Repository gate | `PASS_WITH_WARN`: 0 HARD / 332 repository WARN; G1/G2 passed |
| Browser | Desktop, 768x1024, and 390x844 passed; no horizontal overflow or console errors |
| Request behavior | Mission detail 1 request + lifecycle aggregate 1 request; no per-case N+1 |

Only the final reruns after QA rework count as PASS evidence. The first backend
full run found eight compatibility failures; those results were rejected and
the full suite was rerun after fixes.

## Executed Gates

| Command / check | Exit | Result |
|---|---:|---|
| Lifecycle backend suite | 0 | 17 passed |
| Migration/schema compatibility group | 0 | 22 passed |
| Legacy stamped-schema migration group | 0 | 2 passed |
| `python -m pytest -q` | 0 | 2504 passed, 49 skipped, 1 xfailed, 62 warnings |
| `npm test -- --run` | 0 | 154 files, 688 tests passed |
| `npm test -- --run src/pages/missions` | 0 | 11 files, 25 tests passed |
| `npm run typecheck` | 0 | Passed |
| `npm run lint` | 0 | Passed with zero lint warnings |
| `npm run build` | 0 | Production build completed |
| `python -m alembic heads` | 0 | Exactly one head |
| `pwsh scripts/git/dev-gate.ps1 ...` | 0 | `PASS_WITH_WARN`; 0 HARD, G1/G2 passed |

The 49 skipped tests require unavailable PostgreSQL, Lanhu runtime, Compose, or
production read-only infrastructure. The single xfail is the repository's
documented SQLite full-chain downgrade limitation; the required previous-head
round-trip for this migration passed.

## Acceptance Matrix

| Criterion | Result | Evidence |
|---|---|---|
| Requirement to analysis | PASS | Mission links parsed source facts and reviewed Scope items |
| Requirement decomposition | PASS | Every scenario records module, source refs, and NEW/CHANGED/IMPACTED_BASELINE role |
| Three test lanes | PASS | FUNCTIONAL, API, and UI are required from AI output; a missing lane fails closed |
| Per-case execution | PASS | Lifecycle exposes run count, latest outcome, and executed-case total per scenario |
| Per-case evidence | PASS | Evidence count is aggregated per scenario; missing evidence becomes an explicit gap |
| Defect creation | PASS | A failed AITDE Run creates/reuses one linked open defect; PASS runs are rejected |
| Retest linkage | PASS | Retry Run uses `parent_run_id`; lifecycle reports pending/passed/failed retest state |
| Three testing phases | PASS | FEATURE=requirement test, VERSION=test-environment regression, REGRESSION=production regression |
| Six-stage overview | PASS | Sources, analysis, contract, cases, execution evidence, and acceptance use persisted facts |
| Error truth | PASS | Lifecycle API failure renders retryable ErrorState and is never treated as empty data |

## Browser Verification

- The visible local page was `http://127.0.0.1:5188/missions/9101/overview` with isolated QA data.
- Desktop showed all three phases, six lifecycle stages, three case lanes, evidence gap, linked defect count, and `复验通过`.
- At 768x1024, document `scrollWidth=762` for viewport width 768; no horizontal overflow or overlap was observed.
- At 390x844, document content width and scroll width were both 384; the page stacked phase and case facts without overlap.
- Browser console errors were empty.
- Backend access log recorded exactly one `GET /api/v2/missions/9101` and one `GET /api/v2/missions/9101/lifecycle`.
- The old static text `AI 分析 → Tester 评审` was absent.

## QA Rework Findings

| ID | Severity | Finding | Resolution | Status |
|---|---|---|---|---|
| B232-QA-01 | P1 | New routes were absent from the route inventory contract | Added both routes and updated the count; route guard passes | Fixed |
| B232-QA-02 | P1 | Migration was not safe for current-metadata bootstrap or stamped partial schemas | Added table/column/index/FK guards and verified upgrade/downgrade paths | Fixed |
| B232-QA-03 | P2 | Golden scenario fixtures did not carry the new classification contract | Added case type, requirement role, and module key to the golden corpus | Fixed |

## Production Boundary

- This report proves the code and isolated local workflow; it does not claim that a new production Mission has already run.
- Existing production Mission 34 and VersionTask 6 are disconnected historical data. They are not silently rewritten into a truthful lifecycle.
- After release, the 16.0.0 task must be created or linked in production and executed with real requirement sources and environments.
- FEATURE and VERSION phases target Test5; REGRESSION targets production only after release approval.
- C225-1 remains open. C230-1 is outside this batch and is not closed here.

## Release Recommendation

READY FOR DRAFT PR after the repository-required one-time confirmation. Required
checks and the final successful PR audit must pass before Leader approval and
squash merge. Production deployment and post-release Mission execution follow
the merge and release controls.

## 复盘卡

| Planned vs actual | Defects | Rework | Root cause | Next prevention |
|---|---|---|---|---|
| 12h / actual not reliably measured across handoff | 0 product defects; 3 QA findings | 1 QA correction round | Cross-version schema contracts were not all updated in the first slice | Every schema/API addition must update route inventory, migration drill, golden corpus, and responsive browser proof before full regression |

**Skills used**: Agent Team governed the six-department artifacts and gates; Bug Guard governed migration/API truth; UI conventions governed responsive operational layout; Playwright/Computer Use supplied visible multi-viewport evidence.
