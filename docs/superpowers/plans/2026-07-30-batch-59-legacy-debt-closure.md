# Batch 59 Legacy Debt Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the repository-local legacy defects and false-green quality signals carried from Batch 50–58, while keeping external environment blockers explicitly open.

**Architecture:** Batch 59 is a closure release, not a feature expansion. The work is split into independent frontend quality, backend atomic-acceptance, responsive browser, and evidence-governance slices. Every closed item must have an executable HTTP/schema/business assertion or browser assertion; external credentials, VPNs, devices, AI providers, ELK, and legacy PostgreSQL snapshots remain blocked instead of being replaced by mocks.

**Tech Stack:** React 19, TypeScript, Vite 7, Vitest 4, Playwright 1.61, ESLint flat config, FastAPI, SQLAlchemy 2, Pytest, GitHub Actions.

## Execution outcome (2026-07-30)

This plan intentionally started broader than the final safe Batch 59 slice. The
implemented and verified scope is the CI/Jenkins truthfulness work, hooks and
request-lifecycle fixes, AddCasesModal regression, tablet/mobile test coverage,
Alembic warning cleanup, PostgreSQL required-gate execution, and atomic evidence
for J02/J04/J10/J12/J17 plus selected J19 assertions.

Final review expanded the delivered slice to include spreadsheet-formula
escaping and execution metadata in report snapshots, persistent Jenkins test
deployment credentials with a real Node 22 controller image, WikiDiff request
deduplication/cancellation, CaseDrawer delayed-domain protection, and an
explicit 135-item ESLint legacy-unused baseline that rejects any regression.

J03/J08/J09/J15/J16 and the remaining real-browser/full-chain portions were not
silently treated as complete. Their exact residual scope is recorded in
`test-platform-v2/work-logs/batch-59-legacy-debt-issue-register.md`. The QA
report is the authoritative record of commands actually executed; unchecked
steps below remain planned work rather than claimed results.

---

## Scope boundary

### Batch 59 closes in-repository

- Frontend CI false greens: a11y, hooks lint, and coverage baseline enforcement.
- `AddCasesModal` stale-filter requests and the audited missing abort propagation.
- J02/J03/J04/J08/J09/J10/J12/J15/J16/J17/J19 repository-local HTTP/schema/business evidence.
- C55-5-P2 tablet `768×1024` and mobile `390×844` full-route browser evidence.
- Batch 56–58 tracker drift, including `G56-015`, `B56-B08`, and cloud-registration evidence status.
- Alembic `path_separator` deprecation warning.

### Batch 59 keeps open

- B56-B01 through B56-B10 wherever closure requires external services, VPN, credentials, devices, ELK, real AI/OCR, design sources, or a legacy PostgreSQL snapshot.
- C58-06 until an actual FastAPI hosting target exists and the Vercel `/api` route is verified against it.
- Vercel public availability and Supabase migration evidence until the corresponding project permissions and runtime connection are available.

## File map

- `.github/workflows/pr-check.yml` — make a11y, lint, and coverage results truthful.
- `.github/workflows/main-quality-gate.yml` — add the repository-owned lint command to the required frontend gate.
- `test-platform-v2/frontend/eslint.config.js` — deterministic TypeScript/React Hooks lint configuration.
- `test-platform-v2/frontend/package.json` and `package-lock.json` — pin lint tooling and expose `lint`, `test:coverage`, and deterministic a11y scripts.
- `test-platform-v2/frontend/vitest.config.ts` — enforce the measured Batch 58 coverage floor instead of an unattained aspirational threshold.
- `test-platform-v2/frontend/src/pages/testplan/AddCasesModal.tsx` — remove stale-closure filter requests and abort superseded loads.
- `test-platform-v2/frontend/src/pages/testplan/__tests__/AddCasesModal.test.tsx` — prove new filter values are used on the first request and superseded requests are aborted.
- Audited API/page files under `frontend/src/pages/` and `frontend/src/api/` — pass `AbortSignal` through existing `useApi`/effect call chains.
- `test-platform-v2/frontend/src/api/__tests__/strict-mode-signals.test.ts` — expand the static contract to every Batch 59-touched initial GET.
- `test-platform-v2/frontend/e2e/batch56-full-platform-real-backend.spec.ts` — add tablet/mobile full-route acceptance using the existing real-backend fixture lifecycle.
- `Jenkinsfile` — align the declared Node runtime, Docker build context, and generated test-deployment secrets with the current repository contract.
- `.github/workflows/main-quality-gate.yml` and `.github/workflows/pr-check.yml` — execute the three opt-in PostgreSQL concurrency regressions against disposable CI PostgreSQL.
- `scripts/ci/test_batch59_quality_contracts.py` — prevent false-green and runtime-contract regressions in CI/Jenkins configuration.
- `test-platform-v2/backend/tests/batch59_factories.py` — reusable isolated factories for projects, users, roles, tokens, cases, plans, reports, defects, and release bundles.
- `test-platform-v2/backend/tests/test_batch59_management_acceptance.py` — J02/J03/J04/J19 atomic API evidence.
- `test-platform-v2/backend/tests/test_batch59_lifecycle_acceptance.py` — J08/J09/J10/J12/J17 atomic API evidence.
- `test-platform-v2/backend/tests/test_batch59_runner_acceptance.py` — J15/J16 compile/runner/media API evidence.
- `test-platform-v2/backend/alembic.ini` — replace deprecated separator configuration.
- `test-platform-v2/work-logs/batch-59-legacy-debt-issue-register.md` — canonical Batch 59 issue decisions and evidence.
- `test-platform-v2/work-logs/batch-59-legacy-debt-qa-report.md` — exact commands, exit codes, pass/fail/skip sets, and residual blockers.
- `C-CONDITIONS.md` and affected Batch 56–58 reports — reconcile statuses to the canonical register.

### Task 1: Replace false-green frontend quality jobs

**Files:**
- Create: `test-platform-v2/frontend/eslint.config.js`
- Modify: `test-platform-v2/frontend/package.json`
- Modify: `test-platform-v2/frontend/package-lock.json`
- Modify: `test-platform-v2/frontend/vitest.config.ts`
- Modify: `.github/workflows/pr-check.yml`
- Modify: `.github/workflows/main-quality-gate.yml`

- [ ] **Step 1: Add the repository-owned hooks lint configuration**

Use a TypeScript parser and only the two high-signal React Hooks rules for this closure batch:

```js
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

export default [
  {
    ignores: ['coverage/**', 'dist/**', 'playwright-report/**', 'test-results/**'],
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      globals: {
        ...globals.browser,
        ...globals.es2024,
        ...globals.node,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
    },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
    },
  },
]
```

- [ ] **Step 2: Pin lint dependencies and scripts**

Add `eslint`, `eslint-plugin-react-hooks`, `globals`, and `typescript-eslint` as dev dependencies through `npm install --save-dev`, then add:

```json
{
  "scripts": {
    "lint": "eslint src",
    "test:coverage": "vitest run --coverage",
    "test:a11y:ci": "playwright test e2e/accessibility.spec.ts e2e/batch54-five-theme-production.spec.ts --project=chromium"
  }
}
```

- [ ] **Step 3: Set a truthful non-regression coverage floor**

Replace the unattained `70/50/60/70` declaration with floors just below the measured Batch 58 main baseline (`27.41/22.31/23.08/28.90`):

```ts
thresholds: {
  statements: 27,
  branches: 22,
  functions: 23,
  lines: 28,
},
```

- [ ] **Step 4: Make CI execute pinned tools without swallowed errors**

The a11y job must install the Playwright Chromium matching the lock file, run Vite preview, and execute `npm run test:a11y:ci`. The frontend check must run `npm run lint` and `npm run test:coverage` without `continue-on-error`, `|| true`, or `|| echo`.

```yaml
- name: Install Playwright Chromium
  working-directory: test-platform-v2/frontend
  run: npx playwright install --with-deps chromium

- name: A11y Scan
  working-directory: test-platform-v2/frontend
  run: |
    npm run preview -- --host 127.0.0.1 --port 4173 &
    PREVIEW_PID=$!
    trap 'kill "$PREVIEW_PID" 2>/dev/null || true' EXIT
    npm run test:a11y:ci

- name: Lint
  working-directory: test-platform-v2/frontend
  run: npm run lint

- name: Unit Tests + Coverage
  working-directory: test-platform-v2/frontend
  run: npm run test:coverage
```

- [ ] **Step 5: Verify the frontend quality commands locally**

Run:

```text
npm ci
npm run lint
npm run typecheck
npm test
npm run test:coverage
npm run build
```

Expected: every command exits `0`; coverage is at or above all four committed floors.

### Task 1B: Restore backend/Jenkins CI runtime truthfulness

**Files:**
- Modify: `Jenkinsfile`
- Modify: `.github/workflows/main-quality-gate.yml`
- Modify: `.github/workflows/pr-check.yml`
- Create: `scripts/ci/test_batch59_quality_contracts.py`

- [ ] **Step 1: Write configuration contract tests**

The test reads the three repository-owned CI files and asserts:

```python
def test_required_ci_executes_postgresql_concurrency_regressions():
    workflow = MAIN_QUALITY_GATE.read_text(encoding="utf-8")
    assert "postgres:16-alpine" in workflow
    assert "BATCH48_RUN_PG_INTEGRATION: '1'" in workflow
    assert "test_batch48_postgresql_concurrency.py" in workflow


def test_jenkins_uses_current_node_and_root_backend_context():
    jenkins = JENKINSFILE.read_text(encoding="utf-8")
    assert "NODE_VERSION   = '22.22.0'" in jenkins
    assert (
        "docker build -t ${BACKEND_IMAGE}:${tag} "
        "-t ${BACKEND_IMAGE}:latest "
        "-f test-platform-v2/backend/Dockerfile ."
    ) in jenkins
```

Also assert the frontend workflow uses `npm run lint`, `npm run test:coverage`, and `npm run test:a11y:ci` without `continue-on-error` in those named steps.

- [ ] **Step 2: Run the contract tests and confirm they fail**

Run:

```text
python -m pytest -q scripts/ci/test_batch59_quality_contracts.py
```

Expected: FAIL on the current Node 18 declaration, backend subdirectory Docker context, absent PostgreSQL integration execution, and swallowed frontend checks.

- [ ] **Step 3: Run PostgreSQL concurrency tests in required CI**

Add a disposable `postgres:16-alpine` service to the required backend job and run the existing three tests with:

```yaml
env:
  BATCH48_RUN_PG_INTEGRATION: '1'
  BATCH48_PG_INTEGRATION_URL: postgresql+psycopg2://cameltv:cameltv_test@localhost:5432/cameltv_test

- name: PostgreSQL concurrency regressions
  working-directory: test-platform-v2/backend
  run: python -m pytest -q tests/test_batch48_postgresql_concurrency.py
```

The extended `backend-check-pg` job uses the same explicit variables and command after migrations. The database is job-local and disposable; the URL is a CI-only non-secret service credential.

- [ ] **Step 4: Align Jenkins with the repository runtime**

Set `NODE_VERSION = '22.22.0'`, fail before frontend installation if the agent runtime is below the `package.json` engine, and build the backend from repository root:

```groovy
sh "docker build -t ${BACKEND_IMAGE}:${tag} -t ${BACKEND_IMAGE}:latest -f test-platform-v2/backend/Dockerfile ."
```

For the test deployment, copy `.env.example` then generate independent hexadecimal `SECRET_KEY`, admin/tester passwords, and `POSTGRES_PASSWORD`; write a URL-safe `DATABASE_URL` using the generated PostgreSQL password. Do not commit or print the generated values.

- [ ] **Step 5: Verify policy contracts**

Run:

```text
python -m pytest -q scripts/ci/test_batch59_quality_contracts.py scripts/ci/test_classify_ci_changes.py
```

Expected: PASS. Local PostgreSQL execution is recorded separately when Docker is available; the required GitHub job remains the authoritative disposable-PostgreSQL run.

### Task 2: Fix stale filters and incomplete request cancellation

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/testplan/AddCasesModal.tsx`
- Create: `test-platform-v2/frontend/src/pages/testplan/__tests__/AddCasesModal.test.tsx`
- Modify: audited page/API files identified by the Batch 59 hooks lint output
- Modify: `test-platform-v2/frontend/src/api/__tests__/strict-mode-signals.test.ts`

- [ ] **Step 1: Write the stale-filter regression test**

The test must open the dialog, select a domain/module, and assert the first subsequent `fetchTestCases` call contains the newly selected values, not the previous React state. It must also capture both request signals and assert the superseded request is aborted.

```ts
expect(fetchTestCases).toHaveBeenLastCalledWith(
  expect.objectContaining({ domain: '直播', module: '开播' }),
  expect.any(AbortSignal),
)
expect(firstSignal.aborted).toBe(true)
expect(latestSignal.aborted).toBe(false)
```

- [ ] **Step 2: Run the test and confirm the current implementation fails**

Run:

```text
npx vitest run src/pages/testplan/__tests__/AddCasesModal.test.tsx
```

Expected: FAIL because `load()` reads the previous `selDomain`/`selModule` closure.

- [ ] **Step 3: Make list loading explicit and abortable**

Use a stable loader that receives the complete filter snapshot and aborts any prior controller:

```ts
type CaseFilters = {
  domain: string
  module: string
  keyword: string
}

const listControllerRef = useRef<AbortController | null>(null)

const load = useCallback(async (page: number, filters: CaseFilters) => {
  listControllerRef.current?.abort()
  const controller = new AbortController()
  listControllerRef.current = controller
  setLoading(true)
  try {
    const params: TestCaseFilter = { page, page_size: 10 }
    if (filters.domain) params.domain = filters.domain
    if (filters.module) params.module = filters.module
    if (filters.keyword) params.keyword = filters.keyword
    const response = await fetchTestCases(params, controller.signal)
    if (!controller.signal.aborted) setData(response)
  } finally {
    if (!controller.signal.aborted) setLoading(false)
  }
}, [])
```

Every domain/module/search/pagination action passes the exact next filter values. The dialog effect aborts both domain and list requests on close/unmount.

- [ ] **Step 4: Expand the existing signal contract**

Add every Batch 59-touched initial GET to `strict-mode-signals.test.ts`. Each API function must accept `signal?: AbortSignal`; each `useApi` callback must pass its received signal; each custom async effect must return a cleanup that aborts or marks the request cancelled.

- [ ] **Step 5: Run lint and focused tests**

Run:

```text
npm run lint
npx vitest run src/pages/testplan/__tests__/AddCasesModal.test.tsx src/api/__tests__/strict-mode-signals.test.ts
```

Expected: PASS, with no ignored exhaustive-deps errors added by Batch 59.

### Task 3: Close J02/J03/J04/J19 management evidence

**Files:**
- Create: `test-platform-v2/backend/tests/batch59_factories.py`
- Create: `test-platform-v2/backend/tests/test_batch59_management_acceptance.py`
- Modify only the exact router/service file exposed by a failing regression.

- [ ] **Step 1: Add isolated data factories**

Factories create project A/project B, three role scopes, users, API tokens, datasets, and integration configs in the per-test in-memory database. Secrets are generated test values and never returned by helper assertions.

- [ ] **Step 2: Add J02 Dashboard positive and negative cases**

Cover:

```python
def test_j02_dashboard_counts_are_project_scoped_and_empty_project_is_zero(...):
    own = client.get("/api/v1/dashboard/stats", headers=project_a_headers)
    empty = client.get("/api/v1/dashboard/stats", headers=empty_project_headers)
    assert own.status_code == 200
    assert empty.status_code == 200
    assert own.json()["data"]["case_count"] == expected_own_cases
    assert empty.json()["data"]["case_count"] == 0
    assert foreign_title not in own.text
```

Also verify cross-project totals are available only to a permitted global user.

- [ ] **Step 3: Add J03 CRUD and revocation cases**

Exercise project, user, role, permission, membership, and token create/detail/update/delete. After removing the project role or member, repeat list/detail/write calls and assert denial plus unchanged database rows.

- [ ] **Step 4: Add J04 dataset/integration cases**

Exercise list/create/detail/update/delete, empty/invalid upload or provider payloads, foreign project IDs, and secret redaction. Assert HTTP status, response envelope/schema, database side effects, and that secret values never occur in response text.

- [ ] **Step 5: Add J19 pagination/count/idempotency matrix**

For each covered list resource, create more rows than `page_size`, verify page boundaries and `total`, repeat the same GET for stable results, and attempt foreign detail/update/delete. For mutation retries, assert the documented behavior explicitly: deterministic duplicate rejection or two distinct records if the API is intentionally non-idempotent.

- [ ] **Step 6: Run the focused suite**

Run:

```text
python -m pytest -q tests/test_batch59_management_acceptance.py
```

Expected: PASS with no skip. Any product defect must first remain as a failing test, then receive the smallest router/service fix.

### Task 4: Close J08/J09/J10/J12/J17 lifecycle evidence

**Files:**
- Create: `test-platform-v2/backend/tests/test_batch59_lifecycle_acceptance.py`
- Modify only failing lifecycle router/service code.

- [ ] **Step 1: Add J08 import/list boundary cases**

Cover invalid Excel/XMind content, duplicate import behavior, server-side keyword/domain/module filters, sorting, page boundaries, and `total`. Assert the failed imports create no case/version/category rows.

- [ ] **Step 2: Add J09 execution concurrency and retry cases**

Create a plan/case chain, submit the same execution action twice, verify the persisted states and audit events match the documented semantics, and cover cancel/retry where the API exposes them. A concurrent or duplicate action must not silently overwrite a newer terminal result.

- [ ] **Step 3: Add J10 report endpoint cases**

Cover create/detail/list/export/delete, empty plan, failed execution aggregation, valid template, foreign template, and missing template. Assert CSV/XLSX content type, same-source counts, and deletion side effects.

- [ ] **Step 4: Add J12 defect state-machine cases**

Exercise the complete legal chain and at least one illegal/repeated transition:

```python
for next_status in ("confirmed", "fixing", "resolved", "verified", "closed"):
    response = client.post(
        f"/api/v1/defects/{defect_id}/transition",
        json={"status": next_status, "comment": f"Batch59 -> {next_status}"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == next_status

illegal = client.post(
    f"/api/v1/defects/{defect_id}/transition",
    json={"status": "fixing"},
    headers=headers,
)
assert illegal.json()["code"] != 0
```

Verify history order, stats counts, audit rows, and foreign-project denial.

- [ ] **Step 5: Add J17 release-bundle cases**

Cover create/list/detail/update/delete, cross-project isolation, version chain, incomplete relation data, regression scope, and repeated publish/regression trigger semantics. Aggregated requirement/case/execution/defect/report counts must all come from the same project/bundle graph.

- [ ] **Step 6: Run the focused suite**

Run:

```text
python -m pytest -q tests/test_batch59_lifecycle_acceptance.py
```

Expected: PASS with no skip and no external network.

### Task 5: Close J15/J16 runner and media evidence

**Files:**
- Create: `test-platform-v2/backend/tests/test_batch59_runner_acceptance.py`
- Modify only failing compiler/executor/AV code.

- [ ] **Step 1: Add J15 compile-to-Playwright chain**

Generate TypeScript from a repository-local deterministic page, compile it, execute the generated spec with the pinned Playwright runtime, and assert the persisted run points to a real report/trace/screenshot path. Add negative cases for a compile error, missing element, timeout, cancellation, and foreign artifact access.

- [ ] **Step 2: Add J16 AV API positive and negative cases**

Use the repository media fixtures, create an AV task, add/update/delete measurements, trigger supported analysis, and verify response schemas and persisted metrics. Add invalid/corrupt/too-short media and foreign-project task/measurement cases. A failed measurement must persist a failed state and must not create fabricated metrics.

- [ ] **Step 3: Run the focused suite**

Run:

```text
python -m pytest -q tests/test_batch59_runner_acceptance.py
```

Expected: repository-local cases pass with no skip. Physical-device/SoloX scenarios remain explicitly blocked.

### Task 6: Close C55-5-P2 tablet/mobile full-route evidence

**Files:**
- Modify: `test-platform-v2/frontend/e2e/batch56-full-platform-real-backend.spec.ts`

- [ ] **Step 1: Generalize the viewport type**

```ts
type AcceptanceViewport = 'desktop' | 'tablet' | 'mobile'

const viewportSizes: Record<AcceptanceViewport, { width: number; height: number }> = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
}
```

Use all static and valid dynamic routes for tablet/mobile; do not retain the historical twelve-route mobile subset.

- [ ] **Step 2: Preserve responsive navigation semantics**

Treat `390×844` as the mobile drawer layout and `768×1024` according to the rendered breakpoint. For every route assert: expected path/content, visible main region, no page-level horizontal overflow, keyboard focus, Axe serious/critical zero, clean console/page/request errors, and no duplicate effective GET.

- [ ] **Step 3: Add required-input tablet/mobile cases**

```ts
test('P2 tablet 768x1024 真实登录全路由生产矩阵', async ({ page }, testInfo) => {
  test.setTimeout(660_000)
  await runAcceptanceViewport(page, testInfo, 'tablet', {
    theme: 'obsidian-flow',
    mode: 'dark',
  })
})

test('P2 mobile 390x844 真实登录全路由生产矩阵', async ({ page }, testInfo) => {
  test.setTimeout(660_000)
  await runAcceptanceViewport(page, testInfo, 'mobile', {
    theme: 'obsidian-flow',
    mode: 'dark',
  })
})
```

Missing `E2E_USERNAME`/`E2E_PASSWORD` must fail this required-input suite, never skip.

- [ ] **Step 4: Run against the Batch 59 local runtime**

Run backend on port `8006`, frontend on port `5179`, and execute:

```text
$env:BASE_URL='http://127.0.0.1:5179'
$env:E2E_USERNAME='<local seeded admin username>'
$env:E2E_PASSWORD='<local ignored env password>'
npx playwright test e2e/batch56-full-platform-real-backend.spec.ts --project=chromium --grep 'P2 tablet|P2 mobile'
```

Expected: 2/2 pass, no skip. Credentials remain in ignored local environment only.

### Task 7: Reconcile warnings and the canonical issue register

**Files:**
- Modify: `test-platform-v2/backend/alembic.ini`
- Create: `test-platform-v2/work-logs/batch-59-legacy-debt-issue-register.md`
- Create: `test-platform-v2/work-logs/batch-59-legacy-debt-qa-report.md`
- Modify: `C-CONDITIONS.md`
- Modify: affected Batch 56–58 reports whose current status conflicts with the canonical register.

- [ ] **Step 1: Remove the Alembic separator deprecation**

Replace:

```ini
version_path_separator = os
```

with:

```ini
path_separator = os
```

Run `python -m alembic heads` and the migration tests; expect one head and no separator warning.

- [ ] **Step 2: Establish the canonical Batch 59 issue table**

For every candidate record: source Batch/ID, severity, pre-Batch-59 status, Batch-59 decision (`CLOSED`, `PARTIAL`, `BLOCKED`, `WAIVED`), exact test/evidence, owner boundary, and next closure condition.

- [ ] **Step 3: Reconcile known drift**

- Move `G56-015` to `CLOSED-WITH-NOTICE` with the Batch 57 111/111 Linux lock evidence.
- Keep `B56-B08` as `WAIVED`, never `PASS`.
- Close C55-5-P2 only after the 2/2 real-backend viewport run passes.
- Change C58-01/C58-03/C58-04/C58-05 to evidence-accurate states; registration claims without reproducible repository evidence cannot be `PASS`.
- Keep C58-06 open until a real backend URL replaces the example target and a health/API request succeeds.
- Record the Vercel deployment-protection observation as external follow-up, not a repository code success.

- [ ] **Step 4: Record exact QA results**

The QA report contains every command, exit code, collected/passed/failed/skipped count, coverage percentages, CI scope classification, runtime blockers, and changed-file risk. Never write only “historical issue”.

### Task 8: Full verification and delivery checkpoint

**Files:**
- All Batch 59 changed files.

- [ ] **Step 1: Run backend hard gates and focused suites**

```text
ruff check app/ --select F821
python -m pytest -q tests/test_batch59_management_acceptance.py tests/test_batch59_lifecycle_acceptance.py tests/test_batch59_runner_acceptance.py
python -m pytest -q
```

- [ ] **Step 2: Run frontend hard gates**

```text
npm run lint
npm run typecheck
npm test
npm run test:coverage
npm run build
```

- [ ] **Step 3: Run repository policy checks**

```text
python scripts/ci/classify_ci_changes.py --base origin/main --head HEAD
python -m pytest -q scripts/ci/test_classify_ci_changes.py scripts/ci/test_batch59_quality_contracts.py
git diff --check origin/main...HEAD
pwsh scripts/git/verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex
```

- [ ] **Step 4: Commit in reviewable slices**

Use focused commits such as:

```text
fix(frontend): enforce truthful Batch 59 quality gates
fix(frontend): close stale request and responsive debt
test(backend): close Batch 59 management evidence gaps
test(backend): close Batch 59 lifecycle evidence gaps
docs(qa): reconcile Batch 50-58 legacy issue status
```

- [ ] **Step 5: Stop at the mandatory push gate**

Before every push, show the exact branch, target, file list, commit range, test commands, exit codes, failure/skip sets, and risk. Ask verbatim:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

Do not push or create a PR until the user explicitly says there are no other changes and authorizes that exact push.

## Self-review

- Spec coverage: the plan maps every repository-local Batch 50–58 candidate to a task or explicitly keeps it external-blocked.
- Placeholder scan: implementation steps contain concrete paths, commands, assertions, and status rules; runtime secrets are intentionally represented as local ignored environment inputs.
- Type consistency: `AcceptanceViewport`, request filter snapshots, and the three Batch 59 Pytest modules have one stable naming contract throughout the plan.
