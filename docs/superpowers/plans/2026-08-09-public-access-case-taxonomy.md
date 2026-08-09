# Public Access and Case Taxonomy Implementation Plan

> **For agentic workers:** Execute inline in this Codex session with TDD checkpoints; do not push before the Agent Team total confirmation.

**Goal:** Let guests discover platform modules and authenticate at the point of use, enable ordinary registration, and present test cases/mindmaps by type and user/admin hierarchy.

**Architecture:** Keep all business APIs protected. Add one anonymous metadata endpoint for safe menu/registration facts, gate the authenticated Outlet inside MainLayout, and reuse one login form in page/dialog contexts. Add a backward-compatible `/test-cases/taxonomy` endpoint that derives surface grouping from existing fields without a database migration.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React 18, TypeScript, Zustand, React Router, Radix/shadcn, Vitest, Pytest, Playwright.

---

### Task 1: Public metadata and registration defaults

**Files:**
- Modify: `test-platform-v2/backend/app/core/config.py`
- Modify: `test-platform-v2/backend/app/schemas/auth.py`
- Modify: `test-platform-v2/backend/app/api/v1/auth.py`
- Modify: `test-platform-v2/backend/app/services/menu_service.py`
- Modify: `test-platform-v2/backend/tests/test_register.py`
- Create: `test-platform-v2/backend/tests/test_public_access.py`
- Modify: `test-platform-v2/config/runtime/production.env.example`
- Modify: `test-platform-v2/deploy/production-enablement-checklist.md`

- [ ] Write failing tests asserting `Settings(environment="production")` enables registration and does not require a platform invite by default.
- [ ] Write a failing anonymous `GET /api/v1/auth/public-access` test asserting registration facts and menu metadata, with no user/project/permission fields.
- [ ] Run `pytest tests/test_register.py tests/test_public_access.py -q`; expect failures for old defaults/missing endpoint.
- [ ] Implement `PublicModuleOut/PublicAccessOut`, `menu_tree(db, ["*"])` reuse, and the public route.
- [ ] Update production examples and copy from invite-only to normal registration while preserving explicit overrides.
- [ ] Re-run the focused tests; expect pass.
- [ ] Commit only Task 1 files.

### Task 2: Guest shell and shared login

**Files:**
- Create: `test-platform-v2/frontend/src/components/auth/LoginForm.tsx`
- Create: `test-platform-v2/frontend/src/components/auth/GuestAccessDialog.tsx`
- Create: `test-platform-v2/frontend/src/components/auth/PublicPlatformOverview.tsx`
- Create: `test-platform-v2/frontend/src/components/auth/GuestAccessDialog.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/login/index.tsx`
- Modify: `test-platform-v2/frontend/src/router/index.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`
- Modify: `test-platform-v2/frontend/src/api/auth.ts`

- [ ] Write a failing dialog test: target module name is announced, login success navigates to target, free registration opens `/register`.
- [ ] Write a failing MainLayout guest test or extracted state test proving protected Outlet is absent and guest module activation opens the dialog.
- [ ] Run the focused Vitest files; expect failures.
- [ ] Extract the current login form with an `onSuccess` callback; keep API/store behavior unchanged.
- [ ] Remove the root-level RequireAuth wrapper and make MainLayout render either guest overview or authenticated Outlet.
- [ ] Fetch exactly one menu source per auth state using AbortSignal; guest clicks set the requested path and open Dialog.
- [ ] Re-run focused tests and `npm run typecheck`.
- [ ] Commit only Task 2 files.

### Task 3: Ordinary registration page

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/register/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/register/__tests__/RegisterPage.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/login/index.tsx`

- [ ] Change tests so a valid form without invite submits `invite_code: ""` and succeeds.
- [ ] Add a test for `invite_code_required=true` public metadata causing a field error when empty.
- [ ] Add a project-invite regression test without a platform invite.
- [ ] Run RegisterPage tests; expect old invite-required assertions to fail.
- [ ] Implement dynamic optional/required copy and validation; add return-to-platform and normal registration copy.
- [ ] Re-run focused tests and commit.

### Task 4: Backend case taxonomy

**Files:**
- Modify: `test-platform-v2/backend/app/schemas/test_case.py`
- Modify: `test-platform-v2/backend/app/services/test_case_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/test_case.py`
- Modify: `test-platform-v2/backend/tests/test_testcase.py`
- Create: `test-platform-v2/backend/tests/test_case_taxonomy.py`

- [ ] Add failing unit cases for exact `用户端/运营后台`, sports domains, API type precedence, and unknown→其他.
- [ ] Add failing API tests for `/test-cases/taxonomy?case_type=manual` and `surface=运营后台` list filtering.
- [ ] Run focused Pytest and confirm failures.
- [ ] Implement a small deterministic classifier and grouped taxonomy; reuse `case_type_values` for legacy functional.
- [ ] Register `/taxonomy` before `/{case_id}` and thread `surface` through list filters.
- [ ] Re-run focused tests and commit.

### Task 5: Test case service hierarchy and type tabs

**Files:**
- Modify: `test-platform-v2/frontend/src/api/testcase.ts`
- Create: `test-platform-v2/frontend/src/pages/testcase/caseTaxonomy.ts`
- Create: `test-platform-v2/frontend/src/pages/testcase/__tests__/caseTaxonomy.test.ts`
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.test.tsx`

- [ ] Write failing pure tests transforming surface/domain/full module paths into stable nested keys and parsing leaf selection.
- [ ] Add failing page assertions for four type tabs and default manual request.
- [ ] Run focused Vitest and confirm failures.
- [ ] Implement `fetchCaseTaxonomy(case_type)` and surface/domain/module filter state.
- [ ] Render the desktop tree at three+ levels and mobile Selects; reset dependent filters correctly.
- [ ] Verify one list GET and one taxonomy GET per committed filter change.
- [ ] Re-run tests/typecheck and commit.

### Task 6: Mindmap hierarchy

**Files:**
- Create: `test-platform-v2/frontend/src/pages/mindmap/mindmapMarkdown.ts`
- Create: `test-platform-v2/frontend/src/pages/mindmap/mindmapMarkdown.test.ts`
- Modify: `test-platform-v2/frontend/src/pages/mindmap/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/mindmap/index.test.tsx`

- [ ] Write failing Markdown tests for user/admin roots and slash-delimited module paths.
- [ ] Add failing UI tests for default manual and surface/type request parameters.
- [ ] Run focused tests and confirm failures.
- [ ] Implement pure Markdown generation and two filters while preserving markmap cleanup/fullscreen behavior.
- [ ] Re-run all mindmap tests and commit.

### Task 7: QA, browser evidence, and delivery artifacts

**Files:**
- Create: `test-platform-v2/work-logs/batch-128-public-access-case-taxonomy-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-128-public-access-case-taxonomy-leader-verdict.md`
- Update: `test-platform-v2/work-logs/kanbans/DEV-batch-128-public-access-case-taxonomy.md`
- Update if closed: `C-CONDITIONS.md` for C122-4 evidence.

- [ ] Run backend app import, F821, focused and full Pytest, Alembic unique head/revision checks.
- [ ] Run frontend focused and full Vitest, typecheck, production build.
- [ ] Start isolated local services on 8021/5191; test guest `/`, direct `/testcase`, dialog login, ordinary registration, project creation, type tabs, taxonomy, and mindmap at 1440/768/390.
- [ ] Capture console/network evidence proving zero protected business GETs before login and no duplicate GETs after login.
- [ ] Run `scan-common-bugs.ps1` and `audit-cconditions.ps1 -RequireLatestBatch`; resolve HARD findings.
- [ ] Complete QA and conditional Leader artifacts, then request the one total confirmation covering push, Draft PR, checks, and merge.
