# Batch 53 Obsidian Production UI Implementation Plan

> **For agentic workers:** execute in the isolated Agent Team worktree. Use test-first slices, edit only assigned files, and record exact verification evidence.

> **Execution status (2026-07-28): COMPLETE.** Tasks 1–8 were completed through equivalent scoped changes. The implementation intentionally used the existing page table and Obsidian coarse-pointer contract instead of rewriting the generic DataTable/Checkbox/Pagination components where no shared change was required. Exact results are recorded in the QA report.

**Goal:** Close every P0/P1 item in the Batch 53 issue register and make Obsidian Flow meet the shared 100-point production UI acceptance matrix under populated data.

**Architecture:** Strengthen shared primitives first so accessibility, touch targets, table overflow, pagination and feedback are corrected once. Then adapt the app shell, workbench, testcase and professional workspaces to the same responsive contract. Playwright adds populated fixtures plus one non-mocked backend path; Vitest locks component semantics and request cancellation.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind 3, Radix/shadcn, Vitest, Playwright, Axe, FastAPI local backend.

## Task 1: Lock the production acceptance contract with failing tests

**Files:**
- Create: `frontend/e2e/batch53-production-ui.spec.ts`
- Modify: `frontend/src/components/__tests__/DataTable.a11y.test.tsx`
- Create or modify: `frontend/src/layouts/__tests__/MainLayout.test.tsx`

- [ ] Add populated testcase fixtures with at least 24 rows, long names, every priority/status and visible row actions.
- [ ] Assert 390/768/1440 page overflow, local table scroll, scroll-region accessible name and reachable row actions.
- [ ] Assert every rendered button has an accessible name and Axe returns no violations.
- [ ] Assert coarse-pointer buttons/inputs/checkboxes/pagination have effective 44px hit areas.
- [ ] Add workbench chart title, summary and data-table assertions.
- [ ] Run focused tests and record the expected failures before implementation.

## Task 2: Harden shared interaction primitives

**Files:**
- Modify: `frontend/src/ui/primitives/Button.tsx`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/checkbox.tsx`
- Modify: `frontend/src/components/Pagination.tsx`
- Modify: `frontend/src/components/DataTable.tsx`
- Modify: `frontend/src/ui/themes/obsidian-flow.css`
- Modify: `frontend/src/globals.css`

- [ ] Define a shared coarse-pointer hit-area contract for native/UI/shadcn controls under Obsidian.
- [ ] Keep compact desktop density while ensuring 44px touch targets and visible focus.
- [ ] Give DataTable a named keyboard-focusable local scroll region and mobile edge affordance.
- [ ] Keep sorting `aria-sort`; make pagination wrap predictably and expose full labels.
- [ ] Add component tests for accessible names, scrolling, sorting and touch classes.
- [ ] Run focused Vitest.

## Task 3: Correct app-shell navigation semantics

**Files:**
- Modify: `frontend/src/layouts/MainLayout.tsx`
- Modify: related sidebar/navigation component tests

- [ ] Add `aria-current="page"` to the active destination.
- [ ] Close the mobile drawer after navigation and restore a predictable focus target.
- [ ] Render menu load failure inline with retry, not toast-only.
- [ ] Preserve route-change main-content focus and Escape behavior.
- [ ] Run layout tests and mobile Playwright navigation assertions.

## Task 4: Adapt workbench to production data

**Files:**
- Modify: `frontend/src/pages/workbench/index.tsx`
- Modify: workbench chart/stat child components and tests

- [ ] Remove duplicate KPI presentation; keep one primary metric hierarchy.
- [ ] Make charts use full mobile width with readable axes/legends.
- [ ] Add accessible chart title, key-insight summary and structured data alternative.
- [ ] Preserve loading dimensions; add retry for chart/stat errors.
- [ ] Verify 390/768/1440 screenshots and Axe.

## Task 5: Adapt testcase to dense mobile use

**Files:**
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify: testcase columns/action renderers and tests
- Modify: `frontend/src/hooks/use-api.ts` if cancellation is missing

- [ ] Group filters and actions so the main task remains first at 390px.
- [ ] Give every icon action a concise Chinese `aria-label`.
- [ ] Configure mobile-priority columns and keep row actions discoverable.
- [ ] Ensure search/filter refresh cancels or ignores stale responses.
- [ ] Provide actionable empty/error states.
- [ ] Verify populated-data E2E, one GET per interaction and no stale result.

## Task 6: Remove fixed-size blockers from professional workspaces

**Files:**
- Modify: `frontend/src/pages/knowledge/components/GraphTab.tsx`
- Modify: `frontend/src/pages/knowledge/components/SphereTab.tsx`
- Modify: `frontend/src/pages/release-bundles/VersionPanorama.tsx`
- Modify: `frontend/src/pages/release-bundles/components/InteractionAnnotator.tsx`
- Modify: `frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: their focused tests

- [ ] Replace fixed viewport assumptions with minmax/clamp and explicit local scroll/zoom regions.
- [ ] Prioritize controls and primary content on mobile; move secondary detail into a collapsible/drawer region.
- [ ] Ensure close/back/save actions stay visible and named.
- [ ] Run focused tests and 390/768/1440 overflow checks.

## Task 7: Add one real-backend acceptance path

**Files:**
- Modify: `frontend/e2e/batch53-production-ui.spec.ts`
- Use existing backend test helpers or APIs; avoid committed databases.

- [ ] Start the isolated backend on 8004 and frontend on 5177.
- [ ] Create temporary authenticated test data through supported API/test setup.
- [ ] Exercise at least one core populated flow without intercepting `/api/v1/**`.
- [ ] Assert no unexpected failed requests, duplicate GET, console error or page error.
- [ ] Clean test data through supported API or disposable ignored SQLite workspace.

## Task 8: Full production gate and evidence

**Files:**
- Create: `work-logs/batch-53-obsidian-production-ui-qa-report.md`
- Create: `work-logs/batch-53-obsidian-production-ui-leader-verdict.md`
- Update: issue register status

- [ ] Run `npm run typecheck`.
- [ ] Run `npm run build`.
- [ ] Run full `npm test`.
- [ ] Run Batch 51, Batch 52 and Batch 53 Playwright in visible Chromium.
- [ ] Run repository scans for debug output, secrets, backup/db/temp files and changed async effects without cleanup.
- [ ] Record exact test counts, exits, screenshots, baseline dependency warnings and residual P2/P3.
- [ ] Mark GO only when every P0/P1 acceptance criterion has evidence.
