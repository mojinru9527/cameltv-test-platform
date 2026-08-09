# Full Platform Adversarial Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate every test-platform-v2 capability from first principles, record evidence, and harden the highest-risk cross-module failures without contaminating production data.

**Architecture:** Keep the existing FastAPI/SQLAlchemy and React/Radix architecture. Move authoritative totals and enum normalization to backend services, keep the frontend explicit about full totals versus loaded rows, precompute interaction-search data once per request, and represent expected unavailable states separately from unexpected errors. Production journeys are read-only; write journeys run against an isolated local database.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pytest, React 19, TypeScript, Vite, Vitest, Playwright, Tailwind/shadcn.

---

The recommended execution sub-skills are not installed in this workspace. Codex will execute the same checklist inline, one red/green slice at a time, and update the batch kanban after each slice.

## Task 1: Freeze scope and baselines

- [x] Read router, menu seed, page inventory, tests, prior Batch 126 findings and open C conditions.
- [x] Create PRD, PM plan, design spec, functional matrix, review register and Dev kanban.
- [ ] Record exact production route/tab/detail evidence in `work-logs/evidence/batch-127/` without secrets.
- [ ] Run and record initial `audit-cconditions.ps1` and `scan-common-bugs.ps1` outputs.

## Task 2: Make test-case statistics authoritative

**Files:**
- Modify: `backend/app/services/test_case_service.py`
- Modify: `backend/app/api/v1/test_case.py`
- Modify: `backend/app/services/dashboard_service.py`
- Modify: `frontend/src/api/testcase.ts`
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify or retire: `frontend/src/pages/testcase/caseListFormatters.ts`
- Test: `backend/tests/test_test_case.py` or nearest existing test-case service suite
- Test: `backend/tests/test_dashboard.py`
- Test: `frontend/src/pages/testcase/__tests__/caseListFormatters.test.ts`
- Test: `frontend/src/pages/testcase/__tests__/TestCasePage.test.tsx`

- [ ] Add failing backend tests: soft-deleted cases are excluded; `functional` aliases to `manual`; type sum equals total; manual list includes both values.
- [ ] Add a static `/test-cases/stats` route before `/{case_id}` and verify it is not captured as an integer ID.
- [ ] Implement one canonical case-type helper used by list and stats; normalize new writes while preserving legacy reads.
- [ ] Update dashboard grouping and execution subqueries to use the alias and `is_deleted = false`.
- [ ] Add failing frontend test proving counts come from stats API, not domain names.
- [ ] Fetch stats with AbortSignal and refresh after mutations/imports; display all/manual authoritative counts.
- [ ] Run focused backend/frontend tests and inspect the production discrepancy against local seeded legacy data.

## Task 3: Remove repeated interaction-coverage work

**Files:**
- Modify: `backend/app/services/interaction_coverage_service.py`
- Modify: `backend/tests/test_interaction_coverage.py`
- Modify if needed: `frontend/src/pages/requirement/index.tsx`
- Test if needed: `frontend/src/pages/requirement/__tests__/RequirementPage.test.tsx`

- [ ] Add a failing test that instruments case-text preparation and asserts one preparation per `compute_interaction_gaps` call.
- [ ] Add equivalence cases for full path, type prefix, entry text, module hint, invalid edge and empty inputs.
- [ ] Build a prepared corpus/module-hint index once; keep `_edge_covered` compatibility for direct unit use.
- [ ] Ensure requirement page renders its shell/skeleton before secondary interaction coverage completes.
- [ ] Run focused tests and a non-flaky large fixture; record item counts and observed duration without hard-coding a strict millisecond threshold.

## Task 4: Separate entity totals from loaded rows

**Files:**
- Modify: `backend/app/api/v1/knowledge.py`
- Modify: `backend/app/schemas/knowledge.py`
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/pages/knowledge/components/EntityTab.tsx`
- Modify: shared frontend types in `frontend/src/types/`
- Test: nearest knowledge API tests
- Test: `frontend/src/pages/knowledge/components/__tests__/EntityTab.test.tsx`

- [ ] Add failing API tests for project-isolated entity totals grouped by type and optional filters.
- [ ] Add `/knowledge/graph/entities/stats` before `/graph/entities/{entity_id}` with total/by_type/source_missing counts.
- [ ] Add failing component test where 970 total entities and 200 loaded rows must not display “200” as the total.
- [ ] Fetch stats and rows with abortable effects; label project total, current result/load count and source-missing warning distinctly.
- [ ] Verify graph/overview/entity totals are explainable; record any remaining graph filtering difference rather than hiding it.

## Task 5: Localize states and harden unavailable UI

**Files:**
- Modify: `frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx`
- Modify: `frontend/src/pages/knowledge/components/WikiTab.tsx`
- Modify: knowledge source component resolved during implementation
- Modify: `frontend/src/pages/operations-release/index.tsx`
- Modify: `frontend/src/pages/perftest/index.tsx`
- Test: corresponding component tests

- [ ] Add table-driven tests for known artifact/wiki/source labels and unknown fallback.
- [ ] Centralize or colocate explicit label maps; render labels instead of raw enums.
- [ ] Add a classifier for the known release-control 503/unconfigured response.
- [ ] Render controlled warning/empty state for expected unavailability; preserve `AsyncState` error/retry for unexpected failures.
- [ ] Add `useDocumentTitle('性能测试')` and verify cleanup/network rules remain intact.

## Task 6: Close accessibility, naming and route-state gaps

**Files:**
- Modify: exact UI automation and schedule controls identified by locator audit
- Modify: `frontend/src/router/index.tsx` and/or `frontend/src/layout/MainLayout.tsx` only after route-state decision
- Modify: touched page title strings
- Add/Test: a route/title/accessibility contract test in `frontend/src/`

- [ ] Identify every unnamed button/switch with stable semantic context; add `aria-label` without changing visual layout.
- [ ] Define every hidden route as official, experimental, development-only or retired in the review report.
- [ ] Expose high-value official routes or gate development-only routes; do not silently leave production demo data accessible.
- [ ] Align document title, H1 and navigation labels for touched official pages.
- [ ] Verify keyboard focus and 360/768/1280/1440 document-level overflow on representative dense pages.

## Task 7: Repair governance hard failures

**Files:**
- Modify: `C-CONDITIONS.md`
- Modify: `backend/scripts/build_lanhu_hierarchy.py`
- Modify: `backend/scripts/run_all_base_cases.py`
- Add/modify: script tests where practical

- [ ] Add the four orphan Leader conditions C120-3, C122-1, C122-3 and C123-1 to the tracker with truthful current status/evidence.
- [ ] Replace two `except Exception: pass` paths with contextual logging or structured failure accounting.
- [ ] Run both repository audit scripts until HARD=0; do not suppress warnings globally.

## Task 8: Build repeatable all-function acceptance

**Files:**
- Add or replace: `frontend/e2e/batch127-full-platform-adversarial.spec.ts`
- Update: stale `frontend/e2e/batch56-full-platform-real-backend.spec.ts` expectations or retire duplicate coverage
- Add: `work-logs/evidence/batch-127/` inventories/results

- [ ] Generate a route inventory from the router and assert every route has a declared acceptance owner/status.
- [ ] Production project: read-only page/tab/detail checks; no POST/PUT/PATCH/DELETE except existing idempotent read-like endpoints explicitly reviewed.
- [ ] Local project: reversible CRUD for core assets, validation errors, permission and project isolation.
- [ ] Verify console errors, duplicate GETs, empty/error/loading states, titles, a11y names and responsive overflow.
- [ ] Keep production credentials/session out of files and logs.

## Task 9: Documentation and full QA

**Files:**
- Modify: `README.md`
- Modify: `docs/现状功能PRD.md`
- Complete: Batch 127 review, QA report, Leader Verdict, kanban and C conditions

- [ ] Update current route/module/production facts; remove claims contradicted by the deployed product.
- [ ] Run backend `ruff check app/ --select F821`, affected tests, then full `pytest` and record exact failure set.
- [ ] Run frontend `npm run typecheck`, `npm run build`, affected Vitest, full `npm test`, and relevant Playwright runs.
- [ ] Run `scan-common-bugs.ps1`, `audit-cconditions.ps1`, worktree verification and scope review.
- [ ] Product/PM/Design/Dev/QA adversarial review; fix all P0/P1 or mark truly external blockers with conditions.
- [ ] Leader writes final verdict and retro card only after QA evidence is complete.

## Task 10: Deliver through Git gates

- [ ] Commit only Batch 127 scope.
- [ ] Show exact change summary and self-checks, then ask the mandatory two-line “是否还有其他变动” total confirmation.
- [ ] After explicit confirmation, push once, create Draft PR to main and run base audit.
- [ ] Wait for required checks; if any implementation/scope changes, invalidate authorization and reconfirm.
- [ ] Run final audit with successful checks, mark Ready, squash merge to main, and verify main smoke.
