# Batch 56 Full-Platform Production Acceptance Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with Agent Team. Production verdicts must use real customer-derived inputs and real application services; mock-only evidence never closes a release gate.

**Goal:** Validate and harden every test-platform-v2 module to a production-deliverable standard, expose the latest UI at `http://localhost:5173/`, and produce an A01–A12 verdict backed by realistic customer inputs, real React → FastAPI → PostgreSQL journeys, and authorized external-environment evidence.

**Architecture:** Run the local acceptance stack in the isolated Batch 56 worktree on Vite `5173`, FastAPI `8000`, and a dedicated PostgreSQL database. Use repository customer/requirements artifacts as source-preserving R1 inputs, authorized live pages and contracts as R0 inputs, and schema-faithful R2 data only for boundary, concurrency, and pagination expansion. All primary browser journeys call the real backend. External production systems are read-only; controlled writes occur only in explicitly authorized test environments and must be cleaned up and verified.

**Tech stack:** React 18, Vite 7, TypeScript, Vitest, Playwright, Axe, FastAPI, SQLAlchemy 2, PostgreSQL 16, Pytest, Alembic, Docker/PowerShell, GitHub Actions.

---

## Non-negotiable release rules

- [ ] Work only in `F:\CamelTv-worktrees\codex-batch-56-full-platform-production-acceptance` on `feature/batch-56-full-platform-production-acceptance`.
- [ ] Keep `origin/main@206802431d487a517f3c6d8901143825e11f0ea7` as the Batch 56 starting baseline.
- [ ] Use `http://localhost:5173/` and `http://127.0.0.1:8000`; do not substitute other acceptance ports.
- [ ] Classify every acceptance input as R0, R1, R2, or M:
  - R0: authorized live customer input or environment;
  - R1: redacted, source-preserving snapshot with provenance and SHA-256;
  - R2: schema-faithful generated boundary/load data;
  - M: mock/stub/fault-injection data.
- [ ] Every P0/P1 primary journey requires R0 or R1. R2/M results are reported separately and never count toward the real-acceptance pass rate.
- [ ] The main acceptance chain must use a real browser, real FastAPI routes, real background workers, and PostgreSQL. Do not use `page.route`, `route.fulfill`, MSW, Axios mocks, monkeypatch, or direct database insertion to manufacture a passing primary journey.
- [ ] Direct DB queries are allowed only for post-action state, transaction, audit, count, and cleanup verification.
- [ ] M-class tests may cover timeouts, 5xx, rate limits, corrupt attachments, notification failures, loading/empty/error UI, time, or randomness only after the corresponding real main flow exists.
- [ ] Production sports sites and APIs are GET/HEAD-only. No production login attempts, writes, payment, publishing, load testing, or request replay.
- [ ] Test/admin writes require an explicitly authorized test environment, a unique `B56-<timestamp>-` prefix, state readback, and verified cleanup in `finally`.
- [ ] Missing VPN, credentials, PostgreSQL, AI/Blue Lake/ELK access, legacy DB snapshot, or live requirement URL is `BLOCKED`; it is never converted to `PASS` or a passing skip.
- [ ] `BATCH56_ACCEPTANCE_REQUIRED=1` makes missing required inputs/services fail the executable suite or remain explicitly blocked in the release verdict.

## Task 1: Freeze baselines and the real-input manifest

**Files:**

- Create: `test-platform-v2/work-logs/batch-56-real-input-manifest.md`
- Create: `tests/test-cases/functional/BATCH56-测试平台全功能生产级验收.md`
- Create: `test-platform-v2/work-logs/batch-56-production-acceptance-issue-register.md`
- Create: `test-platform-v2/work-logs/evidence/batch-56-production-acceptance/README.md`

- [ ] Record code SHA, branch, worktree, ports, workflow/executor, browser versions, PostgreSQL version, and external-access restrictions.
- [ ] Hash all repository R1 inputs and map each input to modules and use cases.
- [ ] Register R0 inputs from the environment/account summary without copying credentials, cookies, tokens, query parameters, or private content.
- [ ] Establish the complete frontend route list and backend router/module list from code, not from stale prose.
- [ ] Map Batch 47/48 production acceptance, C55-3/C55-4/C55-5, Batch 54 UI gaps, npm observations, and CI annotations into the issue register.
- [ ] Create the A01–A12 matrix before executing feature tests.
- [ ] Commit the baseline documents before product fixes.

## Task 2: Provision the real local acceptance environment

**Files:**

- Modify only if necessary: ignored `test-platform-v2/backend/.env`
- Modify only if necessary: ignored `test-platform-v2/frontend/.env.local`
- Create if needed: `test-platform-v2/deploy/docker-compose.acceptance.yml`
- Create if needed: `test-platform-v2/backend/tests/support/batch56_acceptance.py`

- [ ] Provision an isolated PostgreSQL 16 database and record host/port/database identifier without credentials.
- [ ] Run `alembic upgrade head`, `alembic current`, `alembic heads`, and `alembic check`.
- [ ] Create strong local admin/tester credentials in ignored environment files before the first seed.
- [ ] Start FastAPI on `127.0.0.1:8000` and verify `/health`, `/api/v1/open/health`, and `/docs`.
- [ ] Start Vite on `localhost:5173` and verify `/login`, `/apitest`, and an authenticated protected route.
- [ ] Confirm every effective GET occurs once under React Strict Mode for the initial shell.
- [ ] Provide a deterministic cleanup command that removes only `B56-*` acceptance entities.

## Task 3: Build deterministic real-backend acceptance coverage

**Files:**

- Create: `test-platform-v2/backend/tests/test_batch56_platform_acceptance.py`
- Create: `test-platform-v2/backend/tests/test_batch56_postgresql_acceptance.py`
- Create as gaps require: focused tests under `test-platform-v2/backend/tests/`

- [ ] Use public service/API paths to build one connected customer chain:
  1. import a real customer-derived requirement document;
  2. parse/review it;
  3. generate or import cases;
  4. create and execute a plan;
  5. generate a report;
  6. verify trace coverage;
  7. create and transition a defect;
  8. verify audit and notifications;
  9. clean the chain and verify deletion.
- [ ] Cover every backend domain: auth, RBAC/system, projects, requirements, test cases, plans/executions, reports, schedules, defects, trace, open API, notifications, environments, datasets, integrations, API test, UI test, performance, knowledge, Wiki, Agent, release bundles/version panorama, and supported special-test behavior.
- [ ] For every write endpoint, assert request validation, business rules, response envelope, DB state, audit/background side effects, and rollback.
- [ ] Create Project A/Project B and admin/tester/limited identities; verify list, detail, subresource, mutation, count, search, and error responses do not leak across projects.
- [ ] Run PostgreSQL multi-connection concurrency for uniqueness, idempotency, repeated execution, cancellation, retries, imports, links, and queue claims.
- [ ] Generate R2 datasets only from R1 constraints to exceed one page; verify search/filter/sort/page/total/count across UI/API/DB.
- [ ] Treat simulated/random special-test metrics as non-production capability and report them honestly.

## Task 4: Build real-browser customer journeys without route mocks

**Files:**

- Create: `test-platform-v2/frontend/e2e/batch56-real-customer-journeys.spec.ts`
- Create: `test-platform-v2/frontend/e2e/batch56-all-routes-themes.spec.ts`
- Create: `test-platform-v2/frontend/e2e/batch56-external-readonly.spec.ts`
- Modify product/UI files only when a failing production acceptance case proves a defect.

- [ ] Login through the visible form with environment-injected admin and tester credentials.
- [ ] Execute the connected requirement → case → plan → execution → report → trace → defect journey through visible UI and real APIs.
- [ ] Execute schedule, API-test, UI-test, knowledge/Wiki/Agent, dataset, environment, integration, notification, project/RBAC, release-bundle, and performance journeys using realistic customer-derived values.
- [ ] Visit all static routes plus valid dynamic route instances; assert meaningful page landmarks and content, not HTTP 200 alone.
- [ ] For each critical action, verify UI state, HTTP/JSON contract, DB/audit state, background task completion, refresh persistence, and cleanup.
- [ ] Capture `console.error`, `pageerror`, `requestfailed`, duplicate effective GETs, and unexpected non-GET requests.
- [ ] Verify keyboard equivalents, visible focus, dialog focus trapping/restoration, labels/names, and Axe serious/critical violations.
- [ ] Run `1440×900`, `768×1024`, and `390×844`; check global and component overflow and full operability.

## Task 5: Validate all six themes and supported modes

**Files:**

- Modify: `test-platform-v2/frontend/e2e/batch56-all-routes-themes.spec.ts`
- Modify theme/component files only for reproduced defects.

- [ ] Source theme IDs from the canonical registry; do not hardcode a stale five-theme list.
- [ ] Cover cyberpunk, apple, clay, xlab, liquid-glass, and obsidian-flow.
- [ ] Cover supported light/dark behavior and document theme-specific mode constraints.
- [ ] On every route, verify heading, navigation, primary action, tables/forms/dialogs, focus ring, contrast, overflow, and screenshot.
- [ ] Detect transparent/unreadable text, clipped controls, fixed-width mobile failures, missing empty/error/loading states, and theme-token bypasses.
- [ ] Store screenshots/traces only in ignored temporary evidence locations; commit only redacted evidence indexes and selected safe artifacts.

## Task 6: Execute authorized external comparisons

**Files:**

- Modify: `test-platform-v2/frontend/e2e/batch56-external-readonly.spec.ts`
- Modify: `test-platform-v2/work-logs/batch-56-real-input-manifest.md`
- Modify: `test-platform-v2/work-logs/evidence/batch-56-production-acceptance/README.md`

- [ ] Production user sites: safe GET/HEAD, visible core content, locale/mirror behavior, console/request failures, and response timing only.
- [ ] Sports test sites: real login/read flows; write flows only when current authorization explicitly permits and cleanup is proven.
- [ ] Admin test site: follow the documented test login rule and default to read-only; never change shared configuration or trigger broadcast/task actions without explicit authorization.
- [ ] User/admin requirement sources: read, compare, and capture redacted evidence; do not comment, edit, upload, or change shared document state.
- [ ] Test OpenAPI/Swagger: pull the live contract where reachable and compare it to the repository R1 snapshot.
- [ ] Keep production and test results separate; test success cannot imply production write readiness.

## Task 7: Fix proven defects in production-risk order

- [ ] Stop the affected flow and preserve redacted evidence for data loss, cross-project leakage, transaction inconsistency, or unsafe external writes.
- [ ] Assign defect IDs in the Batch 56 issue register.
- [ ] Write a failing behavior test before each fix.
- [ ] Make the smallest root-cause fix.
- [ ] Re-run the failing case, connected customer journey, affected module suite, and both full gates.
- [ ] Do not change a test expectation to fit incorrect product behavior.
- [ ] Re-run all previously failed, blocked, and not-run P0/P1 cases after environment or code changes.

## Task 8: Execute A10/A11 release gates

- [ ] Upgrade an isolated, redacted real legacy PostgreSQL snapshot; an empty DB remains only a migration-contract check.
- [ ] Verify row counts, constraints, indexes, relationships, application reads, repeat upgrade, unique head, and zero metadata drift.
- [ ] Run:

```powershell
Set-Location test-platform-v2/backend
ruff check app/ --select F821
python -m pytest tests/test_batch56_platform_acceptance.py -q
$env:BATCH56_ACCEPTANCE_REQUIRED = '1'
python -m pytest tests/test_batch56_postgresql_acceptance.py -q
python -m pytest -q
```

```powershell
Set-Location test-platform-v2/frontend
npm run typecheck
npm test
npm run build
$env:BATCH56_ACCEPTANCE_REQUIRED = '1'
$env:BASE_URL = 'http://localhost:5173'
npx playwright test e2e/batch56-real-customer-journeys.spec.ts --project=chromium
npx playwright test e2e/batch56-all-routes-themes.spec.ts --project=chromium
```

- [ ] Run production and full dependency audits; record exact advisories and never silently force a breaking major upgrade.
- [ ] Scan added lines and evidence for credentials, tokens, cookies, private data, debug artifacts, databases, reports, and local metadata.

## Task 9: Produce the objective verdict

**Files:**

- Create: `test-platform-v2/work-logs/batch-56-production-acceptance-qa-report.md`
- Create: `test-platform-v2/work-logs/batch-56-production-acceptance-leader-verdict.md`
- Modify: `C-CONDITIONS.md`
- Modify: all Batch 56 evidence/index documents.

- [ ] Report real acceptance separately: R0/R1 pass, fail, blocked, and not run.
- [ ] Report simulated regression separately: R2/M pass and fail.
- [ ] Derive READY/CONDITIONAL/NEEDS WORK mechanically from P0/P1 and A01–A12.
- [ ] Keep missing external access, live AI/Blue Lake/ELK, legacy DB, or production admin access visible as blockers.
- [ ] Reconcile code, PRD, OpenAPI, README, C conditions, tests, QA, Leader Verdict, and evidence.
- [ ] Run full local gates and the worktree verifier before the mandatory per-push user confirmation.
- [ ] Push only after showing the exact changed-file/test/risk scope and receiving explicit one-push authorization.
