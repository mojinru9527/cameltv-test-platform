# Guest Browse, Project Onboarding, and Case Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let guests inspect every platform module without exposing business data, guide authenticated users without projects into project creation without request spam, and deterministically reclassify legacy cases out of “其他”.

**Architecture:** `MainLayout` remains the single access boundary. Guests render static route-aware previews and only open the existing login dialog from explicit use actions; authenticated users with no selected project render a project onboarding empty state before any project-scoped Outlet mounts. The backend becomes the single source for case `surface`, using a repository-backed legacy-domain map shared by list and taxonomy responses; the mindmap consumes the returned field.

**Tech Stack:** React 18, TypeScript, React Router, Zustand, shadcn/Radix/Tailwind, Vitest/Testing Library, FastAPI, Pydantic, SQLAlchemy, Pytest.

---

### Task 1: Lock guest navigation behavior with failing tests

**Files:**
- Modify: `test-platform-v2/frontend/src/layouts/__tests__/GuestPlatformHome.test.tsx`
- Create: `test-platform-v2/frontend/src/layouts/__tests__/GuestModulePreview.test.tsx`
- Create: `test-platform-v2/frontend/src/layouts/guestModuleCatalog.test.ts`

- [ ] **Step 1: Change the homepage test from login-on-module-click to browse-on-module-click**

Render with an `onNavigate` spy, click “用例脑图”, and assert `onNavigate('/mindmap')`; separately click “登录并开始使用” and assert `onRequireLogin('/workbench', '工作台')`.

- [ ] **Step 2: Add catalog coverage tests**

Use the current public menu paths (`/workbench`, `/trace`, `/requirement`, `/release-bundles`, `/knowledge`, `/mindmap`, `/testcase`, `/testplan`, `/apitest`, `/uitest`, `/playground`, `/special`, `/schedule`, `/report`, `/system`, `/project`, `/my-projects`, `/organizations`, `/defect`, `/dataset`, `/integration`, `/notify`, `/environment`, `/agent-workbench`, `/perftest`, `/lanhu-evidence`) and assert every path resolves a non-empty title, description, and at least three capabilities.

- [ ] **Step 3: Add preview interaction tests**

Assert the page renders the selected module, does not call login on mount, opens login only from “登录后使用”, and shows `/register` only when registration is enabled.

- [ ] **Step 4: Run tests and verify RED**

Run: `npm test -- --run src/layouts/__tests__/GuestPlatformHome.test.tsx src/layouts/__tests__/GuestModulePreview.test.tsx src/layouts/guestModuleCatalog.test.ts`  
Expected: FAIL because preview/catalog and the new navigation contract do not exist.

### Task 2: Implement guest module previews

**Files:**
- Create: `test-platform-v2/frontend/src/layouts/guestModuleCatalog.ts`
- Create: `test-platform-v2/frontend/src/layouts/GuestModulePreview.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/GuestPlatformHome.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Add a typed catalog and resolver**

Define:

```ts
export interface GuestModuleDefinition {
  title: string
  description: string
  capabilities: readonly { title: string; description: string }[]
}

export function resolveGuestModule(pathname: string, search = ''): GuestModuleDefinition
```

Provide explicit entries for every current public route and a safe fallback based on the menu label; do not import business APIs.

- [ ] **Step 2: Render the static preview**

`GuestModulePreview` receives `module`, `registrationEnabled`, and `onRequireLogin`; render PageHeader-like hierarchy, capability cards, a lock boundary note, “登录后使用 {title}”, and optional “免费注册”.

- [ ] **Step 3: Separate browse from use in MainLayout**

Remove the effect that opens login for every direct guest route. Make sidebar/home navigation call `navigate(path)` for guests. Render `GuestPlatformHome` only at `/`; render `GuestModulePreview` for all other guest paths. Keep `loginTarget` exclusively for explicit use actions.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `npm test -- --run src/layouts/__tests__/GuestPlatformHome.test.tsx src/layouts/__tests__/GuestModulePreview.test.tsx src/layouts/guestModuleCatalog.test.ts`  
Expected: all focused tests PASS.

### Task 3: Lock the no-project boundary with failing tests

**Files:**
- Create: `test-platform-v2/frontend/src/layouts/__tests__/ProjectRequiredState.test.tsx`
- Create or Modify: `test-platform-v2/frontend/src/layouts/__tests__/MainLayout.test.tsx`

- [ ] **Step 1: Add empty-state tests**

Assert a user with no projects sees “先创建一个项目”, a “创建第一个项目” link/button to `/my-projects`, and the three-step onboarding copy.

- [ ] **Step 2: Add Outlet suppression tests**

Render `MainLayout` on `/testcase` with authenticated state and `currentProjectId=null`; use a route child probe and assert it never mounts. Render `/my-projects` and assert the child probe mounts. Repeat `/organizations`.

- [ ] **Step 3: Run tests and verify RED**

Run: `npm test -- --run src/layouts/__tests__/ProjectRequiredState.test.tsx src/layouts/__tests__/MainLayout.test.tsx`  
Expected: FAIL because authenticated no-project users still mount Outlet.

### Task 4: Implement the layout-level no-project state

**Files:**
- Create: `test-platform-v2/frontend/src/layouts/ProjectRequiredState.tsx`
- Modify: `test-platform-v2/frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Add the empty-state component**

Use semantic Card/Button components. Accept `canCreateProject` and `onOpenProjects`; show creation copy when permission includes `project:self_create`, `project:create`, or `*`, otherwise show “联系管理员加入项目”.

- [ ] **Step 2: Add the route boundary**

Define only these project-independent prefixes:

```ts
const PROJECT_SETUP_PATHS = ['/my-projects', '/organizations'] as const
const needsProject = !PROJECT_SETUP_PATHS.some(
  (path) => location.pathname === path || location.pathname.startsWith(`${path}/`),
)
```

If authenticated, `currentProjectId == null`, and `needsProject`, render `ProjectRequiredState` instead of `ProjectScopeBoundary > Outlet`.

- [ ] **Step 3: Run focused tests and verify GREEN**

Run the Task 3 command. Expected: all tests PASS and the child probe mount count is zero for project-scoped routes.

### Task 5: Lock all 31 legacy domains with failing backend tests

**Files:**
- Modify: `test-platform-v2/backend/tests/test_testcase.py`

- [ ] **Step 1: Add parameterized classifier tests**

Assert these user domains map to `用户端`: `个人中心`, `赛事详情`, `直播间`, `APP端数据与排行榜`, `资讯`, `首页`, `PC端`, `搜索`, `登录注册`, `启动引导`, `支付与账户`, `UGC内容`, `WEB端`, `骆驼币系统`, `广告系统`, `银钻系统`, `UGC功能`, `银钻预测`, `付费活动`.

Assert these admin domains map to `运营后台`: `财务管理`, `UGC管理`, `商城管理`, `消息管理`, `赛事预测`, `广告管理`, `活动管理`, `银钻任务管理`, `风控管理`, `装扮管理`, `系统管理`, `球队及联赛管理`.

- [ ] **Step 2: Add list/taxonomy consistency test**

Insert one legacy user case and one legacy admin case, request `/test-cases` and `/test-cases/taxonomy`, and assert list item `surface` matches its taxonomy parent. Assert API case type still wins and unknown manual domain remains `其他`.

- [ ] **Step 3: Run tests and verify RED**

Run: `pytest tests/test_testcase.py::TestCaseTaxonomy -q`  
Expected: FAIL on legacy domain mappings and missing `surface` in list responses.

### Task 6: Implement one backend surface source and regenerate contract

**Files:**
- Modify: `test-platform-v2/backend/app/services/test_case_service.py`
- Modify: `test-platform-v2/backend/app/schemas/test_case.py`
- Modify: `test-platform-v2/frontend/src/types/api.d.ts`

- [ ] **Step 1: Add exact normalized legacy sets**

Add immutable user/admin domain sets from Task 5. Classification order is: canonical API/interface → explicit admin markers → explicit user markers → exact legacy admin set → exact legacy user set → `其他`.

- [ ] **Step 2: Return surface from every TestCaseOut**

Add `surface: str = "其他"` to `TestCaseOut` and set `"surface": classify_case_surface(r.domain, r.case_type)` inside `_row_to_dict`. Keep taxonomy calling the same classifier.

- [ ] **Step 3: Run focused backend tests and verify GREEN**

Run Task 5 command. Expected: all taxonomy tests PASS.

- [ ] **Step 4: Regenerate API types with the locked package script**

Run the repository's existing OpenAPI type generation command from `frontend/package.json`; assert `TestCaseOut.surface` appears in `src/types/api.d.ts` and no unrelated generator-version drift occurs.

### Task 7: Make the mindmap consume backend surface

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/mindmap/caseTaxonomy.ts`
- Modify: `test-platform-v2/frontend/src/pages/mindmap/caseTaxonomy.test.ts`
- Modify: `test-platform-v2/frontend/src/pages/mindmap/index.tsx`

- [ ] **Step 1: Write failing frontend tests**

Build cases with `surface` already assigned and assert the markdown groups them without inspecting legacy domain text. Add `availableCaseSurfaces` tests that omit `其他` when absent and include it after an unknown item is present.

- [ ] **Step 2: Implement the response-driven grouping**

Replace domain-text classification with:

```ts
const SURFACE_ORDER = ['用户端', '运营后台', '接口测试', '其他'] as const
const surface = SURFACE_ORDER.includes(testCase.surface as CaseSurface)
  ? testCase.surface as CaseSurface
  : '其他'
```

Use the same value for filtering and Markdown grouping. Generate Select options from actual cases in `SURFACE_ORDER` order.

- [ ] **Step 3: Run mindmap tests and verify GREEN**

Run: `npm test -- --run src/pages/mindmap/caseTaxonomy.test.ts`  
Expected: PASS.

### Task 8: Run quality gates and browser acceptance

**Files:**
- Create: `test-platform-v2/work-logs/evidence/batch-129-guest-browse-project-taxonomy/README.md`
- Create: screenshots and network manifests under the same evidence directory
- Create: `test-platform-v2/work-logs/batch-129-guest-browse-project-taxonomy-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-129-guest-browse-project-taxonomy-leader-verdict.md`
- Modify: `test-platform-v2/work-logs/kanbans/DEV-batch-129-guest-browse-project-taxonomy.md`

- [ ] **Step 1: Run frontend gates**

Run `npm ci`, focused Vitest, `npm test -- --run`, `npm run typecheck`, and `npm run build`; record commands, exit codes, and totals.

- [ ] **Step 2: Run backend gates**

Run app import, `ruff check app --select F821`, focused Pytest, full `pytest`, Alembic single-head and revision-length checks; record commands, exit codes, and totals.

- [ ] **Step 3: Run repository audits**

Run `scan-common-bugs.ps1`, `audit-cconditions.ps1 -RequireLatestBatch`, secret/debug scans, worktree verification, and changed-file review.

- [ ] **Step 4: Browser acceptance**

Start isolated services on 5192/8022. At 1440×900, 768×1024, and 390×844 verify: guest root → several representative module previews → login CTA/dialog → register link; authenticated zero-project route → creation prompt → `/my-projects`; populated project → testcase/mindmap surfaces. Capture console and Network evidence proving zero protected requests before login/project selection.

- [ ] **Step 5: Finish QA and Leader artifacts**

QA begins NEEDS WORK and moves to PASS only with executable evidence. Leader remains non-approved until the user's one total confirmation, required checks, and final audit are complete.

